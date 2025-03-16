#!/bin/bash
# Azure deployment script for Gimeno Family App

set -e  # Exit on error

echo "Starting deployment to Azure..."

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged in to Azure
echo "Checking Azure login status..."
az account show &> /dev/null || {
    echo "Not logged in to Azure. Please run 'az login' first."
    exit 1
}

# Configuration
APP_NAME="gimenofamilyapp"
RESOURCE_GROUP="GimenoFamilyApp"
LOCATION="eastus"
ENVIRONMENT="production"

# Ensure requirements.txt is up to date
echo "Checking requirements.txt..."
if [ ! -f requirements.txt ]; then
    echo "requirements.txt not found. Creating..."
    pip freeze > requirements.txt
else
    echo "requirements.txt exists. Make sure it's up to date."
fi

# Make sure itsdangerous is in requirements.txt
if ! grep -q "itsdangerous" requirements.txt; then
    echo "Adding itsdangerous to requirements.txt..."
    echo "itsdangerous>=2.0.0" >> requirements.txt
fi

# Create .deployment file for Azure App Service
echo "Creating .deployment file..."
cat > .deployment << EOF
[config]
SCM_DO_BUILD_DURING_DEPLOYMENT=true
EOF

# Create startup command file
echo "Creating startup command file..."
cat > startup.txt << EOF
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind=0.0.0.0:8000
EOF

# Create or update .env file for production
echo "Creating production .env file..."
cat > .env.production << EOF
ENVIRONMENT=production
DB_NAME=fms_prod
DB_USER=jasonadmin
DB_PASSWORD=Thisisfortigraandtaz!
DB_HOST=gimenopgsql.postgres.database.azure.com
DB_PORT=5432
DB_SSL_MODE=require
SECRET_KEY=your-production-secret-key-here
EOF

echo "NOTE: Please review .env.production and update any sensitive values before deploying."
echo "      This file is not committed to version control."

# Create or update web.config for Azure App Service
echo "Creating web.config file..."
cat > web.config << EOF
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="httpPlatformHandler" path="*" verb="*" modules="httpPlatformHandler" resourceType="Unspecified" />
    </handlers>
    <httpPlatform processPath="%home%\site\wwwroot\env\Scripts\python.exe"
                  arguments="%home%\site\wwwroot\startup.txt"
                  stdoutLogEnabled="true"
                  stdoutLogFile="%home%\LogFiles\stdout"
                  startupTimeLimit="120"
                  processesPerApplication="1" />
    <rewrite>
      <rules>
        <rule name="Static Files" stopProcessing="true">
          <match url="^static/.*" ignoreCase="true" />
          <action type="Rewrite" url="{R:0}" />
        </rule>
        <rule name="Configure Python" stopProcessing="true">
          <match url="(.*)" ignoreCase="true" />
          <action type="Rewrite" url="/" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
EOF

# Create a simple README for deployment
echo "Creating deployment README..."
cat > DEPLOY.md << EOF
# Deployment Instructions

This application is configured for deployment to Azure App Service.

## Prerequisites

- Azure CLI installed and logged in
- Azure App Service plan
- Azure PostgreSQL database

## Deployment Steps

1. Run the deployment script: \`./deploy_to_azure.sh\`
2. Review the logs for any errors
3. Access the application at https://${APP_NAME}.azurewebsites.net

## Troubleshooting

- Check the diagnostic endpoints at:
  - https://${APP_NAME}.azurewebsites.net/api/diagnostics/db/status
  - https://${APP_NAME}.azurewebsites.net/api/diagnostics/db/write-test
  - https://${APP_NAME}.azurewebsites.net/api/diagnostics/request-info
- Review logs in the Azure portal
EOF

echo "Deployment files prepared."
echo "To deploy to Azure App Service, run:"
echo "az webapp up --name $APP_NAME --resource-group $RESOURCE_GROUP --location $LOCATION --sku B1"
echo ""
echo "After deployment, you can check the diagnostic endpoints at:"
echo "https://${APP_NAME}.azurewebsites.net/api/diagnostics/db/status"
echo "https://${APP_NAME}.azurewebsites.net/api/diagnostics/db/write-test"
echo "https://${APP_NAME}.azurewebsites.net/api/diagnostics/request-info"
echo ""
echo "Deployment preparation complete!" 