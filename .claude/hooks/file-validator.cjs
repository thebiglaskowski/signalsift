#!/usr/bin/env node
/**
 * PreToolUse Hook for Write/Edit - Validate file operations
 *
 * Triggered before Write or Edit tool execution.
 * Validates file paths and prevents dangerous overwrites.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { parseHookInput, logMessage, getProjectRoot, validateFilePath, LARGE_FILE_THRESHOLD, SECRET_PATTERNS } = require('./utils.cjs');

// Cached home directory (resolved once per process)
const _cachedHomeDir = os.homedir();

// Protected paths that should never be modified
const PROTECTED_PATHS = [
    // System files
    /^\/etc\//,
    /^\/usr\//,
    /^\/bin\//,
    /^\/sbin\//,
    /^C:\\Windows\\/i,
    /^C:\\Program Files/i,

    // User sensitive files
    /\.ssh\/.*$/,
    /\.gnupg\/.*$/,
    /\.aws\/credentials$/,
    /\.env\.production$/,

    // Git internals, config, and hooks (can contain credentials or enable code execution)
    /\.git\/objects\//,
    /\.git\/refs\//,
    /\.git\/HEAD$/,
    /\.git\/config$/,
    /\.git\/hooks\//,

    // Container and package manager credentials
    /\.kube[/\\]config$/,           // Kubernetes cluster credentials
    /\.docker[/\\]config\.json$/,   // Docker registry credentials
    /\.cargo[/\\]credentials$/,      // Rust crates.io token

    // Shell config files (persistent code execution)
    /[/\\]\.bashrc$/,               // persistent shell code execution
    /[/\\]\.zshrc$/,
    /[/\\]\.bash_profile$/,
    /[/\\]\.profile$/,
    /[/\\]\.gitconfig$/,            // can redirect git hook execution
    /[/\\]\.aws[/\\]config$/,       // AWS role/credential_process config
];

// Files that need confirmation (warn but allow)
const SENSITIVE_FILES = [
    /\.env$/,
    /\.env\.local$/,
    /\.env\.staging$/,
    /\.env\.development$/,
    /\.env\.test$/,
    /secrets?\./i,
    /credentials?\./i,
    /password/i,
    /api[_-]?key/i,
    /\.pem$/,
    /\.key$/,
    /id_rsa/,
    /id_ed25519/,
    /\.netrc$/,
    /\.npmrc$/
];

/**
 * Resolve the real path of a file, following symlinks.
 * @param {string} filePath - Path to resolve
 * @returns {string} Resolved path, or original path if resolution fails
 */
function resolveRealPath(filePath) {
    try { return fs.realpathSync(filePath); } catch (_) { return filePath; }
}

/**
 * Block a file operation with a reason and exit.
 * @param {string} toolName - Name of the tool being blocked
 * @param {string} reason - Reason for blocking
 * @param {string} filePath - Path being blocked
 */
function blockPath(toolName, reason, filePath) {
    console.log(JSON.stringify({ hookSpecificOutput: { permissionDecision: 'deny', permissionDecisionReason: `BLOCKED: ${reason}` }, path: filePath }));
    logMessage(`BLOCKED ${toolName}: ${reason} - ${filePath}`, 'BLOCKED');
    process.exit(0);
}

/**
 * Resolve a file path to its real absolute path, following symlinks.
 * @param {string} filePath - Path to resolve
 * @returns {{resolvedPath: string, absolutePath: string, fileExists: boolean}}
 */
function resolveToAbsolutePath(filePath) {
    const fileExists = fs.existsSync(filePath);
    let resolvedPath = filePath;
    if (fileExists) {
        const realPath = resolveRealPath(filePath);
        if (realPath !== path.resolve(filePath)) resolvedPath = realPath;
    } else {
        const parentDir = path.dirname(filePath);
        if (fs.existsSync(parentDir)) {
            resolvedPath = path.join(resolveRealPath(parentDir), path.basename(filePath));
        }
    }
    return { resolvedPath, absolutePath: path.resolve(resolvedPath), fileExists };
}

/**
 * Check global Claude Code settings/commands/rules and project boundary.
 * Calls blockPath (exits) if any boundary is violated.
 */
