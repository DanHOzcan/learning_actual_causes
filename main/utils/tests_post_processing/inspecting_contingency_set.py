from typing import Dict, List
import os

def extract_intervened_on_atoms(answer_sets):
    """
    Extract intervened_on/2 atoms from the answer sets.

    Args:
    answer_sets (list): The list of answer sets.

    Returns:
    list: A list of intervened_on/2 atoms as tuples.
    """
    intervened_on_atoms = []
    for answer_set in answer_sets:
        for atom in answer_set:
            if atom.match("intervened_on", 2):
                intervened_on_atoms.append((str(atom.arguments[0]), str(atom.arguments[1])))
    return intervened_on_atoms


def extract_val_atoms(answer_sets, intervened_on_vars):
    """
    Extract val/2 atoms that correspond to intervened_on/2 atoms.

    Args:
    answer_sets (list): The list of answer sets.
    intervened_on_vars (list): The list of variables from intervened_on/2 atoms.

    Returns:
    list: A list of val/2 atoms as tuples.
    """
    val_atoms = []
    for answer_set in answer_sets:
        for atom in answer_set:
            if atom.match("val", 2) and str(atom.arguments[0]) in intervened_on_vars:
                val_atoms.append((str(atom.arguments[0]), str(atom.arguments[1])))
    return val_atoms


def extract_actual_val_atoms(answer_sets, val_vars):
    """
    Extract actual_val/2 atoms that correspond to val/2 atoms.

    Args:
    answer_sets (list): The list of answer sets.
    val_vars (list): The list of variables from val/2 atoms.

    Returns:
    list: A list of actual_val/2 atoms as tuples.
    """
    actual_val_atoms = []
    for answer_set in answer_sets:
        for atom in answer_set:
            if atom.match("actual_val", 2) and (str(atom.arguments[0]), str(atom.arguments[1])) in val_vars:
                actual_val_atoms.append((str(atom.arguments[0]), str(atom.arguments[1])))
    return actual_val_atoms


def compare_val_and_actual_val(val_atoms, actual_val_atoms):
    """
    Process the atoms to find matching intervened_on and actual_val pairs.

    Args:
    intervened_on_atoms (list): The list of intervened_on/2 atoms as tuples.
    val_atoms (list): The list of val/2 atoms as tuples.
    actual_val_atoms (list): The list of actual_val/2 atoms as tuples.

    Returns:
    list: A list of matching pairs.
    """
    intervened_on_set = set(val_atoms)
    actual_val_set = set(actual_val_atoms)

    W = list(intervened_on_set.intersection(actual_val_set))
    X_prime = list(intervened_on_set.difference(actual_val_set))

    return X_prime, W


def process_all_answer_sets(answer_sets):
    """
    Process each answer set independently to find matching intervened_on and actual_val pairs.

    Args:
    answer_sets (list): The list of answer sets.

    Returns:
    dict: A dictionary of matching pairs for each answer set.
    """
    results = {}
    for i, answer_set in enumerate(answer_sets):
        symbols = list(answer_set)  # Convert _SymbolSequence to list of symbols
        intervened_on_atoms = extract_intervened_on_atoms([symbols])
        val_atoms = extract_val_atoms([symbols], [var for var, _ in intervened_on_atoms])
        actual_val_atoms = extract_actual_val_atoms([symbols], val_atoms)
        X_prime, W = compare_val_and_actual_val(val_atoms, actual_val_atoms)
        results[f"Intervention {i + 1}"] = {'X': X_prime, 'W': W}
    return results


def create_ac2_asp_programs(task_file: str, solutions: List) -> List[Dict[str, str]]:
    """
    Create AC2 ASP programs given the optimal solutions and ILASP task file.

    Args:
        task_file (str): The path to the ILASP task file.
        ilasp_output (str): The ILASP output containing the optimal solutions.

    Returns:
        List[Dict[str, str]]: A list of dictionaries, each containing a hypothesis and the corresponding AC2 program.
    """

    # Extract the test name
    task_filename = os.path.basename(task_file)
    ilasp_task_name = task_filename.replace('LAS_', '').replace('.las', '')

    optimal_solutions = solutions

    # Extract the background knowledge from the ILASP task file
    with open(task_file, 'r') as file:
        ilasp_task = file.read()

    background_knowledge = ilasp_task.split('%%%%% Examples %%%%%')[0].strip()


    # Extract the ASP context
    examples = ilasp_task.split('%%%%% Examples %%%%%')[1]
    ac2_example = examples.split('% AC2 Example')[1].split('%%%%% Search Space %%%%%')[0].strip()
    ac2_asp_context = ac2_example.replace('#pos(ac2,{},{},', '')
    ac2_asp_context = ac2_asp_context[2:]
    ac2_asp_context = ac2_asp_context[:-3]

    # Loop through and join the background knowledge, AC2 example, and hypothesis for each solution
    ac2_asp_programs = []
    for optimal_solution in solutions:
        H = optimal_solution['Solution Content']
        program_components = [background_knowledge, '', '% AC2 Intervention', ac2_asp_context, ' % Hypothesis', '', H]
        program = '\n'.join(program_components)
        ac2_asp_programs.append({'Hypothesis': H, 'AC2_Program': program})
    return ac2_asp_programs


