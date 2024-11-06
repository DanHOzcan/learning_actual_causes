import sys
import os

# Get the absolute path to the parent directory of 'main'
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
sys.path.insert(0, project_root)
from main.utils.tests_post_processing.check_conditions import check_ac1, check_ac2
import threading
import time
import subprocess
import re
from typing import Set, Optional, Any
import argparse

import psutil

# from main.utils.tests_post_processing.check_conditions import check_ac1,check_ac2,check_ac3
from main.utils.tests_post_processing.inspecting_contingency_set import *
from main.utils.clingo_runners.run_clingo_with_checks import *
from main.utils.json_utils.access_json import retrieve_processed_json_data_path, load_json
from main.utils.memory_montors.monitor_with_maxMemory_and_logging import monitor_memory_usage_with_logging
# Checks

# Imports for generating JSON data
from main.causality.binary_models.extract_background_knowledge_binary import generate_initial_asp_rules
from main.causality.binary_models.background_knowledge_generators import generating_lean_background_knowledge
from main.utils.clingo_runners.run_clingo import run_clingo_external
from main.utils.validity_checks.valid_query import check_validity_of_causal_query

##### NOTE: only going to measure time taken to evaluate background knowledge in line with SAT-based approach.
# def generate_las_task_from_json_for_time(json_data):
#     start_time = time.perf_counter()  # Start the timer
#     # Generate background knowledge
#     background_knowledge = generate_background_knowledge_binary(json_data)
#     # Generate ac1 example
#     ac1_example = generate_ac1_example_from_json(json_data)
#     # Generate ac2 example
#     ac2_example = generate_ac2_example_from_json(json_data)
#     # Generate hypothesis space
#     hypothesis_space = generate_search_space(json_data)
#     components = [background_knowledge, ac1_example, ac2_example, hypothesis_space]
#     las_task = '\n'.join(components)
#     end_time = time.perf_counter()  # End the timer
#     elapsed_time = end_time - start_time  # Calculate the elapsed time
#     return elapsed_time


def evaluate_equations(json_data):
    # Step 1: Generate initial ASP rules
    initial_asp_rules = generate_initial_asp_rules(json_data)

    start_time = time.perf_counter()  # Start the timer
    run_clingo_external(initial_asp_rules)
    end_time = time.perf_counter()  # End the timer

    elapsed_time = end_time - start_time  # Calculate the elapsed time

    return elapsed_time


def extract_candidate_cause(task_file: str) -> List[str]:
    with open(task_file, 'r') as file:
        ilasp_task = file.read()

    # Extract and tidy up search space string
    search_space_section = ilasp_task.split('%%%%% Search Space %%%%%')[1].strip()
    search_space_atoms = [atom.strip() for atom in search_space_section.split('\n')]

    # Construct ASP ATOMS
    search_space_atoms = [atom.replace('1 ~', '') for atom in search_space_atoms]
    search_space_atoms = [atom.strip() for atom in search_space_atoms]

    return search_space_atoms


def extract_actual_val_atoms_from_task(task_file: str) -> Set[str]:
    # Get task contents
    with open(task_file, 'r') as file:
        ilasp_task = file.read()

    background_knowledge = ilasp_task.split('%%%%% Examples %%%%% ')[0]

    actual_val_atoms_str = background_knowledge.split('%%%%% Actual value facts %%%%%')[1]

    actual_val_atoms_lst = actual_val_atoms_str.split('\n')

    actual_val_atoms_set = set(actual_val_atoms_lst)

    return actual_val_atoms_set


def check_determinate_background_knowledge(actual_val_atoms: Set[str], task_file: str) -> List[str]:
    json_data_path = retrieve_processed_json_data_path(task_file)
    # print(json_data_path)
    with open(json_data_path, 'r') as file:
        json_data = json.load(file)

    endogenous_variables = extract_endogenous_variables(json_data)

    missing_actual_vals = []

    for endo_var in endogenous_variables:

        if f"actual_val({endo_var},true)." not in actual_val_atoms and f"actual_val({endo_var},false)." not in actual_val_atoms:
            missing_actual_vals.append(endo_var)

    return missing_actual_vals


