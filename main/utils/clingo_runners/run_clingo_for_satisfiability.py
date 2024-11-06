import tempfile
import clingo
import os

def run_clingo_for_satisfiability(asp_rules: str) -> str:
    """
    Run Clingo on the given ASP rules and return the satisfiability status.

    Args:
        asp_rules (str): The ASP rules as a string.

    Returns:
        str: The satisfiability status from Clingo.
    """
    # Create a temporary file to hold the ASP rules
    with tempfile.NamedTemporaryFile(delete=False, suffix='.lp') as temp_file:
        temp_file.write(asp_rules.encode('utf-8'))
        temp_file_path = temp_file.name

    # Print the path and contents of the temporary file for debugging
    print(f"Temporary file path: {temp_file_path}")
    ctl = clingo.Control()
    try:
        ctl.load(temp_file_path)
        ctl.ground([("base", [])])
        satisfiability_status = "UNSATISFIABLE"

        with ctl.solve(yield_=True) as handle:
            for model in handle:
                satisfiability_status = "SATISFIABLE"
                break  # No need to check further if at least one model is found
        return satisfiability_status
    except clingo.ClingoError as e:
        print(f"An error occurred while running clingo: {e}")
        return "ERROR"
    finally:
        # Clean up the temporary file
        os.remove(temp_file_path)
