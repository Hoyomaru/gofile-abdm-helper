param(
    [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Root '.venv'
$VenvPython = Join-Path $Venv 'Scripts\python.exe'
$VenvPythonw = Join-Path $Venv 'Scripts\pythonw.exe'
$Requirements = Join-Path $Root 'requirements.txt'
$Tray = Join-Path $Root 'tray.py'

function Find-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        try {
            & $py.Source -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
            if ($LASTEXITCODE -eq 0) { return @($py.Source, '-3') }
        } catch {}
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        try {
            & $python.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
            if ($LASTEXITCODE -eq 0) { return @($python.Source) }
        } catch {}
    }

    throw 'Python 3.10+ was not found. Install Python 3.10 or newer, then run setup-windows.cmd again.'
}

function Invoke-Python([string[]]$Prefix, [string[]]$Arguments) {
    $exe = $Prefix[0]
    $prefixArgs = @()
    if ($Prefix.Length -gt 1) { $prefixArgs = $Prefix[1..($Prefix.Length - 1)] }
    & $exe @prefixArgs @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

Set-Location $Root
Write-Host 'GoFile ABDM Helper - Windows setup'
Write-Host ''

if (-not (Test-Path $VenvPython)) {
    Write-Host '[1/3] Creating local Python environment (.venv)...'
    $pythonPrefix = Find-Python
    Invoke-Python $pythonPrefix @('-m', 'venv', $Venv)
} else {
    Write-Host '[1/3] Existing .venv found.'
}

Write-Host '[2/3] Installing/updating dependencies...'
& $VenvPython -m pip install --disable-pip-version-check -r $Requirements
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed with exit code $LASTEXITCODE."
}

Write-Host '[3/3] Verifying installation...'
& $VenvPython -c "import flask, requests, pystray, PIL; print('Python dependencies: OK')"
if ($LASTEXITCODE -ne 0) {
    throw 'Dependency verification failed.'
}

if (-not $NoLaunch) {
    Write-Host ''
    Write-Host 'Starting tray launcher...'
    $trayArgument = '"' + $Tray + '"'
    Start-Process -FilePath $VenvPythonw -ArgumentList @($trayArgument) -WorkingDirectory $Root
}

Write-Host ''
Write-Host 'Setup complete.'
Write-Host 'Next: start AB Download Manager, open GoFile, then use Settings > Self-diagnosis.'
Write-Host 'Use the tray menu "Start with Windows" if you want automatic startup.'
