#!/usr/bin/env node
/**
 * SubagentStart Hook - Track subagent spawning
 *
 * Triggered when a subagent (Task tool) is started.
 * Tracks agent metadata for synthesis and cost allocation.
 */

const fs = require('fs');
const path = require('path');
const { parseHookInput, loadState, saveState, logMessage, MAX_ACTIVE_AGENTS } = require('./utils.cjs');

// Known specialized roles — skip YAML scan when agentType matches a specific role name.
// 'general-purpose' is intentionally excluded: when agentType is 'general-purpose',
// YAML scanning must still run so description-based role detection works.
const KNOWN_ROLES = ['implementer', 'reviewer', 'researcher', 'tester', 'architect'];

/**
 * Parse list sections from a YAML file content string.
 * @param {string} content - Raw YAML file content
 * @param {string[]} sectionNames - Section keys to extract as list values
 * @returns {Object} Map of sectionName -> string[] values
 */
function parseYamlListSections(content, sectionNames) {
    const result = {};
    for (const name of sectionNames) result[name] = [];
    let currentSection = null;

    for (const line of content.split('\n')) {
        if (/^[a-z]/.test(line)) {
            currentSection = sectionNames.find(s => line.startsWith(s + ':')) || null;
            continue;
        }
        if (!currentSection) continue;
        const match = line.match(/^\s+-\s+(.+)/);
        if (match) result[currentSection].push(match[1].trim());
    }
    return result;
}

/**
 * Create an agent tracking entry.
 * @param {string} agentId - Unique agent identifier
 * @param {Object} opts - Agent metadata
 * @param {string} opts.type - Agent subtype
 * @param {string} opts.description - Agent task description
 * @param {string} opts.model - Model being used
 * @param {boolean} opts.runInBackground - Whether agent runs in background
 * @returns {Object} Agent tracking entry
 */
function buildAgentEntry(agentId, { type, description, model, runInBackground }) {
    return {
        id: agentId, type, description, model,
        runInBackground, startTime: new Date().toISOString(), status: 'running'
    };
}

/**
 * Detect agent role by matching against YAML definitions in agents/.
 * @param {string} agentType - Agent subtype
 * @param {string} description - Agent task description
 * @returns {{agentRole: string|null, rulesLoaded: string[], expertise: string[]}}
 */
function detectAgentRole(agentType, description) {
    if (KNOWN_ROLES.includes(agentType)) {
        return { agentRole: agentType, rulesLoaded: [], expertise: [] };
    }
    try {
        const agentsDir = path.resolve(__dirname, '..', '..', 'agents');
        if (!fs.existsSync(agentsDir)) return { agentRole: null, rulesLoaded: [], expertise: [] };

        const agentFiles = fs.readdirSync(agentsDir).filter(f => f.endsWith('.yaml'));
        const searchText = (description + ' ' + agentType).toLowerCase();
        for (const file of agentFiles) {
            const roleName = file.replace('.yaml', '');
            if (!searchText.includes(roleName)) continue;
            const content = fs.readFileSync(path.join(agentsDir, file), 'utf8');
            const sections = parseYamlListSections(content, ['rules_to_load', 'expertise']);
            return { agentRole: roleName, rulesLoaded: sections.rules_to_load, expertise: sections.expertise };
        }
    } catch (e) {
        logMessage(`agent-tracker: error: ${e.message}`, 'DEBUG');
    }
    return { agentRole: null, rulesLoaded: [], expertise: [] };
}

/**
 * Prune oldest agents if the map exceeds the cap.
 * @param {Object} activeAgents - Map of agent ID to agent data
 */
function pruneAgents(activeAgents) {
    const agentKeys = Object.keys(activeAgents);
    if (agentKeys.length <= MAX_ACTIVE_AGENTS) return;
    const sorted = agentKeys.sort((a, b) => {
        const ta = activeAgents[a].startTime || '';
        const tb = activeAgents[b].startTime || '';
        return ta.localeCompare(tb);
    });
    for (let i = 0; i < sorted.length - MAX_ACTIVE_AGENTS; i++) {
        delete activeAgents[sorted[i]];
    }
}

function main() {
    const parsed = parseHookInput();
    const agentId = parsed.agent_id || parsed.task_id || `agent-${Date.now()}`;
    const agentType = parsed.tool_input?.subagent_type || 'general-purpose';
    const description = parsed.tool_input?.description || '';
    const model = parsed.tool_input?.model || 'sonnet';

    const activeAgents = loadState('active_agents.json', {});
    activeAgents[agentId] = buildAgentEntry(agentId, {
        type: agentType, description, model,
        runInBackground: parsed.tool_input?.run_in_background || false
    });

    const { agentRole, rulesLoaded, expertise } = detectAgentRole(agentType, description);
    if (agentRole) {
        Object.assign(activeAgents[agentId], { agentRole, rulesLoaded, expertise });
    }

    pruneAgents(activeAgents);
    saveState('active_agents.json', activeAgents);

    logMessage(`SubagentStart id=${agentId} type=${agentType} model=${model}${agentRole ? ` role=${agentRole}` : ''}`);

    const output = { tracked: true, agentId, agentType, model, activeCount: Object.keys(activeAgents).length };
    if (agentRole) Object.assign(output, { agentRole, rulesLoaded, expertise });
    console.log(JSON.stringify(output));
}

main();
