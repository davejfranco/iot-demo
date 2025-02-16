#!/usr/bin/env bash
# stop script on error
set -e

if [ ! -f .env ]; then
    echo "Setting up python environment"
    sudo apt install python3.12-venv
    python3 -m venv .env
fi

echo "Activating python environment"
source .env/bin/activate
echo "Installing python requirements"
pip install -r requirements.txt

echo "Running python script"
python3 connect.py --endpoint ajqo6eprnfcvq-ats.iot.eu-central-1.amazonaws.com \
        --root-ca root-CA.crt \
        --cert multipass-try-certificate.pem.crt \
        --key multipass-try-private.key \
        --client-id basicPubSub \
        --topic sdk/test/python \
        --message 'Hello Mother fucker' \
        --count 0
