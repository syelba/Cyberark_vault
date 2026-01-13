<#
.SYNOPSIS
    Retrieves passwords from CyberArk Vault using certificate from Windows Certificate Store.

.DESCRIPTION
    Uses certificate authentication from LocalMachine\My store to retrieve passwords from CyberArk.
    Certificate CN must match the Safe name.

.PARAMETER AppID
    Application ID (format: IAP#-EnvironmentCode-Label-CERT)

.PARAMETER SafeName
    Safe name (must match certificate CN)

.PARAMETER UserName
    Username of the account

.PARAMETER ObjectName
    Object name of the account (alternative to UserName)

.PARAMETER BaseURI
    Base URI for CyberArk API (default: https://passwordvault.intel.com/AIMWebService/api/Accounts)

.EXAMPLE
    .\Get-CyberArkPassword-CertStore.ps1
    Uses values from .env file

.EXAMPLE
    .\Get-CyberArkPassword-CertStore.ps1 -UserName "sys_poc"
    Retrieves password for specific username
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$AppID,
    
    [Parameter(Mandatory=$false)]
    [string]$SafeName,
    
    [Parameter(Mandatory=$false)]
    [string]$UserName,
    
    [Parameter(Mandatory=$false)]
    [string]$ObjectName,
    
    [Parameter(Mandatory=$false)]
    [string]$Address,
    
    [Parameter(Mandatory=$false)]
    [string]$Database,
    
    [Parameter(Mandatory=$false)]
    [string]$Folder,
    
    [Parameter(Mandatory=$false)]
    [string]$BaseURI
)

# Load .env file
function Import-EnvFile {
    param([string]$Path = ".env")
    
    if (-not (Test-Path $Path)) {
        Write-Warning "Environment file not found: $Path"
        return @{}
    }
    
    $envVars = @{}
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#')) {
            if ($line -match '^\s*([^=]+?)\s*=\s*(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim() -replace '^["'']|["'']$', ''
                $envVars[$key] = $value
            }
        }
    }
    return $envVars
}

try {
    # Get script directory and load .env
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $envPath = Join-Path $scriptDir ".env"
    $envVars = Import-EnvFile -Path $envPath
    
    # Get values from parameters or environment
    $appIDValue = if ($AppID) { $AppID } else { $envVars['AAM_APP_ID'] }
    $safeNameValue = if ($SafeName) { $SafeName } else { $envVars['AAM_SAFE'] }
    $baseURIValue = if ($BaseURI) { 
        $BaseURI 
    } elseif ($envVars['AAM_BASE_URI']) { 
        $envVars['AAM_BASE_URI'].TrimEnd('/') + '/AIMWebService/api/Accounts'
    } else { 
        'https://passwordvault.intel.com/AIMWebService/api/Accounts'
    }
    
    # Determine username or object name
    $userNameValue = $UserName
    $objectNameValue = if ($ObjectName) { $ObjectName } else { $envVars['object_name'] }
    
    # Validate required parameters
    if (-not $appIDValue) { throw "AppID is required" }
    if (-not $safeNameValue) { throw "SafeName is required" }
    
    Write-Host "Retrieving password from CyberArk Vault..." -ForegroundColor Cyan
    Write-Host "AppID: $appIDValue"
    Write-Host "Safe: $safeNameValue"
    Write-Host ""
    
    # Load certificate from PFX file
    $pfxPath = "c:\Users\SAFE.pfx"
    $pfxPassword = "password"
    
    Write-Host "Loading certificate from: $pfxPath"
    
    if (-not (Test-Path $pfxPath)) {
        throw "Certificate file not found: $pfxPath"
    }
    
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
    $cert.Import($pfxPath, $pfxPassword, [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::DefaultKeySet)
    
    Write-Host "Certificate found:" -ForegroundColor Green
    Write-Host "  Subject: $($cert.Subject)"
    Write-Host "  Thumbprint: $($cert.Thumbprint)"
    Write-Host "  Has Private Key: $($cert.HasPrivateKey)"
    Write-Host ""
    
    if (-not $cert.HasPrivateKey) {
        throw "Certificate does not have a private key!"
    }
    
    # Build query parameters
    $queryParams = @{
        'AppID' = $appIDValue
        'Safe' = $safeNameValue
    }
    
    if ($userNameValue) {
        $queryParams['UserName'] = $userNameValue
        Write-Host "UserName: $userNameValue"
    }
    elseif ($objectNameValue) {
        $queryParams['Object'] = $objectNameValue
        Write-Host "Object: $objectNameValue"
    }
    else {
        throw "Either UserName or Object name is required"
    }
    
    if ($Address) { $queryParams['Address'] = $Address }
    if ($Database) { $queryParams['Database'] = $Database }
    if ($Folder) { $queryParams['Folder'] = $Folder }
    
    # Build query string
    $queryParts = @()
    foreach ($key in $queryParams.Keys) {
        $encodedValue = [System.Uri]::EscapeDataString($queryParams[$key])
        $queryParts += "$key=$encodedValue"
    }
    $queryString = $queryParts -join '&'
    
    $uri = "${baseURIValue}?${queryString}"
    
    Write-Host "Base URI: $baseURIValue"
    Write-Host "Query String: $queryString"
    Write-Host "Full Request URI: $uri"
    Write-Host ""
    
    # Force TLS 1.2
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    
    # Make API request with certificate
    Write-Host "Making API request..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Method Get -Uri $uri -ContentType "application/json" -Certificate $cert
    
    # Display result
    Write-Host ""
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host "Password: $($response.Content)" -ForegroundColor Cyan
    Write-Host ""
    
    # Copy to clipboard if available
    if (Get-Command Set-Clipboard -ErrorAction SilentlyContinue) {
        $response.Content | Set-Clipboard
        Write-Host "Password copied to clipboard" -ForegroundColor Yellow
    }
    
    # Return full response
    return $response
}
catch {
    Write-Error "Error: $_"
    if ($_.Exception.Response) {
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Error "API Response: $responseBody"
        }
        catch {
            # Ignore if can't read response
        }
    }
    exit 1
}
