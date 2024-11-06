import os
import json

def load_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def are_equivalent_tests(test1, test2):
    # Check if "phi" values are exactly the same as strings
    if test1['query']['phi'] != test2['query']['phi']:
        return False

    # Check if "candidateCause" values are equivalent (as sets)
    if set(test1['query']['candidateCause']) != set(test2['query']['candidateCause']):
        return False

    # Check if "context" values are equivalent (as sets)
    if set(test1['query']['context']) != set(test2['query']['context']):
        return False

    return True


def find_equivalent_tests(directory):
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    equivalences = []

    # Compare each pair of files
    for i in range(len(files)):
        test1 = load_json_file(os.path.join(directory, files[i]))
        for j in range(i + 1, len(files)):
            test2 = load_json_file(os.path.join(directory, files[j]))
            if are_equivalent_tests(test1, test2):
                equivalences.append((files[i], files[j]))

    return equivalences


def check_all_subdirectories(parent_directory):
    total_equivalent_pairs = 0  # Initialize a counter for total equivalent pairs

    # Loop through all subdirectories in the parent directory
    for subdirectory in os.listdir(parent_directory):
        subdirectory_path = os.path.join(parent_directory, subdirectory)
        if os.path.isdir(subdirectory_path):
            print(f"Checking directory: {subdirectory_path}")
            equivalent_pairs = find_equivalent_tests(subdirectory_path)
            num_equivalent_pairs = len(equivalent_pairs)
            total_equivalent_pairs += num_equivalent_pairs  # Update the total count

            if num_equivalent_pairs > 0:
                print(f"Equivalent test pairs found in {subdirectory_path}:")
                for pair in equivalent_pairs:
                    print(f"  {pair[0]} and {pair[1]}")
            else:
                print(f"No equivalent test pairs found in {subdirectory_path}.\n")

    # Print the total count of equivalent pairs at the end