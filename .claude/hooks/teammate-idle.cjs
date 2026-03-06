#!/usr/bin/env node
/**
 * TeammateIdle Hook — Quality gate enforcement for Agent Teams
 *
 * Runs when a teammate is about to go idle. Checks if the teammate's
 * work passes basic quality checks before allowing them to stop.
 *
 * Exit codes:
 *   0 — Allow teammate to go idle (quality OK or no checks applicable)
 *   2 — Send feedback to teammate (quality issues found, keep working)
 *
 * Hook input (via HOOK_INPUT env var or stdin):
 * {
 *   "teammate_name": "frontend",
 *   "session_id": "...",
 *   "tasks_completed": [...],
 *   "working_directory": "/path/to/project"
 * }
 */

const { parseHookInput, loadState, saveState, logMessage, MAX_TEAMMATES, TEAM_STATE_DEFAULT } = require('./utils.cjs');

/**
 * Record a teammate idle event and update task completion in team state.
 * Prunes oldest entries when the teammates map exceeds MAX_TEAMMATES.
 * @param {Object} teamState - Mutable team state object
 * @param {string} teammateName - Name of the teammate going idle
 * @param {Array|undefined} tasksCompleted - Latest tasks_completed list from hook input
 * @returns {Object} Updated team state
 */
function recordIdleEvent(teamState, teammateName, tasksCompleted) {
    if (!teamState.teammates) {
        teamState.teammates = {};
    }
    if (!teamState.teammates[teammateName]) {
        teamState.teammates[teammateName] = {
            idle_count: 0,
            tasks_completed: [],
            last_idle: null
        };
    }

    teamState.teammates[teammateName].idle_count += 1;
    teamState.teammates[teammateName].last_idle = new Date().toISOString();

    if (tasksCompleted) {
        teamState.teammates[teammateName].tasks_completed = tasksCompleted;
    }

    // Prune oldest teammates if exceeding cap
    const teammateKeys = Object.keys(teamState.teammates);
    if (teammateKeys.length > MAX_TEAMMATES) {
        const toRemove = teammateKeys.slice(0, teammateKeys.length - MAX_TEAMMATES);
        for (const key of toRemove) {
            delete teamState.teammates[key];
        }
    }

    return teamState;
}

function main() {
    const input = parseHookInput();
    const teammateName = input.teammate_name || 'unknown';

    const teamState = loadState('team-state.json', TEAM_STATE_DEFAULT);

    recordIdleEvent(teamState, teammateName, input.tasks_completed);

    const completedTasks = teamState.teammates[teammateName].tasks_completed || [];

    if (completedTasks.length === 0 && teamState.teammates[teammateName].idle_count === 1) {
        // First idle with no tasks completed — nudge teammate
        const feedback = `You haven't completed any tasks yet. Check the shared task list for available work. If you're blocked, message the lead with details about what's preventing progress.`;

        logMessage(`TeammateIdle: ${teammateName} idle with 0 tasks, sending feedback`, 'WARNING');
        saveState('team-state.json', teamState);

        // Exit code 2 sends feedback to the teammate
        console.error(JSON.stringify({ feedback }));
        process.exit(2);
    }

    // Log and allow idle
    logMessage(`TeammateIdle: ${teammateName} going idle (${completedTasks.length} tasks completed)`, 'INFO');
    saveState('team-state.json', teamState);

    // Exit 0 — allow teammate to go idle
    process.exit(0);
}

main();
