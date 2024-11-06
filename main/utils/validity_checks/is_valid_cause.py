from main.exceptions.invalid_cause_exception import InvalidCauseException

def is_valid_cause(json_data):

    cause_atoms = json_data["query"]["candidateCause"]
    endogenous_variables = set(json_data["causal_model"]["variables"]["endogenous"].keys())
    for expression in cause_atoms:
        variable = expression.split(' = ')[0]
        if variable not in endogenous_variables:
            raise InvalidCauseException(f"Variable {variable} in candidate cause not an endogenous variable!")
    return True