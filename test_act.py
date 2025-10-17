import time

"""
raspberry pi 5 python program to control on-board ACT (activity) LED
"""


# Define the path to the ACT LED brightness control file
ACT_LED_BRIGHTNESS_PATH = "/sys/class/leds/ACT/brightness"
ACT_LED_TRIGGER_PATH = "/sys/class/leds/ACT/trigger"

PWR_LED_BRIGHTNESS_PATH = "/sys/class/leds/PWR/brightness"

def set_act_led_state(state):
    """
    Sets the state of the ACT LED (0 for off, 1 for on).
    """
    try:
        with open(ACT_LED_BRIGHTNESS_PATH, 'w') as f:
            f.write(str(state))
            f.flush() # Ensure the change is written immediately
    except IOError as e:
        print(f"Error controlling ACT LED: {e}")
        print("Ensure you have appropriate permissions (e.g., run with sudo).")

    time.sleep(0.5)

    try:
        with open(PWR_LED_BRIGHTNESS_PATH, 'w') as f:
            f.write(str(state))
            f.flush() # Ensure the change is written immediately
    except IOError as e:
        print(f"Error controlling PWR LED: {e}")
        print("Ensure you have appropriate permissions (e.g., run with sudo).")

def restore_default_trigger():
    """
    Restores the default 'mmc0' trigger for the ACT LED.
    """
    try:
        with open(ACT_LED_TRIGGER_PATH, 'w') as f:
            f.write("mmc0") # Default trigger for SD card activity
            f.flush()
    except IOError as e:
        print(f"Error restoring ACT LED trigger: {e}")

if __name__ == "__main__":
    print("Taking control of the ACT LED...")
    # First, disable the default trigger to allow manual control
    try:
        with open(ACT_LED_TRIGGER_PATH, 'w') as f:
            f.write("none")
            f.flush()
    except IOError as e:
        print(f"Error disabling ACT LED trigger: {e}")
        print("Ensure you have appropriate permissions (e.g., run with sudo).")
        exit()

    try:
        print("Blinking the ACT LED 5 times...")
        for _ in range(5):
            print("turn on" )
            set_act_led_state(1)  # Turn on
            time.sleep(0.5)
            print("turn off")  
            set_act_led_state(0)  # Turn off
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    finally:
        print("Restoring default ACT LED trigger...")
        restore_default_trigger()
        print("ACT LED control released.")