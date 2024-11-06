import threading
import time

from main.utils.clingo_runners.run_clingo import evaluate_program_and_extract_atoms
from main.utils.graph_based_processing.build_dependency_graph import build_dependency_graph
from main.utils.graph_based_processing.sort_dependency_graph import topological_sort
from main.utils.memory_montors.memory_monitoring import monitor_memory


def generate_rules_for_variable(var, equations):
    """Generate ASP program for a single variable using its equations and previous results."""
    val_rules = []
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
    return val_rules


def generate_and_evaluate_by_two_levels(json_data):
    """Generate and evaluate ASP programs by processing sorted variables in two halves."""
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
    endogenous_start_index = exogenous_count

    # Split the sorted variables into two halves based on exogenous end index
    first_half_vars = sorted_vars[endogenous_start_index:len(sorted_vars) // 2]
    second_half_vars = sorted_vars[len(sorted_vars) // 2:]

    # Start memory monitoring
    stop_event = threading.Event()
    peak_memory = [0]  # Shared list to store peak memory
    memory_thread = threading.Thread(target=monitor_memory, args=(stop_event, peak_memory))
    memory_thread.start()

    # Start the timer
    start_time = time.perf_counter()

    try:
        # Step 1: Generate a combined program for the first half of the variables
        first_half_program = []
        for var in first_half_vars:
            # Retrieve equations for the current variable
            details = json_data["causal_model"]["variables"]["endogenous"].get(var, {})
            equations = details.get("equations", {})
            first_half_program.extend(generate_rules_for_variable(var, equations))

        first_half_program.extend(exogenous_facts)
        print("Processing the first half of variables...")
        first_half_val_atoms = evaluate_program_and_extract_atoms(first_half_program)
        all_val_atoms.update(first_half_val_atoms)

        # Step 2: Generate a combined program for the second half of the variables using updated atoms
        second_half_program = []
        for var in second_half_vars:
            # Retrieve equations for the current variable
            details = json_data["causal_model"]["variables"]["endogenous"].get(var, {})
            equations = details.get("equations", {})

            # Generate program for the current variable
            second_half_program.extend(generate_rules_for_variable(var, equations))

        # Evaluate the combined program for the second half and update atoms
        print("Processing the second half of variables...")
        second_half_val_atoms = evaluate_program_and_extract_atoms(second_half_program)
        all_val_atoms.update(second_half_val_atoms)

    finally:
        # Stop memory monitoring after the loop completes
        stop_event.set()
        memory_thread.join()


    # End the timer and calculate elapsed time
    end_time = time.perf_counter()
    elapsed_time_seconds = end_time - start_time
    elapsed_time_minutes = elapsed_time_seconds / 60

    print(f"Total execution time: {elapsed_time_minutes:.2f} minutes")

    # Output the final accumulated val/2 atoms
    return peak_memory[0], all_val_atoms, elapsed_time_minutes
