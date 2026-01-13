# Hardcoded values for testing
$AppID = "appid from cyberark"
$SafeName = "safe name here" 
$ObjectName = "Object name here"
$BaseURI = "https://passwordvault.intel.com/AIMWebService/api/Accounts"

if (-not $AppID -or -not $SafeName) { throw "AppID and SafeName required" }
if (-not $ObjectName) { throw "ObjectName required" }

# ---- PFX LOAD (ADDED) ----
$pfxPath     = "certificate.pfx"
$pfxPassword = "password here"
if (-not (Test-Path $pfxPath)) { throw "PFX not found: $pfxPath" }

$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
$cert.Import($pfxPath, $pfxPassword,
    [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::DefaultKeySet)

if (-not $cert.HasPrivateKey) { throw "Certificate has no private key" }
# --------------------------

$params = @{ AppID=$AppID; Safe=$SafeName; Object=$ObjectName }

$query = ($params.GetEnumerator() | ForEach-Object {
    "$($_.Key)=$([uri]::EscapeDataString($_.Value))"
}) -join "&"

Write-Host "Base URI: $BaseURI"
Write-Host "Query:    $query"

$fullUri = $BaseURI + "?" + $query
Write-Host "Full URI: $fullUri"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
(Invoke-RestMethod -Uri $fullUri -Method GET -Certificate $cert).Content
