from main.utils.validity_checks.is_valid_causal_model import *
from typing import Dict, List, Set, Any
import clingo


def extract_endogenous_variables(json_data: Dict[str, Any]) -> List[str]:
    return list(json_data["causal_model"]["variables"]["endogenous"].keys())


def check_missing_values(answer_set, endo_vars: List[str]) -> List[str]:
    variable_value_pairs = set()

    for atom in answer_set:
        if atom.match("val", 2):
            variable = atom.arguments[0]
            value = atom.arguments[1]
            variable_value_pairs.add((variable, value))

    missing_vars = []
    for variable in endo_vars:
        if (clingo.Function(variable), clingo.Function("true")) not in variable_value_pairs and (
        clingo.Function(variable), clingo.Function("false")) not in variable_value_pairs:
            missing_vars.append(variable)
    return missing_vars


def find_ancestors(variable: str, json_data: Dict[str, Any]) -> Set[str]:
    if not is_valid_causal_model(json_data):
        raise ValueError("The provided causal model is invalid.")

    ancestors = set()
    to_visit = [variable]

    while to_visit:
        current_var = to_visit.pop()
        parents = find_parents(current_var, json_data)
        new_ancestors = parents - ancestors
        ancestors.update(new_ancestors)
        to_visit.extend(new_ancestors)

    return ancestors


def find_parents(variable: str, json_data: Dict[str, Any]) -> Set[str]:
    """
    Find all parents of a given variable using the JSON data.

    Args:
    variable (str): The variable to find ancestors for.
    json_data (Dict[str, Any]): The JSON data containing variable definitions.

    Returns:
    Set[str]: A set of parent\] variables.
    """
    exogenous_variables = json_data['causal_model']['variables']['exogenous']
    endogenous_variables = set(json_data['causal_model']['variables']['endogenous'].keys())

    # Exogenous variables have no ancestors
    if variable in exogenous_variables:
        return set()

    # 'variable' is neither an endogenous nor an exogenous variable
    if variable not in endogenous_variables:
        raise ValueError(f"{variable} is not this model.")

    parents = set()
    equations = json_data['causal_model']['variables']['endogenous'][variable]['equations']
    for eq in equations.values():
        parents.update(extract_variables(eq))
    return parents


def find_missing_ancestors(answer_set, json_data: Dict[str, Any]) -> Dict[str, Set[str]]:
    """
    Find all ancestors of missing variables in the answer set.

    Args:
    answer_set (list): The answer set containing the atoms.
    json_data (Dict[str, Any]): The JSON data containing variable definitions.

    Returns:
    Dict[str, Set[str]]: A dictionary where keys are missing variables and values are sets of ancestor variables.
    """
    # Extract endogenous variables
    endo_vars = extract_endogenous_variables(json_data)

    # Find missing values
    missing_vars = check_missing_values(answer_set, endo_vars)

    # Find ancestors for each missing variable
    missing_ancestors = {}
    for var in missing_vars:
        ancestors = find_ancestors(var, json_data)
        missing_ancestors[var] = ancestors

    return missing_ancestors
