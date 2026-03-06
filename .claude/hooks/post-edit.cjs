#!/usr/bin/env node
/**
 * PostToolUse Hook for Write/Edit - Track changes and suggest lint
 *
 * Triggered after Write or Edit tool execution.
 * Tracks file changes and suggests running lint for code files.
 */

const path = require('path');
const { parseHookInput, loadState, saveState, logMessage, MAX_FILE_CHANGES } = require('./utils.cjs');

// Extension-to-lint-command mapping (module-level constant)
const CODE_EXTENSIONS = {
    '.py': 'ruff check', '.ts': 'eslint', '.tsx': 'eslint',
    '.js': 'eslint', '.jsx': 'eslint', '.go': 'golangci-lint run',
    '.rs': 'cargo clippy', '.rb': 'rubocop', '.java': 'checkstyle', '.sh': 'shellcheck'
};

/**
 * Track a file change in state, updating existing entries or appending new ones.
 * @param {string} filePath - Path of the changed file
 * @param {string} toolName - Tool that made the change
 * @returns {Array} Updated changes array
 */
function trackFileChange(filePath, toolName) {
    let changes = loadState('file_changes.json', []);
    const changeEntry = { path: filePath, tool: toolName, timestamp: new Date().toISOString() };
    const existingIndex = changes.findIndex(c => c.path === filePath);
    if (existingIndex >= 0) {
        changes[existingIndex] = changeEntry;
    } else {
        changes.push(changeEntry);
    }
    if (changes.length > MAX_FILE_CHANGES) changes = changes.slice(-MAX_FILE_CHANGES);
    saveState('file_changes.json', changes);
    return changes;
}

/**
 * Suggest lint commands based on file extension.
 * @param {string} filePath - Path of the changed file
 * @returns {string[]} Array of suggestion strings
 */
function suggestLint(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const lintCmd = CODE_EXTENSIONS[ext];
    return lintCmd ? [`Consider running lint: ${lintCmd}`] : [];
}

function main() {
    const parsed = parseHookInput();
    const filePath = parsed.tool_input?.file_path || parsed.tool_input?.path || '';
    const toolName = parsed.tool_name || 'unknown';

    if (parsed.tool_result?.success === false || !filePath) {
        console.log(JSON.stringify({ tracked: false }));
        process.exit(0);
    }

    const changes = trackFileChange(filePath, toolName);
    const suggestions = suggestLint(filePath);
    logMessage(`${toolName} completed: ${filePath}`);

    console.log(JSON.stringify({
        tracked: true, path: filePath, totalChanges: changes.length,
        suggestions: suggestions.length > 0 ? suggestions : undefined
    }));
}

main();
