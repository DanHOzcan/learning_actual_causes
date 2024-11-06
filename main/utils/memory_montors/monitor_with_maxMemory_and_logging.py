import time

import psutil


def monitor_memory_usage_with_logging(pid, memory_usage_result, max_memory_gb, termination_event):
    parent = psutil.Process(pid)
    memory_usage_log = []
    max_memory_usage = 0

    max_memory_bytes = max_memory_gb * 1024 * 1024 * 1024  # Convert GB to bytes

    while not termination_event.is_set():
        if not parent.is_running():
            break  # Exit if the process is no longer running
        try:
            # Get memory usage of parent and all child processes
            memory_usage = parent.memory_info().rss
            for child in parent.children(recursive=True):
                try:
                    memory_usage += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue  # Process terminated between `children()` and `memory_info()`

            memory_usage_log.append(memory_usage)
            max_memory_usage = max(max_memory_usage, memory_usage)

            # Check if the memory usage exceeds the threshold in bytes
            if memory_usage > max_memory_bytes:
                print(
                    f"Terminating process due to excessive memory usage. Memory usage: {memory_usage / (1024 ** 2):.2f} MB")
                parent.kill()
                memory_usage_result.update({
                    'terminated_due_to': 'Memory',
                    'max_memory_usage': max_memory_usage,
                    'memory_usage_log': memory_usage_log
                })
                termination_event.set()
                return

            time.sleep(1)
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            break  # Process has terminated
        except Exception as e:
            print(f"Memory monitoring thread encountered an exception: {e}")
            break

    memory_usage_result.update({
        'max_memory_usage': max_memory_usage,
        'memory_usage_log': memory_usage_log
    })