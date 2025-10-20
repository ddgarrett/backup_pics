import threading
import time
from led_controller import LedController

class StoppableThread(threading.Thread):
    def __init__(self, interval, led, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.interval = interval

        led_controller = LedController()
        if led == "pwr":
            self.led_toggle = led_controller.toggle_power_led
        else:
            self.led_toggle = led_controller.toggle_act_led

    def stop(self):
        """Sets the internal flag to signal the thread to stop."""
        self._stop_event.set()

    def stopped(self):
        """Checks if the stop event has been set."""
        return self._stop_event.is_set()

    def run(self):
        """The main task performed by the thread."""
        print(f"Thread '{self.name}' starting...")
        counter = 0
        while not self.stopped():
            print(f"Thread '{self.name}' working... (iteration {counter})")
            time.sleep(self.interval)  # Simulate some work
            self.led_toggle()

        print(f"Thread '{self.name}' stopping.")

if __name__ == "__main__":
    # Create and start the first thread
    # thread1 = StoppableThread(name="Worker 1", interval=1, led="act")
    # thread1.start()

    led_controller = LedController()
    led_controller.set_power_led(False)
    led_controller.set_act_led(False)

    # Create and start the second thread
    thread2 = StoppableThread(name="Worker 2", interval=.5, led="pwr")
    thread2.start()

    # Let threads run for a bit
    time.sleep(15)

    # Stop thread1 from the main thread
    # print("\nMain thread: Signalling Worker 1 to stop...")
    thread2.stop()

    # Wait for both threads to finish their execution
    # thread1.join()
    thread2.join()

    print("\nMain thread: All threads have stopped.")
    
    led_controller.set_power_led(False)
    led_controller.set_act_led(True)

