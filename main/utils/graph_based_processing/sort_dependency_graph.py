from collections import deque


def topological_sort(graph, all_vars, exogenous_vars):
    # Initialize in_degree with all variables, setting to 0 initially
    in_degree = {var: 0 for var in all_vars}
    in_degree.update({var: 0 for var in exogenous_vars})  # Add exogenous variables

    # Populate in_degree counts for nodes with dependencies
    for node in graph:
        for neighbor in graph[node]:
            in_degree[neighbor] += 1

    # Initialize the queue with nodes with 0 in-degree and sort for stable ordering
    queue = deque(sorted([node for node in in_degree if in_degree[node] == 0]))
    sorted_order = []

    while queue:
        node = queue.popleft()
        sorted_order.append(node)
        for neighbor in sorted(graph[node]):  # Process neighbors in a sorted order
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Final check: make sure all nodes are included and dependencies respected
    if len(sorted_order) == len(in_degree):
        # print("Topological sort order:", sorted_order)  # Debug output to confirm order
        return sorted_order
    else:
        raise ValueError("The graph has a cycle and cannot be topologically sorted.")