import { mkdirSync, createWriteStream, writeFileSync, appendFileSync, existsSync } from 'node:fs'
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
    summary,
    failed_step: status === 'failure' ? label : null,
  }

  writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8')
  writeFileSync(failureContextPath, `${JSON.stringify(failureContext, null, 2)}\n`, 'utf8')

  const junitLine =
    junitPathOption && existsSync(resolve(junitPathOption))
      ? `- JUnit: \`${junitPathOption}\``
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
      `- Summary: ${summary}`,
      '',
    ]
      .filter(Boolean)
      .join('\n')
  )

  process.exit(exitCode)
})
