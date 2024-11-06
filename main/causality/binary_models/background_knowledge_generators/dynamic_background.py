import json
import threading
import time

from main.causality.binary_models.generating_tasks.generating_las_tasks_binary_modified import extract_actual_val_atoms
from main.utils.clingo_runners.run_clingo import run_clingo_external, parse_clingo_output
from main.utils.graph_based_processing.build_dependency_graph import build_dependency_graph
from main.utils.graph_based_processing.sort_dependency_graph import topological_sort
from main.utils.memory_montors.memory_monitoring import monitor_memory


def evaluate_program_and_extract_atoms(asp_program):
    """Evaluate ASP program and extract val/2 atoms from the answer set."""
    # Run Clingo as an external process and get the output
    output = run_clingo_external(asp_program)
    val_atoms = parse_clingo_output(output)

    return val_atoms

def generate_program_for_variable(var, equations, previous_atoms):
    """Generate ASP program for a single variable using its equations and previous results."""
    val_rules = list(previous_atoms)  # Start with the previous atoms

    # Get piecewise_true and piecewise_false equations
    piecewise_true = equations.get("piecewise_true", "")
    piecewise_false = equations.get("piecewise_false", "")

    # Process each equation
    for equation in [piecewise_true, piecewise_false]:
        if 'if' in equation:
            head, body = equation.split(' if ')
            headvar, headval = head.split(' = ')
            body_disjuncts = body.split(' | ')

            for disjunct in body_disjuncts:
                # Handle conjunctions in the body of the equation
                conjuncts = disjunct.replace('(', '').replace(')', '').split(' & ')
                conjuncts_split = [conjunct.split(' = ') for conjunct in conjuncts]
                conjuncts_asp_format = [f"val({var.strip()},{val.strip()})" for var, val in conjuncts_split]
                conjuncts_str = ', '.join(conjuncts_asp_format)

                # Construct structural equation rule
                structural_equation_rule = f"val({headvar.strip()},{headval.strip()}) :- {conjuncts_str}."
                val_rules.append(structural_equation_rule)

    # Combine all rules for this program
    return "\n".join(val_rules)

def generate_and_evaluate_by_levels(json_data):
    """Generate and evaluate ASP programs by levels in sorted order."""

    # Start memory monitoring and timer
    stop_event = threading.Event()
    peak_memory = [0]  # Shared list to store peak memory
    memory_thread = threading.Thread(target=monitor_memory, args=(stop_event, peak_memory))
    memory_thread.start()
    start_time = time.perf_counter()

    # Construct the dependency graph and sort variables directly from json_data
    graph, all_vars = build_dependency_graph(json_data["causal_model"])
    exogenous_vars = json_data["causal_model"]["variables"]["exogenous"]
    sorted_vars = topological_sort(graph, all_vars, exogenous_vars)
    context = json_data["query"]["context"]

    # Generate exogenous facts directly from the context data
    exogenous_facts = [
        f"val({item.split(' = ')[0]}, {item.split(' = ')[1]})." for item in context
    ]

    # Initialize with exogenous facts
    all_val_atoms = set(exogenous_facts)

    # Determine the starting index for endogenous variables
    exogenous_vars_list = json_data["causal_model"]["variables"]["exogenous"]
    exogenous_count = len(exogenous_vars_list)
    endogenous_start_index = exogenous_count + 1

    sorted_vars.reverse()

    print(exogenous_count)
    print(sorted_vars)
    try:
        # Process only endogenous variables starting from the calculated index
        for var in sorted_vars[endogenous_start_index:]:


            # Retrieve equations for the current variable
            details = json_data["causal_model"]["variables"]["endogenous"].get(var, {})
            equations = details.get("equations", {})

            # Generate program for the current variable using previous atoms
            asp_program = generate_program_for_variable(var, equations, all_val_atoms)
            current_val_atoms = evaluate_program_and_extract_atoms(asp_program)
            all_val_atoms.update(current_val_atoms)  # Add the result to the accumulated val atoms
            actual_val_atoms = extract_actual_val_atoms(all_val_atoms)
    finally:
        # Stop memory monitoring after the loop completes
        stop_event.set()
        memory_thread.join()

    # End the timer and calculate elapsed time
    end_time = time.perf_counter()
    elapsed_time_minutes = (end_time - start_time) / 60
    print(f"Total execution time: {elapsed_time_minutes:.2f} minutes")

    # Output the final accumulated val/2 atoms
    return peak_memory[0],actual_val_atoms, elapsed_time_minutes


path = "/homes/dozcan/projects/checking_queries_processed/AssassinFIRST/processed_test_Assassin_firstVariant0e4107a6-20bf-4ee4-a9e3-ec6c212dc3fa.json"

with open(path,'r') as file:
    data = json.load(file)

memory, atoms, elapsed_time = generate_and_evaluate_by_levels(data)

print(atoms)