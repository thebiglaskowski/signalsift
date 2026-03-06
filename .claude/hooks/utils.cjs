#!/usr/bin/env node
/**
 * Shared utilities for Claude Sentient hooks
 *
 * Provides common functionality used across multiple hooks:
 * - State directory management
 * - Hook input parsing
 * - JSON file I/O
 * - Logging
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Cached project root (resolved once per process invocation)
let _cachedProjectRoot = null;

/**
 * Get the project root directory.
 * Uses git rev-parse --show-toplevel, falls back to walking up
 * looking for .claude/ directory, then falls back to cwd.
 * Result is cached per process invocation.
 * @returns {string} Absolute path to project root
 */
function getProjectRoot() {
    if (_cachedProjectRoot) return _cachedProjectRoot;

    // Fast path: read project_root from session_start.json (written by session-start hook)
    try {
        const sessionFile = path.join(process.cwd(), '.claude', 'state', 'session_start.json');
        const cached = JSON.parse(fs.readFileSync(sessionFile, 'utf8'));
        if (cached.project_root && fs.existsSync(cached.project_root)) {
            _cachedProjectRoot = cached.project_root;
            return _cachedProjectRoot;
        }
    } catch (_) {}

    // Try git rev-parse
    try {
        const root = execSync('git rev-parse --show-toplevel', GIT_EXEC_OPTIONS).trim();
        if (root && fs.existsSync(root)) {
            _cachedProjectRoot = root;
            return root;
        }
    } catch (e) {
        // Not in a git repo, fall through
    }

    // Walk up looking for .claude/ directory
    let dir = process.cwd();
    while (dir !== path.dirname(dir)) {
        if (fs.existsSync(path.join(dir, '.claude'))) {
            _cachedProjectRoot = dir;
            return dir;
        }
        dir = path.dirname(dir);
    }

    // Fallback to cwd
    _cachedProjectRoot = process.cwd();
    return _cachedProjectRoot;
}


// Named constants for state management limits
const MAX_PROMPT_HISTORY = 50;
const MAX_FILE_CHANGES = 100;
const MAX_RESULT_LENGTH = 500;
const MAX_BACKUPS = 10;
const MAX_AGENT_HISTORY = 50;

// Constants used by individual hooks (centralized here for single source of truth)
const MAX_FILES_PER_TASK = 20;         // task-completed.cjs: max files per teammate task
const LARGE_FILE_THRESHOLD = 100000;   // file-validator.cjs: 100KB threshold for warnings
const MAX_ACTIVE_AGENTS = 50;          // agent-tracker.cjs: cap on tracked agents
const MAX_ARCHIVES = 100;              // session-end.cjs: cap on session archives
const MAX_LOG_SIZE = 1048576;          // utils.cjs: 1MB log rotation threshold
const MAX_COMPLETED_TASKS = 100;       // task-completed.cjs: cap on completed task history
const MAX_FILE_OWNERSHIP = 200;        // task-completed.cjs: cap on file ownership entries
const MAX_TEAMMATES = 50;              // teammate-idle.cjs: cap on tracked teammates
const MAX_LOGGED_COMMAND_LENGTH = 500; // bash-validator.cjs: truncation for logged commands

// Canonical default shape for team-state.json (used by task-completed.cjs and teammate-idle.cjs)
const TEAM_STATE_DEFAULT = Object.freeze({ teammates: {}, completed_tasks: [], file_ownership: {} });
const MAX_COMPACT_FILE_HISTORY = 10;  // pre-compact.cjs: recent file changes in compact summary
const MAX_COMPACT_DECISION_HISTORY = 5; // pre-compact.cjs: recent decisions in compact summary
const MS_PER_MINUTE = 60000;          // session-end.cjs: milliseconds-to-minutes conversion
const MS_PER_SECOND = 1000;           // agent-synthesizer.cjs: milliseconds-to-seconds conversion
const MAX_PATH_LENGTH = 4096;         // file-validator.cjs: maximum file path length (internal only)
const MAX_INPUT_SIZE = 1048576;       // parseHookInput: max HOOK_INPUT size (1MB)
const MAX_SANITIZE_DEPTH = 50;        // sanitizeJson: max recursion depth
const MAX_GATE_HISTORY = 200;         // gate-monitor.cjs: cap on gate history entries
const MAX_GATE_LOG_TRUNCATE = 80;     // gate-monitor.cjs: truncation for gate log messages
const CONTEXT_DEGRADATION_THRESHOLD = 20; // context-injector.cjs: high warning threshold (prompt count)
const CONTEXT_DEGRADATION_EARLY = 15;     // context-injector.cjs: medium warning threshold
const MAX_OBSERVATION_SIZE = 8000;    // gate-monitor.cjs: max stdout chars before masking to file
const MAX_GATE_OUTPUTS = 20;          // gate-monitor.cjs: cap on saved gate output files

