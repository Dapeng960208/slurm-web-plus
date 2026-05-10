param(
    [string]$RunId,
    [string]$Workflow,
    [string]$Branch = "main",
    [ValidateSet("all", "success", "failure", "cancelled", "skipped", "timed_out", "action_required", "neutral")]
    [string]$Conclusion = "all",
    [int]$Limit = 20,
    [string]$OutputRoot = ".ci-results/github",
    [switch]$DownloadArtifacts,
    [switch]$ShowFailedLog
)

$ErrorActionPreference = "Stop"

function Get-GhCommand {
    $candidates = @(
        "gh",
        (Join-Path $HOME "AppData\Local\Programs\GitHub CLI\gh.exe")
    )
    foreach ($candidate in $candidates) {
        try {
            $command = Get-Command $candidate -ErrorAction Stop
            return $command.Source
        } catch {
        }
    }

    throw "GitHub CLI (gh) was not found. Install it first or add it to PATH."
}

function Invoke-GhJson {
    param(
        [string[]]$Arguments
    )

    $output = & $script:GhExe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "gh command failed: gh $($Arguments -join ' ')"
    }

    return $output | ConvertFrom-Json
}

function Resolve-Run {
    if ($RunId) {
        return Invoke-GhJson -Arguments @(
            "run", "view", $RunId,
            "--json",
            "databaseId,workflowName,displayTitle,status,conclusion,headBranch,headSha,createdAt,updatedAt,url"
        )
    }

    $arguments = @(
        "run", "list",
        "--branch", $Branch,
        "--limit", $Limit,
        "--json",
        "databaseId,workflowName,displayTitle,status,conclusion,headBranch,headSha,createdAt,updatedAt,url"
    )
    if ($Workflow) {
        $arguments += @("--workflow", $Workflow)
    }

    $runs = Invoke-GhJson -Arguments $arguments
    if (-not $runs) {
        throw "No workflow runs were found."
    }

    if ($Conclusion -ne "all") {
        $runs = @($runs | Where-Object { $_.conclusion -eq $Conclusion })
    }

    $selected = @($runs | Select-Object -First 1)
    if (-not $selected) {
        throw "No workflow runs matched the requested filters."
    }

    return $selected[0]
}

function Get-ArtifactNames {
    param(
        [string]$RunId
    )

    $artifacts = Invoke-GhJson -Arguments @(
        "api",
        "repos/:owner/:repo/actions/runs/$RunId/artifacts"
    )
    if (-not $artifacts -or -not $artifacts.artifacts) {
        return @()
    }
    return @($artifacts.artifacts | ForEach-Object { $_.name })
}

$script:GhExe = Get-GhCommand
$run = Resolve-Run
$runId = [string]$run.databaseId
$safeWorkflow = if ($run.workflowName) {
    ($run.workflowName -replace '[^A-Za-z0-9._-]+', '-').Trim('-')
} else {
    "unknown-workflow"
}
$runDir = Join-Path $OutputRoot "$safeWorkflow-$runId"

if (-not (Test-Path $runDir)) {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
}

$summary = [ordered]@{
    run_id = $run.databaseId
    workflow = $run.workflowName
    title = $run.displayTitle
    branch = $run.headBranch
    sha = $run.headSha
    status = $run.status
    conclusion = $run.conclusion
    created_at = $run.createdAt
    updated_at = $run.updatedAt
    url = $run.url
    output_directory = (Resolve-Path $runDir).Path
    downloaded_artifacts = $false
    failed_log_path = $null
}

$summaryPath = Join-Path $runDir "run-summary.json"
$summary | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $summaryPath

if ($DownloadArtifacts) {
    foreach ($artifactName in Get-ArtifactNames -RunId $runId) {
        $artifactDir = Join-Path $runDir $artifactName
        if (Test-Path $artifactDir) {
            Remove-Item -Recurse -Force $artifactDir
        }
    }
    & $script:GhExe run download $runId --dir $runDir
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download artifacts for run $runId."
    }
    $summary.downloaded_artifacts = $true
}

if ($ShowFailedLog) {
    $failedLogPath = Join-Path $runDir "failed.log"
    & $script:GhExe run view $runId --log-failed | Set-Content -Encoding UTF8 $failedLogPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to export failed logs for run $runId."
    }
    $summary.failed_log_path = $failedLogPath
}

$summary | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $summaryPath
$summary | ConvertTo-Json -Depth 5
