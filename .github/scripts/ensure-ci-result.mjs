import { mkdirSync, writeFileSync, appendFileSync, existsSync, readFileSync } from 'node:fs'
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

function parseXmlAttributes(text) {
  const attributes = {}
  const pattern = /([A-Za-z_:][\w:.-]*)\s*=\s*"([^"]*)"/g
  let match = pattern.exec(text)
  while (match) {
    attributes[match[1]] = match[2]
    match = pattern.exec(text)
  }
  return attributes
}

function numberAttribute(attributes, name) {
  const value = Number.parseInt(attributes[name] ?? '0', 10)
  return Number.isFinite(value) ? value : 0
}

function parseJunitStats(junitPath) {
  if (!junitPath) {
    return null
  }
  const resolvedPath = resolve(junitPath)
  if (!existsSync(resolvedPath)) {
    return null
  }

  const xml = readFileSync(resolvedPath, 'utf8')
  const suitesMatch = xml.match(/<testsuites\b([^>]*)>/)
  if (suitesMatch) {
    const attributes = parseXmlAttributes(suitesMatch[1])
    return {
      tests: numberAttribute(attributes, 'tests'),
      failures: numberAttribute(attributes, 'failures'),
      errors: numberAttribute(attributes, 'errors'),
      skipped: numberAttribute(attributes, 'skipped'),
    }
  }

  const suiteMatches = [...xml.matchAll(/<testsuite\b([^>]*)>/g)]
  if (!suiteMatches.length) {
    return null
  }
  return suiteMatches.reduce(
    (total, match) => {
      const attributes = parseXmlAttributes(match[1])
      total.tests += numberAttribute(attributes, 'tests')
      total.failures += numberAttribute(attributes, 'failures')
      total.errors += numberAttribute(attributes, 'errors')
      total.skipped += numberAttribute(attributes, 'skipped')
      return total
    },
    { tests: 0, failures: 0, errors: 0, skipped: 0 }
  )
}

const options = parseArgs(process.argv.slice(2))
const resultsDir = resolve(requireOption(options, 'results-dir'))
const artifactName = requireOption(options, 'artifact-name')
const label = requireOption(options, 'label')
const command = options.command ?? 'n/a'
const junitPathOption = options['junit-path'] ?? null

mkdirSync(resultsDir, { recursive: true })

const stdoutPath = join(resultsDir, 'stdout.log')
const resultPath = join(resultsDir, 'result.json')
const failureContextPath = join(resultsDir, 'failure-context.json')

if (existsSync(resultPath) && existsSync(failureContextPath)) {
  process.exit(0)
}

const testStats = parseJunitStats(junitPathOption)

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
  junit_path: junitPathOption,
  test_stats: testStats,
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
  junit_path: result.junit_path,
  test_stats: testStats,
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
    testStats
      ? `- Tests: **${testStats.tests}** total, **${testStats.failures}** failures, **${testStats.errors}** errors, **${testStats.skipped}** skipped`
      : null,
    `- Summary: ${summary}`,
    '',
  ]
    .filter(Boolean)
    .join('\n')
)
