# Zabbix CyberArk Vault Integration Setup Guide

**Version:** Zabbix 6.4 / 7.2  
**Date:** December 31, 2025  
**Vault Provider:** CyberArk AIM Web Service

---

## Overview

This guide provides step-by-step instructions to configure Zabbix Server and Web Interface to retrieve database credentials from CyberArk vault instead of storing passwords in clear text.

---

## Prerequisites

1. **CyberArk Vault Access:**
   - CyberArk vault URL (e.g., `https://passwordvault.intel.com`)
   - Application ID (AppID)
   - Safe name
   - Object name
   - Client certificate (`.pem` format)
   - Private key (`.pem` format)

2. **Database User:**
   - MySQL/PostgreSQL database username
   - Vault must return username and password

3. **System Requirements:**
   - Zabbix 6.4 or higher
   - OpenSSL support compiled in Zabbix
   - PHP with curl and openssl extensions

---

## Step 1: Prepare Client Certificates

### 1.1 Obtain Certificates from CyberArk

You should have received:
- Client certificate file (e.g., `cert.pem`)
- Private key file (e.g., `key.pem`)

### 1.2 Create Certificate Directory Structure

```bash
sudo mkdir -p /var/lib/zabbix/ssl/certs
sudo mkdir -p /var/lib/zabbix/ssl/keys
```

### 1.3 Combine Certificate and Key

CyberArk integration requires a combined certificate file:

```bash
# Copy certificates to working directory
cp cert.pem /tmp/
cp key.pem /tmp/

# Combine key and certificate into one file
cat /tmp/key.pem /tmp/cert.pem > /tmp/cyberark.pem

# Move to Zabbix SSL directory
sudo mv /tmp/cyberark.pem /var/lib/zabbix/ssl/certs/

# Clean up temporary files
rm /tmp/cert.pem /tmp/key.pem
```

### 1.4 Set Proper Permissions

```bash
sudo chown -R zabbix:zabbix /var/lib/zabbix/ssl
sudo chmod 755 /var/lib/zabbix/ssl
sudo chmod 755 /var/lib/zabbix/ssl/certs
sudo chmod 644 /var/lib/zabbix/ssl/certs/cyberark.pem
```

### 1.5 Verify Certificate Access

```bash
# Test as zabbix user
sudo -u zabbix cat /var/lib/zabbix/ssl/certs/cyberark.pem > /dev/null && echo "OK" || echo "FAILED"

# Test as www-data user (for web interface)
sudo -u www-data cat /var/lib/zabbix/ssl/certs/cyberark.pem > /dev/null && echo "OK" || echo "FAILED"
```

---

## Step 2: Configure Database User

### 2.1 Check Vault Response

Test the CyberArk vault to see what username it returns:

```bash
curl -k --cert /var/lib/zabbix/ssl/certs/cyberark.pem \
  'https://passwordvault.intel.com/AIMWebService/api/Accounts?AppID=YOUR_APP_ID&Query=Safe=YOUR_SAFE;Object=YOUR_OBJECT_NAME'
```

**Expected Response:**
```json
{
  "Content": "password_here",
  "UserName": "returned_username",
  "PolicyID": "...",
  ...
}
```

### 2.2 Create or Update MySQL User

Use the username returned by vault:

```bash
sudo mysql << 'EOF'
-- If vault returns 'zabbix' as username:
ALTER USER 'zabbix'@'localhost' IDENTIFIED BY 'vault_password_here';
FLUSH PRIVILEGES;

-- OR if vault returns different username like 'zabbix_server_database':
CREATE USER IF NOT EXISTS 'zabbix_server_database'@'localhost' IDENTIFIED BY 'vault_password_here';
GRANT ALL PRIVILEGES ON zabbix.* TO 'zabbix_server_database'@'localhost';
FLUSH PRIVILEGES;
EOF
```

**Important:** The database username must match what the vault returns in the `UserName` field.

---

## Step 3: Configure Zabbix Server

### 3.1 Backup Current Configuration

```bash
sudo cp /etc/zabbix/zabbix_server.conf /etc/zabbix/zabbix_server.conf.backup.$(date +%Y%m%d)
```

