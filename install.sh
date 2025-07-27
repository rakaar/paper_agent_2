#!/bin/bash

# Get the absolute path to the project directory
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

# Get the current user and group
CURRENT_USER=$(whoami)
CURRENT_GROUP=$(id -gn "$CURRENT_USER")

# Define the source template and the destination service file
TEMPLATE_FILE="${PROJECT_DIR}/paper-explainer.service.template"
SERVICE_FILE="${PROJECT_DIR}/paper-explainer.service"

# Check if the template file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Error: Template file not found at $TEMPLATE_FILE"
    exit 1
fi

# Replace placeholders in the template and create the new service file
echo "Generating service file from template..."
sed -e "s|__USER__|$CURRENT_USER|g" \
    -e "s|__GROUP__|$CURRENT_GROUP|g" \
    -e "s|__PATH_TO_PROJECT_REPO__|$PROJECT_DIR|g" \
    "$TEMPLATE_FILE" > "$SERVICE_FILE"

chmod 644 "$SERVICE_FILE"

echo "Successfully created ${SERVICE_FILE}"
echo ""
echo "Next steps:"
echo "1. Copy the environment file template: cp .env.example /etc/paper-explainer.env"
echo "2. Edit /etc/paper-explainer.env with your actual API keys."
echo "3. Secure the environment file: sudo chmod 600 /etc/paper-explainer.env"
echo "4. Move the service file to the systemd directory: sudo mv ${SERVICE_FILE} /etc/systemd/system/paper-explainer.service"
echo "5. Reload the systemd daemon, enable, and start the service:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable paper-explainer.service"
echo "   sudo systemctl start paper-explainer.service"
echo "   sudo systemctl status paper-explainer.service"
