from datetime import datetime
from enum import Enum
from typing import Union, Optional, Dict, Any, Tuple

import pandas as pd
import pytz

from pm4py.util import exec_utils, constants, xes_constants
from pm4py.util.vers_checker import check_pandas_ge_024


class Parameters(Enum):
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    TIMESTAMP_KEY = constants.PARAMETER_CONSTANT_TIMESTAMP_KEY
    START_TIMESTAMP_KEY = constants.PARAMETER_CONSTANT_START_TIMESTAMP_KEY
    RESOURCE_KEY = constants.PARAMETER_CONSTANT_RESOURCE_KEY
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY


def get_dt_from_string(dt: Union[datetime, str]) -> datetime:
    """
    If the date is expressed as string, do the conversion to a datetime.datetime object

    Parameters
    -----------
    dt
        Date (string or datetime.datetime)

    Returns
    -----------
    dt
        Datetime object
    """
    if type(dt) is str:
        dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")

    needs_conversion = check_pandas_ge_024()
    if needs_conversion:
        dt = dt.replace(tzinfo=pytz.utc)
        dt = pd.to_datetime(dt, utc=True)

    return dt


def distinct_activities(df: pd.DataFrame, t1: Union[datetime, str], t2: Union[datetime, str], r: str,
                        parameters: Optional[Dict[str, Any]] = None) -> int:
    """
    Number of distinct activities done by a resource in a given time interval [t1, t2)

    Metric RBI 1.1 in Pika, Anastasiia, et al.
    "Mining resource profiles from event logs." ACM Transactions on Management Information Systems (TMIS) 8.1 (2017): 1-30.

    Parameters
    -----------------
    df
        Dataframe
    t1
        Left interval
    t2
        Right interval
    r
        Resource

    Returns
    -----------------
    distinct_activities
        Distinct activities
    """
    if parameters is None:
        parameters = {}

    activity_key = exec_utils.get_param_value(Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY)
    timestamp_key = exec_utils.get_param_value(Parameters.TIMESTAMP_KEY, parameters,
                                               xes_constants.DEFAULT_TIMESTAMP_KEY)
    resource_key = exec_utils.get_param_value(Parameters.RESOURCE_KEY, parameters, xes_constants.DEFAULT_RESOURCE_KEY)

    t1 = get_dt_from_string(t1)
    t2 = get_dt_from_string(t2)

    df = df[[activity_key, timestamp_key, resource_key]]
    df = df[df[resource_key] == r]
    df = df[df[timestamp_key] >= t1]
    df = df[df[timestamp_key] < t2]

    return df[activity_key].nunique()


def activity_frequency(df: pd.DataFrame, t1: Union[datetime, str], t2: Union[datetime, str], r: str, a: str,
                       parameters: Optional[Dict[str, Any]] = None) -> float:
    """
    Fraction of completions of a given activity a, by a given resource r, during a given time slot, [t1, t2),
    with respect to the total number of activity completions by resource r during [t1, t2)

    Metric RBI 1.3 in Pika, Anastasiia, et al.
    "Mining resource profiles from event logs." ACM Transactions on Management Information Systems (TMIS) 8.1 (2017): 1-30.

    Parameters
    -----------------
    df
        Dataframe
    t1
        Left interval
    t2
        Right interval
    r
        Resource
    a
        Activity

    Returns
    ----------------
    metric
        Value of the metric
    """
    if parameters is None:
        parameters = {}

    activity_key = exec_utils.get_param_value(Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY)
    timestamp_key = exec_utils.get_param_value(Parameters.TIMESTAMP_KEY, parameters,
                                               xes_constants.DEFAULT_TIMESTAMP_KEY)
    resource_key = exec_utils.get_param_value(Parameters.RESOURCE_KEY, parameters, xes_constants.DEFAULT_RESOURCE_KEY)

    t1 = get_dt_from_string(t1)
    t2 = get_dt_from_string(t2)

    df = df[[activity_key, timestamp_key, resource_key]]
    df = df[df[resource_key] == r]
    df = df[df[timestamp_key] >= t1]
    df = df[df[timestamp_key] < t2]

    total = len(df)

    df = df[df[activity_key] == a]

    activity_a = len(df)

    return float(activity_a) / float(total) if total > 0 else 0.0


