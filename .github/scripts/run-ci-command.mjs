import { mkdirSync, createWriteStream, writeFileSync, appendFileSync, existsSync, readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { spawn } from 'node:child_process'

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

function trimOutput(text, maxLength = 12000) {
  if (text.length <= maxLength) {
    return text
  }
  return text.slice(text.length - maxLength)
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
const command = requireOption(options, 'command')
const junitPathOption = options['junit-path']

mkdirSync(resultsDir, { recursive: true })

const stdoutPath = join(resultsDir, 'stdout.log')
const resultPath = join(resultsDir, 'result.json')
const failureContextPath = join(resultsDir, 'failure-context.json')
const stdoutStream = createWriteStream(stdoutPath, { flags: 'w', encoding: 'utf8' })

const startedAt = new Date()
let outputBuffer = ''

function recordChunk(chunk) {
  const text = chunk.toString()
  process.stdout.write(text)
  stdoutStream.write(text)
  outputBuffer = trimOutput(outputBuffer + text)
}

const child = spawn(command, {
  shell: true,
  stdio: ['ignore', 'pipe', 'pipe'],
  env: process.env,
})

child.stdout.on('data', recordChunk)
child.stderr.on('data', recordChunk)

child.on('error', (error) => {
  recordChunk(Buffer.from(`${error.stack ?? error.message}\n`, 'utf8'))
})

child.on('close', (code, signal) => {
  stdoutStream.end()

  const finishedAt = new Date()
  const exitCode = typeof code === 'number' ? code : 1
  const status = exitCode === 0 && !signal ? 'success' : 'failure'
  const testStats = parseJunitStats(junitPathOption)
  const summary =
    status === 'success'
      ? `${label} succeeded.`
      : `${label} failed with exit code ${exitCode}${signal ? ` (signal: ${signal})` : ''}.`
  const result = {
    workflow: process.env.GITHUB_WORKFLOW ?? null,
    job: process.env.GITHUB_JOB ?? null,
    run_id: process.env.GITHUB_RUN_ID ?? null,
    sha: process.env.GITHUB_SHA ?? null,
    ref: process.env.GITHUB_REF ?? null,
    label,
    command,
    artifact_name: artifactName,
    status,
    exit_code: exitCode,
    signal: signal ?? null,
    started_at: startedAt.toISOString(),
    finished_at: finishedAt.toISOString(),
    duration_ms: finishedAt.getTime() - startedAt.getTime(),
    primary_log: 'stdout.log',
    junit_path: junitPathOption ?? null,
    test_stats: testStats,
    output_excerpt: outputBuffer,
    summary,
  }
  const failureContext = {
    workflow: result.workflow,
    job: result.job,
    run_id: result.run_id,
    sha: result.sha,
    ref: result.ref,
    command,
    status,
    artifact_names: [artifactName],
    primary_log: result.primary_log,
    junit_path: result.junit_path,
    test_stats: testStats,
    summary,
    failed_step: status === 'failure' ? label : null,
  }

  writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8')
  writeFileSync(failureContextPath, `${JSON.stringify(failureContext, null, 2)}\n`, 'utf8')

  const junitLine =
    junitPathOption && existsSync(resolve(junitPathOption))
      ? `- JUnit: \`${junitPathOption}\``
      : ''
  const testStatsLine = testStats
    ? `- Tests: **${testStats.tests}** total, **${testStats.failures}** failures, **${testStats.errors}** errors, **${testStats.skipped}** skipped`
    : ''
  appendSummary(
    [
      `### ${label}`,
      '',
      `- Status: **${status}**`,
      `- Artifact: \`${artifactName}\``,
      `- Command: \`${command}\``,
      `- Log: \`${dirname(stdoutPath) === resultsDir ? 'stdout.log' : stdoutPath}\``,
      junitLine,
      testStatsLine,
      `- Summary: ${summary}`,
      '',
    ]
      .filter(Boolean)
      .join('\n')
  )

  process.exit(exitCode)
})
