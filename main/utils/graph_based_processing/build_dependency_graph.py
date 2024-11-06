from collections import defaultdict, deque

from main.causality.binary_models.generating_tasks.generating_las_tasks_binary_modified import \
    extract_variables_from_piecewise


def build_dependency_graph(causal_model: dict):
    graph = defaultdict(set)  # Use sets for adjacency lists
    endogenous_vars = causal_model["variables"]["endogenous"]

    # Build the graph considering only piecewise_true dependencies
    for var, details in endogenous_vars.items():
        piecewise_true = details["equations"].get("piecewise_true", "")

        # Extract dependencies only from piecewise_true using the optimized extraction function
        dependencies = extract_variables_from_piecewise(piecewise_true)

        # Ensure every endogenous variable is added to the graph and add edges correctly
        graph[var]  # Initialize an empty entry for var
        for dep in dependencies:
            graph[var].add(dep)  # Use set to add dependency, avoiding duplicates

    return graph, endogenous_vars.keys()