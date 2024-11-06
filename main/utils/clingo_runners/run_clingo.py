import os
import subprocess


import os
import subprocess
import tempfile

def run_clingo_external(asp_rules):
    """
    Run Clingo as an external process with the given ASP rules.

    Args:
    asp_rules (str or list): The ASP rules as a single string or a list of strings.

    Returns:
    str: The output from Clingo, or an empty string if something goes wrong.
    """

    # print(f"Rules being passed are: {asp_rules}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".lp") as temp_file:
        temp_file_name = temp_file.name
        asp_content = "\n".join(asp_rules) if isinstance(asp_rules, list) else asp_rules
        temp_file.write(asp_content.encode('utf-8'))

        # Debugging: Print contents of the temporary file
        # print(f"Temporary file content ({temp_file_name}):\n{asp_content}")

    # Prepare the command to run Clingo
    command = ["/homes/dozcan/clingo_install/bin/clingo", temp_file_name, "0"]

    try:
        # Run Clingo as an external process, capturing both stdout and stderr
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # Capture stderr separately
            text=True,
            check=False  # Do not raise an exception for non-zero exit codes
        )

        # # Debugging
        # print("Clingo Command:", " ".join(command))
        # print("Clingo Stdout:", result.stdout)
        # print("Clingo Stderr:", result.stderr)

        return result.stdout

    except subprocess.CalledProcessError as e:
        print(f"Clingo error: {e.stderr}")
        return ""

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_name):
            os.remove(temp_file_name)


def parse_clingo_output(clingo_output):
    """
    Parse the Clingo output to extract val/2 atoms.

    Args:
    clingo_output (str): The output string from Clingo.

    Returns:
    set: A set of val/2 atoms extracted from the answer set.
    """
    val_atoms = set()
    inside_answer = False

    # Split the output by lines to find the answer set
    for line in clingo_output.splitlines():
        # Start parsing once we find the "Answer:" line
        if line.startswith("Answer:"):
            inside_answer = True
            continue

        # Stop processing when we hit summary lines
        if inside_answer and any(term in line for term in ["SATISFIABLE", "UNSATISFIABLE", "Models", "Calls", "Time", "CPU Time"]):
            inside_answer = False
            break

        # If inside an answer, process val atoms
        if inside_answer:
            symbols = line.strip().split()
            for symbol in symbols:
                if symbol.startswith("val(") and symbol.endswith(")"):
                    val_atoms.add(symbol)

    print("Extracted val atoms:", val_atoms)  # Debugging
    return val_atoms

def evaluate_program_and_extract_atoms(asp_program):
    """Evaluate ASP program and extract val/2 atoms from the answer set."""
    # Run Clingo as an external process and get the output
    output = run_clingo_external(asp_program)
    val_atoms = parse_clingo_output(output)

    return val_atoms