### 3.2 Edit Zabbix Server Configuration

```bash
sudo nano /etc/zabbix/zabbix_server.conf
```

### 3.3 Configure Database and Vault Parameters

Find and modify the following parameters:

```ini
### DATABASE CONFIGURATION ###

# DBName is MANDATORY even with vault
DBName=zabbix

# DBHost (uncomment if needed)
# DBHost=localhost

# DBUser should be COMMENTED OUT when using CyberArk vault
# (vault provides both username and password)
#DBUser=zabbix

# DBPassword should be COMMENTED OUT when using vault
#DBPassword=

### VAULT CONFIGURATION ###

# Vault provider (CyberArk)
Vault=CyberArk

# Vault URL (base URL only, no API path)
VaultURL=https://passwordvault.intel.com

# Vault DB Path (URL-encode spaces as %20)
# Format: AppID=<id>&Query=Safe=<safe>;Object=<object>
VaultDBPath=AppID=38427-PP-ILSSAFE-CERT&Query=Safe=AAM-PP-38427-ILSSAFE;Object=Operating%20System-UnmanagedAccounts-Linux-zabbix

# Vault TLS Certificate (filename only when using SSLCertLocation)
VaultTLSCertFile=cyberark.pem

# Vault TLS Key File (leave commented if using combined cert)
#VaultTLSKeyFile=

# SSL Certificate Location
SSLCertLocation=/var/lib/zabbix/ssl/certs
```

**Important Notes:**
- `DBName` is mandatory even with vault
- `DBUser` must be commented out (vault provides it)
- `DBPassword` must be commented out (vault provides it)
- Encode spaces in `VaultDBPath` as `%20`
- `VaultURL` should be base URL only (no `/AIMWebService/api/Accounts`)
- Use relative filename for `VaultTLSCertFile` when `SSLCertLocation` is set

### 3.4 Validate Configuration

```bash
sudo zabbix_server -c /etc/zabbix/zabbix_server.conf -R config_cache_reload 2>&1 | head -20
```

Expected output: `Validation successful`

### 3.5 Restart Zabbix Server

```bash
sudo systemctl restart zabbix-server
sudo systemctl status zabbix-server
```

### 3.6 Check Logs

```bash
sudo tail -50 /var/log/zabbix/zabbix_server.log
```

Look for successful database connection. If you see vault errors, check:
- Certificate permissions
- VaultDBPath encoding (spaces must be `%20`)
- Database user matches vault's UserName response

---

## Step 4: Configure Zabbix Web Interface

### 4.1 Backup Web Configuration

```bash
sudo cp /etc/zabbix/web/zabbix.conf.php /etc/zabbix/web/zabbix.conf.php.backup.$(date +%Y%m%d)
```

### 4.2 Edit Web Configuration

```bash
sudo nano /etc/zabbix/web/zabbix.conf.php
```

### 4.3 Configure PHP Vault Parameters

```php
<?php
// Zabbix GUI configuration file.

$DB['TYPE']                     = 'MYSQL';
$DB['SERVER']                   = 'localhost';
$DB['PORT']                     = '0';
$DB['DATABASE']                 = 'zabbix';

// IMPORTANT: Leave USER and PASSWORD empty when using vault
$DB['USER']                     = '';
$DB['PASSWORD']                 = '';

// Schema name. Used for PostgreSQL.
$DB['SCHEMA']                   = '';

// Used for TLS connection.
$DB['ENCRYPTION']               = false;
$DB['KEY_FILE']                 = '';
$DB['CERT_FILE']                = '';
$DB['CA_FILE']                  = '';
$DB['VERIFY_HOST']              = false;
$DB['CIPHER_LIST']              = '';

// Vault configuration
$DB['VAULT']                    = 'CyberArk';
$DB['VAULT_URL']                = 'https://passwordvault.intel.com';
$DB['VAULT_PREFIX']             = '/AIMWebService/api/Accounts?';
$DB['VAULT_DB_PATH']            = 'AppID=38427-PP-ILSSAFE-CERT&Query=Safe=AAM-PP-38427-ILSSAFE;Object=Operating%20System-UnmanagedAccounts-Linux-zabbix';
$DB['VAULT_TOKEN']              = '';
$DB['VAULT_CERT_FILE']          = '/var/lib/zabbix/ssl/certs/cyberark.pem';
$DB['VAULT_KEY_FILE']           = '/var/lib/zabbix/ssl/certs/cyberark.pem';
$DB['VAULT_CACHE']              = false;

// Rest of configuration...
$DB['DOUBLE_IEEE754']           = true;
$ZBX_SERVER_NAME                = 'Zabbix';
?>
```

