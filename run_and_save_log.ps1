# Run main.py and save the entire execution output to recent__experiment_run.txt
# Use this to capture a full run (terminal buffer files are rolling and may truncate).
Set-Location $PSScriptRoot
$out = Join-Path $PSScriptRoot "recent__experiment_run.txt"
& .\.venv\Scripts\python.exe main.py *>&1 | Tee-Object -FilePath $out
Write-Host "`n[Log saved to $out]"
