param(
    [string]$RunId,
    [string]$Workflow,
    [string]$Branch = "main",
    [ValidateSet("all", "success", "failure", "cancelled", "skipped", "timed_out", "action_required", "neutral")]
    [string]$Conclusion = "failure",
    [string]$OutputRoot = ".ci-results/github",
    [int]$FailedLogLines = 200,
    [string]$ExtraInstruction,
    [switch]$RunCodex,
    [ValidateSet("read-only", "workspace-write", "danger-full-access")]
    [string]$CodexSandbox = "workspace-write",
    [string]$CodexModel
)

$ErrorActionPreference = "Stop"

function Get-CodexCommand {
    try {
        return (Get-Command "codex" -ErrorAction Stop).Source
    } catch {
        throw "Codex CLI was not found in PATH."
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$fetchScript = Join-Path $PSScriptRoot "fetch-github-ci-result.ps1"
if (-not (Test-Path $fetchScript)) {
    throw "Missing script: $fetchScript"
}

$fetchParams = @{
    OutputRoot = $OutputRoot
    DownloadArtifacts = $true
    ShowFailedLog = $true
}
if ($RunId) {
    $fetchParams.RunId = $RunId
} else {
    if ($Workflow) {
        $fetchParams.Workflow = $Workflow
    }
    $fetchParams.Branch = $Branch
    $fetchParams.Conclusion = $Conclusion
}

$run = & $fetchScript @fetchParams | ConvertFrom-Json
$runDir = $run.output_directory

$failureContextPath = Get-ChildItem -Path $runDir -Recurse -Filter "failure-context.json" | Select-Object -First 1 -ExpandProperty FullName
$resultPath = Get-ChildItem -Path $runDir -Recurse -Filter "result.json" | Select-Object -First 1 -ExpandProperty FullName
$failedLogPath = if ($run.failed_log_path) {
    Join-Path $repoRoot $run.failed_log_path
} else {
    $null
}

$failureContext = if ($failureContextPath) {
    Get-Content -Raw -Encoding UTF8 $failureContextPath | ConvertFrom-Json
} else {
    $null
}
$result = if ($resultPath) {
    Get-Content -Raw -Encoding UTF8 $resultPath | ConvertFrom-Json
} else {
    $null
}

$failedLogExcerpt = $null
if ($failedLogPath -and (Test-Path $failedLogPath)) {
    $failedLogExcerpt = (Get-Content -Encoding UTF8 $failedLogPath | Select-Object -First $FailedLogLines) -join "`n"
}

$failureContextDisplay = if ($failureContextPath) { $failureContextPath } else { "missing failure-context.json" }
$resultDisplay = if ($resultPath) { $resultPath } else { "missing result.json" }
$failedLogDisplay = if ($failedLogPath) { $failedLogPath } else { "missing failed.log" }
$summaryDisplay = if ($failureContext) { $failureContext.summary } else { $run.conclusion }
$failedStepDisplay = if ($failureContext) { $failureContext.failed_step } else { "unknown" }
$commandDisplay = if ($failureContext) { $failureContext.command } else { "unknown" }
$resultExcerptDisplay = if ($result -and $result.output_excerpt) { $result.output_excerpt } else { "No output_excerpt available." }
$failedLogExcerptDisplay = if ($failedLogExcerpt) { $failedLogExcerpt } else { "No failed.log excerpt available." }

$extraBlock = if ($ExtraInstruction) {
@"

## Extra Instruction

$ExtraInstruction
"@
} else {
    ""
}

$prompt = @"
# GitHub CI Autofix Context

You are working in the repository at:

- $repoRoot

The latest GitHub Actions run to investigate is:

- Workflow: $($run.workflow)
- Run ID: $($run.run_id)
- Title: $($run.title)
- Branch: $($run.branch)
- SHA: $($run.sha)
- Status: $($run.status)
- Conclusion: $($run.conclusion)
- URL: $($run.url)

Artifacts and logs were downloaded to:

- $runDir

Primary local files:

- $failureContextDisplay
- $resultDisplay
- $failedLogDisplay

## Failure Summary

- Summary: $summaryDisplay
- Failed step: $failedStepDisplay
- Command: $commandDisplay

## Result Excerpt

```text
$resultExcerptDisplay
```

## Failed Log Excerpt

```text
$failedLogExcerptDisplay
```

## Required Tasks

1. Read the repository rules and docs requirements before editing.
2. Use the downloaded CI context to identify the real failure cause instead of guessing from the summary alone.
3. Fix only the failures that belong to this GitHub Actions run.
4. Run focused local verification for the affected scope.
5. Update required docs/tracking files when behavior, CI flow, tests, or debugging guidance changes.
6. Do not commit or push unless explicitly requested later.

## Safety Constraints

- Keep unrelated local changes untouched.
- If frontend files must be changed, use the frontend workflow rules and read frontend/src/style.css first.
- Prefer the smallest targeted fix that makes the failing CI checks green.
$extraBlock
"@

$promptPath = Join-Path $runDir "codex-autofix-prompt.md"
$prompt | Set-Content -Encoding UTF8 $promptPath

$contextSummary = [ordered]@{
    run_id = $run.run_id
    workflow = $run.workflow
    conclusion = $run.conclusion
    run_directory = $runDir
    prompt_path = $promptPath
    failure_context_path = $failureContextPath
    result_path = $resultPath
    failed_log_path = $failedLogPath
    codex_invoked = $false
    codex_last_message_path = $null
}

if ($RunCodex) {
    $codexExe = Get-CodexCommand
    $lastMessagePath = Join-Path $runDir "codex-last-message.txt"
    $codexArgs = @(
        "exec",
        "-C", $repoRoot,
        "-s", $CodexSandbox,
        "-o", $lastMessagePath,
        "-"
    )
    if ($CodexModel) {
        $codexArgs = @("exec", "-m", $CodexModel, "-C", $repoRoot, "-s", $CodexSandbox, "-o", $lastMessagePath, "-")
    }

    Get-Content -Raw -Encoding UTF8 $promptPath | & $codexExe @codexArgs
    if ($LASTEXITCODE -ne 0) {
        throw "codex exec failed."
    }

    $contextSummary.codex_invoked = $true
    $contextSummary.codex_last_message_path = $lastMessagePath
}

$contextSummary | ConvertTo-Json -Depth 5
