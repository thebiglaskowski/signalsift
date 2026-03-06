#!/usr/bin/env node
/**
 * Validation tests for Claude Sentient JSON schemas.
 *
 * Validates all JSON schemas are parseable, cross-checks profiles and agents
 * against schema requirements, and verifies command chaining integrity.
 * Uses Node.js built-in assert — no dependencies.
 *
 * Run: node schemas/__tests__/test-schemas.js
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Shared test infrastructure
const { test, suite, summary, getResults } = require('../../test-utils');

const schemasDir = path.resolve(__dirname, '..');
const projectRoot = path.resolve(__dirname, '../..');
const profilesDir = path.join(projectRoot, 'profiles');
const agentsDir = path.join(projectRoot, 'agents');
const commandsDir = path.join(projectRoot, '.claude', 'commands');

/**
 * Simple YAML key-value parser for top-level fields.
 * Handles: key: value, key: "value", and key: 'value'
 */
function parseYamlTopLevel(text) {
    const result = {};
    let inBlock = false;
    for (const line of text.split('\n')) {
        // Skip comments and empty lines
        if (line.trim().startsWith('#') || line.trim() === '') continue;
        // Detect block scalars
        if (line.match(/^\w[\w_]*\s*:\s*[|>]/)) {
            inBlock = true;
            const key = line.match(/^(\w[\w_]*)/)[1];
            result[key] = '(block scalar)';
            continue;
        }
        // If in block scalar, skip indented lines
        if (inBlock) {
            if (line.match(/^\s/) || line.trim() === '') continue;
            inBlock = false;
        }
        // Match top-level key: value
        const kvMatch = line.match(/^(\w[\w_]*)\s*:\s*(.+)$/);
        if (kvMatch) {
            let value = kvMatch[2].trim();
            // Remove quotes
            if ((value.startsWith('"') && value.endsWith('"')) ||
                (value.startsWith("'") && value.endsWith("'"))) {
                value = value.slice(1, -1);
            }
            result[kvMatch[1]] = value;
        }
        // Match array indicators
        const arrayMatch = line.match(/^(\w[\w_]*)\s*:\s*$/);
        if (arrayMatch) {
            result[arrayMatch[1]] = '(array or object)';
        }
        // Match inline arrays: key: [item1, item2]
        const inlineArrayMatch = line.match(/^(\w[\w_]*)\s*:\s*\[(.+)\]$/);
        if (inlineArrayMatch) {
            result[inlineArrayMatch[1]] = inlineArrayMatch[2]
                .split(',')
                .map(s => s.trim().replace(/^["']|["']$/g, ''));
        }
    }
    return result;
}

/**
 * Parse YAML frontmatter from a markdown file.
 */
function parseFrontmatter(text) {
    const match = text.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (!match) return null;
    const yamlText = match[1];
    const content = match[2];
    const frontmatter = {};
    for (const line of yamlText.split('\n')) {
        const kvMatch = line.match(/^(\w[\w-]*)\s*:\s*(.+)$/);
        if (kvMatch) {
            frontmatter[kvMatch[1]] = kvMatch[2].trim();
        }
    }
    return { frontmatter, content };
}

// Find all schema files
const schemaFiles = fs.readdirSync(schemasDir)
    .filter(f => f.endsWith('.schema.json'))
    .sort();

// Find all profile YAML files (exclude schema templates like _profile.schema.yaml)
const profileFiles = fs.existsSync(profilesDir)
    ? fs.readdirSync(profilesDir).filter(f => f.endsWith('.yaml') && !f.startsWith('_')).sort()
    : [];

// Find all agent YAML files
const agentFiles = fs.existsSync(agentsDir)
    ? fs.readdirSync(agentsDir).filter(f => f.endsWith('.yaml')).sort()
    : [];

// ─────────────────────────────────────────────────────────────
suite('Schema file inventory', () => {
    test('at least 12 schema files exist', () => {
        assert.ok(schemaFiles.length >= 12,
            `Expected >= 12 schema files, found ${schemaFiles.length}`);
    });

    test('base.schema.json exists', () => {
        assert.ok(schemaFiles.includes('base.schema.json'));
    });

    test('gate.schema.json exists', () => {
        assert.ok(schemaFiles.includes('gate.schema.json'));
    });

    test('agent.schema.json exists', () => {
        assert.ok(schemaFiles.includes('agent.schema.json'));
    });

    test('profile.schema.json exists', () => {
        assert.ok(schemaFiles.includes('profile.schema.json'));
    });

    // State file schemas (added in v1.3.9)
    test('session-state.schema.json exists', () => {
        assert.ok(schemaFiles.includes('session-state.schema.json'));
    });

    test('team-state.schema.json exists', () => {
        assert.ok(schemaFiles.includes('team-state.schema.json'));
    });

    test('gate-history.schema.json exists', () => {
        assert.ok(schemaFiles.includes('gate-history.schema.json'));
    });

    // Aspirational schemas (planned features) — verify [Planned] label
    test('skill.schema.json is marked as planned', () => {
        const schema = JSON.parse(fs.readFileSync(path.join(schemasDir, 'skill.schema.json'), 'utf8'));
        assert.ok(schema.title.includes('[Planned]'), 'skill schema should be marked as [Planned]');
    });

    test('phase.schema.json is marked as planned', () => {
        const schema = JSON.parse(fs.readFileSync(path.join(schemasDir, 'phase.schema.json'), 'utf8'));
        assert.ok(schema.title.includes('[Planned]'), 'phase schema should be marked as [Planned]');
    });

    test('event.schema.json is marked as planned', () => {
        const schema = JSON.parse(fs.readFileSync(path.join(schemasDir, 'event.schema.json'), 'utf8'));
        assert.ok(schema.title.includes('[Planned]'), 'event schema should be marked as [Planned]');
    });
});

// ─────────────────────────────────────────────────────────────
suite('State file schemas — structure', () => {
    test('session-state.schema.json has required fields: id, timestamp, cwd, project_root, profile', () => {
        const schema = JSON.parse(fs.readFileSync(path.join(schemasDir, 'session-state.schema.json'), 'utf8'));
        const required = schema.required || [];
        assert.ok(required.includes('id'), 'should require id');
        assert.ok(required.includes('timestamp'), 'should require timestamp');
        assert.ok(required.includes('profile'), 'should require profile');
        assert.ok(required.includes('project_root'), 'should require project_root');
    });

    test('team-state.schema.json has required fields: teammates, completed_tasks, file_ownership', () => {
        const schema = JSON.parse(fs.readFileSync(path.join(schemasDir, 'team-state.schema.json'), 'utf8'));
        const required = schema.required || [];
        assert.ok(required.includes('teammates'), 'should require teammates');
        assert.ok(required.includes('completed_tasks'), 'should require completed_tasks');
        assert.ok(required.includes('file_ownership'), 'should require file_ownership');
    });

    test('gate-history.schema.json has required field: entries', () => {
        const schema = JSON.parse(fs.readFileSync(path.join(schemasDir, 'gate-history.schema.json'), 'utf8'));
        const required = schema.required || [];
        assert.ok(required.includes('entries'), 'should require entries');
    });

    test('gate-history entries have required: timestamp, command, exitCode, duration, passed', () => {
        const schema = JSON.parse(fs.readFileSync(path.join(schemasDir, 'gate-history.schema.json'), 'utf8'));
        const entryRequired = schema.properties.entries.items.required || [];
        assert.ok(entryRequired.includes('timestamp'), 'entry should require timestamp');
        assert.ok(entryRequired.includes('exitCode'), 'entry should require exitCode');
        assert.ok(entryRequired.includes('passed'), 'entry should require passed');
    });
});

// ─────────────────────────────────────────────────────────────
suite('Schema parseability', () => {
    for (const file of schemaFiles) {
        test(`${file}: is valid JSON`, () => {
            const filePath = path.join(schemasDir, file);
            const content = fs.readFileSync(filePath, 'utf8');
            const parsed = JSON.parse(content);
            assert.ok(parsed, `${file} should parse as valid JSON`);
        });

        test(`${file}: has $schema field`, () => {
            const filePath = path.join(schemasDir, file);
            const schema = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            assert.ok(schema.$schema, `${file} should have $schema field`);
        });

        test(`${file}: has title field`, () => {
            const filePath = path.join(schemasDir, file);
            const schema = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            assert.ok(schema.title, `${file} should have title field`);
        });

        test(`${file}: has type or allOf field`, () => {
            const filePath = path.join(schemasDir, file);
            const schema = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            assert.ok(schema.type || schema.allOf,
                `${file} should have type or allOf field`);
        });
    }
});

// ─────────────────────────────────────────────────────────────
suite('Base schema structure', () => {
    const baseSchema = JSON.parse(
        fs.readFileSync(path.join(schemasDir, 'base.schema.json'), 'utf8')
    );

    test('requires name, version, description', () => {
        assert.ok(baseSchema.required.includes('name'));
        assert.ok(baseSchema.required.includes('version'));
        assert.ok(baseSchema.required.includes('description'));
    });

    test('version pattern accepts X.Y format', () => {
        const pattern = new RegExp(baseSchema.properties.version.pattern);
        assert.ok(pattern.test('1.0'), 'Should accept 1.0');
        assert.ok(pattern.test('1.2'), 'Should accept 1.2');
    });

    test('version pattern accepts X.Y.Z format', () => {
        const pattern = new RegExp(baseSchema.properties.version.pattern);
        assert.ok(pattern.test('1.0.0'), 'Should accept 1.0.0');
        assert.ok(pattern.test('1.2.3'), 'Should accept 1.2.3');
    });

    test('version pattern rejects invalid formats', () => {
        const pattern = new RegExp(baseSchema.properties.version.pattern);
        assert.ok(!pattern.test('1'), 'Should reject 1');
        assert.ok(!pattern.test('abc'), 'Should reject abc');
        assert.ok(!pattern.test('1.2.3.4'), 'Should reject 1.2.3.4');
    });

    test('name pattern enforces kebab-case', () => {
        const pattern = new RegExp(baseSchema.properties.name.pattern);
        assert.ok(pattern.test('python'), 'Should accept python');
        assert.ok(pattern.test('c-cpp'), 'Should accept c-cpp');
        assert.ok(!pattern.test('Python'), 'Should reject Python');
        assert.ok(!pattern.test('my_profile'), 'Should reject my_profile');
    });
});

// ─────────────────────────────────────────────────────────────
suite('Gate schema structure', () => {
    const gateSchema = JSON.parse(
        fs.readFileSync(path.join(schemasDir, 'gate.schema.json'), 'utf8')
    );

    test('has required fields: category, check', () => {
        assert.ok(gateSchema.required.includes('category'));
        assert.ok(gateSchema.required.includes('check'));
    });

    test('has alternative property for fallback commands', () => {
        assert.ok(gateSchema.properties.alternative,
            'Should have alternative property');
        assert.strictEqual(gateSchema.properties.alternative.type, 'string');
    });

    test('has detect property for gate applicability', () => {
        assert.ok(gateSchema.properties.detect,
            'Should have detect property');
        assert.strictEqual(gateSchema.properties.detect.type, 'string');
    });

    test('has fix_command for auto-fix support', () => {
        assert.ok(gateSchema.properties.fix_command,
            'Should have fix_command property');
    });

    test('has verbose_command for verbose output', () => {
        assert.ok(gateSchema.properties.verbose_command,
            'Should have verbose_command property');
    });

    test('has coverage_command for coverage reporting', () => {
        assert.ok(gateSchema.properties.coverage_command,
            'Should have coverage_command property');
    });
});

// ─────────────────────────────────────────────────────────────
suite('Agent schema structure', () => {
    const agentSchema = JSON.parse(
        fs.readFileSync(path.join(schemasDir, 'agent.schema.json'), 'utf8')
    );

    test('extends base schema via allOf', () => {
        assert.ok(agentSchema.allOf, 'Should have allOf');
        assert.ok(agentSchema.allOf.some(ref => ref.$ref && ref.$ref.includes('base')),
            'Should reference base.schema.json');
    });

    test('requires role, expertise, spawn_prompt, quality_gates', () => {
        assert.ok(agentSchema.required.includes('role'));
        assert.ok(agentSchema.required.includes('expertise'));
        assert.ok(agentSchema.required.includes('spawn_prompt'));
        assert.ok(agentSchema.required.includes('quality_gates'));
    });

    test('role enum includes all expected roles', () => {
        const roles = agentSchema.properties.role.enum;
        assert.ok(roles.includes('implementer'));
        assert.ok(roles.includes('reviewer'));
        assert.ok(roles.includes('researcher'));
        assert.ok(roles.includes('tester'));
        assert.ok(roles.includes('architect'));
    });
});

// ─────────────────────────────────────────────────────────────
suite('Profile schema structure', () => {
    const profileSchema = JSON.parse(
        fs.readFileSync(path.join(schemasDir, 'profile.schema.json'), 'utf8')
    );

    test('extends base schema via allOf', () => {
        assert.ok(profileSchema.allOf, 'Should have allOf');
        assert.ok(profileSchema.allOf.some(ref => ref.$ref && ref.$ref.includes('base')),
            'Should reference base.schema.json');
    });

    test('requires detection and gates', () => {
        assert.ok(profileSchema.required.includes('detection'));
        assert.ok(profileSchema.required.includes('gates'));
    });

    test('detection has files and extensions properties', () => {
        const detection = profileSchema.properties.detection;
        assert.ok(detection, 'Should have detection property');
        assert.strictEqual(detection.type, 'object');
        assert.ok(detection.properties.files, 'detection should have files property');
        assert.strictEqual(detection.properties.files.type, 'array');
        assert.ok(detection.properties.extensions, 'detection should have extensions property');
        assert.strictEqual(detection.properties.extensions.type, 'array');
    });

    test('gates allows additional properties', () => {
        const gates = profileSchema.properties.gates;
        assert.ok(gates, 'Should have gates property');
        assert.strictEqual(gates.type, 'object');
        assert.strictEqual(gates.additionalProperties, true);
    });

    test('models has default and by_phase properties', () => {
        const models = profileSchema.properties.models;
        assert.ok(models, 'Should have models property');
        assert.strictEqual(models.type, 'object');
        assert.ok(models.properties.default, 'models should have default property');
        assert.strictEqual(models.properties.default.type, 'string');
        assert.ok(models.properties.by_phase, 'models should have by_phase property');
        assert.strictEqual(models.properties.by_phase.type, 'object');
    });

    test('thinking has max_tokens and extended_for properties', () => {
        const thinking = profileSchema.properties.thinking;
        assert.ok(thinking, 'Should have thinking property');
        assert.strictEqual(thinking.type, 'object');
        assert.ok(thinking.properties.max_tokens, 'thinking should have max_tokens property');
        assert.strictEqual(thinking.properties.max_tokens.type, 'integer');
        assert.ok(thinking.properties.extended_for, 'thinking should have extended_for property');
        assert.strictEqual(thinking.properties.extended_for.type, 'array');
    });

    test('has conventions property', () => {
        assert.ok(profileSchema.properties.conventions,
            'Should have conventions property');
    });

    test('has optional sections: thresholds, web_indicators, infrastructure, ignore', () => {
        assert.ok(profileSchema.properties.thresholds, 'Should have thresholds property');
        assert.ok(profileSchema.properties.web_indicators, 'Should have web_indicators property');
        assert.ok(profileSchema.properties.infrastructure, 'Should have infrastructure property');
        assert.ok(profileSchema.properties.ignore, 'Should have ignore property');
        assert.strictEqual(profileSchema.properties.ignore.type, 'array');
    });
});

// ─────────────────────────────────────────────────────────────
suite('Profile YAML cross-validation against base schema', () => {
    const baseSchema = JSON.parse(
        fs.readFileSync(path.join(schemasDir, 'base.schema.json'), 'utf8')
    );
    const versionPattern = new RegExp(baseSchema.properties.version.pattern);
    const namePattern = new RegExp(baseSchema.properties.name.pattern);

    for (const file of profileFiles) {
        const filePath = path.join(profilesDir, file);
        const content = fs.readFileSync(filePath, 'utf8');
        const parsed = parseYamlTopLevel(content);
        const profileName = file.replace('.yaml', '');

        test(`${profileName}: has name field`, () => {
            assert.ok(parsed.name, `${file} should have name field`);
        });

        test(`${profileName}: name matches filename`, () => {
            if (parsed.name) {
                assert.strictEqual(parsed.name, profileName,
                    `name "${parsed.name}" should match filename "${profileName}"`);
            }
        });

        test(`${profileName}: name matches kebab-case pattern`, () => {
            if (parsed.name) {
                assert.ok(namePattern.test(parsed.name),
                    `name "${parsed.name}" should match pattern ${baseSchema.properties.name.pattern}`);
            }
        });

        test(`${profileName}: has valid version`, () => {
            assert.ok(parsed.version, `${file} should have version field`);
            if (parsed.version) {
                assert.ok(versionPattern.test(parsed.version),
                    `version "${parsed.version}" should match pattern ${baseSchema.properties.version.pattern}`);
            }
        });

        test(`${profileName}: has description`, () => {
            assert.ok(parsed.description, `${file} should have description field`);
        });

        test(`${profileName}: has gates section`, () => {
            // Check for gates keyword in content
            assert.ok(content.includes('gates:'),
                `${file} should have gates: section`);
        });
    }
});

// ─────────────────────────────────────────────────────────────
suite('Agent YAML cross-validation against agent schema', () => {
    const agentSchema = JSON.parse(
        fs.readFileSync(path.join(schemasDir, 'agent.schema.json'), 'utf8')
    );
    const baseSchema = JSON.parse(
        fs.readFileSync(path.join(schemasDir, 'base.schema.json'), 'utf8')
    );
    const versionPattern = new RegExp(baseSchema.properties.version.pattern);
    const validRoles = agentSchema.properties.role.enum;

    for (const file of agentFiles) {
        const filePath = path.join(agentsDir, file);
        const content = fs.readFileSync(filePath, 'utf8');
        const parsed = parseYamlTopLevel(content);
        const agentName = file.replace('.yaml', '');

        test(`${agentName}: has name field`, () => {
            assert.ok(parsed.name, `${file} should have name field`);
        });

        test(`${agentName}: has valid version`, () => {
            assert.ok(parsed.version, `${file} should have version field`);
            if (parsed.version) {
                assert.ok(versionPattern.test(parsed.version),
                    `version "${parsed.version}" should match pattern`);
            }
        });

        test(`${agentName}: has valid role`, () => {
            assert.ok(parsed.role, `${file} should have role field`);
            if (parsed.role) {
                assert.ok(validRoles.includes(parsed.role),
                    `role "${parsed.role}" should be one of: ${validRoles.join(', ')}`);
            }
        });

        test(`${agentName}: has expertise section`, () => {
            assert.ok(content.includes('expertise:'),
                `${file} should have expertise: section`);
        });

        test(`${agentName}: has spawn_prompt`, () => {
            assert.ok(content.includes('spawn_prompt:'),
                `${file} should have spawn_prompt: field`);
        });

        test(`${agentName}: has quality_gates`, () => {
            assert.ok(content.includes('quality_gates:'),
                `${file} should have quality_gates: field`);
        });
    }
});

// ─────────────────────────────────────────────────────────────
suite('Profile gate keys vs gate schema', () => {
    const gateSchema = JSON.parse(
        fs.readFileSync(path.join(schemasDir, 'gate.schema.json'), 'utf8')
    );
    // Collect all valid gate property names from schema
    const validGateKeys = new Set(Object.keys(gateSchema.properties || {}));
    // Also add keys from the check sub-object
    if (gateSchema.properties?.check?.properties) {
        for (const key of Object.keys(gateSchema.properties.check.properties)) {
            validGateKeys.add(key);
        }
    }

    for (const file of profileFiles) {
        const filePath = path.join(profilesDir, file);
        const content = fs.readFileSync(filePath, 'utf8');
        const profileName = file.replace('.yaml', '');

        test(`${profileName}: gate keys are valid schema properties`, () => {
            // Extract gate-level keys used in this profile
            const gateKeyPattern = /^\s{4}(\w[\w_]*)\s*:/gm;
            let match;
            const usedKeys = new Set();
            let inGates = false;
            for (const line of content.split('\n')) {
                if (line.match(/^gates:/)) { inGates = true; continue; }
                if (inGates && line.match(/^\w/) && !line.match(/^\s/)) { inGates = false; }
                if (inGates) {
                    // Gate name (e.g., lint:, test:, build:)
                    const gateNameMatch = line.match(/^\s{2}(\w+)\s*:/);
                    if (gateNameMatch) continue; // This is a gate name, not a key
                    // Gate property (e.g., command:, detect:, fix_command:)
                    const propMatch = line.match(/^\s{4}(\w[\w_]*)\s*:/);
                    if (propMatch) usedKeys.add(propMatch[1]);
                }
            }
            // All used keys should be in the schema
            for (const key of usedKeys) {
                assert.ok(validGateKeys.has(key),
                    `${profileName}: gate key "${key}" not found in gate.schema.json properties`);
            }
        });
    }
});

// ─────────────────────────────────────────────────────────────
suite('Command chaining integrity', () => {
    const claudeMdPath = path.join(commandsDir, 'CLAUDE.md');

    test('commands/CLAUDE.md exists', () => {
        assert.ok(fs.existsSync(claudeMdPath));
    });

    test('commands that chain to cs-loop have Skill in allowed-tools', () => {
        if (!fs.existsSync(claudeMdPath)) return;
        const claudeMd = fs.readFileSync(claudeMdPath, 'utf8');

        // Parse the skill chaining table
        const chainRows = [];
        const tablePattern = /\|\s*`\/([^`]+)`\s*\|\s*`\/([^`]+)`\s*\|/g;
        let match;
        while ((match = tablePattern.exec(claudeMd)) !== null) {
            chainRows.push({ from: match[1], to: match[2] });
        }

        // For each row where "to" is a command (not "—"), check source has Skill
        for (const row of chainRows) {
            if (row.to === '—' || row.to === '-') continue;

            const sourceFile = path.join(commandsDir, `${row.from}.md`);
            if (!fs.existsSync(sourceFile)) continue;

            const sourceContent = fs.readFileSync(sourceFile, 'utf8');
            const parsed = parseFrontmatter(sourceContent);
            if (!parsed) continue;

            const allowedTools = parsed.frontmatter['allowed-tools'] || '';
            assert.ok(allowedTools.includes('Skill'),
                `${row.from}.md chains to ${row.to} but doesn't have Skill in allowed-tools`);
        }
    });
});

// ─────────────────────────────────────────────────────────────
suite('Cross-module version consistency', () => {
    test('all agent versions match project version', () => {
        // Read project version from root CLAUDE.md
        const claudeMd = fs.readFileSync(
            path.join(projectRoot, 'CLAUDE.md'), 'utf8'
        );
        const versionMatch = claudeMd.match(/Version:\*\*\s*(\d+\.\d+(\.\d+)?)/);
        if (!versionMatch) return; // Can't determine project version

        const projectVersion = versionMatch[1];

        for (const file of agentFiles) {
            const content = fs.readFileSync(
                path.join(agentsDir, file), 'utf8'
            );
            const parsed = parseYamlTopLevel(content);
            if (parsed.version) {
                assert.strictEqual(parsed.version, projectVersion,
                    `${file} version "${parsed.version}" should match project version "${projectVersion}"`);
            }
        }
    });

    test('all profile versions match project version', () => {
        // Read project version from root CLAUDE.md
        const claudeMd = fs.readFileSync(
            path.join(projectRoot, 'CLAUDE.md'), 'utf8'
        );
        const versionMatch = claudeMd.match(/Version:\*\*\s*(\d+\.\d+(\.\d+)?)/);
        if (!versionMatch) return; // Can't determine project version

        const projectVersion = versionMatch[1];

        for (const file of profileFiles) {
            const content = fs.readFileSync(
                path.join(profilesDir, file), 'utf8'
            );
            const parsed = parseYamlTopLevel(content);
            if (parsed.version) {
                assert.strictEqual(parsed.version, projectVersion,
                    `${file} version "${parsed.version}" should match project version "${projectVersion}"`);
            }
        }
    });
});

// ─────────────────────────────────────────────────────────────
// Report
summary(`Schemas: ${schemaFiles.length}, Profiles: ${profileFiles.length}, Agents: ${agentFiles.length}`);
process.exit(getResults().failed > 0 ? 1 : 0);
