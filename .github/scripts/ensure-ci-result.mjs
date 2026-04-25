import { mkdirSync, writeFileSync, appendFileSync, existsSync } from 'node:fs'
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

const options = parseArgs(process.argv.slice(2))
const resultsDir = resolve(requireOption(options, 'results-dir'))
const artifactName = requireOption(options, 'artifact-name')
const label = requireOption(options, 'label')
const command = options.command ?? 'n/a'

mkdirSync(resultsDir, { recursive: true })

const stdoutPath = join(resultsDir, 'stdout.log')
const resultPath = join(resultsDir, 'result.json')
const failureContextPath = join(resultsDir, 'failure-context.json')

if (existsSync(resultPath) && existsSync(failureContextPath)) {
  process.exit(0)
}

if (!existsSync(stdoutPath)) {
  writeFileSync(
    stdoutPath,
    'Primary CI command did not produce a log file. Inspect the GitHub job log for setup or bootstrap failures.\n',
    'utf8'
  )
}

const summary = `${label} did not reach the main CI command. Inspect the GitHub job log for setup or bootstrap failures.`
const result = {
  workflow: process.env.GITHUB_WORKFLOW ?? null,
  job: process.env.GITHUB_JOB ?? null,
  run_id: process.env.GITHUB_RUN_ID ?? null,
  sha: process.env.GITHUB_SHA ?? null,
  ref: process.env.GITHUB_REF ?? null,
  label,
  command,
  artifact_name: artifactName,
  status: 'failure',
  exit_code: null,
  signal: null,
  started_at: null,
  finished_at: new Date().toISOString(),
  duration_ms: null,
  primary_log: 'stdout.log',
  junit_path: null,
  output_excerpt: 'Main CI command was not executed or failed before result generation.',
  summary,
}
const failureContext = {
  workflow: result.workflow,
  job: result.job,
  run_id: result.run_id,
  sha: result.sha,
  ref: result.ref,
  command,
  status: result.status,
  artifact_names: [artifactName],
  primary_log: result.primary_log,
  summary,
  failed_step: label,
}

writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8')
writeFileSync(failureContextPath, `${JSON.stringify(failureContext, null, 2)}\n`, 'utf8')

appendSummary(
  [
    `### ${label}`,
    '',
    `- Status: **failure**`,
    `- Artifact: \`${artifactName}\``,
    `- Summary: ${summary}`,
    '',
  ].join('\n')
)
