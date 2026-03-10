param(
  [string]$Version = "",
  [switch]$FullProject
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$packagesRoot = Join-Path $root "server_packages"
New-Item -ItemType Directory -Force -Path $packagesRoot | Out-Null

if (-not $Version -or [string]::IsNullOrWhiteSpace($Version)) {
  $Version = Get-Date -Format "yyyyMMdd_HHmmss"
}

$target = Join-Path $packagesRoot ("package_" + $Version)
if (Test-Path $target) {
  throw "Package path already exists: $target"
}
New-Item -ItemType Directory -Force -Path $target | Out-Null

$excludeDirs = @(
  ".git",
  ".venv",
  "node_modules",
  "__pycache__",
  "uploads",
  "outputs",
  "temp",
  "server_packages"
)

$excludeFiles = @(
  "*.pyc",
  "*.pyo",
  "*.log",
  "*.tmp",
  "*.part"
)

if ($FullProject) {
  # Mirror almost the whole project for server deployment, excluding runtime/cache folders.
  $xd = $excludeDirs | ForEach-Object { '/XD', (Join-Path $root $_) }
  $xf = $excludeFiles | ForEach-Object { '/XF', $_ }
  $args = @(
    $root,
    $target,
    '/E',
    '/R:1',
    '/W:1',
    '/NFL',
    '/NDL',
    '/NJH',
    '/NJS',
    '/NP'
  ) + $xd + $xf

  & robocopy @args | Out-Null
  if ($LASTEXITCODE -gt 7) {
    throw "robocopy failed with exit code $LASTEXITCODE"
  }
} else {
  New-Item -ItemType Directory -Force -Path (Join-Path $target "templates") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $target "static") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $target "scripts") | Out-Null

  $filesToCopy = @(
    "web_app.py",
    "requirements.txt",
    "requirements-server.txt",
    "Procfile",
    "README.md",
    "run_full_tests.ps1",
    "install_linux_apache.sh"
  )

  foreach ($file in $filesToCopy) {
    $src = Join-Path $root $file
    if (Test-Path $src) {
      Copy-Item -Path $src -Destination (Join-Path $target $file) -Force
    }
  }

  Copy-Item -Path (Join-Path $root "templates\*.html") -Destination (Join-Path $target "templates") -Force
  Copy-Item -Path (Join-Path $root "static\*") -Destination (Join-Path $target "static") -Recurse -Force
  Copy-Item -Path (Join-Path $root "scripts\*") -Destination (Join-Path $target "scripts") -Recurse -Force
}

$manifestPath = Join-Path $target "PACKAGE_INFO.txt"
$lines = @(
  "Package Version: $Version",
  "Created At: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')",
  "Project Root: $root",
  "Mode: " + ($(if ($FullProject) { 'FullProject' } else { 'AppCore' })),
  "",
  "Server setup (Windows/PowerShell):",
  "python -m venv .venv",
  ".\\.venv\\Scripts\\Activate.ps1",
  "pip install -r requirements-server.txt",
  "python web_app.py",
  "",
  "Server setup (Linux/macOS):",
  "python3 -m venv .venv",
  "source .venv/bin/activate",
  "pip install -r requirements-server.txt",
  "python web_app.py",
  "",
  "Linux + Apache install (copiar/colar no servidor):",
  "sudo bash install_linux_apache.sh --domain _",
  "",
  "Optional full features (YouTube/Spotify/Audio OCR):",
  "pip install -r requirements.txt",
  "python web_app.py"
)
$lines | Set-Content -Path $manifestPath -Encoding UTF8

$zipPath = Join-Path $packagesRoot ("package_" + $Version + ".zip")
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path (Join-Path $target '*') -DestinationPath $zipPath -CompressionLevel Optimal

Write-Output "Created package folder: $target"
Write-Output "Created package zip: $zipPath"