def activity_completions(df: pd.DataFrame, t1: Union[datetime, str], t2: Union[datetime, str], r: str,
                         parameters: Optional[Dict[str, Any]] = None) -> int:
    """
    The number of activity instances completed by a given resource during a given time slot.

    Metric RBI 2.1 in Pika, Anastasiia, et al.
    "Mining resource profiles from event logs." ACM Transactions on Management Information Systems (TMIS) 8.1 (2017): 1-30.

    Parameters
    -----------------
    df
        Dataframe
    t1
        Left interval
    t2
        Right interval
    r
        Resource

    Returns
    ----------------
    metric
        Value of the metric
    """
    if parameters is None:
        parameters = {}

    timestamp_key = exec_utils.get_param_value(Parameters.TIMESTAMP_KEY, parameters,
                                               xes_constants.DEFAULT_TIMESTAMP_KEY)
    resource_key = exec_utils.get_param_value(Parameters.RESOURCE_KEY, parameters, xes_constants.DEFAULT_RESOURCE_KEY)

    t1 = get_dt_from_string(t1)
    t2 = get_dt_from_string(t2)

    df = df[[timestamp_key, resource_key]]
    df = df[df[resource_key] == r]
    df = df[df[timestamp_key] >= t1]
    df = df[df[timestamp_key] < t2]

    total = len(df)

    return total


def case_completions(df: pd.DataFrame, t1: Union[datetime, str], t2: Union[datetime, str], r: str,
                     parameters: Optional[Dict[str, Any]] = None) -> int:
    """
    The number of cases completed during a given time slot in which a given resource was involved.

    Metric RBI 2.2 in Pika, Anastasiia, et al.
    "Mining resource profiles from event logs." ACM Transactions on Management Information Systems (TMIS) 8.1 (2017): 1-30.

    Parameters
    -----------------
    df
        Dataframe
    t1
        Left interval
    t2
        Right interval
    r
        Resource

    Returns
    ----------------
    metric
        Value of the metric
    """
    if parameters is None:
        parameters = {}

    timestamp_key = exec_utils.get_param_value(Parameters.TIMESTAMP_KEY, parameters,
                                               xes_constants.DEFAULT_TIMESTAMP_KEY)
    resource_key = exec_utils.get_param_value(Parameters.RESOURCE_KEY, parameters, xes_constants.DEFAULT_RESOURCE_KEY)
    case_id_key = exec_utils.get_param_value(Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME)

    t1 = get_dt_from_string(t1)
    t2 = get_dt_from_string(t2)

    df = df[[timestamp_key, resource_key, case_id_key]]

    res_df = df[df[resource_key] == r]
    cases_res = set(res_df[case_id_key])

    last_df = df.groupby(case_id_key).last().reset_index()
    last_df = last_df[last_df[timestamp_key] >= t1]
    last_df = last_df[last_df[timestamp_key] < t2]
    cases_last = set(last_df[case_id_key])

    return len(cases_last.intersection(cases_res))


def fraction_case_completions(df: pd.DataFrame, t1: Union[datetime, str], t2: Union[datetime, str], r: str,
                              parameters: Optional[Dict[str, Any]] = None) -> float:
    """
    The fraction of cases completed during a given time slot in which a given resource was involved with respect to the
    total number of cases completed during the time slot.

    Metric RBI 2.3 in Pika, Anastasiia, et al.
    "Mining resource profiles from event logs." ACM Transactions on Management Information Systems (TMIS) 8.1 (2017): 1-30.

    Parameters
    -----------------
    df
        Dataframe
    t1
        Left interval
    t2
        Right interval
    r
        Resource

    Returns
    ----------------
    metric
        Value of the metric
    """
    if parameters is None:
        parameters = {}

    timestamp_key = exec_utils.get_param_value(Parameters.TIMESTAMP_KEY, parameters,
                                               xes_constants.DEFAULT_TIMESTAMP_KEY)
    resource_key = exec_utils.get_param_value(Parameters.RESOURCE_KEY, parameters, xes_constants.DEFAULT_RESOURCE_KEY)
    case_id_key = exec_utils.get_param_value(Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME)

    t1 = get_dt_from_string(t1)
    t2 = get_dt_from_string(t2)

    df = df[[timestamp_key, resource_key, case_id_key]]

    res_df = df[df[resource_key] == r]
    cases_res = set(res_df[case_id_key])

    last_df = df.groupby(case_id_key).last().reset_index()
    last_df = last_df[last_df[timestamp_key] >= t1]
    last_df = last_df[last_df[timestamp_key] < t2]
    cases_last = set(last_df[case_id_key])

    q1 = float(len(cases_last.intersection(cases_res)))
    q2 = float(len(cases_last))

    return q1 / q2 if q2 > 0 else 0.0


