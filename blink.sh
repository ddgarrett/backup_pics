#!/bin/bash

# Blink Red Power or Green ACT LED until terminated

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

# default color to red and blink rate to 0.25
color="red"
blink_rate="0.25"

# Process command-line arguments using a while loop
while [[ $# -gt 0 ]]; do
    case "$1" in
        --color)
            color="$2"
            shift 2
            ;;
        --blink_rate)
            blink_rate="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter passed: $1"
            exit 1
            ;;
    esac
done

# Check and validate parameter values
if [[ "$color" != "green" && "$color" != "red" ]]; then
    echo "Invalid color value: $color. Color must be 'green' or 'red'."
    exit 1
fi
if ! [[ "$blink_rate" =~ ^[0-9]*\.?[0-9]+$ ]]; then
    echo "Invalid blink_rate value: $blink_rate. Must be a decimal number."
    exit 1
fi

# set LED based on color
if [[ "$color" == "green" ]]; then
    LED="${ACT_LED}"
else
    LED="${PWR_LED}"
fi

# Turn off ACT and PWR LED
echo 1 | sudo tee "${ACT_LED}/brightness" > /dev/null # For Pi 5, ACT is active-low, so 1 turns it off
echo 0 | sudo tee "${PWR_LED}/brightness" > /dev/null # For Pi 5, PWR is active-low, so 1 turns it off

echo "Bash script is running Color: $color, Blink rate: $blink_rate"

# Blink LED until terminated
while true; do
    # Turn on (or off) LED
    echo 1 | sudo tee "${LED}/brightness" > /dev/null
    sleep ${blink_rate}
    # Turn off (or on) LED
    echo 0 | sudo tee "${LED}/brightness" > /dev/null
    sleep ${blink_rate}
done

echo "blink.sh Should never reach here."