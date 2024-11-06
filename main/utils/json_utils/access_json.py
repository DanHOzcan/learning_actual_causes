import os
import json


## Old version
# def retrieve_processed_json_data_path(ilasp_filename: str) -> str:
#     # Extract the base name of the ILASP file (without the directory path)
#     base_name = os.path.basename(ilasp_filename)
#     # print(f"Base name is {base_name}")
#
#     # Remove the .las extension
#     base_name_without_ext = os.path.splitext(base_name)[0]
#
#     # print(f"Base name without extension is  {base_name_without_ext}")
#
#     # Remove the "LAS_" prefix to get the relevant part of the filename
#     relevant_part = base_name_without_ext.replace("LAS_", "")
#
#     # print(f"relevant part is {relevant_part}")
#
#     # Form the JSON filename
#     json_filename = f"processed_{relevant_part}.json"
#
#     # print(f"json filename is: {json_filename}" )
#     # Reconstruct the full JSON file path
#     full_path = f"/Users/hakano/Documents/learning_causes_experiments/finding_and_inferring/finding_piecewise/{json_filename}"
#
#     return full_path


def retrieve_processed_json_data_path(ilasp_filename: str) -> str:

    # Extract the base name of the ILASP file (without the directory path)
    base_name = os.path.basename(ilasp_filename)

    # Remove the .las extension
    base_name_without_ext = os.path.splitext(base_name)[0]

    # Remove the "LAS_" prefix to get the relevant part of the filename
    relevant_part = base_name_without_ext.replace("LAS_", "")

    # Get the parent directory (e.g., RockThrowing) of the ILASP file
    parent_directory = os.path.basename(os.path.dirname(ilasp_filename))
    # if parent_directory == "":
    #     print("HAVEN'T FOUND PARENT DIRECTORY")
    # else:
    #     print("Found parent directory!")

    # Form the JSON filename
    json_filename = f"processed_{relevant_part}.json"

    # Reconstruct the full JSON file path based on the parent directory
    full_path = os.path.join("/homes/dozcan/projects/checking_queries_processed", parent_directory, json_filename)

    return full_path



# print(os.path.dirname("homes/dozcan/projects/checking_queries_processed/RockThrowing/LAS_test_BillySuzy0a2cf73d-8f6f-4f42-9331-5e3bcaed3ada.las"))

def load_json(json_filepath: str) -> dict:
    """
    Load JSON data from a file and return it as a dictionary.

    Args:
        json_filepath (str): The path to the JSON file.

    Returns:
        dict: The JSON data as a Python dictionary.
    """
    try:
        with open(json_filepath, 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"Error: The file {json_filepath} was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file {json_filepath} does not contain valid JSON data.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

