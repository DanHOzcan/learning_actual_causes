import time
import psutil

def monitor_memory(stop_event, peak_memory):
    """Prints and logs the peak memory usage of the process and its children at one-second intervals."""
    process = psutil.Process()
    max_memory_usage = 0  # Track maximum memory usage

    while not stop_event.is_set():
        # Get memory usage of the main process
        total_memory = process.memory_info().rss

        # Add memory usage of all child processes
        for child in process.children(recursive=True):
            try:
                total_memory += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.ZombieProcess):

                continue

        # Update the peak memory usage if current usage is higher
        max_memory_usage = max(max_memory_usage, total_memory)
        print(f"Current total memory usage (including children): {total_memory / (1024 ** 2):.2f} MB")
        time.sleep(2)

    # Store the peak memory usage in the shared list or value
    peak_memory[0] = max_memory_usage / (1024 ** 2)  # Convert to MB
