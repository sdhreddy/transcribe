# PowerShell script to pull changes while preserving API key
Write-Host "========================================"
Write-Host "GIT PULL WITH API KEY PRESERVATION" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""

# 1. Backup current override.yaml if it exists
$overridePath = "app\transcribe\override.yaml"
$backupPath = "override.yaml.backup"

if (Test-Path $overridePath) {
    Write-Host "Backing up current API key..." -ForegroundColor Yellow
    Copy-Item $overridePath $backupPath -Force
    Write-Host "Backup saved to: $backupPath" -ForegroundColor Green
} else {
    Write-Host "No override.yaml found to backup" -ForegroundColor Red
}

# 2. Stash any local changes
Write-Host ""
Write-Host "Stashing local changes..." -ForegroundColor Yellow
git stash

# 3. Pull latest changes
Write-Host ""
Write-Host "Pulling latest changes from GitHub..." -ForegroundColor Yellow
git pull origin disc-clean

# 4. Restore API key
if (Test-Path $backupPath) {
    Write-Host ""
    Write-Host "Restoring API key..." -ForegroundColor Yellow
    Copy-Item $backupPath $overridePath -Force
    Write-Host "API key restored!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "WARNING: No API key backup found!" -ForegroundColor Red
    Write-Host "You'll need to manually add your API key to $overridePath"
}

# 5. Verify API key is set
Write-Host ""
Write-Host "Checking API key status..." -ForegroundColor Yellow

if (Test-Path $overridePath) {
    $content = Get-Content $overridePath -Raw
    if ($content -match "api_key:\s*[^n\s]+(?<!null)(?<!YOUR_API_KEY)") {
        Write-Host "[SUCCESS] API key is set and ready!" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] API key not found or invalid!" -ForegroundColor Red
        Write-Host "Please update $overridePath with your OpenAI API key"
    }
} else {
    Write-Host "[ERROR] override.yaml not found!" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================"
Write-Host "Pull complete!" -ForegroundColor Green
Write-Host "To test: python test_windows_audio_direct.py"
Write-Host "To run: python transcribe.py"
Write-Host "========================================"
Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")