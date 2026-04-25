import { mkdirSync, readdirSync, readFileSync, writeFileSync, appendFileSync } from 'node:fs'
import { join, resolve } from 'node:path'

function parseArgs(argv) {
  const options = {}
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index]
    if (!value.startsWith('--')) {
      continue
    }
    const key = value.slice(2)
    const next = argv[index + 1]
    if (!next || next.startsWith('--')) {
      options[key] = 'true'
      continue
    }
    options[key] = next
    index += 1
  }
  return options
}

function requireOption(options, name) {
  if (!options[name]) {
    throw new Error(`Missing required option --${name}`)
  }
  return options[name]
}

function appendSummary(markdown) {
  const summaryPath = process.env.GITHUB_STEP_SUMMARY
  if (!summaryPath) {
    return
  }
  appendFileSync(summaryPath, `${markdown}\n`, 'utf8')
}

function loadJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'))
}

function matchesScope(scope, artifactName) {
  if (scope === 'all') {
    return true
  }
  return artifactName.startsWith(`${scope}-`)
}

function collectArtifactDirs(baseDir) {
  return readdirSync(baseDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
}

const options = parseArgs(process.argv.slice(2))
const artifactsDir = resolve(requireOption(options, 'artifacts-dir'))
const outDir = resolve(requireOption(options, 'out-dir'))
const scope = options.scope ?? 'all'
const runId = options['run-id'] ?? null

mkdirSync(outDir, { recursive: true })

const selectedArtifacts = []

for (const artifactName of collectArtifactDirs(artifactsDir)) {
  if (!matchesScope(scope, artifactName)) {
    continue
  }

  const artifactDir = join(artifactsDir, artifactName)
  const failureContextPath = join(artifactDir, 'failure-context.json')
  const resultPath = join(artifactDir, 'result.json')

  try {
    const failureContext = loadJson(failureContextPath)
    const result = loadJson(resultPath)
    selectedArtifacts.push({
      artifact_name: artifactName,
      failure_context: failureContext,
      result,
    })
  } catch (error) {
    selectedArtifacts.push({
      artifact_name: artifactName,
      failure_context: {
        workflow: null,
        job: null,
        run_id: runId,
        sha: null,
        ref: null,
        command: null,
        status: 'failure',
        artifact_names: [artifactName],
        primary_log: null,
        summary: `Unable to parse artifact metadata: ${error.message}`,
        failed_step: 'triage-parse',
      },
      result: null,
    })
  }
}

const failedArtifacts = selectedArtifacts.filter(
  (artifact) => artifact.failure_context?.status !== 'success'
)

const triageContext = {
  generated_at: new Date().toISOString(),
  repository: process.env.GITHUB_REPOSITORY ?? null,
  run_id: runId,
  scope,
  total_artifacts: selectedArtifacts.length,
  failed_artifacts: failedArtifacts.length,
  artifacts: selectedArtifacts,
}

writeFileSync(
  join(outDir, 'triage-context.json'),
  `${JSON.stringify(triageContext, null, 2)}\n`,
  'utf8'
)

const summaryLines = [
  '# CI Triage Summary',
  '',
  `- Run ID: \`${runId ?? 'unknown'}\``,
  `- Scope: \`${scope}\``,
  `- Selected artifacts: **${selectedArtifacts.length}**`,
  `- Failed artifacts: **${failedArtifacts.length}**`,
  '',
]

if (selectedArtifacts.length === 0) {
  summaryLines.push('未找到符合条件的结构化 CI artifact。')
} else {
  summaryLines.push('| Artifact | Status | Job | Summary |')
  summaryLines.push('|---|---|---|---|')
  for (const artifact of selectedArtifacts) {
    summaryLines.push(
      `| ${artifact.artifact_name} | ${artifact.failure_context?.status ?? 'unknown'} | ${artifact.failure_context?.job ?? '-'} | ${artifact.failure_context?.summary ?? '-'} |`
    )
  }
}

writeFileSync(join(outDir, 'summary.md'), `${summaryLines.join('\n')}\n`, 'utf8')
appendSummary(summaryLines.join('\n'))
