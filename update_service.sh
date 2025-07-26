#!/bin/bash

# This script updates the systemd service file for the Paper Explainer app,
# reloads the systemd daemon, and restarts the service to apply the changes.

# Exit immediately if a command exits with a non-zero status.
set -e

echo "1. Copying the updated systemd service file..."
sudo cp /home/raghavendra_kaushik_iitkgp/paper_agent_2/paper-explainer.service /etc/systemd/system/paper-explainer.service

echo "2. Reloading the systemd daemon to recognize the changes..."
sudo systemctl daemon-reload

echo "3. Restarting the Paper Explainer application service..."
sudo systemctl restart paper-explainer.service

echo "Done. The service has been updated and restarted successfully."
