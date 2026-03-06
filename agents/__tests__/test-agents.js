#!/usr/bin/env node
/**
 * Agent definition validation test
 *
 * Validates all agents/*.yaml files against schema requirements.
 * Uses simple line-based YAML parsing — no dependencies.
 *
 * Run: node agents/__tests__/test-agents.js
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const agentsDir = path.resolve(__dirname, '..');
const rulesDir = path.resolve(__dirname, '..', '..', 'rules');

const { test, suite, summary, getResults } = require('../../test-utils');

/**
 * Minimal YAML top-level key extractor.
 * Returns an object with top-level keys and their raw values.
 */
function parseTopLevelKeys(content) {
    const result = {};
    const lines = content.split('\n');
    for (const line of lines) {
        if (line.startsWith('#') || line.trim() === '') continue;
        const match = line.match(/^([a-z_][a-z0-9_]*)\s*:\s*(.*)/);
        if (match) {
            let value = match[2].trim();
            if ((value.startsWith('"') && value.endsWith('"')) ||
                (value.startsWith("'") && value.endsWith("'"))) {
                value = value.slice(1, -1);
            }
            result[match[1]] = value;
        }
    }
    return result;
}

/**
 * Extract array items from a YAML section (lines starting with "  - ").
 */
function extractArrayItems(content, sectionName) {
    const lines = content.split('\n');
    let capturing = false;
    const items = [];
    for (const line of lines) {
        const topKeyMatch = line.match(/^([a-z_][a-z0-9_]*)\s*:/);
        if (topKeyMatch) {
            if (capturing) break;
            if (topKeyMatch[1] === sectionName) {
                capturing = true;
                continue;
            }
        }
        if (capturing) {
            const itemMatch = line.match(/^\s+-\s+(.+)/);
            if (itemMatch) {
                let val = itemMatch[1].trim();
                if ((val.startsWith('"') && val.endsWith('"')) ||
                    (val.startsWith("'") && val.endsWith("'"))) {
                    val = val.slice(1, -1);
                }
                items.push(val);
            }
        }
    }
    return items;
}

/**
 * Extract a multiline scalar (block scalar) from YAML.
 * Handles the | (literal block) indicator.
 */
function extractBlockScalar(content, sectionName) {
    const lines = content.split('\n');
    let capturing = false;
    let text = [];
    for (const line of lines) {
        const topKeyMatch = line.match(/^([a-z_][a-z0-9_]*)\s*:/);
        if (topKeyMatch) {
            if (capturing) break;
            if (topKeyMatch[1] === sectionName) {
                capturing = true;
                continue;
            }
        }
        if (capturing) {
            // Stop if we hit another top-level key
            if (/^[a-z_]/.test(line)) break;
            text.push(line);
        }
    }
    return text.join('\n').trim();
}

const validRoles = ['implementer', 'reviewer', 'researcher', 'tester', 'architect'];

// Discover all agent files
const agentFiles = fs.readdirSync(agentsDir)
    .filter(f => f.endsWith('.yaml'))
    .sort();

// ─────────────────────────────────────────────────────────────
// Discovery validations
// ─────────────────────────────────────────────────────────────
suite('Agent discovery', () => {
    test('found at least 5 agent files', () => {
        assert.ok(agentFiles.length >= 5,
            `Expected at least 5 agents, found ${agentFiles.length}: ${agentFiles.join(', ')}`);
    });

    test('expected agents exist', () => {
        const expected = ['security.yaml', 'backend.yaml', 'frontend.yaml', 'tester.yaml', 'architect.yaml'];
        for (const name of expected) {
            assert.ok(agentFiles.includes(name), `Missing agent: ${name}`);
        }
    });

    test('schema file exists', () => {
        const schemaPath = path.resolve(__dirname, '..', '..', 'schemas', 'agent.schema.json');
        assert.ok(fs.existsSync(schemaPath),
            'schemas/agent.schema.json not found');
    });

    test('CLAUDE.md exists', () => {
        assert.ok(fs.existsSync(path.join(agentsDir, 'CLAUDE.md')),
            'agents/CLAUDE.md not found');
    });
});