const MIN_SHELL_FILES = 3;              // session-start.cjs: threshold for shell profile detection
const SESSION_ID_SUFFIX_LEN = 9;        // session-start.cjs: random suffix length for session IDs

const GIT_TIMEOUT_MS = 3000;           // git operations timeout in milliseconds
// Centralized git exec options (eliminates duplication across hooks)
const GIT_EXEC_OPTIONS = { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], timeout: GIT_TIMEOUT_MS };

// Patterns for redacting secrets from log output
// Patterns are ordered so specific prefixed secrets run before broad catch-alls
// (prevents the generic AWS base64 pattern from partially consuming prefixed tokens).
const SECRET_PATTERNS = [
    /sk-[a-zA-Z0-9_\-]{20,}/g,        // OpenAI/Anthropic API keys (including sk-ant-api03- format)
    /ghp_[a-zA-Z0-9]{36,}/g,          // GitHub personal access tokens
    /gho_[a-zA-Z0-9]{36,}/g,          // GitHub OAuth tokens
    /ghu_[a-zA-Z0-9]{36,}/g,          // GitHub user tokens
    /ghs_[a-zA-Z0-9]{36,}/g,          // GitHub server tokens
    /github_pat_[a-zA-Z0-9_]{80,}/g,  // GitHub fine-grained PATs
    /Bearer\s+[a-zA-Z0-9._\-]{20,}/g, // Bearer tokens
    /AKIA[A-Z0-9]{16}/g,              // AWS access key IDs
    /xox[bpsa]-[a-zA-Z0-9\-]{10,}/g,  // Slack tokens
    /eyJ[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}/g, // JWTs
    /sk_live_[a-zA-Z0-9]{20,}/g,          // Stripe secret keys
    /pk_live_[a-zA-Z0-9]{20,}/g,          // Stripe publishable keys
    /(?:postgres|mysql|mongodb):\/\/\w+:[^@]+@/g, // Database connection strings (mask password)
    /-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----/g, // Private key headers
    /ya29\.[a-zA-Z0-9_\-]{68,}/g,         // GCP OAuth access tokens (before AWS catch-all)
    /AccountKey=[a-zA-Z0-9+\/=]{40,}/g,   // Azure Storage account keys
    /npm_[a-zA-Z0-9]{36,}/g,              // npm automation tokens
    /pypi-[a-zA-Z0-9_\-]{100,}/g,         // PyPI API tokens
    /SK[a-f0-9]{32}/g,                    // Twilio API keys (SK + 32 hex chars)
    /SG\.[a-zA-Z0-9_\-]{66}/g,            // SendGrid API keys (SG. + 66 chars)
    /hvs\.[a-zA-Z0-9_\-]{24,}/g,          // HashiCorp Vault service tokens
    /[a-zA-Z0-9\/+]{40}(?=\s|$)/g,    // AWS secret keys (40-char base64) — keep last
];

// Cached state directory path (verified once per process)
let _cachedStateDir = null;

/**
 * Ensure the .claude/state directory exists
 * @returns {string} Path to the state directory
 */
function ensureStateDir() {
    if (_cachedStateDir) return _cachedStateDir;
    const stateDir = path.join(getProjectRoot(), '.claude', 'state');
    if (!fs.existsSync(stateDir)) {
        fs.mkdirSync(stateDir, { recursive: true });
    }
    _cachedStateDir = stateDir;
    return stateDir;
}

/**
 * Check if an input string exceeds MAX_INPUT_SIZE and log a warning if so.
 * @param {string} input - Input string to check
 * @param {string} source - Label for log message ('HOOK_INPUT' or 'stdin')
 * @returns {boolean} true if the input is too large
 */
function isInputTooLarge(input, source) {
    if (input.length <= MAX_INPUT_SIZE) return false;
    logMessage(`${source} too large (${input.length} bytes, max ${MAX_INPUT_SIZE})`, 'WARNING');
    return true;
}

/**
 * Parse hook input from environment variable or stdin
 * @returns {Object} Parsed input object or empty object if parsing fails
 */