def run_ilasp_task_with_logging(task_file: str, flags: Optional[str] = None, max_memory_gb: int = 4,
                                timeout_seconds: int = 7200) -> Dict[str, Any]:
    """
    Runs a binary LAS_cause task with memory monitoring and timeout handling.

    Args:
        task_file (str): The path to the ILASP task file (.las).
        flags (Optional[str]): Additional flags to pass to ILASP.
        max_memory_gb (int): Maximum memory usage in GB before terminating the process.
        timeout_seconds (int): Maximum time in seconds before terminating the process.

    Returns:
        Dict[str, Any]: A dictionary containing the results and metadata of the ILASP run.
    """

    # Paths to ILASP and PYLASP scripts
    ilasp_path = "/homes/dozcan/bin/ILASP"
    pylasp_script_path = "/homes/dozcan/projects/learning_actual_causes/main/utils/pylasp/pylasp_for_causal_models.py"

    print("Running Pre-processing")
    candidate_cause = extract_candidate_cause(task_file)

    actual_val_atoms = extract_actual_val_atoms_from_task(task_file)
    missing_vals = check_determinate_background_knowledge(actual_val_atoms, task_file)
    if missing_vals:
        raise ValueError(
            f"Background Knowledge Incorrect. The following endogenous variables do not have actual value atoms: {missing_vals}")

    json_data_path = retrieve_processed_json_data_path(task_file)
    json_data = load_json(json_data_path)

    valid = check_validity_of_causal_query(task_file)
    if not valid:
        raise ValueError("Query Invalid.")

    # task_generation_time = generate_las_task_from_json_for_time(json_data)
    equation_evaluation_time = evaluate_equations(json_data)

    print("Causal Model is valid and background knowledge yields determinate results. Proceeding with ILASP task.")

    memory_usage_result = {}
    termination_reason = 'None'
    output_str = ''

    print("Running ILASP TASK")

    task_filename = os.path.basename(task_file)
    test_name = task_filename.replace('LAS_', '').replace('.las', '')

    command = [ilasp_path, task_file, pylasp_script_path]

    if flags:
        command.extend(flags.split())

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Start the memory monitoring thread with a termination event
    termination_event = threading.Event()
    memory_thread = threading.Thread(target=monitor_memory_usage_with_logging,
                                     args=(process.pid, memory_usage_result, max_memory_gb, termination_event))
    memory_thread.start()

    output_lines = []
    start_time = time.perf_counter()  # Use perf_counter for more precise timing

    try:
        # Wait for the process to complete or timeout
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        output_lines.append(stdout)

        if stderr:
            output_lines.append(stderr)

        # Check if memory monitoring detected a termination
        if memory_usage_result.get('terminated_due_to') == 'Memory':
            termination_reason = 'Memory Limit Exceeded'
            print("Process terminated due to excessive memory usage.")

    except subprocess.TimeoutExpired:
        print(f"Terminating process due to timeout. Elapsed time: {timeout_seconds} seconds")
        process.kill()
        termination_reason = 'Timeout'
        memory_usage_result.update({
            'terminated_due_to': 'Timeout',
            'solving_time': timeout_seconds
        })
        termination_event.set()
    except Exception as e:
        print(f"An unexpected exception occurred: {e}")
        termination_reason = 'Error'
        memory_usage_result.update({
            'terminated_due_to': 'Error',
            'error_message': str(e)
        })
        termination_event.set()
    finally:
        process.kill()
        termination_event.set()
        memory_thread.join()

    output_str = '\n'.join(output_lines)

    # Determine satisfiability status
    if 'UNSATISFIABLE' in output_str:
        satisfiability_status = 'Unsatisfiable'
        ac1 = check_ac1(task_file)
        ac2 = check_ac2(task_file)
    elif 'Solution 1' in output_str:
        satisfiability_status = 'Satisfiable'
        ac1 = ac2 = True
    else:
        satisfiability_status = 'Error'
        if termination_reason == 'None':
            termination_reason = memory_usage_result.get('terminated_due_to', 'Unknown')

    # Extract timings from output
    timings = {}
    timing_pattern = re.compile(r"^%%\s*(.*?)\s*:\s*([\d.]+s)\s*$", re.MULTILINE)
    for match in timing_pattern.findall(output_str):
        phase, time_taken = match
        timings[phase.strip()] = time_taken.strip()

    # Extract solutions from output
    solutions = []
    solution_pattern = re.compile(r"^%% Solution (\d+) \(score (\d+)\)\s*(.*?)\n?%%", re.DOTALL | re.MULTILINE)
    for match in solution_pattern.findall(output_str):
        solution_number, solution_score, solution_content = match
        solutions.append({
            'Solution Number': int(solution_number),
            'Solution Length': int(solution_score),
            'Solution Content': solution_content.strip()
        })

    # Process AC2 ASP programs
    asp_ac2_programs = create_ac2_asp_programs(task_file, solutions)

    for idx, solution in enumerate(asp_ac2_programs):
        answer_sets = run_clingo_with_checks(solution['AC2_Program'], task_file)
        interventions = process_all_answer_sets(answer_sets)
        solutions[idx]['AC2-satisfying interventions'] = interventions

    max_memory_usage_gb = memory_usage_result.get('max_memory_usage', 0) / (1024 ** 3)
    memory_usage_log = memory_usage_result.get('memory_usage_log', [])
    termination_reason = termination_reason or memory_usage_result.get('terminated_due_to', 'None')

    if termination_reason:
        total_time = "N/A"
    else:
        total_time =   float(
            str.replace(timings['Total'], 's', ''))  # Total time is task generation time + solving time

    results = {
        'Candidate cause': candidate_cause,
        'Test name': test_name,
        'Satisfiability status': satisfiability_status,
        'Output': output_str,
        # 'Task generation time': task_generation_time,
        'Equation evaluation time': equation_evaluation_time,
        'Solving time': timings['Total'] if not termination_reason else "N/A",
        'Breakdown of Solving Timings': timings if not termination_reason else "N/A",
        'Total time': total_time,
        'Max memory usage (GB)': max_memory_usage_gb,
        'Memory usage log': memory_usage_log,
        'Solutions': solutions,
        'Satisfied Conditions': {
            'AC1': ac1,
            'AC2': ac2,
            'AC3': True
        },
        'Termination reason': termination_reason
    }

    return results


