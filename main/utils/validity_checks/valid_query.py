from main.utils.json_utils.access_json import retrieve_processed_json_data_path, load_json
from main.utils.validity_checks.is_valid_causal_model import is_valid_causal_model
from is_valid_causal_model import is_valid_causal_model
from is_valid_phi import is_valid_phi
from is_valid_cause import is_valid_cause
from is_valid_context import is_valid_context


def check_validity_of_causal_query(task_file: str) -> bool:

    # Load data
    json_data_path = retrieve_processed_json_data_path(task_file)
    json_data = load_json(json_data_path)

    # Perform checks
    is_valid_causal_model(json_data)
    is_valid_cause(json_data)
    is_valid_context(json_data)
    is_valid_phi(json_data)

    valid = is_valid_causal_model and is_valid_cause and is_valid_context and is_valid_phi

    if valid:
        return True
    else:
        return False
