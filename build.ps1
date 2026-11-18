$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Copy-Item -Force (Join-Path $PSScriptRoot '..\Naqsh\logo.ico') (Join-Path $PSScriptRoot 'logo.ico')

if (Test-Path 'build') { Remove-Item -Recurse -Force 'build' }
if (Test-Path 'dist')  { Remove-Item -Recurse -Force 'dist' }

python -m PyInstaller `
  --onefile `
  --noconsole `
  --clean `
  --name 'NaqshDesktop' `
  --icon 'logo.ico' `
  --add-data 'logo.ico;.' `
  --add-data 'fonts;fonts' `
  --hidden-import 'tkinterdnd2' `
  --hidden-import 'customtkinter' `
  --collect-data 'customtkinter' `
  app.py

$exe = Join-Path $PSScriptRoot 'dist\NaqshDesktop.exe'
if (-not (Test-Path $exe)) { throw 'Build failed: NaqshDesktop.exe not found' }

# Arabic app name built from char codes (PowerShell 5.1 ANSI-safe)
$appName = [string][char]1606 + [char]1602 + [char]1588
$desktop = [Environment]::GetFolderPath('Desktop')
Copy-Item -Force $exe (Join-Path $desktop ($appName + '.exe'))

Write-Host "Built: $exe"
Write-Host "Desktop updated: $(Join-Path $desktop ($appName + '.exe'))"