def process_all_ilasp_tasks(input_directory: str, output_directory: str):
    """
    Process all .las files in the input directory, run the ILASP task with logging,
    and save the output as JSON files in the output directory.

    Args:
        input_directory (str): The path to the input directory containing .las files.
        output_directory (str): The path to the output directory where JSON results will be saved.
    """

    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)
    input_directory = os.path.abspath(input_directory)
    output_directory = os.path.abspath(output_directory)

    # Get a list of all .las files starting with 'LAS_' in the input directory
    las_tasks = [filename for filename in os.listdir(input_directory) if
                 filename.startswith('LAS_') and filename.endswith('.las')]
    total_files = len(las_tasks)  # Total number of files to process

    # Iterate over all files in the input directory
    for idx, filename in enumerate(las_tasks, start=1):
        task_file = os.path.join(input_directory, filename)

        # Printing for updates on progress
        print("\n" + "#" * 80)
        print(f"##### Processing file {idx} out of {total_files} #####")
        print(f"##### Task file: {task_file}")
        print("#" * 80 + "\n")

        # Run the ILASP task with logging
        result = run_ilasp_task_with_logging(task_file)

        # Define the output file path, removing 'LAS_' and adding 'results_las_'
        output_filename = f"results_las_{filename.replace('LAS_', '').replace('.las', '')}.json"
        output_file = os.path.join(output_directory, output_filename)

        # Save the result as a JSON file
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=4)

        # Printing for updates on progress
        print("\n" + "#" * 80)
        print(f"##### Processing file {idx} out of {total_files} #####")
        print(f"##### Task file: {task_file}")
        print("#" * 80 + "\n")
        print(f"Results saved to {output_file}")


if __name__ == "__main__":
    # Use argparse to parse command-line arguments
    parser = argparse.ArgumentParser(description="Process ILASP tasks and save results.")
    parser.add_argument('input_directory', type=str, help='Path to the input directory containing .las files.')
    parser.add_argument('output_directory', type=str, help='Path to the output directory where results will be saved.')

    args = parser.parse_args()

    # Call the function with the provided arguments
    process_all_ilasp_tasks(args.input_directory, args.output_directory)

# result = run_ilasp_task_with_logging("/homes/dozcan/projects/ilasp_tasks/RockThrowing/LAS_test_BillySuzy0a2cf73d
# -8f6f-4f42-9331-5e3bcaed3ada.las",max_memory_gb=0) for res in result: print(res,":", result.get(res))

