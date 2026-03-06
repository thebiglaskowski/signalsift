#!/usr/bin/env node
/**
 * Stop Hook - Definition of Done verification
 *
 * Triggered when Claude stops (task completion).
 * Verifies that quality gates passed and DoD is met.
 */

const path = require('path');
const { execSync } = require('child_process');
const { loadState, saveState, logMessage, GIT_EXEC_OPTIONS } = require('./utils.cjs');

// Extension-to-language mapping for change categorization
const EXT_TO_LANG = {
    '.py': 'python', '.ts': 'typescript', '.tsx': 'typescript',
    '.js': 'javascript', '.jsx': 'javascript', '.go': 'go'
};

// Languages that require quality gates before sign-off
const CODE_LANGS = ['python', 'typescript', 'javascript', 'go'];

/**
 * Check whether quality gates ran for code files modified this session.
 * Implements the Evaluator stage from context engineering literature:
 * validates that the model's output claims (gates passing) have evidence.
 * @param {Object} changesByType - Changes categorized by language
 * @returns {Object} Integrity check results
 */
function buildIntegrityChecks(changesByType) {
    const gateHistory = loadState('gate_history.json', { entries: [] });
    const entries = Array.isArray(gateHistory.entries) ? gateHistory.entries : [];
    const gatesRan = entries.length > 0;
    const lastGate = entries[entries.length - 1] || null;
    const lastGatePassed = lastGate ? lastGate.passed : null;
    const codeFilesModified = CODE_LANGS.some(lang => (changesByType[lang] || []).length > 0);
    const codeModifiedWithoutGates = codeFilesModified && !gatesRan;
    return { gatesRan, lastGatePassed, codeFilesModified, codeModifiedWithoutGates };
}

/**
 * Categorize file changes by language.
 * @param {Array} fileChanges - Array of change entries with .path
 * @returns {Object} Map of language to array of file paths
 */
function categorizeChanges(fileChanges) {
    const byType = { python: [], typescript: [], javascript: [], go: [], other: [] };
    for (const change of fileChanges) {
        const ext = path.extname(change.path || '').toLowerCase();
        const lang = EXT_TO_LANG[ext] || 'other';
        byType[lang].push(change.path);
    }
    return byType;
}

/**
 * Get git working tree state.
 * @returns {{gitClean: boolean, uncommittedChanges: number}}
 */
function getGitState() {
    try {
        const status = execSync('git status --porcelain', GIT_EXEC_OPTIONS).trim();
        return { gitClean: !status, uncommittedChanges: status ? status.split('\n').length : 0 };
    } catch (e) {
        return { gitClean: false, uncommittedChanges: 0 };
    }
}

/**
 * Build recommendations based on session state.
 * @param {boolean} gitClean - Whether git working tree is clean
 * @param {Array} fileChanges - Array of tracked file changes
 * @param {Object} changesByType - Changes categorized by language
 * @returns {string[]} Array of recommendation strings
 */
function buildRecommendations(gitClean, fileChanges, changesByType) {
    const recs = [];
    if (!gitClean && fileChanges.length > 0) recs.push('Consider committing changes before ending session');
    if (changesByType.python.length > 0) recs.push('Run ruff check and pytest before finalizing');
    if (changesByType.typescript.length > 0 || changesByType.javascript.length > 0) {
        recs.push('Run eslint and tests before finalizing');
    }
    return recs;
}

/**
 * Summarize which rule topics were detected during this session.
 * Surfaces retrieval frequency to diagnose memory-loading effectiveness.
 * Research finding: retrieval failure (11-46%) dominates over utilization failure (4-8%).
 * Raw topic counts show which domains were active vs. which rules may have been missed.
 * @returns {Object} Memory retrieval summary
 */
function buildMemoryEffectiveness() {
    const prompts = loadState('prompts.json', []);
    const entries = Array.isArray(prompts) ? prompts : [];
    const topicCounts = {};
    for (const entry of entries) {
        for (const topic of (entry.topics || [])) {
            topicCounts[topic] = (topicCounts[topic] || 0) + 1;
        }
    }
    const totalPrompts = entries.length;
    const noTopicPrompts = entries.filter(p => !p.topics || p.topics.length === 0).length;
    return {
        totalPrompts,
        topicsDetected: Object.keys(topicCounts).length,
        topicCounts,
        noTopicPrompts
    };
}

function main() {
    logMessage('DoD verification started');

    const fileChanges = loadState('file_changes.json', []);
    const changesByType = categorizeChanges(fileChanges);
    const { gitClean, uncommittedChanges } = getGitState();

    const verification = {
        timestamp: new Date().toISOString(),
        filesModified: fileChanges.length,
        changesByType: Object.fromEntries(
            Object.entries(changesByType).map(([k, v]) => [k, v.length])
        ),
        git: { clean: gitClean, uncommittedChanges },
        recommendations: buildRecommendations(gitClean, fileChanges, changesByType),
        integrityChecks: buildIntegrityChecks(changesByType),
        memoryEffectiveness: buildMemoryEffectiveness()
    };

    saveState('last_verification.json', verification);
    console.log(JSON.stringify(verification));

    if (!gitClean && fileChanges.length > 0) process.exit(2);
}

main();
