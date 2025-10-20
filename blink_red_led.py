import threading
import time
from led_controller import LedController

class TogglePowerLed(threading.Thread):
    """ Thread class that toggles the red (power) LED at regular intervals 
        and can be stopped gracefully."""
    
    def __init__(self, interval, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.interval = interval

        self.led_controller = LedController()

        # turn off green LED
        self.led_controller.set_act_led(True)

    def stop(self):
        """Sets the internal flag to signal the thread to stop."""
        self._stop_event.set()

    def stopped(self):
        """Checks if the stop event has been set."""
        return self._stop_event.is_set()

    def run(self):
        """The main task performed by the thread.
           Toggles the power LED at specified intervals until stopped.
        """

        while not self.stopped():
            self.led_controller.led_toggle()

             # wait for specified interval
            time.sleep(self.interval)

        # stopping, ensure Power LED is off
        # and Activity LED is on
        self.led_controller.set_power_led(False)
        self.led_controller.set_act_led(True)

if __name__ == "__main__":
 
    # Create and start the thread to blink red LED
    thread = TogglePowerLed(interval=0.5)
    thread.start()

    # Let threads run for a bit
    time.sleep(15)

    # Stop thread from the main thread
    print("\nMain thread: Signalling Worker to stop...")
    thread.stop()

    # Wait for the thread to finish its execution
    thread.join()

    print("\nMain thread: All threads have stopped.")
    


