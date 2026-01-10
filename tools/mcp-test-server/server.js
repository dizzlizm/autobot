#!/usr/bin/env node
/**
 * MCP Test Server
 * Provides intelligent testing tools for AI coding agents
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { execSync, spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

// Create MCP server
const server = new Server(
  {
    name: 'mcp-test-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Helper to run commands
function runCommand(cmd, cwd, timeout = 60000) {
  try {
    const result = execSync(cmd, {
      cwd,
      encoding: 'utf8',
      timeout,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    return { success: true, output: result };
  } catch (err) {
    return {
      success: false,
      output: err.stdout || '',
      error: err.stderr || err.message,
      exitCode: err.status,
    };
  }
}

// Detect project type by examining files
function detectProjectType(projectPath) {
  const types = [];
  const files = fs.readdirSync(projectPath);

  // Check for various project indicators
  if (files.includes('package.json')) {
    const pkg = JSON.parse(fs.readFileSync(path.join(projectPath, 'package.json'), 'utf8'));
    types.push('nodejs');

    if (pkg.dependencies?.react || pkg.devDependencies?.react) types.push('react');
    if (pkg.dependencies?.vue || pkg.devDependencies?.vue) types.push('vue');
    if (pkg.dependencies?.express || pkg.devDependencies?.express) types.push('express');
    if (pkg.devDependencies?.typescript) types.push('typescript');
    if (pkg.devDependencies?.jest) types.push('jest');
    if (pkg.devDependencies?.mocha) types.push('mocha');
    if (pkg.devDependencies?.vitest) types.push('vitest');
  }

  if (files.includes('requirements.txt') || files.includes('pyproject.toml') || files.includes('setup.py')) {
    types.push('python');
  }

  if (files.includes('Cargo.toml')) types.push('rust');
  if (files.includes('go.mod')) types.push('go');
  if (files.includes('pom.xml') || files.includes('build.gradle')) types.push('java');

  // Check for web files
  if (files.some(f => f.endsWith('.html'))) types.push('html');
  if (files.some(f => f.endsWith('.js') && !files.includes('package.json'))) types.push('vanilla-js');

  return types.length > 0 ? types : ['unknown'];
}

// Get recommended test command based on project type
function getTestCommand(projectPath, types) {
  if (types.includes('jest')) return 'npm test';
  if (types.includes('vitest')) return 'npm test';
  if (types.includes('mocha')) return 'npm test';
  if (types.includes('nodejs')) {
    const pkg = JSON.parse(fs.readFileSync(path.join(projectPath, 'package.json'), 'utf8'));
    if (pkg.scripts?.test && pkg.scripts.test !== 'echo "Error: no test specified" && exit 1') {
      return 'npm test';
    }
  }
  if (types.includes('python')) return 'pytest';
  if (types.includes('rust')) return 'cargo test';
  if (types.includes('go')) return 'go test ./...';
  return null;
}

// Get recommended lint command
function getLintCommand(projectPath, types) {
  if (types.includes('typescript')) return 'npx tsc --noEmit';
  if (types.includes('nodejs')) {
    const pkg = JSON.parse(fs.readFileSync(path.join(projectPath, 'package.json'), 'utf8'));
    if (pkg.scripts?.lint) return 'npm run lint';
    if (pkg.devDependencies?.eslint) return 'npx eslint .';
  }
  if (types.includes('vanilla-js') || types.includes('html')) {
    return 'npx eslint *.js --no-eslintrc --env browser,es2021 --rule "no-undef: error"';
  }
  if (types.includes('python')) return 'ruff check . || python -m flake8';
  if (types.includes('rust')) return 'cargo clippy';
  if (types.includes('go')) return 'go vet ./...';
  return null;
}

// Define available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'detect_project',
        description: 'Detect the type of project and what testing tools are available. Call this first to understand the project.',
        inputSchema: {
          type: 'object',
          properties: {
            project_path: {
              type: 'string',
              description: 'Absolute path to the project directory',
            },
          },
          required: ['project_path'],
        },
      },
      {
        name: 'run_tests',
        description: 'Run tests for the project. Will auto-detect the test framework if no command specified.',
        inputSchema: {
          type: 'object',
          properties: {
            project_path: {
              type: 'string',
              description: 'Absolute path to the project directory',
            },
            command: {
              type: 'string',
              description: 'Optional specific test command to run. If not provided, will auto-detect.',
            },
          },
          required: ['project_path'],
        },
      },
      {
        name: 'run_lint',
        description: 'Run linting/static analysis on the project. Will auto-detect the linter if no command specified.',
        inputSchema: {
          type: 'object',
          properties: {
            project_path: {
              type: 'string',
              description: 'Absolute path to the project directory',
            },
            command: {
              type: 'string',
              description: 'Optional specific lint command to run. If not provided, will auto-detect.',
            },
          },
          required: ['project_path'],
        },
      },
      {
        name: 'check_syntax',
        description: 'Check syntax of specific files without running full tests.',
        inputSchema: {
          type: 'object',
          properties: {
            file_path: {
              type: 'string',
              description: 'Absolute path to the file to check',
            },
          },
          required: ['file_path'],
        },
      },
      {
        name: 'browser_test',
        description: 'Load an HTML file in a headless browser and check for JavaScript errors.',
        inputSchema: {
          type: 'object',
          properties: {
            html_path: {
              type: 'string',
              description: 'Absolute path to the HTML file to test',
            },
            wait_seconds: {
              type: 'number',
              description: 'Seconds to wait for page to load (default: 2)',
            },
          },
          required: ['html_path'],
        },
      },
      {
        name: 'analyze_error',
        description: 'Analyze an error message and provide suggestions for fixing it.',
        inputSchema: {
          type: 'object',
          properties: {
            error_message: {
              type: 'string',
              description: 'The error message to analyze',
            },
            file_path: {
              type: 'string',
              description: 'Optional path to the file that caused the error',
            },
            language: {
              type: 'string',
              description: 'Programming language (js, python, etc.)',
            },
          },
          required: ['error_message'],
        },
      },
      {
        name: 'install_dependencies',
        description: 'Install project dependencies (npm install, pip install, etc.)',
        inputSchema: {
          type: 'object',
          properties: {
            project_path: {
              type: 'string',
              description: 'Absolute path to the project directory',
            },
          },
          required: ['project_path'],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'detect_project': {
        const types = detectProjectType(args.project_path);
        const testCmd = getTestCommand(args.project_path, types);
        const lintCmd = getLintCommand(args.project_path, types);

        // List files
        const files = fs.readdirSync(args.project_path).slice(0, 20);

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                project_types: types,
                recommended_test_command: testCmd,
                recommended_lint_command: lintCmd,
                files: files,
                has_package_json: fs.existsSync(path.join(args.project_path, 'package.json')),
                has_node_modules: fs.existsSync(path.join(args.project_path, 'node_modules')),
              }, null, 2),
            },
          ],
        };
      }

      case 'run_tests': {
        const types = detectProjectType(args.project_path);
        const cmd = args.command || getTestCommand(args.project_path, types);

        if (!cmd) {
          return {
            content: [{ type: 'text', text: 'No test command found. Project may not have tests configured.' }],
          };
        }

        const result = runCommand(cmd, args.project_path, 120000);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                command: cmd,
                success: result.success,
                output: result.output?.slice(0, 5000),
                error: result.error?.slice(0, 2000),
              }, null, 2),
            },
          ],
        };
      }

      case 'run_lint': {
        const types = detectProjectType(args.project_path);
        const cmd = args.command || getLintCommand(args.project_path, types);

        if (!cmd) {
          return {
            content: [{ type: 'text', text: 'No lint command found for this project type.' }],
          };
        }

        const result = runCommand(cmd, args.project_path, 60000);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                command: cmd,
                success: result.success,
                output: result.output?.slice(0, 5000),
                error: result.error?.slice(0, 2000),
              }, null, 2),
            },
          ],
        };
      }

      case 'check_syntax': {
        const ext = path.extname(args.file_path);
        let result;

        if (ext === '.js' || ext === '.mjs') {
          // Check JS syntax
          result = runCommand(`node --check "${args.file_path}"`, path.dirname(args.file_path));
        } else if (ext === '.py') {
          // Check Python syntax
          result = runCommand(`python -m py_compile "${args.file_path}"`, path.dirname(args.file_path));
        } else if (ext === '.json') {
          // Check JSON syntax
          try {
            JSON.parse(fs.readFileSync(args.file_path, 'utf8'));
            result = { success: true, output: 'Valid JSON' };
          } catch (e) {
            result = { success: false, error: e.message };
          }
        } else if (ext === '.html') {
          result = { success: true, output: 'HTML syntax check not implemented, use browser_test instead' };
        } else {
          result = { success: false, error: `Unknown file type: ${ext}` };
        }

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                file: args.file_path,
                success: result.success,
                output: result.output,
                error: result.error,
              }, null, 2),
            },
          ],
        };
      }

      case 'browser_test': {
        // Dynamic import puppeteer
        const puppeteer = await import('puppeteer');
        const browser = await puppeteer.default.launch({
          headless: 'new',
          args: ['--no-sandbox', '--disable-setuid-sandbox'],
        });

        const page = await browser.newPage();
        const errors = [];
        const logs = [];

        page.on('pageerror', (err) => errors.push(`JS Error: ${err.message}`));
        page.on('console', (msg) => {
          if (msg.type() === 'error') errors.push(`Console Error: ${msg.text()}`);
          else logs.push(`${msg.type()}: ${msg.text()}`);
        });
        page.on('requestfailed', (req) => errors.push(`Failed to load: ${req.url()}`));

        try {
          await page.goto('file://' + path.resolve(args.html_path), {
            waitUntil: 'networkidle0',
            timeout: 30000,
          });

          await new Promise((r) => setTimeout(r, (args.wait_seconds || 2) * 1000));

          const title = await page.title();
          const hasCanvas = await page.$('canvas');

          await browser.close();

          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify({
                  success: errors.length === 0,
                  title,
                  has_canvas: !!hasCanvas,
                  errors,
                  console_logs: logs.slice(0, 10),
                }, null, 2),
              },
            ],
          };
        } catch (err) {
          await browser.close();
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify({
                  success: false,
                  error: err.message,
                  errors,
                }, null, 2),
              },
            ],
          };
        }
      }

      case 'analyze_error': {
        const error = args.error_message;
        const suggestions = [];

        // Common error patterns and suggestions
        if (error.includes('is not defined')) {
          const match = error.match(/(\w+) is not defined/);
          if (match) {
            suggestions.push(`Variable or function '${match[1]}' is used before being defined.`);
            suggestions.push('Check for typos in the variable name.');
            suggestions.push('Make sure the variable is declared with let, const, or var.');
            suggestions.push('If it\'s a global, make sure the script that defines it loads first.');
          }
        }

        if (error.includes('Cannot read properties of undefined') || error.includes('Cannot read property')) {
          suggestions.push('You\'re trying to access a property on something that is undefined.');
          suggestions.push('Add a null check before accessing the property.');
          suggestions.push('Check if the object is being initialized correctly.');
        }

        if (error.includes('SyntaxError')) {
          suggestions.push('There\'s a syntax error in the code.');
          suggestions.push('Check for missing brackets, parentheses, or semicolons.');
          suggestions.push('Look for unclosed strings or template literals.');
        }

        if (error.includes('TypeError')) {
          suggestions.push('A value is not the type that was expected.');
          suggestions.push('Check if you\'re calling a function on the wrong type.');
        }

        if (error.includes('ENOENT') || error.includes('no such file')) {
          suggestions.push('A file or directory was not found.');
          suggestions.push('Check that the path is correct.');
          suggestions.push('Make sure the file exists before trying to access it.');
        }

        if (error.includes('ModuleNotFoundError') || error.includes('Cannot find module')) {
          suggestions.push('A module/package is not installed.');
          suggestions.push('Run npm install or pip install to install dependencies.');
        }

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                error_type: error.match(/^\w+Error/)?.[0] || 'Unknown',
                suggestions: suggestions.length > 0 ? suggestions : ['No specific suggestions available.'],
                original_error: error.slice(0, 500),
              }, null, 2),
            },
          ],
        };
      }

      case 'install_dependencies': {
        const types = detectProjectType(args.project_path);
        const results = [];

        if (types.includes('nodejs') || types.includes('html')) {
          if (fs.existsSync(path.join(args.project_path, 'package.json'))) {
            const result = runCommand('npm install', args.project_path, 180000);
            results.push({ type: 'npm', ...result });
          }
        }

        if (types.includes('python')) {
          if (fs.existsSync(path.join(args.project_path, 'requirements.txt'))) {
            const result = runCommand('pip install -r requirements.txt', args.project_path, 180000);
            results.push({ type: 'pip', ...result });
          }
        }

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({ results }, null, 2),
            },
          ],
        };
      }

      default:
        return {
          content: [{ type: 'text', text: `Unknown tool: ${name}` }],
          isError: true,
        };
    }
  } catch (err) {
    return {
      content: [{ type: 'text', text: `Error: ${err.message}` }],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Test Server running on stdio');
}

main().catch(console.error);
