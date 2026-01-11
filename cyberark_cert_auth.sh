#!/bin/bash

# CyberArk AAM Certificate-Based Authentication Script
# Configure these parameters according to your environment

# Application ID (format: IAP#-EnvironmentCode-Label-CERT)
# Example: 12345-PR-CUSTOMLABEL-CERT
appID="38427-PP-ILSSAFE-CERT"

# Safe name (must match the Common Name of your certificate)
safeName="AAM-PP-38427-ILSSAFE"

# Username associated with the account
userName="Operating System-UnmanagedAccounts-Linux-zabbix"

# Base URI for the Cert AAM API endpoint
baseURI="https://passwordvault.intel.com/AIMWebService/api/Accounts"

# Common Name of the certificate (must match safe name)
aamCertCommonName=""

# Path to certificate and key files (separated and unencrypted)
certFile="../certificates/cert.pem"
keyFile="../certificates/key.pem"

# Build the Query parameter for Zabbix format
# Format: Safe=safeName;Object=objectName
# URL-encode the query since userName contains spaces and special characters
query=$(printf "Safe=%s;Object=%s" "$safeName" "$userName" | jq -sRr @uri)

# Make the API call using curl with certificate authentication
# Using Query parameter (Zabbix format) with separate cert and key files
response=$(curl -v -X GET \
  --header "Content-Type: application/json" \
  --cert "$certFile" \
  --key "$keyFile" \
  "$baseURI?AppID=$appID&Query=$query" 2>&1)

exit_code=$?

# Display the response
echo "Exit code: $exit_code"
echo "Response:"
echo "$response"

# Parse JSON if successful
if [ $exit_code -eq 0 ]; then
    echo ""
    echo "Formatted JSON:"
    echo "$response" | jq '.' 2>/dev/null || echo "Could not parse JSON"
fi
