
import tempfile
from main.utils.json_utils.access_json import *
from main.utils.ilasp_runners.run_ilasp import *
from main.utils.clingo_runners.run_clingo_for_satisfiability import run_clingo_for_satisfiability
from main.causality.binary_models.generating_tasks.generating_las_tasks_binary_modified import translate_to_asp_atoms


def generate_adjusted_ac1_example_from_json(json_data):
    """
    Generates an ASP positive example from the provided JSON data.

    Args:
        json_data (dict): The JSON data containing the context, cause, and phi.

    Returns:
        str: The formatted ASP positive example string.
    """
    # Extract context, cause, and phi from JSON
    context = json_data["query"]["context"]
    cause = json_data["query"]["candidateCause"]
    phi = json_data["query"]["phi"]


    # Generate the val/2 atoms for the cause
    cause_asp_atoms = translate_to_asp_atoms(cause)
    cause_str = ", ".join(cause_asp_atoms)

    # Generate the val/2 atoms for phi
    phi_asp_atoms = translate_to_asp_atoms(phi)

    # Check if the phi_asp_atoms list is flat or nested
    is_flat_list = all(not isinstance(i, list) for i in phi_asp_atoms)

    # Generate the ac1 rules (meaning not a disjunction)
    if is_flat_list:
        phi_conjunction = ', '.join(phi_asp_atoms)
        ac1_rules_str = f" ac1 :- {cause_str},{phi_conjunction}. "
    else:
        joined_conjunctions = [', '.join(conjunction) for conjunction in phi_asp_atoms]
        phi_rules = [f" phi :- {cause_str},{conjunction}." for conjunction in joined_conjunctions]
        ac1_rules_str = '\n'.join(phi_rules)

    # Generate the ASP positive example string
    ac1_positive_example = f"""

%%%%% Examples %%%%%

% AC1 Example

#pos(ac1,{{ac1}},{{}},
{{
{ac1_rules_str}
}}).
"""
    return ac1_positive_example


def check_ac2(ilasp_filename: str) -> bool:
    # Create the ASP program for checking AC2 - we do this instead of ILASP to avoid finding a subset.
    ac2_asp_program = generate_ac2_asp_program(ilasp_filename)

    # run clingo and extract output
    result = run_clingo_for_satisfiability(ac2_asp_program)

    if result == 'SATISFIABLE':
        return True
    elif result == 'UNSATISFIABLE':
        return False
    else:
        raise ValueError(f"Result Neither Satisfiable nor unsatisfiable: {result}")

#  Incorrect logic: if the task is UNSAT, then AC3 is satisfied: if there was AC1- and AC2-satisfying subset, ILASP would have found it, so no subset is, meaning AC3 is satisfied.
# def check_ac3(ilasp_filename: str) -> bool:
#     # We assume that ILASP returns UNSAT for the original script
#
#     # Load file into string for processing
#     with open(ilasp_filename, 'r') as file:
#         ilasp_task = file.read()
#
#     # Extract the ASP atoms from the search space
#     search_space = ilasp_task.split('%%%%% Search Space %%%%%')[1]
#     search_space_atoms = search_space.replace('1 ~', '').strip().split()
#
#     # Ensure search_space_atoms is processed correctly
#     if len(search_space_atoms) == 1:
#         return True
#     elif len(search_space_atoms) > 1:
#         return False


def check_ac1(ilasp_file: str) -> bool:
    ilasp_ac1_task = generate_ac1_task(ilasp_file)

    #     print(ilasp_ac1_task)

    # If Satisfiable, return True; if not, return not

    # Create Temporary File to run ILASP task
    with tempfile.NamedTemporaryFile(delete=False, suffix='.las') as temp_file:
        # Write the ILASP task contents to the temporary file
        temp_file.write(ilasp_ac1_task.encode('utf-8'))
        temp_file_path = temp_file.name

    result = run_ilasp_task(temp_file_path)

    # Clean up the temporary file
    os.remove(temp_file_path)

    if 'UNSATISFIABLE' in result['output']:
        return False
    else:
        return True


def generate_ac1_task(ilasp_file: str) -> str:
    # Load file into string for processing
    with open(ilasp_file, 'r') as file:
        ilasp_task = file.read()

    # Extract the background knowledge and search space
    background_knowledge = ilasp_task.split('%%%%% Examples %%%%%')[0]
    search_space = ilasp_task.split('%%%%% Search Space %%%%%')[1]

    # Find and retrieve json data to reconstruct AC1 example in different form.
    json_data_path = retrieve_processed_json_data_path(ilasp_file)
    json_data = load_json(json_data_path)

    # Generate adjusted AC1 example
    ac1_example = generate_adjusted_ac1_example_from_json(json_data)

    # Put components together into a full task
    ilasp_ac1_task = (
            background_knowledge +
            ac1_example +
            search_space
    )

    return ilasp_ac1_task


def generate_ac2_asp_program(ilasp_filename: str) -> str:
    # Load file into string for processing
    with open(ilasp_filename, 'r') as file:
        ilasp_task = file.read()

    # Extract the background knowledge
    background_knowledge = ilasp_task.split('%%%%% Examples %%%%%')[0]

    # Extract the ASP context
    examples = ilasp_task.split('%%%%% Examples %%%%%')[1]
    ac2_example = examples.split('% AC2 Example')[1].split('%%%%% Search Space %%%%%')[0].strip()
    ac2_asp_context = ac2_example.replace('#pos(ac2,{},{},', '')
    ac2_asp_context = ac2_asp_context[2:]
    ac2_asp_context = ac2_asp_context[:-3]

    # Extract the ASP atoms from search space
    search_space = ilasp_task.split('%%%%% Search Space %%%%%')[1]
    search_space_atoms = search_space.replace('1 ~', '').strip()

    # Construct full ac2 program
    ac2_asp_program = (
            background_knowledge
            + '\n% AC2\n'
            + ac2_asp_context
            + '\n% in_cause/2 atoms \n'
            + search_space_atoms
    )

    # Strip leading and trailing whitespace from the constructed program
    ac2_asp_program = ac2_asp_program.strip()

    #     print("Generated AC2 ASP Program:\n")
    #     print(ac2_asp_program)
    return ac2_asp_program
