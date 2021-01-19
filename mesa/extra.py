from __future__ import annotations
import numpy as np
import numba
import typing
if typing.TYPE_CHECKING:
    from mesaPROTON_OC import ProtonOC
    from entities import Person
    from typing import List, Set, Dict, Tuple, Optional, Union, Any
    import pandas as pd


def find_neighb(netname: str, togo: int, found: Set, border: Set[Person]):
    # found and border must have null intersection
    # includes the initial found
    # https://stackoverflow.com/questions/12555627/python-3-starred-expression-to-unpack-a-list
    found = found | border
    if togo == 0: return found
    #print_id(set().union(*[x.neighbors.get(netname) for x in border]))
    nextlayer = set().union(*[x.neighbors.get(netname) for x in border]) - found
    if not nextlayer:
        return found
    else:
        togo -= 1
        return find_neighb(netname, togo, found, nextlayer)


def wedding_proximity_with(ego, pool):
    """
    Given an agent and a pool of agents this function returns a list of proximities with ego. Careful not to shuffle it!
    :param ego: Person
    :param pool: list of Person objects
    :return: list, list of proximities with ego.
    """
    proximity = np.array([(social_proximity(ego,x) + (4 - abs(x.hobby - ego.hobby)) / 4 ) / 2 for x in pool])
    if all([True for n in proximity if n <= 0]):
        proximity = np.ones(len(proximity))
    proximity /= np.sum(proximity)
    return proximity


def social_proximity(ego, alter):
    """
    This function calculates the social proximity between two agents based on age, gender, wealth level, education level and friendship
    :param ego: Person
    :param alter: Person
    :return: int, social proximity
    """
    acc = 0
    #normalization =  0
    acc += 1 - abs(alter.age - ego.age) / 18 if abs(
        alter.age - ego.age) < 18 else 0
    acc += 1 if alter.gender_is_male == ego.gender_is_male else 0
    acc += 1 if alter.wealth_level == ego.wealth_level else 0
    acc += 1 if alter.education_level == ego.education_level else 0
    acc += 1 if [x for x in alter.neighbors.get("friendship") if (x in ego.neighbors.get("friendship"))] else 0
    return acc

def at_most(agentset, n, rng_istance):
    if len(agentset) < n:
        return agentset
    else:
        return list(rng_istance.choice(agentset, n, replace=False))

def weighted_n_of(n, agentset, weight_function, rng_istance):
    p = [float(weight_function(x)) for x in agentset]
    for pi in p:
        if pi < 0:
            min_value = np.min(p)
            p = [i - min_value for i in p]
            break
    sump = sum(p)
    #if there are more zeros than n required in p
    if np.count_nonzero(p) < n:
        n = np.count_nonzero(p)
    #If there are only zeros
    if sump == 0:
        p = None
    else:
        p = [i/sump for i in p]
    #If the type is wrong
    if type(agentset) != list:
        agentset = list(agentset)
    return rng_istance.choice(agentset, int(n), replace=False, p=p)

def weighted_one_of(agentset, weight_function, rng_istance):
    return weighted_n_of(1, agentset, weight_function, rng_istance)[0]

def pick_from_pair_list(a_list_of_pairs, rng_istance):
    """
    given a list of pairs, containing an object and a probability (e.g. [[object, p],[object, p]])
    return an object based on the probability(p)
    :param a_list_of_pairs:list, a list of pairs (e.g. [[object, p],[object, p]])
    :param rng_istance: numpy.random instance,
    :return: object
    """
    return weighted_one_of(a_list_of_pairs, lambda x: x[-1], rng_istance)[0]


def incestuos(ego: Person, candidates: Union[List[Person], Set[Person]]) -> Union[bool, None]:
    """
    This procedure checks if there are any links between partners within the candidate pool.
    Returns True if there are, None if there are not. It is used during ProtonOc.setup_siblings
    procedure to avoid incestuous marriages.
    :param ego: Person, the agent
    :param candidates: Union[List[Person], Set[Person]], the candidates
    :return: Union[bool, None], True if there are links between partners, None otherwise.
    """
    all_potential_siblings = [ego] + ego.get_neighbor_list("sibling") + candidates + [sibling for candidate in
                                                                                      candidates for sibling in
                                                                                      candidate.neighbors.get(
                                                                                          'sibling')]
    for sibling in all_potential_siblings:
        if sibling.get_neighbor_list("partner") and sibling.get_neighbor_list("partner")[0] in all_potential_siblings:
            return True

