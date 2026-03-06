#!/usr/bin/env node
/**
 * SessionStart Hook - Initialize session context
 *
 * Triggered when a Claude Code session begins.
 * Creates session state file and injects initial context.
 *
 * NOTE: Commands (cs-loop, cs-status, cs-team, cs-ui, cs-init) depend on
 * the `profile` field in .claude/state/session_start.json written by this hook.
 * If you change the profile detection logic, update the commands accordingly.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { ensureStateDir, saveState, logMessage, GIT_EXEC_OPTIONS, getProjectRoot, MIN_SHELL_FILES, SESSION_ID_SUFFIX_LEN } = require('./utils.cjs');

/**
 * Detect project profile from root-level marker files.
 * @param {string} cwd - Current working directory
 * @returns {string|null} Profile name or null if not detected
 */
function detectRootProfile(cwd) {
    if (fs.existsSync(path.join(cwd, 'pyproject.toml')) || fs.existsSync(path.join(cwd, 'setup.py')) || fs.existsSync(path.join(cwd, 'requirements.txt'))) {
        return 'python';
    }
    if (fs.existsSync(path.join(cwd, 'tsconfig.json'))) return 'typescript';
    if (fs.existsSync(path.join(cwd, 'go.mod'))) return 'go';
    if (fs.existsSync(path.join(cwd, 'Cargo.toml'))) return 'rust';
    if (fs.existsSync(path.join(cwd, 'pom.xml')) || fs.existsSync(path.join(cwd, 'build.gradle'))) {
        return 'java';
    }
    if (fs.existsSync(path.join(cwd, 'CMakeLists.txt')) || fs.existsSync(path.join(cwd, 'Makefile'))) {
        return 'cpp';
    }
    if (fs.existsSync(path.join(cwd, 'Gemfile'))) return 'ruby';
    return null;
}

/**
 * Check a single directory for profile marker files.
 * @param {string} subdirPath - Absolute path to the directory to inspect
 * @returns {string|null} Profile name or null if not detected
 */
function detectSubdirProfile(subdirPath) {
    if (!fs.existsSync(subdirPath) || !fs.statSync(subdirPath).isDirectory()) return null;
    if (fs.existsSync(path.join(subdirPath, 'tsconfig.json'))) return 'typescript';
    if (fs.existsSync(path.join(subdirPath, 'pyproject.toml'))) return 'python';
    return null;
}

/**
 * Scan one monorepo parent directory for the first detectable subproject profile.
 * @param {string} dirPath - Absolute path to a monorepo parent (e.g. packages/, apps/)
 * @returns {string|null} First detected profile or null
 */
function scanMonorepoDir(dirPath) {
    try {
        for (const subdir of fs.readdirSync(dirPath)) {
            const result = detectSubdirProfile(path.join(dirPath, subdir));
            if (result) return result;
        }
    } catch (_) {
        // Ignore read errors on individual directories
    }
    return null;
}

/**
 * Detect project profile by scanning common monorepo directory structures.
 * @param {string} cwd - Current working directory
 * @returns {string|null} Profile name or null if not detected
 */
function detectMonorepoProfile(cwd) {
    const monorepoLocations = ['packages', 'apps', 'src'];
    // Early exit: if none of the monorepo dirs exist, skip scanning entirely
    if (!monorepoLocations.some(dir => fs.existsSync(path.join(cwd, dir)))) return null;
    for (const dir of monorepoLocations) {
        const dirPath = path.join(cwd, dir);
        if (!fs.existsSync(dirPath) || !fs.statSync(dirPath).isDirectory()) continue;
        const result = scanMonorepoDir(dirPath);
        if (result) return result;
    }
    return null;
}

/**
 * Fallback profile detection via package.json dependency inspection.
 * @param {string} cwd - Current working directory
 * @returns {string|null} 'typescript' if TypeScript is listed, 'general' if package.json exists, null otherwise
 */
function detectFromPackageJson(cwd) {
    const pkgPath = path.join(cwd, 'package.json');
    if (!fs.existsSync(pkgPath)) return null;

    try {
        const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
        if (pkg.devDependencies?.typescript || pkg.dependencies?.typescript) {
            return 'typescript';
        }
    } catch (e) {
        // Ignore parse errors
    }
    return 'general';
}

