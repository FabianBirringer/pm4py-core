from pm4py.log.util import trace_log as tl_util
from pm4py.algo.dfg.versions import native as dfg_inst
from pm4py.algo.inductive.data_structures.dfg_graph import DfgGraph as DfgGraph
from pm4py.models import petri
from pm4py.models.petri.petrinet import Marking
from collections import Counter
import time
from copy import deepcopy, copy
import math
import sys
from pm4py.models.petri.petrinet import PetriNet

sys.setrecursionlimit(100000)

def apply(trace_log, parameters, activity_key='concept:name'):
    indMinDirFollows = InductMinDirFollows()
    return indMinDirFollows.apply_log(trace_log, parameters, activity_key=activity_key)

class Counts(object):
    def __init__(self):
        self.noOfPlaces = 0
        self.noOfHiddenTransitions = 0
        self.dictSkips = {}
        self.dictLoops = {}

    def inc_places(self):
        self.noOfPlaces = self.noOfPlaces + 1

    def inc_noOfHidden(self):
        self.noOfHiddenTransitions = self.noOfHiddenTransitions + 1

class Subtree(object):
    def __init__(self, dfg, initialDfg, activities, counts, recDepth):
        self.dfg = copy(dfg)
        self.initialDfg = copy(initialDfg)
        self.counts = counts
        self.recDepth = recDepth
        if activities is None:
            self.activities = self.get_activities_from_dfg(self.dfg)
        else:
            self.activities = copy(activities)
        self.outgoing = self.get_outgoing_edges(self.dfg)
        self.ingoing = self.get_ingoing_edges(self.dfg)
        self.selfLoopActivities = self.get_activities_self_loop()
        self.initialOutgoing = self.get_outgoing_edges(self.initialDfg)
        self.initialIngoing = self.get_ingoing_edges(self.initialDfg)
        self.activitiesDirection = self.get_activities_direction()
        self.activitiesDirlist = self.get_activities_dirlist()
        self.negatedDfg = self.negate()
        self.negatedActivities = self.get_activities_from_dfg(self.negatedDfg)
        self.negatedOutgoing = self.get_outgoing_edges(self.negatedDfg)
        self.negatedIngoing = self.get_ingoing_edges(self.negatedDfg)

        self.detectedCut = None
        self.children = []

        self.detect_cut()

    def negate(self):
        negatedDfg = []
        for el in self.dfg:
            if not(el[0][1] in self.outgoing and el[0][0] in self.outgoing[el[0][1]]):
                negatedDfg.append(el)
        return negatedDfg

    def get_activities_from_dfg(self, dfg):
        set_activities = set()
        for el in dfg:
            set_activities.add(el[0][0])
            set_activities.add(el[0][1])
        list_activities = sorted(list(set_activities))

        return list_activities

    def get_outgoing_edges(self, dfg):
        outgoing = {}
        for el in dfg:
            if not el[0][0] in outgoing:
                outgoing[el[0][0]] = {}
            outgoing[el[0][0]][el[0][1]] = el[1]
        return outgoing

    def get_ingoing_edges(self, dfg):
        ingoing = {}
        for el in dfg:
            if not el[0][1] in ingoing:
                ingoing[el[0][1]] = {}
            ingoing[el[0][1]][el[0][0]] = el[1]
        return ingoing

    def get_activities_self_loop(self):
        self_loop_act = []
        for act in self.outgoing:
            if act in list(self.outgoing[act].keys()):
                self_loop_act.append(act)
        return self_loop_act

    def get_activities_direction(self):
        direction = {}
        for act in self.activities:
            outgoing = 0
            ingoing = 0
            if act in self.outgoing:
                outgoing = sum(list(self.outgoing[act].values()))
            if act in self.ingoing:
                ingoing = sum(list(self.ingoing[act].values()))
            dependency = (outgoing - ingoing)/(ingoing + outgoing + 1)
            direction[act] = dependency
        return direction

    def get_activities_dirlist(self):
        dirlist = []
        for act in self.activitiesDirection:
            dirlist.append([act, self.activitiesDirection[act]])
        dirlist = sorted(dirlist, key=lambda x: (x[1], x[0]), reverse=True)
        return dirlist

    def determine_best_set_sequential(self, act, set1, set2):
        hasOutgoingConnInSet1 = False
        if act[0] in self.outgoing:
            for act2 in self.outgoing[act[0]]:
                if act2 in set1:
                    hasOutgoingConnInSet1 = True
        hasIngoingConnInSet2 = False
        if act[0] in self.ingoing:
            for act2 in self.ingoing[act[0]]:
                if act2 in set2:
                    hasIngoingConnInSet2 = True

        if hasOutgoingConnInSet1 and hasIngoingConnInSet2:
            return [False, set1, set2]

        if hasOutgoingConnInSet1:
            set1.add(act[0])
        elif hasIngoingConnInSet2:
            set2.add(act[0])
        else:
            set2.add(act[0])

        return [True, set1, set2]

    def detect_sequential_cut(self, dfg):
        set1 = set()
        set2 = set()

        if len(self.activitiesDirlist) > 0:
            set1.add(self.activitiesDirlist[0][0])
        if len(self.activitiesDirlist) > -1:
            if not (self.activitiesDirlist[0][0] in self.ingoing and self.activitiesDirlist[-1][0] in self.ingoing[self.activitiesDirlist[0][0]]):
                set2.add(self.activitiesDirlist[-1][0])
            else:
                return [False, [], []]
        i = 1
        while i < len(self.activitiesDirlist)-1:
            act = self.activitiesDirlist[i]
            ret, set1, set2 = self.determine_best_set_sequential(act, set1, set2)
            if ret is False:
                return [False, [], []]
            i = i + 1

        if len(set1) > 0 and len(set2) > 0:
            if not set1 == set2:
                return [True, list(set1), list(set2)]
        return [False, [], []]

    def get_connected_components(self, ingoing, outgoing, activities):
        connectedComponents = []

        for act in ingoing:
            ingoing_act = set(ingoing[act].keys())
            if act in outgoing:
                ingoing_act = ingoing_act.union(set(outgoing[act].keys()))

            ingoing_act.add(act)

            if not ingoing_act in connectedComponents:
                connectedComponents.append(ingoing_act)

        for act in outgoing:
            if not act in ingoing:
                outgoing_act = set(outgoing[act].keys())
                outgoing_act.add(act)
                if not outgoing_act in connectedComponents:
                    connectedComponents.append(outgoing_act)

        something_changed = True
        it = 0
        while something_changed:
            it = it + 1
            something_changed = False

            oldConnectedComponents = copy(connectedComponents)
            connectedComponents = 0
            connectedComponents = []

            i = 0
            while i < len(oldConnectedComponents):
                conn1 = oldConnectedComponents[i]
                j = i + 1
                while j < len(oldConnectedComponents):
                    conn2 = oldConnectedComponents[j]
                    inte = conn1.intersection(conn2)

                    if len(inte) > 0:
                        conn1 = conn1.union(conn2)
                        something_changed = True
                        del oldConnectedComponents[j]
                        continue
                    j = j + 1

                if not conn1 in connectedComponents:
                    connectedComponents.append(conn1)
                i = i + 1

        if len(connectedComponents) == 0:
            for activity in activities:
                connectedComponents.append([activity])

        return connectedComponents

    def checkParCut(self, conn_components):
        i = 0
        while i < len(conn_components):
            conn1 = conn_components[i]
            j = i + 1
            while j < len(conn_components):
                conn2 = conn_components[j]

                for act1 in conn1:
                    for act2 in conn2:
                        if not((act1 in self.outgoing and act2 in self.outgoing[act1]) and (act1 in self.ingoing and act2 in self.ingoing[act1])):
                            return False
                j = j + 1
            i = i + 1
        return True

    def detect_concurrent_cut(self):
        if len(self.dfg) > 0:
            conn_components = self.get_connected_components(self.ingoing, self.outgoing, self.activities)

            if len(conn_components) > 1:
                return [True, conn_components]

        return [False, []]

    def detect_parallel_cut(self):
        conn_components = self.get_connected_components(self.negatedIngoing, self.negatedOutgoing, self.activities)

        if len(conn_components) > 1:
            if self.checkParCut(conn_components):
                return [True, conn_components]

        return [False, []]

    def detect_loop_cut(self, dfg):
        LOOP_CONST_1 = 0.2
        LOOP_CONST_2 = 0.02
        LOOP_CONST_3 = -0.2

        if len(self.activitiesDirlist) > 1:
            set1 = set()
            set2 = set()

            if self.activitiesDirlist[0][1] > LOOP_CONST_1:
                if self.activitiesDirlist[0][0] in self.ingoing:
                    activInput = list(self.ingoing[self.activitiesDirlist[0][0]])
                    for act in activInput:
                        if not act == self.activitiesDirlist[0][0] and self.activitiesDirection[act] < LOOP_CONST_2:
                            set2.add(act)

            if len(set2) > 0:
                for act in self.activities:
                    if not act in set2 or act in set1:
                        if self.activitiesDirection[act] < LOOP_CONST_3:
                            set2.add(act)
                        else:
                            set1.add(act)
                if len(set1) > 0:
                    if not set1 == set2:
                        return [True, set1, set2]

        return [False, [], []]

    def detect_cut(self):
        if self.dfg:
            parCut = self.detect_parallel_cut()
            concCut = self.detect_concurrent_cut()
            seqCut = self.detect_sequential_cut(self.dfg)
            loopCut = self.detect_loop_cut(self.dfg)

            if parCut[0]:
                for comp in parCut[1]:
                    newDfg = self.filter_dfg_on_act(self.dfg, comp)
                    self.detectedCut = "parallel"
                    self.children.append(Subtree(newDfg, newDfg, comp, self.counts, self.recDepth + 1))
            else:
                if concCut[0]:
                    for comp in concCut[1]:
                        newDfg = self.filter_dfg_on_act(self.dfg, comp)
                        self.detectedCut = "concurrent"
                        self.children.append(Subtree(newDfg, newDfg, comp, self.counts, self.recDepth + 1))
                else:
                    if seqCut[0]:
                        dfg1 = self.filter_dfg_on_act(self.dfg, seqCut[1])
                        dfg2 = self.filter_dfg_on_act(self.dfg, seqCut[2])
                        self.detectedCut = "sequential"
                        self.children.append(Subtree(dfg1, self.initialDfg, seqCut[1], self.counts, self.recDepth+1))
                        self.children.append(Subtree(dfg2, self.initialDfg, seqCut[2], self.counts, self.recDepth+1))
                    else:
                        if loopCut[0]:
                            dfg1 = self.filter_dfg_on_act(self.dfg, loopCut[1])
                            dfg2 = self.filter_dfg_on_act(self.dfg, loopCut[2])
                            self.detectedCut = "loopCut"
                            self.children.append(Subtree(dfg1, self.initialDfg, loopCut[1], self.counts, self.recDepth+1))
                            self.children.append(Subtree(dfg2, self.initialDfg, loopCut[2], self.counts, self.recDepth + 1))
                        else:
                            self.detectedCut = "flower"
        else:
            self.detectedCut = "base_concurrent"

    def filter_dfg_on_act(self, dfg, listact):
        newDfg = []
        for el in dfg:
            if el[0][0] in listact and el[0][1] in listact:
                newDfg.append(el)
        return newDfg

    def get_new_place(self):
        self.counts.inc_places()
        return petri.petrinet.PetriNet.Place('p_' + str(self.counts.noOfPlaces))

    def get_new_hidden_trans(self, type="tau"):
        self.counts.inc_noOfHidden()
        return petri.petrinet.PetriNet.Transition(type+'_' + str(self.counts.noOfHiddenTransitions), None)

    def get_transition(self, label):
        return petri.petrinet.PetriNet.Transition(label, label)

    def getMaxValue(self, dfg):
        ingoing = self.get_ingoing_edges(dfg)
        outgoing = self.get_outgoing_edges(dfg)
        max_value = -1

        for act in ingoing:
            sum = 0
            for act2 in ingoing[act]:
                sum += ingoing[act][act2]
            if sum > max_value:
                max_value = sum

        for act in outgoing:
            sum = 0
            for act2 in outgoing[act]:
                sum += outgoing[act][act2]
            if sum > max_value:
                max_value = sum

        return max_value

    def verify_skip_transition_necessity(self, mAddSkip, initialDfg, dfg, childrenDfg):
        if mAddSkip:
            return True
        maxValueInitial = self.getMaxValue(initialDfg)
        maxValueDfg = self.getMaxValue(dfg)
        maxValueChildrenDfg = self.getMaxValue(childrenDfg)
        if maxValueChildrenDfg > -1 and maxValueChildrenDfg < maxValueInitial:
            return True
        if maxValueDfg > -1 and maxValueDfg < maxValueInitial:
            return True
        return False

    def form_petrinet(self, net, initial_marking, final_marking, must_add_initial_place=False, must_add_final_place=False, initial_connect_to=None, final_connect_to=None, must_add_skip=False, must_add_loop=False):
        #print(self.recDepth, self.activities, self.detectedCut, initial_connect_to, final_connect_to)
        lastAddedPlace = None
        initialPlace = None
        finalPlace = None
        if self.recDepth == 0:
            source = self.get_new_place()
            source.name = "source"
            initial_connect_to = source
            initialPlace = source
            net.places.add(source)
            sink = self.get_new_place()
            final_connect_to = sink
            net.places.add(sink)
            lastAddedPlace = sink
        elif self.recDepth > 0:
            if must_add_initial_place or type(initial_connect_to) is PetriNet.Transition:
                initialPlace = self.get_new_place()
                net.places.add(initialPlace)
                petri.utils.add_arc_from_to(initial_connect_to, initialPlace, net)
            else:
                initialPlace = initial_connect_to
            if must_add_final_place or type(final_connect_to) is PetriNet.Transition:
                finalPlace = self.get_new_place()
                net.places.add(finalPlace)
                petri.utils.add_arc_from_to(finalPlace, final_connect_to, net)
            else:
                finalPlace = final_connect_to
            if self.counts.noOfPlaces == 2 and len(self.activities) > 1:
                initialTrans = self.get_new_hidden_trans(type="tau")
                net.transitions.add(initialTrans)
                newPlace = self.get_new_place()
                net.places.add(newPlace)
                petri.utils.add_arc_from_to(initial_connect_to, initialTrans, net)
                petri.utils.add_arc_from_to(initialTrans, newPlace, net)
            if self.detectedCut == "base_concurrent" or self.detectedCut == "flower":
                if final_connect_to is None or type(final_connect_to) is PetriNet.Transition:
                    if finalPlace is not None:
                        lastAddedPlace = finalPlace
                    else:
                        lastAddedPlace = self.get_new_place()
                        net.places.add(lastAddedPlace)
                else:
                    lastAddedPlace = final_connect_to

                for act in self.activities:
                    trans = self.get_transition(act)
                    net.transitions.add(trans)
                    petri.utils.add_arc_from_to(initialPlace, trans, net)
                    petri.utils.add_arc_from_to(trans, lastAddedPlace, net)
        # iterate over childs
        if self.detectedCut == "sequential" or self.detectedCut == "loopCut":

            mAddSkip = False
            mAddLoop = False
            if self.detectedCut == "loopCut":
                mAddSkip = True
                mAddLoop = True

            net, initial_marking, final_marking, lastAddedPlace = self.children[0].form_petrinet(net, initial_marking,
                                                                                      final_marking,
                                                                                      initial_connect_to=initialPlace, must_add_skip=self.verify_skip_transition_necessity(mAddSkip, self.initialDfg, self.dfg, self.children[0].dfg), must_add_loop=mAddLoop)
            net, initial_marking, final_marking, lastAddedPlace = self.children[1].form_petrinet(net, initial_marking,
                                                                                      final_marking,
                                                                                        initial_connect_to=lastAddedPlace,
                                                                                      final_connect_to=finalPlace, must_add_skip=self.verify_skip_transition_necessity(mAddSkip, self.initialDfg, self.dfg, self.children[1].dfg), must_add_loop=mAddLoop)
        elif self.detectedCut == "parallel":
            mAddSkip = False
            mAddLoop = False

            if finalPlace is None:
                finalPlace = self.get_new_place()
                net.places.add(finalPlace)

            parallelSplit = self.get_new_hidden_trans("tauSplit")
            net.transitions.add(parallelSplit)
            petri.utils.add_arc_from_to(initialPlace, parallelSplit, net)

            parallelJoin = self.get_new_hidden_trans("tauJoin")
            net.transitions.add(parallelJoin)
            petri.utils.add_arc_from_to(parallelJoin, finalPlace, net)

            for child in self.children:
                net, initial_marking, final_marking, lastAddedPlace = child.form_petrinet(net, initial_marking,
                                                                                          final_marking,
                                                                                        must_add_initial_place=True, must_add_final_place=True,
                                                                                          initial_connect_to=parallelSplit, final_connect_to=parallelJoin, must_add_skip=self.verify_skip_transition_necessity(mAddSkip, self.initialDfg, self.dfg, child.dfg), must_add_loop=mAddLoop)

            lastAddedPlace = finalPlace

        elif self.detectedCut == "concurrent":
            mAddSkip = False
            mAddLoop = False

            if finalPlace is None:
                finalPlace = self.get_new_place()
                net.places.add(finalPlace)

            for child in self.children:
                net, initial_marking, final_marking, lastAddedPlace = child.form_petrinet(net, initial_marking,
                                                                                          final_marking,
                                                                                          initial_connect_to=initialPlace, final_connect_to=finalPlace, must_add_skip=self.verify_skip_transition_necessity(mAddSkip, self.initialDfg, self.dfg, child.dfg), must_add_loop=mAddLoop)

            lastAddedPlace = finalPlace

        if self.detectedCut == "flower" or self.detectedCut == "sequential" or self.detectedCut == "loopCut" or self.detectedCut == "base_concurrent" or self.detectedCut == "parallel" or self.detectedCut == "concurrent":
            if self.detectedCut == "flower" or must_add_skip:
                skipTrans = self.get_new_hidden_trans(type="skip")
                net.transitions.add(skipTrans)
                petri.utils.add_arc_from_to(initialPlace, skipTrans, net)
                petri.utils.add_arc_from_to(skipTrans, lastAddedPlace, net)

                if not initialPlace.name in self.counts.dictSkips:
                    self.counts.dictSkips[initialPlace.name] = []

                self.counts.dictSkips[initialPlace.name].append(skipTrans.name)

                #print(self.counts.dictSkips)



            if self.detectedCut == "flower" or must_add_loop:
                loopTrans = self.get_new_hidden_trans(type="loop")
                net.transitions.add(loopTrans)
                petri.utils.add_arc_from_to(lastAddedPlace, loopTrans, net)
                petri.utils.add_arc_from_to(loopTrans, initialPlace, net)

        if self.recDepth == 0:
            if len(sink.out_arcs) == 0 and len(sink.in_arcs) == 0:
                net.places.remove(sink)
                sink = lastAddedPlace

            if len(sink.out_arcs) > 0:
                newSink = self.get_new_place()
                net.places.add(newSink)
                newHidden = self.get_new_hidden_trans(type="tau")
                net.transitions.add(newHidden)
                petri.utils.add_arc_from_to(sink, newHidden, net)
                petri.utils.add_arc_from_to(newHidden, newSink, net)
                sink = newSink

            sink.name = "sink"
            initial_marking[source] = 1
            final_marking[sink] = 1

        return net, initial_marking, final_marking, lastAddedPlace

class InductMinDirFollows(object):
    def apply_log(self, trace_log, parameters, activity_key="concept:name"):
        self.trace_log = trace_log
        labels = tl_util.get_event_labels(trace_log, activity_key)
        dfg = [(k, v) for k, v in dfg_inst.apply(trace_log, activity_key=activity_key).items() if v > 0]
        return self.apply_dfg(dfg, parameters)

    def apply_dfg(self, dfg, parameters):
        c = Counts()
        s = Subtree(dfg, dfg, None, c, 0)
        net = petri.petrinet.PetriNet('imdf_net_' + str(time.time()))
        initial_marking = Marking()
        final_marking = Marking()
        net, initial_marking, final_marking, lastAddedPlace = s.form_petrinet(net, initial_marking, final_marking)

        return net, initial_marking, final_marking