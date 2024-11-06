from main.exceptions.invalid_context_exception import InvalidContextException


def is_valid_context(json_data):
    context = json_data["query"]["context"]
    exogenous_variables = set(json_data["causal_model"]["variables"]["exogenous"])
    endogenous_variables = set(json_data["causal_model"]["variables"]["endogenous"].keys())

    for assignment in context:
        variable = assignment.split(' = ')[0]
        if variable not in exogenous_variables:
            raise InvalidContextException(f"Variable '{variable}' in context is not defined as an exogenous variable!")
        if variable in endogenous_variables:
            raise InvalidContextException(f"Variable '{variable}' in context is endogenous!")

    # If no exception is raised, the context is valid
    return True