function checkProjectBoundaries({ absolutePath, projectRoot, claudeHome }, toolName, filePath) {
    const globalSettingsProtected = [
        path.join(claudeHome, 'settings.json'),
        path.join(claudeHome, 'settings.local.json')
    ];
    if (globalSettingsProtected.some(p => absolutePath === p)) {
        blockPath(toolName, 'Cannot modify global Claude Code settings', filePath);
    }
    if (absolutePath.startsWith(path.join(claudeHome, 'commands') + path.sep) ||
        absolutePath.startsWith(path.join(claudeHome, 'rules') + path.sep)) {
        blockPath(toolName, 'Cannot modify global Claude Code commands or rules', filePath);
    }
    if (!absolutePath.startsWith(path.resolve(projectRoot) + path.sep) &&
        !absolutePath.startsWith(os.tmpdir() + path.sep) &&
        !absolutePath.startsWith(claudeHome + path.sep)) {
        blockPath(toolName, 'Cannot modify files outside project root', filePath);
    }
}

/**
 * Protect active hook scripts from self-modification during a session.
 * Calls blockPath (exits) if the absolute path targets a .cjs file in the hooks directory.
 * @param {string} absolutePath - Absolute resolved path of the file being written
 */
function checkHookSelfProtection(absolutePath, projectRoot, toolName, filePath) {
    const hookDir = path.join(projectRoot, '.claude', 'hooks');
    if (absolutePath.startsWith(hookDir + path.sep) && absolutePath.endsWith('.cjs')) {
        blockPath(toolName, 'Cannot modify active hook scripts. Edit hooks outside a running session or restart after changes', filePath);
    }
}

/**
 * Check a path against the PROTECTED_PATHS list.
 * Calls blockPath (exits) on first match.
 */
function checkProtectedPaths(normalizedPath, filePath, toolName) {
    for (const pattern of PROTECTED_PATHS) {
        if (pattern.test(normalizedPath) || pattern.test(filePath)) {
            blockPath(toolName, 'Cannot modify protected path', filePath);
        }
    }
}

/**
 * Collect warning strings for sensitive files and large files.
 * @returns {string[]} Array of warning messages (may be empty)
 */
function collectWarnings(normalizedPath, filePath, fileExists) {
    const warnings = [];
    for (const pattern of SENSITIVE_FILES) {
        if (pattern.test(normalizedPath) || pattern.test(path.basename(filePath))) {
            warnings.push('Modifying sensitive file');
            break;
        }
    }
    if (fileExists) {
        const stats = fs.statSync(filePath);
        if (stats.size > LARGE_FILE_THRESHOLD) {
            warnings.push('Large file modification');
        }
    }
    return warnings;
}


/**
 * Scan file content for embedded secrets or API keys.
 * Warns (does not block) when a potential secret pattern is detected.
 * Covers both Write (full content) and Edit (new_string) tool inputs.
 * @param {string} content - Content being written
 * @returns {string[]} Warning messages if potential secrets detected
 */
function scanContentForSecrets(content) {
    if (!content) return [];
    for (const pattern of SECRET_PATTERNS) {
        const regex = new RegExp(pattern.source, pattern.flags);
        if (regex.test(content)) {
            return ['Potential secret or API key detected in file content — review before committing'];
        }
    }
    return [];
}

function main() {
    const parsed = parseHookInput();
    const filePath = parsed.tool_input?.file_path || parsed.tool_input?.path || '';
    const toolName = parsed.tool_name || 'unknown';

    const pathError = validateFilePath(filePath);
    if (pathError) {
        blockPath(toolName, pathError, filePath);
    }

    const { resolvedPath, absolutePath, fileExists } = resolveToAbsolutePath(filePath);
    const normalizedPath = path.normalize(resolvedPath).replace(/\\/g, '/');
    const projectRoot = getProjectRoot();
    const claudeHome = path.join(_cachedHomeDir, '.claude');

    checkProjectBoundaries({ absolutePath, projectRoot, claudeHome }, toolName, filePath);
    checkHookSelfProtection(absolutePath, projectRoot, toolName, filePath);
    checkProtectedPaths(normalizedPath, filePath, toolName);

    // Warn on writes to ~/.claude/projects/ (auto-memory persistence vector)
    const claudeProjects = path.join(claudeHome, 'projects');
    if (absolutePath.startsWith(claudeProjects + path.sep)) {
        logMessage(`WARNING ${toolName}: Writing to auto-memory directory: ${filePath}`, 'WARNING');
    }

    const warnings = collectWarnings(normalizedPath, filePath, fileExists);
    const fileContent = parsed.tool_input?.content || parsed.tool_input?.new_string || '';
    warnings.push(...scanContentForSecrets(fileContent));
    if (warnings.length > 0) {
        logMessage(`${toolName}: ${warnings.join(', ')} - ${filePath}`, 'WARNING');
    }

    console.log(JSON.stringify({
        hookSpecificOutput: { permissionDecision: 'allow' },
        warnings: warnings.length > 0 ? warnings : undefined,
        path: filePath
    }));
}

main();
