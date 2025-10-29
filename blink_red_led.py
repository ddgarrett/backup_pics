import os
import subprocess
import time

class TogglePowerLed():
    """ Class that toggles the red (power) LED 
        using blink.sh shell subprocess
    """
    
    def __init__(self):
        """ Start Shell subprocess to blink red LED """
        script_dir = os.path.dirname(os.path.realpath(__file__))
        script = os.path.join(script_dir, "blink.sh")
        self._process = subprocess.Popen(['sudo','bash', script], shell=False)


    def stop(self):
        """Stop shell subprocess """   

        print("Sending SIGTERM to the bash script...")
        self._process.terminate() # Sends SIGTERM

        # Wait for the bash script to finish its cleanup
        # timeout added to prevent indefinite waiting
        try:
            print("Waiting for the bash script to finish...")
            self._process.wait(timeout=5) 
            print("Bash script terminated gracefully after cleanup.")
        except subprocess.TimeoutExpired:
            print("Bash script did not terminate within the timeout. Sending SIGKILL.")
            self._process.kill() # Sends SIGKILL if cleanup takes too long
            print("Bash script forcefully terminated.")


if __name__ == "__main__":
 
    # Create subprocess to blink red LED
    led  = TogglePowerLed()

    # Let subprocess run for a bit
    time.sleep(15)

    # Stop subprocess
    print("\nMain thread: Signalling Worker to stop...")
    led.stop()

