# Pakai (PowerShell): .\buat-password.ps1 -User namauser
param([Parameter(Mandatory=$true)][string]$User)
$sec = Read-Host "Password untuk $User" -AsSecureString
$pass = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$line = docker run --rm httpd:2.4.62-alpine htpasswd -nbm $User $pass
$existing = @()
if (Test-Path .htpasswd) { $existing = Get-Content .htpasswd | Where-Object { $_ -notmatch "^$User:" } }
($existing + $line) | Out-File -FilePath .htpasswd -Encoding ascii
Write-Host "User $User tersimpan di .htpasswd"
