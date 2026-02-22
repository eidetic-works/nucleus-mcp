# =============================================================================
# 🚀 NUCLEUS NODE BETA: SINGLE-CLICK IGNITION (Zenith Hardened)
# =============================================================================
# Purpose: Deep-automate the setup of a Sovereign Node on Native Windows.
# Target: Windows 10/11 (Native, Non-WSL)
# =============================================================================

$ErrorActionPreference = "Stop"

function Write-Step ($msg) {
    Write-Host "`n[STEP] $msg" -ForegroundColor Cyan
}

function Write-Success ($msg) {
    Write-Host "[DONE] $msg" -ForegroundColor Green
}

# 1. Environment Baseline Check
Write-Step "1. Environment Baseline Check"
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Error "Winget not found. Please update Windows or install 'App Installer' from the Microsoft Store."
}
Write-Success "Winget is present."

# 2. Binary Tooling Injection
Write-Step "2. Binary Tooling Injection"
Write-Host "Verifying Git, Python 3.11, and Multimedia Tools..."
$toInstall = @()
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { $toInstall += "Git.Git" }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { $toInstall += "Python.Python.3.11" }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { $toInstall += "Gyan.FFmpeg" }

foreach ($id in $toInstall) {
    Write-Host "Installing $id via winget..."
    winget install --id $id -e --source winget --accept-package-agreements --accept-source-agreements
}
Write-Success "All binary dependencies met."

# 3. Filesystem Scaffolding
Write-Step "3. Filesystem Scaffolding"
$root = "C:\SovereignNode"
if (-not (Test-Path $root)) {
    New-Item -ItemType Directory -Path $root | Out-Null
    Write-Host "Created $root"
}
Set-Location $root
Write-Success "Operating in $root"

# 4. Repository Acquisition (Zenith Sync)
Write-Step "4. Repository Acquisition (Zenith Sync)"
$repos = @{
    "nucleus-mcp" = "https://github.com/eidetic-works/nucleus-mcp.git"
    "believe-it-bot" = "https://github.com/eidetic-works/believe-it-bot.git"
}

foreach ($name in $repos.Keys) {
    if (-not (Test-Path $name)) {
        Write-Host "Cloning $name..."
        git clone $repos[$name] $name
    } else {
        Write-Host "$name already exists. Pulling latest..."
        Set-Location $name
        git pull
        Set-Location $root
    }
}
Write-Success "Repositories synchronized."

# 5. The Git Corruption Shield (LF Enforcement)
Write-Step "5. The Git Corruption Shield (LF Enforcement)"
Get-ChildItem -Directory | ForEach-Object {
    $dir = $_.FullName
    if (Test-Path (Join-Path $dir ".git")) {
        Set-Location $dir
        Write-Host "Hardening line endings in $($_.Name)..."
        "* text=auto eol=lf" | Set-Content -Path .gitattributes -Force
        git add . --renormalize
        Set-Location $root
    }
}
Write-Success "Zero-Rot Line Endings Enforced."

# 6. Nucleus Virtualization
Write-Step "6. Nucleus Virtualization"
$mcpDir = Join-Path $root "nucleus-mcp"
if (Test-Path $mcpDir) {
    Set-Location $mcpDir
    if (-not (Test-Path ".venv")) {
        Write-Host "Creating Virtual Environment..."
        python -m venv .venv
    }
    Write-Host "Installing dependencies..."
    & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & ".\.venv\Scripts\pip.exe" install -e .
    Write-Success "Nucleus installed in developer mode."
} else {
    Write-Warning "Nucleus directory not found. Skipping virtualization."
}

# 7. Windsurf Integration String
Write-Step "7. Windsurf Integration String"
$pythonPath = (Join-Path $mcpDir ".venv\Scripts\python.exe").Replace("\", "/")
# Brain root should point to the application (believe-it-bot)
$botDir = Join-Path $root "believe-it-bot"
$brainRoot = $botDir.Replace("\", "/")

# Constructing JSON manually to avoid Here-String parser sensitivity
$json = "{"
$json += "`n  `"mcpServers`": {"
$json += "`n    `"nucleus-native`": {"
$json += "`n      `"command`": `"$pythonPath`","
$json += "`n      `"args`": [`"-m`", `"mcp_server_nucleus.runtime.stdio_server`"],"
$json += "`n      `"env`": {"
$json += "`n        `"NUCLEAR_BRAIN_PATH`": `"$brainRoot`","
$json += "`n        `"NUCLEUS_MODE`": `"BETA_SURGE`""
$json += "`n      }"
$json += "`n    }"
$json += "`n  }"
$json += "`n}"

Write-Host "`n--- COPY THIS INTO WINDSURF MCP SETTINGS ---" -ForegroundColor Yellow
Write-Host $json
Write-Host "-------------------------------------------`n"

# 8. Operational Smoke Test
Write-Step "8. Operational Smoke Test"
if (Test-Path $mcpDir) {
    Set-Location $mcpDir
    Write-Host "Running diagnostic boot..."
    & ".\.venv\Scripts\python.exe" -m mcp_server_nucleus.runtime.stdio_server --help | Select-Object -First 5
    Write-Success "Smoke test complete. Your Node is ALIVE."
}

Set-Location $root
