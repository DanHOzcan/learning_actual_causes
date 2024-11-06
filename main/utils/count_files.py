import os


def count_files_in_subdirectories(parent_directory):
    total_file_count = 0  # Initialize a counter for the total number of files

    # Loop through all subdirectories in the parent directory
    for subdirectory in os.listdir(parent_directory):
        subdirectory_path = os.path.join(parent_directory, subdirectory)
        if os.path.isdir(subdirectory_path):
            # Count the number of files in the current subdirectory
            num_files = len([f for f in os.listdir(subdirectory_path) if os.path.isfile(os.path.join(subdirectory_path, f))])
            total_file_count += num_files  # Update the total file count

            print(f"Subdirectory: {subdirectory_path} contains {num_files} file(s).")

    # Print the total count of all files across subdirectories
    print(f"\nTotal number of files in all subdirectories: {total_file_count}")
    return total_file_count


## Usage
# Parent directory containing subdirectories to check
parent_directory = "/homes/dozcan/projects/checking_queries_processed/"

# Count all files in each subdirectory and return the total count
total_files = count_files_in_subdirectories(parent_directory)