$proc = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*run_scheduler*"
}
if ($proc) {
    $proc | Stop-Process -Force
    Write-Host "Scheduler stopped"
} else {
    Write-Host "No scheduler process found"
}
