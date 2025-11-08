#!/bin/bash

# Set default values for optional parameters
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

# Display the final parameter values
echo "Script will run with the following parameters:"
echo "Color: $color"
echo "Blink rate: $blink_rate"

# The rest of your script logic would go here
