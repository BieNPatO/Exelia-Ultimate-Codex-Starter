# Windows-native launcher gives accurate guidance; full Codex development is supported in WSL2.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$InstallerArgs)
Write-Host 'Exelia Ultimate Installer v2.0.1'
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
  Write-Error 'WSL2 not found. Install WSL2 Ubuntu, then run ./install.sh inside Linux.'
  exit 2
}
Write-Host 'Run this installer from the WSL2 terminal, in the Linux project directory:'
Write-Host '  ./install.sh --check'
Write-Host '  ./install.sh --plan'
Write-Host '  ./install.sh --apply'
Write-Host 'Native Windows installation is diagnostic-only. Nothing was changed.'
exit 0
