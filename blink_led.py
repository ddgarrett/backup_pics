import os
import subprocess
import time

class ToggleLed():
    """ Class that toggles the red (power) LED 
        using blink.sh shell subprocess
    """
    
    def __init__(self,color="red",rate=0.25):
        """ Start Shell subprocess to blink red LED """
        script_dir = os.path.dirname(os.path.realpath(__file__))
        script = os.path.join(script_dir, "blink.sh")
        self._process = subprocess.Popen(
            ['sudo','bash', script,
             '--color', color,
             '--blink_rate', str(rate)], 
            stdout=subprocess.PIPE, # hide stdout and stderr
            stderr=subprocess.PIPE,
            text=True,
            shell=False)

    def stop(self):
        """Stop shell subprocess """   
        # print("Sending SIGTERM to the bash script...")
        self._process.terminate() # Sends SIGTERM

        # Wait for the bash script to finish its cleanup
        # timeout added to prevent indefinite waiting
        try:
            # print("Waiting for the bash script to finish...")
            self._process.wait(timeout=5) 
            # print("Bash script terminated gracefully after cleanup.")
        except subprocess.TimeoutExpired:
            print("Bash script did not terminate within the timeout. Sending SIGKILL.")
            self._process.kill() # Sends SIGKILL if cleanup takes too long
            print("Bash script forcefully terminated.")

if __name__ == "__main__":
    print("\nMain thread: Blink Red LED...")

    # Create subprocess to blink red LED
    led  = ToggleLed(color="red",rate=0.25)

    # Let subprocess run for a bit
    time.sleep(5)

    # Stop subprocess
    led.stop()

    print("\nMain thread: Blink Green LED...")
    # Create subprocess to blink green LED
    led  = ToggleLed(color="green",rate=0.75)

    # Let subprocess run for a bit
    time.sleep(5)

    # Stop subprocess
    print("\nMain thread: Signalling Worker to stop...")
    led.stop()