function parseHookInput() {
    try {
        const input = process.env.HOOK_INPUT;
        if (input && !isInputTooLarge(input, 'HOOK_INPUT')) {
            return sanitizeJson(JSON.parse(input));
        }
    } catch (e) {
        // Fall through to stdin
    }

    try {
        const stdin = fs.readFileSync(0, 'utf8');
        if (!isInputTooLarge(stdin, 'stdin')) {
            return sanitizeJson(JSON.parse(stdin));
        }
        return {};
    } catch (e) {
        return {};
    }
}

/**
 * Sanitize parsed JSON to prevent prototype pollution.
 * Removes __proto__, constructor, and prototype keys.
 * @param {*} obj - Parsed JSON value
 * @returns {*} Sanitized value
 */
function sanitizeJson(obj, depth = 0) {
    if (depth > MAX_SANITIZE_DEPTH) return null; // Truncate deeply nested objects rather than returning unsanitized
    if (obj === null || typeof obj !== 'object') {
        return obj;
    }
    if (Array.isArray(obj)) {
        return obj.map(item => sanitizeJson(item, depth + 1));
    }
    const clean = Object.create(null);
    for (const [key, value] of Object.entries(obj)) {
        if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
            continue; // Skip dangerous keys
        }
        clean[key] = sanitizeJson(value, depth + 1);
    }
    return clean;
}

/**
 * Redact secrets from a string before logging.
 * @param {string} text - Text to redact
 * @returns {string} Text with secrets replaced by [REDACTED]
 */
function redactSecrets(text) {
    // Fast path: shortest possible secret is ~20 chars (sk- prefix + token body)
    if (text.length < 20) return text;
    let redacted = text;
    for (const pattern of SECRET_PATTERNS) {
        redacted = redacted.replace(pattern, '[REDACTED]');
    }
    return redacted;
}

/**
 * Load JSON data from a file
 * @param {string} filePath - Path to the JSON file
 * @param {Object} defaultValue - Default value if file doesn't exist or is invalid
 * @returns {Object} Parsed JSON or default value (sanitized against prototype pollution)
 */
function loadJsonFile(filePath, defaultValue = {}) {
    try {
        const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        return sanitizeJson(parsed);
    } catch (e) {
        // ENOENT (file not found) is expected — return default silently
        if (e.code !== 'ENOENT') {
            logMessage(`Failed to parse ${path.basename(filePath)}: ${e.message}`, 'WARNING');
        }
        return defaultValue;
    }
}

/**
 * Save JSON data to a file (atomic write via temp file + rename)
 * @param {string} filePath - Path to the JSON file
 * @param {Object} data - Data to save
 * @returns {boolean} True if successful, false otherwise
 */
function saveJsonFile(filePath, data) {
    try {
        ensureStateDir();
        const content = JSON.stringify(data, null, 2);
        const tmpPath = filePath + '.tmp.' + process.pid;
        fs.writeFileSync(tmpPath, content, 'utf8');
        fs.renameSync(tmpPath, filePath);
        return true;
    } catch (e) {
        logMessage(`Failed to save ${filePath}: ${e.message}`, 'ERROR');
        // Clean up temp file if rename failed
        try { fs.unlinkSync(filePath + '.tmp.' + process.pid); } catch (_) {}
        return false;
    }
}

/**
 * Validate file path for safety.
 * Returns null if valid, error string if invalid.
 */
function validateFilePath(filePath) {
    if (!filePath || typeof filePath !== 'string') return 'Empty or non-string path';
    if (filePath.length > MAX_PATH_LENGTH) return `Path too long (max ${MAX_PATH_LENGTH} chars)`;
    if (filePath.includes('\0')) return 'Path contains null byte';
    if (/[\n\r]/.test(filePath)) return 'Path contains newline characters';
    if (/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(filePath)) return 'Path contains control characters';
    return null;
}

/**
 * Rotate the session log file if it exceeds MAX_LOG_SIZE.
 * Renames log → log.1, removing any previous .1 backup first.
 * @param {string} logFile - Absolute path to the active log file
 */
function rotateLogIfNeeded(logFile) {
    try {
        const stats = fs.statSync(logFile);
        if (stats.size > MAX_LOG_SIZE) {
            const rotatedPath = logFile + '.1';
            try { fs.unlinkSync(rotatedPath); } catch (_) {}
            fs.renameSync(logFile, rotatedPath);
        }
    } catch (_) { /* file doesn't exist yet — that's fine */ }
}

/**
 * Log a message to the session log file.
 * Rotates the log once per process invocation if it exceeds MAX_LOG_SIZE.
 * @param {string} message - Message to log
 * @param {string} level - Log level (INFO, WARNING, ERROR, BLOCKED)
 */
