$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Create .venv and install .[build] first. See README.md.'
}
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
$previousPath = $env:PATH
try {
    # Do not collect unrelated DLLs (for example Poppler's incompatible ICU)
    # from developer toolchains that happen to be in PATH.
    $env:PATH = ((Join-Path $PWD '.venv\Scripts'), (Join-Path $env:SystemRoot 'System32'), $env:SystemRoot) -join ';'
    & .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name ChatScout --collect-all keyring --copy-metadata keyring run.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
} finally {
    $env:PATH = $previousPath
}
$env:QT_QPA_PLATFORM = 'offscreen'
try {
    $smokeProcess = Start-Process -FilePath '.\dist\ChatScout\ChatScout.exe' -ArgumentList '--smoke-test' -WindowStyle Hidden -PassThru
    if (-not $smokeProcess.WaitForExit(20000)) {
        $smokeProcess.Kill()
        throw 'Packaged startup test timed out'
    }
    if ($smokeProcess.ExitCode -ne 0) { throw 'Packaged startup test failed' }
} finally {
    Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
}
Copy-Item -LiteralPath LICENSE,README.md,THIRD_PARTY_NOTICES.md -Destination dist\ChatScout
& .\.venv\Scripts\python.exe scripts\collect_licenses.py
if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
Compress-Archive -Path dist\ChatScout -DestinationPath dist\ChatScout-Windows.zip -Force
