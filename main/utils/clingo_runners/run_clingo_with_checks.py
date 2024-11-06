import clingo
import json
from main.utils.json_utils.access_json import retrieve_processed_json_data_path


# Function to run Clingo with checks for missing values
def run_clingo_with_checks(asp_rules, ilasp_filename):
    """
    Run Clingo on the given ASP rules, check for missing values, and return the answer sets.

    Args:
    asp_rules (str or list): The ASP rules as a single string or a list of strings.
    ilasp_filename (str): The ILASP file path to retrieve the corresponding JSON data.

    Returns:
    list: A list of answer sets.
    """
    ctl = clingo.Control()

    # If the input is a single string, split it into a list of rules
    if isinstance(asp_rules, str):
        asp_rules = asp_rules.split('\n')

    try:
        ctl.add("base", [], "\n".join(asp_rules))
        ctl.ground([("base", [])])
        answer_sets = []

        with ctl.solve(yield_=True) as handle:
            for model in handle:
                answer_sets.append(model.symbols(atoms=True))

        # Retrieve the JSON data path and extract endogenous variables
        json_data_path = retrieve_processed_json_data_path(ilasp_filename)
        with open(json_data_path, 'r') as json_file:
            json_data = json.load(json_file)

        endo_vars = extract_endogenous_variables(json_data)

        # Check for missing values in each answer set
        for answer_set in answer_sets:
            missing_vars = check_missing_values(answer_set, endo_vars)
            if missing_vars:
                raise ValueError(f"Missing values found for variables: {', '.join(missing_vars)}")

        return answer_sets
    except RuntimeError as e:
        print(f"RuntimeError: {e}")
        return []


# Function to check for missing values
def check_missing_values(answer_set, endo_vars):
    variable_value_pairs = set()

    for atom in answer_set:
        if atom.match("val", 2):
            variable = atom.arguments[0]
            value = atom.arguments[1]
            variable_value_pairs.add((variable, value))

    missing_vars = []
    # Check if any variable is missing a true/false value
    for variable in endo_vars:
        if (clingo.Function(variable), clingo.Function("true")) not in variable_value_pairs and (
        clingo.Function(variable), clingo.Function("false")) not in variable_value_pairs:
            missing_vars.append(variable)
    return missing_vars



# Function to extract endogenous variables from JSON data
def extract_endogenous_variables(json_data):
    endo_vars = list(json_data["causal_model"]["variables"]["endogenous"].keys())
    return endo_vars
