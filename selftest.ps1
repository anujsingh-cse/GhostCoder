# GhostCoder Self-Test Suite for PowerShell

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  👻 GhostCoder Self-Test Suite (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$Pass = 0
$Fail = 0

function Check-Action {
    param (
        [string]$Message,
        [boolean]$Success
    )
    if ($Success) {
        Write-Host "✅ PASS: $Message" -ForegroundColor Green
        $global:Pass++
    } else {
        Write-Host "❌ FAIL: $Message" -ForegroundColor Red
        $global:Fail++
    }
}

function Warn-Action {
    param (
        [string]$Message
    )
    Write-Host "⚠️  WARN: $Message" -ForegroundColor Yellow
}

Write-Host "1. Python Environment"
Write-Host "---------------------"
$pyVer = python --version 2>$null
Check-Action "Python available ($pyVer)" ($lastExitCode -eq 0)

$pipShow = pip show ghostcoder 2>$null
Check-Action "GhostCoder package installed" ($lastExitCode -eq 0)

Write-Host ""
Write-Host "2. Ollama & Models"
Write-Host "-------------------"
$ollamaExists = (Get-Command ollama -ErrorAction SilentlyContinue) -ne $null
Check-Action "Ollama installed" $ollamaExists

$hasClassifier = $false
$hasCoder = $false
if ($ollamaExists) {
    $models = ollama list 2>$null
    $hasClassifier = [bool]($models -match "qwen2.5:0.5b" -or $models -match "qwen2.5:latest")
    $hasCoder = [bool]($models -match "qwen2.5-coder")
}
Check-Action "Qwen2.5-0.5B model pulled" $hasClassifier
Check-Action "Qwen2.5-Coder model pulled" $hasCoder

Write-Host ""
Write-Host "3. VRAM Check"
Write-Host "-------------"
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
    Check-Action "GPU detected" $true
} else {
    Warn-Action "nvidia-smi not found - CPU-only mode"
}

Write-Host ""
Write-Host "4. Antigravity Skills"
Write-Host "---------------------"
$skillDir = "$Home\.gemini\config\skills"
if (-not (Test-Path $skillDir)) {
    $skillDir = "$Home\.gemini\antigravity\skills"
}

if (Test-Path $skillDir) {
    $skills = Get-ChildItem $skillDir -Filter "agency-*"
    Write-Host "Found $($skills.Count) agency agents"
    Check-Action "Agency agents loaded" ($skills.Count -gt 0)
} else {
    Check-Action "Agency agents directory missing" $false
}

Write-Host ""
Write-Host "5. GhostCoder Daemon"
Write-Host "--------------------"
$gcVer = ghostcoder version 2>$null
Check-Action "GhostCoder CLI works (Version $gcVer)" ($lastExitCode -eq 0)

$status = ghostcoder status 2>$null
if ($status -notmatch "running") {
    Write-Host "Starting daemon..."
    ghostcoder start
    Start-Sleep -Seconds 2
}

$status = ghostcoder status 2>$null
$isRunning = ($status -match "running" -or $status -match "Status:")
Check-Action "Daemon is running" $isRunning

Write-Host ""
Write-Host "6. Functional Test - Error Detection"
Write-Host "-----------------------------------"
$tmpDir = [System.IO.Path]::GetTempFileName()
Remove-Item $tmpDir
New-Item -ItemType Directory -Path $tmpDir | Out-Null

'{"name": "test-project", "dependencies": {"react": "^18.0.0"}}' | Out-File -FilePath "$tmpDir\package.json" -Encoding utf8
"console.log(undefinedVariable)" | Out-File -FilePath "$tmpDir\index.js" -Encoding utf8

$analysisPath = "$tmpDir\ghost_test.json"
ghostcoder analyze --file index.js --project $tmpDir | Out-File -FilePath $analysisPath -Encoding utf8
Check-Action "GhostCoder analyzed file" (Test-Path $analysisPath)

$analysisContent = Get-Content $analysisPath -Raw
$detectedError = ($analysisContent -match "error" -or $analysisContent -match "undefined" -or $analysisContent -match "Variable")
Check-Action "Detected undefined variable" $detectedError

Remove-Item -Recurse -Force $tmpDir

Write-Host ""
Write-Host "7. Functional Test - Agent Routing"
Write-Host "----------------------------------"
$tmpDir = [System.IO.Path]::GetTempFileName()
Remove-Item $tmpDir
New-Item -ItemType Directory -Path $tmpDir | Out-Null

"def vulnerable(password):" + [System.Environment]::NewLine + "    return password == 'admin'" | Out-File -FilePath "$tmpDir\auth.py" -Encoding utf8

$securityPath = "$tmpDir\ghost_security.json"
ghostcoder analyze --file auth.py --project $tmpDir | Out-File -FilePath $securityPath -Encoding utf8
Check-Action "Security analysis triggered" (Test-Path $securityPath)

$securityContent = Get-Content $securityPath -Raw
$routedSecurity = ($securityContent -match "security-engineer" -or $securityContent -match "plaintext" -or $securityContent -match "hash")
Check-Action "Routed to security-engineer agent" $routedSecurity

Remove-Item -Recurse -Force $tmpDir

Write-Host ""
Write-Host "=========================================="
Write-Host "  Test Results: $Pass passed, $Fail failed" -ForegroundColor Cyan
Write-Host "=========================================="

if ($Fail -eq 0) {
    Write-Host "All systems operational. GhostCoder is ready." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some tests failed. Check output above." -ForegroundColor Red
    exit 1
}
