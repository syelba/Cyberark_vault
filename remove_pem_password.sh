#!/bin/bash

# Script to extract certificate and remove password from key for Zabbix use

echo "Extracting certificate and private key from ../crt.pem..."
echo ""

# Extract the certificate (public part)
echo "1. Extracting certificate..."
openssl x509 -in ../crt.pem -out ../certificates/cert.pem

if [ $? -ne 0 ]; then
    echo "Error extracting certificate!"
    exit 1
fi

# Extract and decrypt the private key
echo "2. Extracting and decrypting private key..."
echo "   Enter the PEM password when prompted..."
openssl rsa -in ../crt.pem -out ../certificates/key.pem

if [ $? -ne 0 ]; then
    echo "Error extracting private key!"
    exit 1
fi

echo ""
echo "✓ Done! Created:"
echo "  - ../certificates/cert.pem (certificate)"
echo "  - ../certificates/key.pem (private key - unencrypted)"
echo ""
echo "Setting secure permissions..."
chmod 600 ../certificates/cert.pem ../certificates/key.pem

echo ""
echo "Update your Zabbix configuration to use:"
echo "  VaultTLSCertFile=/home/zabbix/CyberArk/certificates/cert.pem"
echo "  VaultTLSKeyFile=/home/zabbix/CyberArk/certificates/key.pem"
echo ""
echo "IMPORTANT: Protect these files!"
echo "  sudo chown zabbix:zabbix /home/zabbix/CyberArk/certificates/*.pem"
echo "  sudo chmod 600 /home/zabbix/CyberArk/certificates/*.pem"
