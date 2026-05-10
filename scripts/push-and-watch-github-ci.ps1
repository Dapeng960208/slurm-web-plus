param(
    [string]$Remote = "origin",
    [string]$Branch = "main",
    [string]$Workflow,
    [string]$OutputRoot = ".ci-results/github",
    [int]$PollIntervalSeconds = 30,
    [int]$TimeoutMinutes = 30,
    [switch]$SkipPush,
    [switch]$RunCodex,
    [string]$ExtraInstruction,
    [ValidateSet("read-only", "workspace-write", "danger-full-access")]
    [string]$CodexSandbox = "workspace-write",
    [string]$CodexModel
)

$ErrorActionPreference = "Stop"

function Get-GhCommand {
    $candidates = @(
        "gh",
        (Join-Path $HOME "AppData\Local\Programs\GitHub CLI\gh.exe")
    )
    foreach ($candidate in $candidates) {
        try {
            return (Get-Command $candidate -ErrorAction Stop).Source
        } catch {
        }
    }
    throw "GitHub CLI (gh) was not found."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ghExe = Get-GhCommand
$continueScript = Join-Path $PSScriptRoot "continue-from-github-ci.ps1"
if (-not (Test-Path $continueScript)) {
    throw "Missing script: $continueScript"
}

$headSha = (git rev-parse HEAD).Trim()
if (-not $headSha) {
    throw "Unable to resolve HEAD commit SHA."
}

if (-not $SkipPush) {
    git push $Remote $Branch
    if ($LASTEXITCODE -ne 0) {
        throw "git push $Remote $Branch failed."
    }
}

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
$selectedRun = $null

while ((Get-Date) -lt $deadline) {
    $runsJson = & $ghExe run list --commit $headSha --limit 20 --json databaseId,workflowName,status,conclusion,headSha,displayTitle,createdAt,url
    if ($LASTEXITCODE -ne 0) {
        throw "gh run list failed for commit $headSha."
    }

    $runs = $runsJson | ConvertFrom-Json
    if ($Workflow) {
        $runs = @($runs | Where-Object { $_.workflowName -eq $Workflow })
    }

    $completedRuns = @($runs | Where-Object { $_.status -eq "completed" })
    if ($completedRuns.Count -gt 0) {
        $selectedRun = $completedRuns | Sort-Object createdAt -Descending | Select-Object -First 1
        break
    }

    Start-Sleep -Seconds $PollIntervalSeconds
}

if (-not $selectedRun) {
    throw "Timed out waiting for completed GitHub Actions runs for commit $headSha."
}

$continueArgs = @(
    "-RunId", [string]$selectedRun.databaseId,
    "-OutputRoot", $OutputRoot
)
if ($ExtraInstruction) {
    $continueArgs += @("-ExtraInstruction", $ExtraInstruction)
}
if ($RunCodex) {
    $continueArgs += @("-RunCodex", "-CodexSandbox", $CodexSandbox)
    if ($CodexModel) {
        $continueArgs += @("-CodexModel", $CodexModel)
    }
}

powershell -ExecutionPolicy Bypass -File $continueScript @continueArgs
if ($LASTEXITCODE -ne 0) {
    throw "continue-from-github-ci.ps1 failed for run $($selectedRun.databaseId)."
}