**Critical Parameters for Web Interface:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| `$DB['USER']` | `''` | MUST be empty for vault |
| `$DB['PASSWORD']` | `''` | MUST be empty for vault |
| `$DB['VAULT']` | `'CyberArk'` | Enable CyberArk vault |
| `$DB['VAULT_URL']` | `https://passwordvault.intel.com` | Base URL only |
| `$DB['VAULT_PREFIX']` | `/AIMWebService/api/Accounts?` | **REQUIRED** for CyberArk |
| `$DB['VAULT_DB_PATH']` | Full query string | URL-encode spaces |
| `$DB['VAULT_CERT_FILE']` | Absolute path | Combined cert file |
| `$DB['VAULT_KEY_FILE']` | Absolute path | Same as cert file |

### 4.4 Set Configuration File Permissions

```bash
sudo chown www-data:www-data /etc/zabbix/web/zabbix.conf.php
sudo chmod 600 /etc/zabbix/web/zabbix.conf.php
```

### 4.5 Verify PHP Syntax

```bash
sudo php -l /etc/zabbix/web/zabbix.conf.php
```

Expected: `No syntax errors detected`

### 4.6 Restart Web Server

```bash
# For Apache
sudo systemctl restart apache2

# For Nginx with PHP-FPM
sudo systemctl restart php-fpm
sudo systemctl restart nginx
```

---

## Step 5: Verification and Testing

### 5.1 Test Vault Connection from Command Line

**Test as root:**
```bash
curl -k --cert /var/lib/zabbix/ssl/certs/cyberark.pem \
  'https://passwordvault.intel.com/AIMWebService/api/Accounts?AppID=YOUR_APP_ID&Query=Safe=YOUR_SAFE;Object=YOUR_OBJECT'
```

**Test as www-data (PHP test):**
```bash
sudo cat > /tmp/test_vault.php << 'EOF'
<?php
$url = 'https://passwordvault.intel.com/AIMWebService/api/Accounts?AppID=YOUR_APP_ID&Query=Safe=YOUR_SAFE;Object=YOUR_OBJECT';
$cert = '/var/lib/zabbix/ssl/certs/cyberark.pem';

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_SSLCERT, $cert);
curl_setopt($ch, CURLOPT_SSLKEY, $cert);

$response = curl_exec($ch);
echo "HTTP Code: " . curl_getinfo($ch, CURLINFO_HTTP_CODE) . "\n";
echo "Error: " . curl_error($ch) . "\n";
echo "Response: " . substr($response, 0, 200) . "\n";
curl_close($ch);
?>
EOF

sudo -u www-data php /tmp/test_vault.php
```

### 5.2 Check Zabbix Server Status

```bash
sudo systemctl status zabbix-server --no-pager
```

Should show: `Active: active (running)`

### 5.3 Check Zabbix Server Logs

```bash
sudo tail -100 /var/log/zabbix/zabbix_server.log | grep -i "vault\|database"
```

Look for successful database connection, no vault errors.

### 5.4 Test Web Interface

```bash
curl -k https://localhost/zabbix/
```

Should return the login page (not a vault error page).

Open in browser: `https://your-zabbix-server/zabbix/`

You should see the login page without database errors.

---

## Common Issues and Troubleshooting

### Issue 1: "missing mandatory parameter DBName"

**Cause:** DBName is commented out  
**Solution:** Uncomment `DBName=zabbix` in `zabbix_server.conf`

### Issue 2: "DBUser cannot be used when VaultDBPath is defined"

**Cause:** DBUser is uncommented  
**Solution:** Comment out `DBUser` in server config when using CyberArk vault