let _logRotationChecked = false;
function logMessage(message, level = 'INFO') {
    const logFile = path.join(getProjectRoot(), '.claude', 'session.log');
    const timestamp = new Date().toISOString().slice(0, 19);
    const safeMessage = redactSecrets(message);
    const logEntry = `[cs] ${timestamp} ${level}: ${safeMessage}\n`;
    try {
        if (!_logRotationChecked) {
            _logRotationChecked = true;
            rotateLogIfNeeded(logFile);
        }
        fs.appendFileSync(logFile, logEntry);
    } catch (e) {
        // Fallback to stderr so log failures are visible during debugging
        process.stderr.write(`[cs] log write failed: ${e.message}\n`);
    }
}

/**
 * Prune old files in a directory, keeping only the newest N.
 * @param {string} dir - Directory to prune
 * @param {number} maxFiles - Maximum files to keep
 * @param {string} [prefix] - Optional filename prefix filter (default: .json suffix)
 */
function pruneDirectory(dir, maxFiles, prefix) {
    try {
        const files = fs.readdirSync(dir)
            .filter(f => prefix ? f.startsWith(prefix) : f.endsWith('.json'))
            .sort()
            .reverse();
        for (let i = maxFiles; i < files.length; i++) {
            try { fs.unlinkSync(path.join(dir, files[i])); } catch (_) {}
        }
    } catch (_) {}
}

/**
 * Get the path to a state file
 * @param {string} filename - Name of the state file
 * @returns {string} Full path to the state file
 */
function getStateFilePath(filename) {
    return path.join(ensureStateDir(), filename);
}

/**
 * Load state from a named state file
 * @param {string} filename - Name of the state file (without path)
 * @param {Object} defaultValue - Default value if file doesn't exist
 * @returns {Object} State data or default value
 */
function loadState(filename, defaultValue = {}) {
    return loadJsonFile(getStateFilePath(filename), defaultValue);
}

/**
 * Save state to a named state file
 * @param {string} filename - Name of the state file (without path)
 * @param {Object} data - State data to save
 * @returns {boolean} True if successful
 */
function saveState(filename, data) {
    return saveJsonFile(getStateFilePath(filename), data);
}

/**
 * Append an entry to a state array file, capped at maxLength.
 * Loads, appends, caps, and saves atomically.
 * @param {string} filename - State file name (without path)
 * @param {*} entry - Entry to append
 * @param {number} maxLength - Maximum array length
 * @param {Array} defaultVal - Default value if file doesn't exist
 */
function appendCapped(filename, entry, maxLength, defaultVal = []) {
    let arr = loadState(filename, defaultVal);
    arr.push(entry);
    if (arr.length > maxLength) arr = arr.slice(-maxLength);
    saveState(filename, arr);
    return arr.length;
}

module.exports = {
    ensureStateDir,
    parseHookInput,
    loadJsonFile,
    saveJsonFile,
    logMessage,
    getStateFilePath,
    loadState,
    saveState,
    appendCapped,
    sanitizeJson,
    redactSecrets,
    validateFilePath,
    pruneDirectory,
    MAX_PROMPT_HISTORY,
    MAX_FILE_CHANGES,
    MAX_RESULT_LENGTH,
    MAX_BACKUPS,
    MAX_AGENT_HISTORY,
    getProjectRoot,
    MAX_FILES_PER_TASK,
    LARGE_FILE_THRESHOLD,
    MAX_ACTIVE_AGENTS,
    MAX_ARCHIVES,
    MAX_LOG_SIZE,
    MAX_COMPLETED_TASKS,
    MAX_FILE_OWNERSHIP,
    MAX_TEAMMATES,
    MAX_LOGGED_COMMAND_LENGTH,
    TEAM_STATE_DEFAULT,
    MAX_COMPACT_FILE_HISTORY,
    MAX_COMPACT_DECISION_HISTORY,
    MS_PER_MINUTE,
    MS_PER_SECOND,
    MAX_GATE_HISTORY,
    MAX_GATE_LOG_TRUNCATE,
    MAX_INPUT_SIZE,
    MAX_SANITIZE_DEPTH,
    GIT_EXEC_OPTIONS,
    MIN_SHELL_FILES,
    SESSION_ID_SUFFIX_LEN,
    CONTEXT_DEGRADATION_THRESHOLD,
    CONTEXT_DEGRADATION_EARLY,
    MAX_OBSERVATION_SIZE,
    MAX_GATE_OUTPUTS,
    SECRET_PATTERNS,
};
