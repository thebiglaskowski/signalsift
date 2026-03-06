#!/usr/bin/env node
/**
 * Hook for WorktreeCreate and WorktreeRemove events
 *
 * WorktreeCreate: writes worktree-context.json into the new worktree's
 *   .claude/state/ so agents opened there know their parent session.
 * WorktreeRemove: logs the removal to the parent session archive.
 *
 * Runs async (fire-and-forget) — result not needed synchronously.
 */

const fs = require('fs');
const path = require('path');
const { parseHookInput, loadState, saveState, logMessage, getProjectRoot } = require('./utils.cjs');

function main() {
    const parsed = parseHookInput();
    const eventName = parsed.hook_event_name || parsed.event || '';
    const worktreePath = parsed.tool_input?.path || parsed.tool_input?.worktree_path || '';

    if (!worktreePath) {
        process.exit(0);
    }

    if (eventName === 'WorktreeCreate') {
        handleWorktreeCreate(worktreePath, parsed);
    } else if (eventName === 'WorktreeRemove') {
        handleWorktreeRemove(worktreePath);
    }
}

function handleWorktreeCreate(worktreePath, parsed) {
    // Read parent session info
    const sessionState = loadState('session_start.json', {});
    const parentSessionId = sessionState.session_id || null;
    const profile = sessionState.profile || null;

    // Ensure .claude/state/ exists in the worktree
    const stateDir = path.join(worktreePath, '.claude', 'state');
    try {
        fs.mkdirSync(stateDir, { recursive: true });
    } catch (_) {
        process.exit(0);
    }

    // Write worktree context
    const context = {
        worktreePath,
        parentSessionId,
        parentProjectRoot: getProjectRoot(),
        profile,
        createdAt: new Date().toISOString()
    };
    try {
        fs.writeFileSync(path.join(stateDir, 'worktree-context.json'), JSON.stringify(context, null, 2), 'utf8');
    } catch (_) {}

    logMessage(`WorktreeCreate: initialized context at ${worktreePath}`, 'INFO');
}

function handleWorktreeRemove(worktreePath) {
    // Load the worktree's own context to get creation time
    const contextFile = path.join(worktreePath, '.claude', 'state', 'worktree-context.json');
    let createdAt = null;
    try {
        const ctx = JSON.parse(fs.readFileSync(contextFile, 'utf8'));
        createdAt = ctx.createdAt || null;
    } catch (_) {}

    const removedAt = new Date().toISOString();
    const durationMs = createdAt ? (new Date(removedAt) - new Date(createdAt)) : null;

    // Append removal record to parent session archive entry
    const sessionState = loadState('session_start.json', {});
    const sessionId = sessionState.session_id || 'unknown';
    const archiveDir = path.join(getProjectRoot(), '.claude', 'state', 'archive');

    try {
        const archiveFile = path.join(archiveDir, `${sessionId}.json`);
        let archive = {};
        if (fs.existsSync(archiveFile)) {
            archive = JSON.parse(fs.readFileSync(archiveFile, 'utf8'));
        }
        if (!archive.worktrees) archive.worktrees = [];
        archive.worktrees.push({ worktreePath, removedAt, durationMs });
        fs.writeFileSync(archiveFile, JSON.stringify(archive, null, 2), 'utf8');
    } catch (_) {}

    logMessage(`WorktreeRemove: ${worktreePath} (duration: ${durationMs ? Math.round(durationMs / 1000) + 's' : 'unknown'})`, 'INFO');
}

main();