// ─────────────────────────────────────────────────────────────
// Per-agent validations
// ─────────────────────────────────────────────────────────────
for (const file of agentFiles) {
    const agentPath = path.join(agentsDir, file);
    const content = fs.readFileSync(agentPath, 'utf8');
    const keys = parseTopLevelKeys(content);
    const agentName = file.replace('.yaml', '');

    suite(`${file} — required fields`, () => {
        test('has name field', () => {
            assert.ok(keys.name, 'missing name field');
        });

        test('name matches filename', () => {
            assert.strictEqual(keys.name, agentName,
                `name "${keys.name}" doesn't match filename "${agentName}"`);
        });

        test('has description field', () => {
            assert.ok(keys.description, 'missing description field');
            assert.ok(keys.description.length >= 10,
                `description too short: "${keys.description}"`);
        });

        test('has version field', () => {
            assert.ok(keys.version, 'missing version field');
        });

        test('has role field', () => {
            assert.ok(keys.role, 'missing role field');
        });

        test('role is valid', () => {
            assert.ok(validRoles.includes(keys.role),
                `invalid role "${keys.role}", expected one of: ${validRoles.join(', ')}`);
        });

        test('has expertise section', () => {
            assert.ok(content.includes('expertise:'), 'missing expertise section');
        });

        test('has spawn_prompt section', () => {
            assert.ok(content.includes('spawn_prompt:'), 'missing spawn_prompt section');
        });

        test('has quality_gates section', () => {
            assert.ok(content.includes('quality_gates:'), 'missing quality_gates section');
        });
    });

    suite(`${file} — expertise`, () => {
        const expertiseItems = extractArrayItems(content, 'expertise');

        test('has at least 3 expertise items', () => {
            assert.ok(expertiseItems.length >= 3,
                `expected at least 3 expertise items, found ${expertiseItems.length}`);
        });

        test('expertise items are non-empty strings', () => {
            for (const item of expertiseItems) {
                assert.ok(item.length > 0, 'expertise item is empty');
            }
        });
    });

    suite(`${file} — spawn_prompt`, () => {
        const spawnPrompt = extractBlockScalar(content, 'spawn_prompt');

        test('spawn_prompt is at least 50 chars', () => {
            assert.ok(spawnPrompt.length >= 50,
                `spawn_prompt too short (${spawnPrompt.length} chars), minimum 50`);
        });
    });

    suite(`${file} — quality_gates`, () => {
        const gates = extractArrayItems(content, 'quality_gates');

        test('has at least 1 quality gate', () => {
            assert.ok(gates.length >= 1,
                `expected at least 1 quality gate, found ${gates.length}`);
        });

        test('quality gates are valid', () => {
            const validGates = ['lint', 'test', 'build'];
            for (const gate of gates) {
                assert.ok(validGates.includes(gate),
                    `invalid quality gate "${gate}", expected one of: ${validGates.join(', ')}`);
            }
        });
    });

    suite(`${file} — rules_to_load`, () => {
        const rules = extractArrayItems(content, 'rules_to_load');

        if (rules.length > 0) {
            test('rules_to_load references exist in rules/ directory', () => {
                for (const rule of rules) {
                    const rulePath = path.join(rulesDir, `${rule}.md`);
                    assert.ok(fs.existsSync(rulePath),
                        `rules_to_load references "${rule}" but rules/${rule}.md not found`);
                }
            });
        }
    });

    suite(`${file} — file_scope_hints`, () => {
        const hints = extractArrayItems(content, 'file_scope_hints');

        if (hints.length > 0) {
            test('file_scope_hints are present and non-empty', () => {
                assert.ok(hints.length > 0, 'file_scope_hints is empty');
                for (const hint of hints) {
                    assert.ok(hint.length > 0, 'file_scope_hint item is empty');
                }
            });

            test('file_scope_hints contain glob patterns', () => {
                for (const hint of hints) {
                    assert.ok(hint.includes('*') || hint.includes('/'),
                        `file_scope_hint "${hint}" doesn't look like a glob pattern`);
                }
            });
        }
    });
}

// ─────────────────────────────────────────────────────────────
// Cross-agent consistency
// ─────────────────────────────────────────────────────────────
suite('Cross-agent consistency', () => {
    test('no duplicate agent names', () => {
        const names = agentFiles.map(f => {
            const content = fs.readFileSync(path.join(agentsDir, f), 'utf8');
            const keys = parseTopLevelKeys(content);
            return keys.name;
        });
        const unique = [...new Set(names)];
        assert.strictEqual(unique.length, names.length,
            `duplicate agent names found: ${names.filter((n, i) => names.indexOf(n) !== i).join(', ')}`);
    });

    test('all roles are covered', () => {
        const roles = agentFiles.map(f => {
            const content = fs.readFileSync(path.join(agentsDir, f), 'utf8');
            const keys = parseTopLevelKeys(content);
            return keys.role;
        });
        const uniqueRoles = [...new Set(roles)];
        assert.ok(uniqueRoles.length >= 3,
            `expected at least 3 different roles, found: ${uniqueRoles.join(', ')}`);
    });
});

// ─────────────────────────────────────────────────────────────
// Report
// ─────────────────────────────────────────────────────────────
summary(`Agents tested: ${agentFiles.length}`);
process.exit(getResults().failed > 0 ? 1 : 0);
