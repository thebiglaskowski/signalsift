#!/usr/bin/env node
/**
 * TaskCompleted Hook — Quality gate enforcement for Agent Teams
 *
 * Runs when a task is being marked as complete. Validates that the
 * task deliverables meet quality standards before allowing completion.
 *
 * Exit codes:
 *   0 — Allow task completion (quality OK)
 *   2 — Reject completion, send feedback (quality issues found)
 *
 * Hook input (via HOOK_INPUT env var or stdin):
 * {
 *   "task_id": "...",
 *   "task_subject": "...",
 *   "teammate_name": "frontend",
 *   "files_changed": ["src/components/Button.tsx", ...],
 *   "session_id": "..."
 * }
 */

const { parseHookInput, loadState, saveState, logMessage, MAX_FILES_PER_TASK, MAX_COMPLETED_TASKS, MAX_FILE_OWNERSHIP, TEAM_STATE_DEFAULT } = require('./utils.cjs');

/**
 * Check whether the number of changed files exceeds the per-task maximum.
 * @param {string[]} filesChanged - List of file paths changed by the task
 * @returns {string|null} Warning message if limit exceeded, null otherwise
 */
function checkFileCount(filesChanged) {
    if (filesChanged.length > MAX_FILES_PER_TASK) {
        return `Task modified ${filesChanged.length} files (max ${MAX_FILES_PER_TASK}). ` +
            `This may indicate scope creep. Review changes and split if needed.`;
    }
    return null;
}

/**
 * Detect file ownership conflicts where another teammate already owns a modified file.
 * @param {string[]} filesChanged - Files changed by this task
 * @param {Object} fileOwnership - Map of file path to owning teammate name
 * @param {string} teammateName - Name of the teammate completing the task
 * @returns {string[]} Array of conflict warning messages (empty if none)
 */
function checkOwnershipConflicts(filesChanged, fileOwnership, teammateName) {
    const conflicts = [];
    for (const file of filesChanged) {
        const owner = fileOwnership[file];
        if (owner && owner !== teammateName) {
            conflicts.push(
                `File conflict: ${file} is owned by teammate "${owner}" ` +
                `but was modified by "${teammateName}". ` +
                `Coordinate with ${owner} to avoid overwrites.`
            );
        }
    }
    return conflicts;
}

/**
 * Trim completed_tasks and file_ownership collections to their configured caps.
 * @param {Object} teamState - Mutable team state object to prune in place
 */
function pruneTeamState(teamState) {
    if (teamState.completed_tasks.length > MAX_COMPLETED_TASKS) {
        teamState.completed_tasks = teamState.completed_tasks.slice(-MAX_COMPLETED_TASKS);
    }

    const ownershipKeys = Object.keys(teamState.file_ownership);
    if (ownershipKeys.length > MAX_FILE_OWNERSHIP) {
        const toRemove = ownershipKeys.slice(0, ownershipKeys.length - MAX_FILE_OWNERSHIP);
        for (const key of toRemove) {
            delete teamState.file_ownership[key];
        }
    }
}

/**
 * Record the current teammate as the owner of each changed file.
 * @param {Object} teamState - Mutable team state object
 * @param {string[]} filesChanged - Files to assign ownership for
 * @param {string} teammateName - Teammate taking ownership
 */
function updateFileOwnership(teamState, filesChanged, teammateName) {
    for (const file of filesChanged) {
        teamState.file_ownership[file] = teammateName;
    }
}

/**
 * Append a task completion record to the team state history.
 * @param {Object} teamState - Mutable team state object
 * @param {Object} record - Task completion record fields
 * @param {string} record.taskId - Unique task identifier
 * @param {string} record.taskSubject - Human-readable task title
 * @param {string} record.teammateName - Teammate who completed the task
 * @param {string[]} record.filesChanged - Files modified during the task
 * @param {boolean} record.hadIssues - Whether quality issues were found
 */
function recordTaskCompletion(teamState, { taskId, taskSubject, teammateName, filesChanged, hadIssues }) {
    if (!teamState.completed_tasks) {
        teamState.completed_tasks = [];
    }
    teamState.completed_tasks.push({
        task_id: taskId,
        subject: taskSubject,
        teammate: teammateName,
        files: filesChanged,
        timestamp: new Date().toISOString(),
        had_issues: hadIssues
    });
}

function main() {
    const input = parseHookInput();
    const taskId = input.task_id || 'unknown';
    const taskSubject = input.task_subject || '';
    const teammateName = input.teammate_name || 'unknown';
    const filesChanged = input.files_changed || [];

    const teamState = loadState('team-state.json', TEAM_STATE_DEFAULT);

    // Ensure required fields exist (state may have been created before v1.3.5)
    if (!teamState.completed_tasks) teamState.completed_tasks = [];
    if (!teamState.file_ownership) teamState.file_ownership = {};

    const issues = [];

    const fileCountIssue = checkFileCount(filesChanged);
    if (fileCountIssue) issues.push(fileCountIssue);

    const conflicts = checkOwnershipConflicts(filesChanged, teamState.file_ownership, teammateName);
    issues.push(...conflicts);

    updateFileOwnership(teamState, filesChanged, teammateName);
    recordTaskCompletion(teamState, { taskId, taskSubject, teammateName, filesChanged, hadIssues: issues.length > 0 });
    pruneTeamState(teamState);
    saveState('team-state.json', teamState);

    if (issues.length > 0) {
        const feedback = `Quality issues found before completing task "${taskSubject}":\n` +
            issues.map((issue, i) => `${i + 1}. ${issue}`).join('\n') +
            `\n\nPlease address these issues before marking the task complete.`;

        logMessage(`TaskCompleted: ${taskId} rejected — ${issues.length} issues`, 'WARNING');
        console.error(JSON.stringify({ feedback }));
        process.exit(2);
    }

    logMessage(`TaskCompleted: ${taskId} by ${teammateName} (${filesChanged.length} files)`, 'INFO');
    process.exit(0);
}

main();
