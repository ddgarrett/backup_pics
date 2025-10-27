import subprocess
import time
import signal

# Start the bash script as a subprocess
# shell=True is used for simplicity, but consider the security implications
process = subprocess.Popen(['sudo','bash', 'blink.sh'], shell=False) 

print("Bash script started. Waiting for 5 seconds...")
time.sleep(5)

print("Sending SIGTERM to the bash script...")
process.terminate() # Sends SIGTERM

# Wait for the bash script to finish its cleanup
# timeout added to prevent indefinite waiting
try:
    print("Waiting for the bash script to finish...")
    process.wait(timeout=5) 
    print("Bash script terminated gracefully after cleanup.")
except subprocess.TimeoutExpired:
    print("Bash script did not terminate within the timeout. Sending SIGKILL.")
    process.kill() # Sends SIGKILL if cleanup takes too long
    print("Bash script forcefully terminated.")