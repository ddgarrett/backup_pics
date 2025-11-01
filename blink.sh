#!/bin/bash

# Blink Red Power LED until terminated

# Define LED paths (these might vary slightly depending on your specific kernel version)
ACT_LED="/sys/class/leds/ACT" # green light
PWR_LED="/sys/class/leds/PWR" # red light

# Function to perform cleanup
cleanup() {
    # echo "Performing cleanup in bash script..."
    echo 0 | sudo tee "${PWR_LED}/brightness" > /dev/null # Turn off PWR LED
    echo 0 | sudo tee "${ACT_LED}/brightness" > /dev/null # Turn on ACT LED
    exit 0 # Exit after cleanup
}

# Trap SIGTERM signal and call the cleanup function
trap cleanup SIGTERM

# Turn off ACT LED
echo 1 | sudo tee "${ACT_LED}/brightness" > /dev/null # For Pi 5, ACT is active-low, so 1 turns it off

# echo "Bash script is running..."
# Blink PWR LED until terminated
while true; do
    # Turn on PWR LED
    echo 1 | sudo tee "${PWR_LED}/brightness" > /dev/null
    sleep 0.25
    # Turn off PWR LED
    echo 0 | sudo tee "${PWR_LED}/brightness" > /dev/null
    sleep 0.25
done

echo "blink.sh Should never reach here."