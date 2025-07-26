#!/bin/bash

# This script updates the Nginx configuration to allow for larger file uploads
# and then restarts the Nginx service to apply the changes.

# Exit immediately if a command exits with a non-zero status.
set -e

echo "1. Copying the updated Nginx configuration file..."
sudo cp /home/raghavendra_kaushik_iitkgp/paper_agent_2/paper-explainer-nginx.conf /etc/nginx/sites-available/paper-explainer.conf

echo "2. Testing the Nginx configuration for syntax errors..."
sudo nginx -t

echo "3. Restarting Nginx to apply the new configuration..."
sudo systemctl restart nginx

echo "Done. The Nginx configuration has been updated successfully."
