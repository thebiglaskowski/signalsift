#!/usr/bin/env node
/**
 * Shared test infrastructure for Claude Sentient
 *
 * Provides test(), suite(), skip(), and summary() functions used by all
 * __tests__/ files. No external dependencies — uses Node.js built-in assert.
 *
 * Usage:
 *   const { test, suite, skip, summary } = require('../../test-utils');
 *   // ... run tests ...
 *   summary();
 *   process.exit(getResults().failed > 0 ? 1 : 0);
 */

let passed = 0;
let failed = 0;
let skipped = 0;
const failures = [];

function test(name, fn) {
    try {
        fn();
        passed++;
        process.stdout.write(`  \x1b[32m✓\x1b[0m ${name}\n`);
    } catch (e) {
        failed++;
        failures.push({ name, error: e.message });
        process.stdout.write(`  \x1b[31m✗\x1b[0m ${name}\n    ${e.message}\n`);
    }
}

function skip(name, _reason) {
    skipped++;
    process.stdout.write(`  \x1b[33m-\x1b[0m ${name} (skipped)\n`);
}

function suite(name, fn) {
    process.stdout.write(`\n\x1b[1m${name}\x1b[0m\n`);
    fn();
}

/**
 * Print summary and failure details.
 * @param {string} [extra] - Optional extra summary line (e.g., "Profiles tested: 9")
 */
function summary(extra) {
    process.stdout.write('\n─────────────────────────────────────\n');
    const parts = [`${passed} passed`, `${failed} failed`];
    if (skipped > 0) parts.push(`${skipped} skipped`);
    process.stdout.write(`\x1b[1mResults:\x1b[0m ${parts.join(', ')}\n`);
    if (extra) {
        process.stdout.write(`\x1b[1m${extra}\x1b[0m\n`);
    }
    if (failures.length > 0) {
        process.stdout.write('\n\x1b[31mFailures:\x1b[0m\n');
        for (const f of failures) {
            process.stdout.write(`  - ${f.name}: ${f.error}\n`);
        }
    }
}

function getResults() {
    return { passed, failed, skipped, failures };
}

module.exports = { test, suite, skip, summary, getResults };
