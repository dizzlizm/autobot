#!/usr/bin/env node
/**
 * JS Lint Tool
 * Lints JavaScript files for syntax errors
 *
 * Usage: node lint-js.js /path/to/file.js
 *    or: node lint-js.js /path/to/directory
 */

const { execSync } = require('child_process');
const path = require('path');

const target = process.argv[2];

if (!target) {
    console.error('Usage: node lint-js.js <file-or-directory>');
    process.exit(1);
}

const absolutePath = path.resolve(target);
const scriptDir = __dirname;
const configPath = path.join(scriptDir, 'eslint.config.cjs');

console.log(`Linting: ${absolutePath}`);

try {
    const result = execSync(
        `npx eslint "${absolutePath}" --no-eslintrc -c "${configPath}" --format stylish`,
        { encoding: 'utf8', cwd: scriptDir }
    );
    if (result.trim()) {
        console.log(result);
    }
    console.log('PASSED: No lint errors');
    process.exit(0);
} catch (err) {
    if (err.stdout) console.log(err.stdout);
    if (err.stderr) console.error(err.stderr);
    console.log('FAILED: Lint errors found');
    process.exit(1);
}
