#!/bin/bash

SERVER_NAME=$(hostname)

# Check if .env directory exists and contains a valid virtual environment
if [ ! -f .env/bin/activate ]; then
    echo "Setting up python environment"
    sudo apt update
    sudo apt install python3.12-venv -y
    python3 -m venv .env
fi

# Check if awscrt is installed
if ! .env/bin/pip freeze | grep -q "awscrt"; then
    echo "Installing python requirements"
    .env/bin/pip install -r requirements.txt
fi

# Run the script
echo "Running python script"
.env/bin/python connect.py --endpoint "$1" \
        --root-ca root-CA.crt \
        --cert "$SERVER_NAME.pem.crt" \
        --key "$SERVER_NAME-private.key" \
        --client-id onomondoPubSub \
        --topic onomondo/youtube/demo \
        --message "$2" \
        --count 0