def __insert_start_from_previous_event(df: pd.DataFrame, parameters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Inserts the start timestamp of an event set to the completion of the previous event in the case

    Parameters
    ---------------
    df
        Dataframe

    Returns
    ---------------
    df
        Dataframe with the start timestamp for each event
    """
    if parameters is None:
        parameters = {}

    timestamp_key = exec_utils.get_param_value(Parameters.TIMESTAMP_KEY, parameters,
                                               xes_constants.DEFAULT_TIMESTAMP_KEY)
    resource_key = exec_utils.get_param_value(Parameters.RESOURCE_KEY, parameters, xes_constants.DEFAULT_RESOURCE_KEY)
    case_id_key = exec_utils.get_param_value(Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME)
    activity_key = exec_utils.get_param_value(Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY)
    start_timestamp_key = exec_utils.get_param_value(Parameters.START_TIMESTAMP_KEY, parameters,
                                                     xes_constants.DEFAULT_START_TIMESTAMP_KEY)

    from pm4py.util import pandas_utils

    df = df[[timestamp_key, resource_key, case_id_key, activity_key]]

    df = pandas_utils.insert_index(df)
    df = df.sort_values([case_id_key, timestamp_key, constants.DEFAULT_INDEX_KEY])

    shifted_df = df[[case_id_key, timestamp_key]].shift(1)
    shifted_df.columns = [x + "_2" for x in shifted_df.columns]

    concat_df = pd.concat([df, shifted_df], axis=1)
    concat_df = concat_df[concat_df[case_id_key] == concat_df[case_id_key + "_2"]][
        [constants.DEFAULT_INDEX_KEY, timestamp_key + "_2"]]

    del shifted_df
    concat_df = concat_df.to_dict("r")
    concat_df = {x[constants.DEFAULT_INDEX_KEY]: x[timestamp_key + "_2"] for x in concat_df}

    df[start_timestamp_key] = df[constants.DEFAULT_INDEX_KEY].map(concat_df)
    df[start_timestamp_key] = df[start_timestamp_key].fillna(df[timestamp_key])
    df = df.sort_values([start_timestamp_key, timestamp_key, constants.DEFAULT_INDEX_KEY])

    return df


def __compute_workload(df: pd.DataFrame, resource: Optional[str] = None, activity: Optional[str] = None,
                       parameters: Optional[Dict[str, Any]] = None) -> Dict[Tuple, int]:
    """
    Computes the workload of resources/activities, corresponding to each event a number
    (number of concurring events)

    Parameters
    ---------------
    df
        Dataframe
    resource
        (if provided) Resource on which we want to compute the workload
    activity
        (if provided) Activity on which we want to compute the workload

    Returns
    ---------------
    workload_dict
        Dictionary associating to each event the number of concurring events
    """
    if parameters is None:
        parameters = {}

    timestamp_key = exec_utils.get_param_value(Parameters.TIMESTAMP_KEY, parameters,
                                               xes_constants.DEFAULT_TIMESTAMP_KEY)
    resource_key = exec_utils.get_param_value(Parameters.RESOURCE_KEY, parameters, xes_constants.DEFAULT_RESOURCE_KEY)
    activity_key = exec_utils.get_param_value(Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY)
    start_timestamp_key = exec_utils.get_param_value(Parameters.START_TIMESTAMP_KEY, parameters, None)
    if start_timestamp_key is None:
        df = __insert_start_from_previous_event(df, parameters=parameters)
        start_timestamp_key = xes_constants.DEFAULT_START_TIMESTAMP_KEY
    df = df[[timestamp_key, resource_key, activity_key, start_timestamp_key]]
    if resource is not None:
        df = df[df[resource_key] == resource]
    if activity is not None:
        df = df[df[activity_key] == activity]
    events = df.to_dict("r")
    events = [(x[start_timestamp_key].timestamp(), x[timestamp_key].timestamp(), x[resource_key], x[activity_key]) for x
              in events]
    events = sorted(events)
    from intervaltree import IntervalTree, Interval
    tree = IntervalTree()
    ev_map = {}
    k = 0.000001
    for ev in events:
        tree.add(Interval(ev[0], ev[1] + k))
    for ev in events:
        ev_map[ev] = len(tree[ev[0]:ev[1] + k])
    return ev_map
