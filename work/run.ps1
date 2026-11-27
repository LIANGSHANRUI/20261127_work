$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$py = "D:\Users\Student\anaconda3\envs\yolov8\python.exe"
if (Test-Path -LiteralPath $py) {
    & $py app.py
    exit $LASTEXITCODE
}

python app.py
exit $LASTEXITCODE