def df_to_dict(df: pd.DataFrame, extra_depth: bool = False) -> Dict:
    """
    Based on the number of pandas DataFrame columns, transforms the dataframe into nested dictionaries as follows:
    df-columns = age, sex, education, p --> dict-keys = {age:{sex:[education, p]}}

    If extra_depth is True the transformation has an extra level of depth as follows:
    df-columns = age, sex, education, p --> dict-keys = {age:{sex:{education: p}}}

    This transformation ensures a faster access to the values using the dictionary keys.
    :param df: pd.DataFrame, the df to be transformed
    :param extra_depth: bool, if True gives an extra level of depth
    :return: Dict, a new dictionary
    """
    dic = dict()
    extra_depth_modifier = 0
    if extra_depth:
        extra_depth_modifier = 1
    if len(df.columns) + extra_depth_modifier == 2:
        for col in np.unique(df.iloc[:, 0]):
            dic[col] = df[df.iloc[:, 0] == col].iloc[:, 1].values
    if len(df.columns) + extra_depth_modifier == 3:
        for col in np.unique(df.iloc[:, 0]):
            dic[col] = df[df.iloc[:, 0] == col].iloc[:, 1:].values
    if len(df.columns) + extra_depth_modifier == 4:
        for col in np.unique(df.iloc[:, 0]):
            dic[col] = df[df.iloc[:, 0] == col].iloc[:, 1:]
        for key in dic:
            subdic = dict()
            for subcol in np.unique(dic[key].iloc[:, 0]):
                if extra_depth:
                    subdic[subcol] = dic[key][dic[key].iloc[:, 0] == subcol].iloc[:, 1:].values[0][0]
                else:
                    subdic[subcol] = dic[key][dic[key].iloc[:, 0] == subcol].iloc[:, 1:].values
            dic[key] = subdic
    return dic

def decide_conn_number(agents: Union[List, Set], max_lim: int, also_me: bool = True) -> int:
    """
    Given a set of agents decides the number of connections to be created between them based on a maximum number.
    :param agents: Union[List, Set], agents
    :param max_lim: int, an arbitrary maximum number
    :param also_me: bool, include caller
    :return: max_lim if the agents are more than max_lim otherwise returns the number of agents minus one.
    """
    if len(agents) <= max_lim:
        return len(agents) - 1 if also_me else len(agents)
    else:
        return max_lim


def df_to_lists(df: pd.DataFrame, split_row: bool =True) -> List:
    """
    This function transforms a pandas DataFrame into nested lists as follows:
    df-columns = age, sex, education, p --> list = [[age,sex],[education,p]]

    This transformation ensures a faster access to the values using the position in the list
    :param df: pandas df, the df to be transformed
    :return: list, a new list
    """
    output_list = list()
    if split_row:
        temp_list = df.iloc[:, :2].values.tolist()
        for index, row in df.iterrows():
            output_list.append([temp_list[index], [row.iloc[2], row.iloc[3]]])
    else:
        output_list = df.values.tolist()
    return output_list


def calculate_oc_status( co_offenders: List[Person]) -> None:
    """
    This procedure modify in-place the arrest_weigh attribute of the Person objects passed to co_offenders
    :param co_offenders: list, of Person object
    :return: None
    """
    for agent in co_offenders:
        agent.arrest_weight = agent.calculate_oc_member_position()
    min_score = np.min([agent.arrest_weight for agent in co_offenders])
    divide_score = np.mean([agent.arrest_weight - min_score for agent in co_offenders])
    for agent in co_offenders:
        if divide_score > 0:
            agent.arrest_weight = (agent.arrest_weight - min_score) / divide_score
        else:
            agent.arrest_weight = 1


def commit_crime( co_offenders: List[Person]) -> None:
    """
    This procedure modify in-place the num_crimes_committed,num_crimes_committed_this_tick, co_off_flag and num_co_offenses
    attributes of the Person objects passed to co_offenders
    :param co_offenders: list, of Person object
    :return: None
    """
    for co_offender in co_offenders:
        co_offender.num_crimes_committed += 1
        co_offender.num_crimes_committed_this_tick += 1
        other_co_offenders = [agent for agent in co_offenders if agent != co_offender]
        for agent in other_co_offenders:
            if agent not in co_offender.neighbors.get("criminal"):
                co_offender.add_criminal_link(agent)
                co_offender.co_off_flag[agent] = 0
    for co_offender in co_offenders:
        for co_off_key in co_offender.co_off_flag.keys():
            co_offender.co_off_flag[co_off_key] += 1
            if co_offender.co_off_flag[co_off_key] == 2:
                co_offender.num_co_offenses[co_off_key] += 1


#Numba functions
@numba.jit(nopython=True)
def _age(tick, birth_tick):
    return np.floor((tick - birth_tick) / 12)



