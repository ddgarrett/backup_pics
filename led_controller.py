import time

# Define the path to the ACT LED brightness control file
ACT_LED_BRIGHTNESS_PATH = "/sys/class/leds/ACT/brightness"
PWR_LED_BRIGHTNESS_PATH = "/sys/class/leds/PWR/brightness"

class LedController:
    """ Control Power and Activity LEDs on a Raspberry Pi 5
        NOTE: Must be run as suodo to have permission to write to LED control files
    """

    def __init__(self):
        """ Initialize the LED controller """
        self.act_on = True
        self.power_on = False

    def set_act_led(self, state: bool):
        """ Set the Activity LED state """
        self.act_on = state
        brightness = '0' if state else '1' # Inverted logic for ACT LED

        try:
            with open(ACT_LED_BRIGHTNESS_PATH, 'w') as f:
                f.write(brightness)
                f.flush() # Ensure the change is written immediately
        except IOError as e:
            print(f"Error controlling ACT LED: {e}")
            print("Ensure you have appropriate permissions (e.g., run with sudo).")

    def set_power_led(self, state: bool):
        """ Set the Power LED state """
        self.power_on = state
        brightness = '1' if state else '0'
        try:
            with open(PWR_LED_BRIGHTNESS_PATH, 'w') as f:
                f.write(brightness)
                f.flush() # Ensure the change is written immediately
        except IOError as e:
            print(f"Error controlling PWR LED: {e}")
            print("Ensure you have appropriate permissions (e.g., run with sudo).")

    def toggle_act_led(self):
        """ Toggle the Activity LED state """
        self.set_act_led(not self.act_on)

    def toggle_power_led(self):
        """ Toggle the Power LED state """
        self.set_power_led(not self.power_on)

if __name__ == "__main__":

    controller = LedController()
    try:
        print("Blinking the ACT LED 5 times...")
        controller.set_act_led(False)  # Ensure ACT LED starts off
        for _ in range(5):
            print("turn on" )
            controller.toggle_act_led()  # Turn on
            time.sleep(0.5)
            print("turn off")
            controller.toggle_act_led()  # Turn off
            time.sleep(0.5)
            
        print("Blinking the PWR LED 5 times...")
        for _ in range(5):
            print("turn on" )
            controller.toggle_power_led()  # Turn on
            time.sleep(0.5)
            print("turn off")
            controller.toggle_power_led()  # Turn off
            time.sleep(0.5)

        print("\nProgram interrupted by user.")
    finally:
        print("Restoring default ACT LED state...")
        controller.set_act_led(True)
        controller.set_power_led(False)
        