/**
 * Detect shell profile by counting shell script files in the project root.
 * @param {string} cwd - Current working directory
 * @returns {string|null} 'shell' if enough shell scripts found, null otherwise
 */
function detectShellProfile(cwd) {
    try {
        const files = fs.readdirSync(cwd);
        const shellFiles = files.filter(f => f.endsWith('.sh') || f.endsWith('.ps1'));
        if (shellFiles.length >= MIN_SHELL_FILES) return 'shell';
    } catch (e) {
        // Ignore read errors
    }
    return null;
}

/**
 * Detect the project's language profile by scanning the working directory.
 * Tries root markers, monorepo structures, package.json, and shell scripts in order.
 * @returns {string} Detected profile name (defaults to 'general')
 */
function detectProfile() {
    const cwd = process.cwd();
    return detectRootProfile(cwd)
        || detectMonorepoProfile(cwd)
        || detectFromPackageJson(cwd)
        || detectShellProfile(cwd)
        || 'general';
}

/**
 * Get git branch name and working tree status.
 * @returns {{gitBranch: string, gitStatus: string}}
 */
function getGitInfo() {
    try {
        const gitBranch = execSync('git rev-parse --abbrev-ref HEAD', GIT_EXEC_OPTIONS).trim();
        const status = execSync('git status --porcelain', GIT_EXEC_OPTIONS).trim();
        return { gitBranch, gitStatus: status ? 'dirty' : 'clean' };
    } catch (e) {
        try {
            execSync('git rev-parse --git-dir', GIT_EXEC_OPTIONS);
            return { gitBranch: 'no-commits', gitStatus: 'unknown' };
        } catch (_) {
            return { gitBranch: 'not-a-repo', gitStatus: 'unknown' };
        }
    }
}


/**
 * Self-heal: patch hook commands in settings.json to use absolute node binary
 * path and absolute hook file paths. Fixes two failure modes:
 *   1. Relative paths  → MODULE_NOT_FOUND when Claude opens from a subdirectory
 *   2. Bare "node" cmd → nvm shell function recursive loop (FUNCNEST) on zsh
 * @param {string} projectRoot - Absolute path to project root
 */
function fixHookPaths(projectRoot) {
    const settingsPath = path.join(projectRoot, '.claude', 'settings.json');
    if (!fs.existsSync(settingsPath)) return;
    try {
        const content = fs.readFileSync(settingsPath, 'utf8');
        // Quick check: only process if there are hook commands that might need fixing.
        // Already-fixed commands start with the absolute node binary path (e.g. "/usr/bin/node")
        // so they won't contain the literal string '"node '.
        if (!content.includes('"node ') || !content.includes('.claude/hooks/')) return;
        const nodeExec = process.execPath;
        const fixed = content.replace(
            /"node\s+(?:[^\s"]*?)\.claude\/hooks\//g,
            '"' + nodeExec + ' ' + projectRoot + '/.claude/hooks/'
        );
        if (fixed === content) return;
        fs.writeFileSync(settingsPath, fixed, 'utf8');
        logMessage('Self-healed: patched hook commands to use absolute node binary and paths in .claude/settings.json');
    } catch (e) {
        logMessage('fixHookPaths: ' + e.message, 'WARNING');
    }
}

function main() {
    ensureStateDir();
    const { gitBranch, gitStatus } = getGitInfo();
    const sessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 2 + SESSION_ID_SUFFIX_LEN)}`;
    const profile = detectProfile();
    const projectRoot = getProjectRoot();

    fixHookPaths(projectRoot);

    const sessionInfo = {
        id: sessionId, timestamp: new Date().toISOString(),
        cwd: process.cwd(), project_root: projectRoot,
        gitBranch, gitStatus, profile,
        platform: process.platform, nodeVersion: process.version
    };

    saveState('session_start.json', sessionInfo);
    logMessage(`SessionStart id=${sessionId} branch=${gitBranch} profile=${profile}`);
    console.log(JSON.stringify({
        continue: true,
        context: { sessionId, profile, gitBranch, gitStatus }
    }));
}

main();