### Issue 3: "URL using bad/illegal format"

**Causes:**
- Semicolons in URL not properly formatted
- Spaces not URL-encoded
- Line wrapping in config file

**Solutions:**
- Encode spaces as `%20` in VaultDBPath
- Ensure VaultDBPath is on a single line
- For server config: VaultURL should NOT include `/AIMWebService/api/Accounts`
- For web config: Use VAULT_PREFIX parameter

### Issue 4: "Unable to load database credentials from Vault" (Web Interface)

**Causes:**
- Missing `VAULT_PREFIX` parameter in PHP config
- Empty `VAULT_KEY_FILE` parameter
- Wrong certificate path

**Solutions:**
```php
// Add these to zabbix.conf.php:
$DB['VAULT_PREFIX']    = '/AIMWebService/api/Accounts?';
$DB['VAULT_CERT_FILE'] = '/var/lib/zabbix/ssl/certs/cyberark.pem';
$DB['VAULT_KEY_FILE']  = '/var/lib/zabbix/ssl/certs/cyberark.pem';
```

### Issue 5: "could not load PEM client certificate"

**Causes:**
- Certificate file permissions wrong
- Certificate path incorrect
- Certificate not in proper PEM format

**Solutions:**
```bash
# Check permissions
ls -la /var/lib/zabbix/ssl/certs/cyberark.pem

# Should be readable by zabbix and www-data
sudo chmod 644 /var/lib/zabbix/ssl/certs/cyberark.pem

# Verify certificate format
openssl x509 -in /var/lib/zabbix/ssl/certs/cyberark.pem -text -noout
```

### Issue 6: "Access denied for user" with vault configured

**Cause:** Database username doesn't match vault's UserName response

**Solution:**
1. Check what username vault returns:
```bash
curl -k --cert /var/lib/zabbix/ssl/certs/cyberark.pem \
  'https://vault-url/...' | grep -o '"UserName":"[^"]*"'
```

2. Create/update database user to match:
```sql
CREATE USER 'returned_username'@'localhost' IDENTIFIED BY 'password_from_vault';
GRANT ALL PRIVILEGES ON zabbix.* TO 'returned_username'@'localhost';
```

### Issue 7: "Password object matching query was not found" (Error APPAP004E)

**Error Message:**
```
{"ErrorCode":"APPAP004E","ErrorMsg":"Password object matching query [Safe=AAM-PP-38427-ILSSAFE;Object=Operating System-UnmanagedAccounts-Linux-zabbix] was not found"}
```

**Cause:** The vault object specified in VaultDBPath does not exist in CyberArk

**Solutions:**
1. Verify object name exists in CyberArk vault:
   - Contact CyberArk administrator
   - Confirm exact object name (case-sensitive)
   - Ensure object is in specified Safe

2. Test vault with correct object name:
```bash
curl -k --cert /var/lib/zabbix/ssl/certs/cyberark.pem \
  'https://passwordvault.intel.com/AIMWebService/api/Accounts?AppID=38427-PP-ILSSAFE-CERT&Query=Safe=AAM-PP-38427-ILSSAFE;Object=Operating%20System-UnmanagedAccounts-Linux-zabbix'
```

3. If object doesn't exist, ask CyberArk admin to create it with:
   - Object name: `Operating System-UnmanagedAccounts-Linux-zabbix`
   - UserName: `zabbix`
   - Content: Database password
   - Safe: `AAM-PP-38427-ILSSAFE`

### Issue 8: "Vault connection failed"

**Causes:**
- Network connectivity to vault
- Certificate not trusted
- Firewall blocking connection

**Solutions:**
```bash
# Test network connectivity
curl -k https://passwordvault.intel.com

# Test with certificate
curl -k --cert /var/lib/zabbix/ssl/certs/cyberark.pem \
     --key /var/lib/zabbix/ssl/certs/cyberark.pem \
     https://passwordvault.intel.com/AIMWebService/api/Accounts
```

---

## Configuration Templates

### Zabbix Server Configuration Template

