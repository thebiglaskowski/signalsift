#!/usr/bin/env node
/**
 * SessionEnd Hook - Archive session and update STATUS.md
 *
 * Triggered when a Claude Code session ends.
 * Archives session state and optionally updates STATUS.md.
 */

const fs = require('fs');
const path = require('path');
const { loadState, saveJsonFile, logMessage, getStateFilePath, getProjectRoot, MAX_ARCHIVES, pruneDirectory, MS_PER_MINUTE } = require('./utils.cjs');

/**
 * Calculate session duration in minutes.
 * @param {Object} sessionInfo - Session start info with .timestamp
 * @returns {{endTime: Date, durationMin: number}}
 */
function calculateSessionDuration(sessionInfo) {
    const startTime = sessionInfo.timestamp ? new Date(sessionInfo.timestamp) : new Date();
    const endTime = new Date();
    return { endTime, durationMin: Math.round((endTime - startTime) / MS_PER_MINUTE) };
}

/**
 * Create session archive object from session info and changes.
 * @param {Object} sessionInfo - Session start info
 * @param {Date} endTime - Session end timestamp
 * @param {number} durationMin - Duration in minutes
 * @param {Array} fileChanges - Tracked file changes
 * @returns {Object} Archive record
 */
function createSessionArchive(sessionInfo, endTime, durationMin, fileChanges) {
    return {
        ...sessionInfo, endTimestamp: endTime.toISOString(),
        durationMinutes: durationMin, filesChanged: fileChanges.length, filesList: fileChanges
    };
}

/**
 * Remove transient session state files.
 */
function cleanupSessionFiles() {
    for (const file of ['session_start.json', 'file_changes.json']) {
        const p = getStateFilePath(file);
        if (fs.existsSync(p)) fs.unlinkSync(p);
    }
}

function main() {
    const stateDir = path.join(getProjectRoot(), '.claude', 'state');
    const archiveDir = path.join(stateDir, 'archive');
    if (!fs.existsSync(archiveDir)) fs.mkdirSync(archiveDir, { recursive: true });

    const sessionInfo = loadState('session_start.json', { id: 'unknown', timestamp: new Date().toISOString() });
    const fileChanges = loadState('file_changes.json', []);
    const { endTime, durationMin } = calculateSessionDuration(sessionInfo);

    const archiveFile = path.join(archiveDir, `${sessionInfo.id || 'session'}.json`);
    saveJsonFile(archiveFile, createSessionArchive(sessionInfo, endTime, durationMin, fileChanges));
    pruneDirectory(archiveDir, MAX_ARCHIVES);
    cleanupSessionFiles();

    logMessage(`SessionEnd id=${sessionInfo.id || 'unknown'} duration=${durationMin}min files=${fileChanges.length}`);
    console.log(JSON.stringify({
        sessionId: sessionInfo.id, duration: `${durationMin} minutes`,
        filesChanged: fileChanges.length, archived: archiveFile
    }));
}

main();
