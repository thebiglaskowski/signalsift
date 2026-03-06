#!/usr/bin/env node
/**
 * ConfigChange Hook
 *
 * Observe-only hook that logs settings.json changes to config_changes.json.
 * If the change touches the hooks section, outputs a context note so Claude
 * is aware that hook configuration was modified.
 *
 * Runs async (fire-and-forget) — result not needed synchronously.
 */

const { parseHookInput, appendCapped, logMessage } = require('./utils.cjs');

const MAX_CONFIG_CHANGES = 20;

function main() {
    const parsed = parseHookInput();
    const changedFile = parsed.tool_input?.file || parsed.tool_input?.path || '';
    const changeType = parsed.tool_input?.change_type || '';

    const entry = {
        timestamp: new Date().toISOString(),
        file: changedFile,
        changeType
    };

    appendCapped('config_changes.json', entry, MAX_CONFIG_CHANGES, []);

    const hooksModified = changedFile.includes('settings.json') && changeType === 'hooks';
    if (hooksModified) {
        console.log(JSON.stringify({
            context: 'Hook configuration was modified. If hooks behave unexpectedly, verify settings.json and restart the session.'
        }));
        logMessage(`ConfigChange: hooks section modified in ${changedFile}`, 'INFO');
    }
}

main();
