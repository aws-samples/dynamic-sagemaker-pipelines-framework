#!/bin/bash

# Check if the env.txt file exists
if [[ ! -f "env.txt" ]]; then
    echo "env.txt file does not exist"
    exit 1
fi

# Read the env.txt file line by line and export the variables
while read -r line; do
    export $line
    echo "export $line"
done < env.txt

# Display the exported variables
echo "Environment variables set:"
env | grep -E '^(SMP_)'