#!/usr/bin/env node
/**
 * SubagentStop Hook - Synthesize subagent results
 *
 * Triggered when a subagent completes.
 * Synthesizes results and updates cost tracking.
 */

const { parseHookInput, loadState, saveState, appendCapped, logMessage, MAX_RESULT_LENGTH, MAX_AGENT_HISTORY, MS_PER_SECOND } = require('./utils.cjs');

/**
 * Calculate agent duration in seconds, guarding against invalid startTime.
 * @param {string} startTimeStr - ISO timestamp string
 * @param {Date} endTime - End time
 * @returns {number} Duration in seconds (0 if startTime is invalid)
 */
function calculateDurationSec(startTimeStr, endTime) {
    const startTime = new Date(startTimeStr);
    const durationMs = isNaN(startTime.getTime()) ? 0 : (endTime - startTime);
    return Math.round(durationMs / MS_PER_SECOND);
}

/**
 * Create a history entry for a completed agent.
 * @param {Object} agentInfo - Agent metadata from active_agents.json
 * @param {Object} completion - Completion details
 * @param {Date} completion.endTime - Completion timestamp
 * @param {number} completion.durationSec - Duration in seconds
 * @param {boolean} completion.success - Whether the agent succeeded
 * @param {string} completion.resultSummary - Summary of results (truncated)
 * @returns {Object} History entry
 */
function createHistoryEntry(agentInfo, { endTime, durationSec, success, resultSummary }) {
    return {
        ...agentInfo,
        endTime: endTime.toISOString(),
        durationSeconds: durationSec,
        success,
        resultSummary: resultSummary.substring(0, MAX_RESULT_LENGTH)
    };
}

function main() {
    const parsed = parseHookInput();
    const agentId = parsed.agent_id || parsed.task_id || '';
    const success = parsed.success !== false;
    const resultSummary = parsed.result_summary || parsed.output?.substring(0, MAX_RESULT_LENGTH) || '';

    const activeAgents = loadState('active_agents.json', {});
    const agentInfo = activeAgents[agentId] || {
        id: agentId, type: 'unknown', startTime: new Date().toISOString()
    };

    const endTime = new Date();
    const durationSec = calculateDurationSec(agentInfo.startTime, endTime);

    appendCapped('agent_history.json',
        createHistoryEntry(agentInfo, { endTime, durationSec, success, resultSummary }),
        MAX_AGENT_HISTORY);

    if (activeAgents[agentId]) {
        delete activeAgents[agentId];
        saveState('active_agents.json', activeAgents);
    }

    const status = success ? 'completed' : 'failed';
    logMessage(`SubagentStop id=${agentId} status=${status} duration=${durationSec}s`);

    console.log(JSON.stringify({
        agentId, type: agentInfo.type, success,
        durationSeconds: durationSec,
        remainingAgents: Object.keys(activeAgents).length
    }));
}

main();
