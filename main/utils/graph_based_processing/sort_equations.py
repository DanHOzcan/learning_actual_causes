from main.utils.graph_based_processing.build_dependency_graph import build_dependency_graph
from main.utils.graph_based_processing.sort_dependency_graph import topological_sort


def sort_equations(json_data):
    causal_model = json_data["causal_model"]
    graph, all_vars = build_dependency_graph(causal_model)
    exogenous_vars = causal_model["variables"]["exogenous"]
    sorted_vars = topological_sort(graph, all_vars, exogenous_vars)
    # print(sorted_vars)
    # Map sorted variables to their equations
    equations = causal_model["variables"]["endogenous"]
    sorted_equations = [equations[var] for var in sorted_vars if var in equations]

    return sorted_equations