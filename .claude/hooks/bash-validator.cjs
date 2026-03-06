#!/usr/bin/env node
/**
 * PreToolUse Hook for Bash - Validate dangerous commands
 *
 * Triggered before Bash tool execution.
 * Blocks dangerous commands that could harm the system.
 */

const { parseHookInput, logMessage, MAX_LOGGED_COMMAND_LENGTH, MAX_INPUT_SIZE } = require('./utils.cjs');

// Dangerous command patterns
const DANGEROUS_PATTERNS = [
    // Destructive file operations — block any rm with combined -r and -f flags regardless of path
    { pattern: /\brm\s+(-\w*r\w*f\w*|-\w*f\w*r\w*)/i, reason: 'Recursive force delete (rm -rf)' },
    { pattern: /\brm\b.*--recursive\b/i, reason: 'Recursive force delete (rm --recursive long flag)' },
    { pattern: /\brm\b.*--no-preserve-root\b/i, reason: 'Delete from root (rm --no-preserve-root)' },

    // Disk operations
    { pattern: />\s*\/dev\/sd/, reason: 'Direct write to disk device' },
    { pattern: /mkfs/, reason: 'Filesystem creation' },
    { pattern: /dd\s+if=.*of=\/dev/, reason: 'Direct disk write with dd' },

    // Permission changes
    { pattern: /chmod\s+-R\s+777\s+\//, reason: 'Recursive chmod 777 from root' },
    { pattern: /chown\s+-R\s+.*\s+\//, reason: 'Recursive chown from root' },

    // System modification
    { pattern: /:(){ :|:& };:/, reason: 'Fork bomb' },
    { pattern: />\s*\/dev\/null\s*2>&1\s*&\s*disown/, reason: 'Background process hiding' },

    // Network attacks
    { pattern: /nc\s+-l.*-e\s+\/bin/, reason: 'Netcat reverse shell' },

    // History manipulation
    { pattern: /history\s+-c/, reason: 'Clear command history' },
    { pattern: /shred.*\.bash_history/, reason: 'Shred bash history' },

    // Supply-chain attacks — piping remote scripts to interpreters
    { pattern: /curl.*\|\s*(sh|bash|zsh|fish|python[23]?|node|ruby|perl)/, reason: 'Piping curl to interpreter' },
    { pattern: /wget.*\|\s*(sh|bash|zsh|fish|python[23]?|node|ruby|perl)/, reason: 'Piping wget to interpreter' },
    // Supply-chain bypass via command substitution: bash -c "$(curl URL)"
    { pattern: /(?:bash|sh|zsh|fish)\b.*\$\((?:curl|wget)\s/, reason: 'Shell executing curl/wget via command substitution' },
    // Supply-chain bypass via process substitution: bash <(curl URL)
    { pattern: /(?:bash|sh|zsh|fish)\s+<\((?:curl|wget)\s/, reason: 'Shell executing curl/wget via process substitution' },

    // Encoded command injection
    { pattern: /base64\s+(-d|--decode).*\|\s*(sh|bash|zsh)/, reason: 'Base64-encoded command injection' },

    // Destructive find operations
    { pattern: /\bfind\s+\/\s+.*-delete\b/, reason: 'find with -delete from root' },
    { pattern: /\bfind\s+\/\s+.*-exec\s+rm\b/, reason: 'find with -exec rm from root' },

    // Scripting language one-liners (obfuscation risk)
    // Note: ['"]? makes the quote optional to catch ANSI-C quoting bypass ($'...') and
    // unquoted forms that survive normalizeCommand's quote-stripping pass.
    { pattern: /\bpython[23]?\s+-c\s+['"]?.*(?:import\s+(?:os|socket|pty)|subprocess|eval|exec|__import__)/, reason: 'Python one-liner with dangerous imports or functions' },
    { pattern: /\bperl\s+-e\s+['"]?.*(?:system|exec|unlink)/, reason: 'Perl one-liner with dangerous functions' },
    { pattern: /\bruby\s+-e\s+['"]?.*(?:system|exec|File\.delete)/, reason: 'Ruby one-liner with dangerous functions' },
    { pattern: /\bnode\s+(?:-e|--eval)\s+['"]?.*(?:child_process|fs\.rm|fs\.unlink|fs\.writeFileSync|fs\.rmdirSync|fs\.unlinkSync|fs\.appendFileSync|fs\.chmod|fs\.mkdir|fs\.rename|fs\.copyFile|fs\.symlink|fs\.createWriteStream)/, reason: 'Node one-liner with dangerous modules' },

    // Supply-chain attacks — downloading then executing (chained with && or ;)
    { pattern: /curl\s.*>\s*\S+\.sh\s*[;&|]+\s*(sh|bash|zsh|source)\s/, reason: 'Downloading script then executing' },
    { pattern: /wget\s.*-O\s*\S+\.sh\s*[;&|]+\s*(sh|bash|zsh|source)\s/, reason: 'Downloading script then executing' },
    { pattern: /curl\s.*>\s*\S+\s*[;&|]+\s*(chmod\s.*\+x|\.\/\S)/, reason: 'Downloading file then making executable' },
    { pattern: /wget\s.*-O\s*\S+\s*[;&|]+\s*(chmod\s.*\+x|\.\/\S)/, reason: 'Downloading file then making executable' },

    // Direct disk writes, bulk deletion, and privilege escalation
    { pattern: /\btee\s+\/dev\/sd[a-z]/i, reason: 'Direct disk write via tee' },
    { pattern: /\bfind\b.*\bxargs\b.*\brm\b/i, reason: 'Bulk file deletion via find|xargs' },
    { pattern: /\bchmod\s+[ao]\+[rwx]*w/i, reason: 'World/all-writable permission change' },
    { pattern: /\bchmod\s+-R\s+[0-7]*[2367][0-7]{2}\s+\//i, reason: 'Recursive world-writable chmod on root' },
    { pattern: /\bsudo\s+bash\b|\bsudo\s+sh\b/i, reason: 'Privilege escalation to root shell' },

    // Shell eval execution — match only when eval is used as a shell command,
    // not when it appears inside argument strings (e.g. node --eval, git commit -m "eval")
    { pattern: /(^|[|;&{(=]\s*)eval\b/, reason: 'Shell eval execution' },

    // Broader sudo privilege escalation patterns
    { pattern: /\bsudo\s+(?:bash|sh|su\b|su\s+-|-i\b|-s\b)/, reason: 'Privilege escalation via sudo' },

    // Privilege escalation via sudo (writing to system files, editing sudoers, SUID bits)
    { pattern: /\bsudo\s+tee\s+\/etc\//, reason: 'Writing to /etc/ via sudo tee' },
    { pattern: /\bsudo\s+visudo\b/, reason: 'Editing sudoers file via sudo visudo' },
    { pattern: /\bsudo\s+passwd\s+root\b/, reason: 'Changing root password via sudo' },
    { pattern: /\bsudo\s+chmod\s+[ugo+]*s/, reason: 'Setting SUID/SGID bit via sudo' },

    // Reverse shell variants not covered by netcat pattern
    { pattern: /\bsocat\b.*\b(?:EXEC|TCP|UDP):.*(?:bash|sh|cmd)/i, reason: 'socat reverse shell' },
    { pattern: /\bopenssl\s+s_client\b.*\|\s*(?:bash|sh)\b/i, reason: 'openssl reverse shell via s_client' },
    { pattern: /\bncat\b.*-e\s+\/(?:bin|usr)/i, reason: 'ncat reverse shell (-e flag)' },

    // Cron-based persistence
    { pattern: /\bcrontab\s+-[eli]\b/, reason: 'Crontab modification (persistence vector)' },
    { pattern: /\becho\b.*\|\s*crontab\b/, reason: 'Piping to crontab (persistence vector)' },

    // Environment variable injection
    { pattern: /\bLD_PRELOAD\s*=/, reason: 'LD_PRELOAD library injection' },
];

// Warning patterns (allow but log)
const WARNING_PATTERNS = [
    { pattern: /sudo\s+/, reason: 'Using sudo' },
    { pattern: /npm\s+install\s+-g/, reason: 'Global npm install' },
    { pattern: /pip\s+install\s+--user/, reason: 'User pip install' }
];

/**
 * Normalize a command string to prevent regex bypasses.
 * Handles: variable substitution, full paths, extra whitespace, encoding tricks.
 * @param {string} cmd - Raw command string
 * @returns {string} Normalized command for pattern matching
 */
function normalizeCommand(cmd) {
    let normalized = cmd;
    normalized = normalized.replace(/\s+/g, ' ').trim();
    normalized = normalized.replace(/\$'((?:[^'\\]|\\.)*)'/g, '$1');
    normalized = normalized.replace(/\$\{(\w+)\}/g, '$1');
    normalized = normalized.replace(/\$(\w+)/g, '$1');
    normalized = normalized.replace(/(?:\/usr\/local\/s?bin|\/usr\/s?bin|\/s?bin)\/(\w+)/g, '$1');
    normalized = normalized.replace(/["']([^"']+)["']/g, '$1');
    normalized = normalized.replace(/\\(?=\w)/g, '');
    normalized = normalized.replace(/`([^`]*)`/g, '$1');
    let _iterCount = 0;
    let prev;
    do { prev = normalized; normalized = normalized.replace(/\$\(([^)]*)\)/g, '$1'); }
    while (normalized !== prev && ++_iterCount < 10);
    return normalized;
}

/**
 * Check for oversized HOOK_INPUT and block if too large.
 * @returns {boolean} true if input was blocked (caller should exit)
 */
function rejectOversizedInput() {
    const hookInputStr = process.env.HOOK_INPUT;
    if (hookInputStr && hookInputStr.length > MAX_INPUT_SIZE) {
        console.log(JSON.stringify({
            hookSpecificOutput: { permissionDecision: 'deny', permissionDecisionReason: 'BLOCKED: Hook input too large to process safely' },
            command: '[oversized input]'
        }));
        logMessage('BLOCKED: Oversized hook input rejected (potential bypass attempt)', 'BLOCKED');
        return true;
    }
    return false;
}

/**
 * Test command against DANGEROUS_PATTERNS and block on first match.
 * @param {string} command - Normalized command
 * @param {string} rawCommand - Original command (for pre-normalization patterns)
 * @returns {boolean} true if command was blocked
 */
function blockIfDangerous(command, rawCommand) {
    for (const { pattern, reason } of DANGEROUS_PATTERNS) {
        if (pattern.test(command) || pattern.test(rawCommand)) {
            console.log(JSON.stringify({
                hookSpecificOutput: { permissionDecision: 'deny', permissionDecisionReason: `BLOCKED: ${reason}` },
                command: command.substring(0, MAX_LOGGED_COMMAND_LENGTH)
            }));
            logMessage(`BLOCKED dangerous command: ${reason}`, 'BLOCKED');
            return true;
        }
    }
    return false;
}

/**
 * Collect warnings from WARNING_PATTERNS for a command.
 * @param {string} command - Normalized command
 * @returns {string[]} Array of warning reason strings
 */
function collectWarnings(command) {
    const warnings = [];
    for (const { pattern, reason } of WARNING_PATTERNS) {
        if (pattern.test(command)) {
            warnings.push(reason);
        }
    }
    return warnings;
}

function main() {
    if (rejectOversizedInput()) { process.exit(0); }

    const parsed = parseHookInput();
    const rawCommand = parsed.tool_input?.command || parsed.command || '';
    const command = normalizeCommand(rawCommand);

    if (blockIfDangerous(command, rawCommand)) { process.exit(0); }

    const warnings = collectWarnings(command);
    if (warnings.length > 0) { logMessage(warnings.join(', '), 'WARNING'); }

    console.log(JSON.stringify({
        hookSpecificOutput: { permissionDecision: 'allow', permissionDecisionReason: warnings.length > 0 ? warnings.join('; ') : undefined },
        warnings: warnings.length > 0 ? warnings : undefined
    }));
}

main();
