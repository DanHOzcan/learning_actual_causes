from typing import Optional, Dict
import subprocess
def run_ilasp_task(task_file: str, flags: Optional[str] = None) -> Dict[str, str]:
    """
    Run an ILASP task and optional flags, capturing the output in real-time.

    Args:
        task_file (str): The path to the ILASP task file.
        flags (str, optional): Optional flags to pass to ILASP as a single string.

    Returns:
        Dict[str, str]: A dictionary containing the captured output and timing information.
    """
    ilasp_path = "/homes/dozcan/bin/ILASP"

    try:

        # Construct the ILASP command
        command = [ilasp_path, '--version=4', task_file]

        # If flags are provided, add them to the command
        if flags:
            command.extend(flags.split())

        # Run the ILASP command with Popen and capture the output in real-time
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                                   bufsize=0)

        # Capture the output
        output_lines = []
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                line = output.strip()
                print(line)  # Print each line of output
                output_lines.append(line)  # Save the output to a list

        # Capture and print any remaining error output
        rc = process.poll()
        if rc != 0:
            error_output = process.stderr.read()
            print(f"Error: ILASP task failed with return code {rc}")
            print(f"Error output: {error_output}")
            output_lines.append(error_output)

        # Combine all lines into a single string
        output_str = '\n'.join(output_lines)

        return {
            'output': output_str,
        }

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {
            'output': str(e),
        }


