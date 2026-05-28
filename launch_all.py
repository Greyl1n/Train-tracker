import subprocess
import time
import os
import sys

# Define the trackers to launch
TRACKERS = [
    "hub.py",
    "rail_tracker.py",
    "road_tracker.py",
    "marine_tracker.py",
    "flight_tracker.py"
]

def launch():
    processes = []
    tracker_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Starting Traffic Tracker Services...")
    
    for tracker in TRACKERS:
        script_path = os.path.join(tracker_dir, tracker)
        print(f"  Starting {tracker}...")
        # Use sys.executable to ensure we use the same python interpreter
        # Set PYTHONIOENCODING to handle emoji output from child processes
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        p = subprocess.Popen(
            [sys.executable, script_path], 
            cwd=tracker_dir,
            env=env
        )
        processes.append(p)
        time.sleep(1) # Brief delay between starts

    print("\nAll services are starting!")
    print("Visit http://127.0.0.1:5000 for the Hub Portal.")
    print("Press Ctrl+C to stop all services.\n")

    try:
        while True:
            time.sleep(1)
            # Check if all processes have exited
            if all(p.poll() is not None for p in processes):
                print("\nAll processes have terminated.")
                break
    except KeyboardInterrupt:
        print("\nStopping all services...")
        for p in processes:
            p.terminate()
        print("Bye!")

if __name__ == "__main__":
    launch()
