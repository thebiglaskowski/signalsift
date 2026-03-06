#!/usr/bin/env node
/**
 * PostToolUse Hook for Bash - Monitor gate results
 *
 * Read-only observer that records exit codes, commands, and durations
 * to gate_history.json for quality gate tracking.
 * Decision: always allow (never blocks).
 */

const fs = require('fs');
const path = require('path');
const { parseHookInput, loadState, saveState, logMessage, getProjectRoot, MAX_LOGGED_COMMAND_LENGTH, MAX_GATE_HISTORY, MAX_GATE_LOG_TRUNCATE, MAX_OBSERVATION_SIZE, MAX_GATE_OUTPUTS, pruneDirectory } = require('./utils.cjs');

/**
 * Mask large tool outputs by saving to a file and returning a reference.
 * @param {string} stdout - The tool output to check
 * @param {string} stateDir - Path to state directory
 * @returns {{ outputRef: string, lines: number, preview: string }|null} Ref or null if no masking needed
 */
function maskLargeOutput(stdout, stateDir) {
    if (!stdout || stdout.length <= MAX_OBSERVATION_SIZE) return null;

    const outputDir = path.join(stateDir, 'gate-output');
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const outFile = path.join(outputDir, `gate-output-${timestamp}.txt`);
    fs.writeFileSync(outFile, stdout, 'utf8');
    pruneDirectory(outputDir, MAX_GATE_OUTPUTS, 'gate-output-');

    const lines = stdout.split('\n').length;
    const preview = stdout.substring(0, 200).replace(/\n/g, ' ');
    return { outputRef: outFile, lines, preview };
}

// Only record gate-relevant commands (lint, test, build, format)
const GATE_PATTERNS = [
    /\b(ruff|eslint|golangci-lint|clippy|checkstyle|rubocop|clang-tidy|shellcheck|cppcheck)\b/,
    /\b(pytest|vitest|jest|mocha|go\s+test|cargo\s+test|mvn\s+test|rspec|ctest)\b/,
    /\b(tsc|cargo\s+build|cmake\s+--build|mvn\s+compile|go\s+build|make)\b/,
    /\b(gofmt|clang-format|prettier|black|ruff\s+format)\b/,
    /\bnode\s+.*__tests__/
];

function main() {
    const parsed = parseHookInput();
    const command = parsed.tool_input?.command || '';
    const exitCode = parsed.tool_result?.exit_code ?? parsed.tool_result?.exitCode ?? null;
    const duration = parsed.tool_result?.duration_ms ?? null;
    const stdout = parsed.tool_result?.stdout || '';

    // Early exit for non-gate commands — avoids sync disk ops per Bash call
    const isGate = GATE_PATTERNS.some(p => p.test(command));
    if (!isGate) {
        process.exit(0);
    }

    // Only gate commands reach here
    const history = loadState('gate_history.json', { entries: [] });
    const stateDir = path.join(getProjectRoot(), '.claude', 'state');

    const entry = {
        timestamp: new Date().toISOString(),
        command: command.substring(0, MAX_LOGGED_COMMAND_LENGTH),
        exitCode,
        duration,
        // null exit code = inconclusive (hook input didn't include exit code)
        passed: exitCode === null ? null : exitCode === 0
    };

    // Mask large outputs — save to file, store reference instead
    const masked = maskLargeOutput(stdout, stateDir);
    if (masked) {
        entry.outputRef = masked.outputRef;
        entry.outputLines = masked.lines;
        entry.outputPreview = masked.preview;
    }

    history.entries.push(entry);

    // Cap history size
    if (history.entries.length > MAX_GATE_HISTORY) {
        history.entries = history.entries.slice(-MAX_GATE_HISTORY);
    }

    saveState('gate_history.json', history);

    // Only log as failure when exit code is definitively non-zero
    if (exitCode !== null && exitCode !== 0) {
        logMessage(`Gate failed: ${command.substring(0, MAX_GATE_LOG_TRUNCATE)} (exit ${exitCode})`, 'WARNING');
    }

    // PostToolUse is observe-only — no output needed
}

main();
