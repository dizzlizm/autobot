#!/usr/bin/env node
/**
 * Browser Test Tool
 * Tests that an HTML file loads without JS errors
 *
 * Usage: node test-html.js /path/to/index.html
 */

const puppeteer = require('puppeteer');
const path = require('path');

async function testHtml(htmlPath) {
    if (!htmlPath) {
        console.error('Usage: node test-html.js <path-to-html>');
        process.exit(1);
    }

    const absolutePath = path.resolve(htmlPath);
    console.log(`Testing: ${absolutePath}`);

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    const errors = [];
    const warnings = [];

    // Capture JS errors
    page.on('pageerror', err => errors.push(`JS Error: ${err.message}`));

    // Capture console errors/warnings
    page.on('console', msg => {
        if (msg.type() === 'error') {
            errors.push(`Console Error: ${msg.text()}`);
        } else if (msg.type() === 'warning') {
            warnings.push(`Console Warning: ${msg.text()}`);
        }
    });

    // Capture failed requests
    page.on('requestfailed', req => {
        errors.push(`Failed to load: ${req.url()}`);
    });

    try {
        const fileUrl = 'file://' + absolutePath;
        await page.goto(fileUrl, {
            waitUntil: 'networkidle0',
            timeout: 30000
        });

        // Wait for any async initialization
        await new Promise(r => setTimeout(r, 2000));

        // Check if canvas exists (for games)
        const hasCanvas = await page.$('canvas');
        if (hasCanvas) {
            console.log('✓ Canvas element found');
        }

        // Check page title
        const title = await page.title();
        if (title) {
            console.log(`✓ Page title: ${title}`);
        }

    } catch (err) {
        errors.push(`Page load error: ${err.message}`);
    }

    await browser.close();

    // Report results
    console.log('');

    if (warnings.length > 0) {
        console.log('WARNINGS:');
        warnings.forEach(w => console.log(`  ⚠ ${w}`));
        console.log('');
    }

    if (errors.length > 0) {
        console.log('ERRORS:');
        errors.forEach(e => console.log(`  ✗ ${e}`));
        console.log('');
        console.log(`FAILED: ${errors.length} error(s) found`);
        process.exit(1);
    }

    console.log('PASSED: No errors found');
    process.exit(0);
}

testHtml(process.argv[2]);
