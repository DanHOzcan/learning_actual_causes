# from main.causality.binary_models.process_causal_model_json import process_all_files, process_causal_model_JSON
#
#
#
#
# # # Parent directory containing subdirectories to check
# # parent_directory = '/Users/hakano/Documents/duplicate'
# #
# # # Check all subdirectories for equivalent files
# # check_all_subdirectories(parent_directory)
# #
# #
# #
# #
# # # def count_files_in_subdirectories(parent_directory):
# # #     total_file_count = 0  # Initialize a counter for the total number of files
# # #
# # #     # Loop through all subdirectories in the parent directory
# # #     for subdirectory in os.listdir(parent_directory):
# # #         subdirectory_path = os.path.join(parent_directory, subdirectory)
# # #         if os.path.isdir(subdirectory_path):
# # #             # Count the number of files in the current subdirectory
# # #             num_files = len([f for f in os.listdir(subdirectory_path) if os.path.isfile(os.path.join(subdirectory_path, f))])
# # #             total_file_count += num_files  # Update the total file count
# # #
# # #             print(f"Subdirectory: {subdirectory_path} contains {num_files} file(s).")
# # #
# # #     # Print the total count of all files across subdirectories
# # #     print(f"\nTotal number of files in all subdirectories: {total_file_count}")
# # #     return total_file_count
# # #
# # # # Parent directory containing subdirectories to check
# # # parent_directory = '/Users/hakano/Documents/learning_causes_experiments/checking_queries'
# # #
# # # # Count all files in each subdirectory and return the total count
# # # total_files = count_files_in_subdirectories(parent_directory)
# #
# # #
# # # def remove_files_from_subdirectories(base_directory):
# # #     # Iterate through all subdirectories within the base directory
# # #     for root, dirs, files in os.walk(base_directory):
# # #         for file in files:
# # #             file_path = os.path.join(root, file)
# # #             try:
# # #                 os.remove(file_path)
# # #                 print(f"Removed file: {file_path}")
# # #             except Exception as e:
# # #                 print(f"Failed to remove {file_path}: {e}")
# # #
# # # # Specify the base directory
# # # base_directory = "/Users/hakano/Documents/learning_causes_experiments/checking_queries"
# # #
# # # # Call the function
# # # remove_files_from_subdirectories(base_directory)
# #
# # # def count_files_in_subdirectories(base_directory):
# # #     total_files = 0
# # #
# # #     for root, dirs, files in os.walk(base_directory):
# # #         # Only count files in subdirectories, not in the base directory itself
# # #         if root != base_directory:
# # #             num_files = len(files)
# # #             print(f"Directory: {root}, File Count: {num_files}")
# # #             total_files += num_files
# # #
# # #     print(f"Total number of files in all subdirectories: {total_files}")
# # #     return total_files
# # #
# # # # Specify the base directory
# # # base_directory = "/Users/hakano/Documents/duplicate"
# # #
# # # # Call the function
# # # count_files_in_subdirectories(base_directory)
#
# #
# # # # Define the input and output directories
# # input_directory = ('/Users/hakano/Documents/duplicate/com.example.benchmarks.finding_and_inferring'
# #                    '.BenchmarkStealMasterKey650Users')
# # output_directory = '/Users/hakano/Documents/processed_650Users'
# #
# # # # Call the function to process all files
# # process_all_files(input_directory, output_directory)
#
#
# import os
# import json
#
#
# def process_all_files_in_subdirectories(input_directory, output_base_directory):
#     """
#     Processes all JSON files in each subdirectory of the input directory and outputs the processed files
#     to corresponding subdirectories in the output base directory.
#
#     Args:
#         input_directory (str): Path to the base input directory containing subdirectories with JSON files.
#         output_base_directory (str): Path to the base output directory to save processed JSON files.
#     """
#     # Iterate over all subdirectories in the input directory
#     for subdir in os.listdir(input_directory):
#         input_subdir_path = os.path.join(input_directory, subdir)
#         if os.path.isdir(input_subdir_path):
#             # Create corresponding subdirectory in the output directory with 'processed_' prefix
#             output_subdir_name = 'processed_' + subdir
#             output_subdir_path = os.path.join(output_base_directory, output_subdir_name)
#             if not os.path.exists(output_subdir_path):
#                 os.makedirs(output_subdir_path)
#
#             # Process each JSON file in the subdirectory
#             files = os.listdir(input_subdir_path)
#             for file in files:
#                 input_file_path = os.path.join(input_subdir_path, file)
#                 if os.path.isfile(input_file_path) and file.endswith('.json') and not file.startswith('.'):
#                     output_file_name = 'processed_' + file
#                     output_file_path = os.path.join(output_subdir_path, output_file_name)
#                     with open(input_file_path, 'r', encoding='utf-8') as json_file:
#                         input_data = json.load(json_file)
#                         print(f"Currently processing {file} in {subdir}")
#                     processed_data = process_causal_model_JSON(input_data)
#                     with open(output_file_path, 'w', encoding='utf-8') as json_file:
#                         json.dump(processed_data, json_file, indent=2)
#                     print(f"Processed: {input_file_path} -> {output_file_path}")
#
#
# # Parent directory containing subdirectories to check
# parent_directory = '/Users/hakano/Documents/duplicate'
#
# # Check all subdirectories for equivalent files
# check_all_subdirectories(parent_directory)
#
# # Define the input and output base directories
# input_directory = '/Users/hakano/Documents/duplicate'
# output_base_directory = '/Users/hakano/Documents/learning_causes_experiments/checking_queries_processed/'
#
# # Call the function to process all files
# process_all_files_in_subdirectories(input_directory, output_base_directory)
import os


def rename_directories(base_directory):
    # Loop through all the subdirectories in the base directory
    for subdir in os.listdir(base_directory):
        # Check if the current item is a directory and has "Benchmark" in the name
        if os.path.isdir(os.path.join(base_directory, subdir)) and "finding_and_inferring" in subdir:
            # Find the part after "Benchmark"
            new_name = subdir.split("finding_and_inferring.", 1)[-1]

            # Construct the full path to the old and new directory names
            old_path = os.path.join(base_directory, subdir)
            new_path = os.path.join(base_directory, new_name)

            # Rename the directory
            print(f"Renaming '{old_path}' to '{new_path}'")  # Optional: for debugging
            os.rename(old_path, new_path)


# # Example usage
# base_dir = "/homes/dozcan/projects/checking_queries_processed"
# rename_directories(base_dir)