```ini
# /etc/zabbix/zabbix_server.conf

# Database
DBName=zabbix
#DBUser=zabbix
#DBPassword=

# Vault
Vault=CyberArk
VaultURL=https://passwordvault.intel.com
VaultDBPath=AppID=<YOUR_APP_ID>&Query=Safe=<YOUR_SAFE>;Object=<YOUR_OBJECT>
VaultTLSCertFile=cyberark.pem
#VaultTLSKeyFile=

# SSL
SSLCertLocation=/var/lib/zabbix/ssl/certs
```

### Zabbix Web Configuration Template

```php
<?php
// /etc/zabbix/web/zabbix.conf.php

$DB['TYPE']           = 'MYSQL';
$DB['SERVER']         = 'localhost';
$DB['PORT']           = '0';
$DB['DATABASE']       = 'zabbix';
$DB['USER']           = '';
$DB['PASSWORD']       = '';

$DB['VAULT']          = 'CyberArk';
$DB['VAULT_URL']      = 'https://passwordvault.intel.com';
$DB['VAULT_PREFIX']   = '/AIMWebService/api/Accounts?';
$DB['VAULT_DB_PATH']  = 'AppID=<YOUR_APP_ID>&Query=Safe=<YOUR_SAFE>;Object=<YOUR_OBJECT>';
$DB['VAULT_TOKEN']    = '';
$DB['VAULT_CERT_FILE'] = '/var/lib/zabbix/ssl/certs/cyberark.pem';
$DB['VAULT_KEY_FILE']  = '/var/lib/zabbix/ssl/certs/cyberark.pem';
$DB['VAULT_CACHE']    = false;

$DB['DOUBLE_IEEE754'] = true;
$ZBX_SERVER_NAME      = 'Zabbix';
?>
```

---

## Security Best Practices

1. **Certificate Security:**
   - Store certificates in `/var/lib/zabbix/ssl/` (not in web-accessible directories)
   - Set minimal permissions (644 for cert, 600 for config files)
   - Use separate certificates per environment (dev/prod)

2. **Configuration Files:**
   - Backup before changes
   - Restrict access to root and service users only
   - Keep backups in secure location

3. **Vault Access:**
   - Use dedicated AppID for Zabbix
   - Limit vault permissions to read-only
   - Rotate certificates regularly per security policy

4. **Monitoring:**
   - Monitor Zabbix server logs for vault connection issues
   - Set up alerts for authentication failures
   - Regularly verify vault connectivity

---

## Quick Reference

### Key Differences: Server vs Web Config

| Setting | Server Config | Web Config |
|---------|--------------|------------|
| File | `/etc/zabbix/zabbix_server.conf` | `/etc/zabbix/web/zabbix.conf.php` |
| Format | INI | PHP |
| DBName | `DBName=zabbix` (required) | `$DB['DATABASE'] = 'zabbix';` |
| DBUser | Commented out | `$DB['USER'] = '';` (empty) |
| DBPassword | Commented out | `$DB['PASSWORD'] = '';` (empty) |
| VaultURL | Base URL only | Base URL only |
| Vault Prefix | Not needed | `VAULT_PREFIX` **required** |
| Cert Path | Relative (with SSLCertLocation) | Absolute path |

### Vault Parameter Encoding

- Spaces → `%20`
- Ampersand → `&` (no encoding needed)
- Semicolon → `;` (no encoding needed)
- Keep query string on single line (no line breaks)

---

## Appendix: Version-Specific Notes

### Zabbix 6.4
- Full CyberArk support in both server and web
- Requires OpenSSL 1.1.1 or higher
- PHP 7.4+ required for web interface

### Zabbix 7.0+
- Enhanced vault error messages
- Improved certificate handling
- Same configuration parameters as 6.4

### Zabbix 7.2
- All vault features from 6.4 supported
- Better debugging information in logs
- Configuration syntax unchanged

---

## Support and Resources

- **Zabbix Documentation:** https://www.zabbix.com/documentation/
- **CyberArk AIM Documentation:** Contact your CyberArk administrator
- **Community Forum:** https://www.zabbix.com/forum/

---

**Document Version:** 1.0  
**Last Updated:** December 31, 2025  
**Tested On:** Zabbix 7.2.12, Ubuntu 22.04
