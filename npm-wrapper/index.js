#!/usr/bin/env node

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

/**
 * Nucleus-MCP NPX Wrapper
 * This script ensures the Python package is installed and then executes it.
 */

function checkPython() {
    try {
        execSync('python3 --version', { stdio: 'ignore' });
        return true;
    } catch (e) {
        return false;
    }
}

function isInstalled() {
    try {
        execSync('python3 -m mcp_server_nucleus --help', { stdio: 'ignore' });
        return true;
    } catch (e) {
        return false;
    }
}

function install() {
    console.error('[Nucleus] Installing Python dependencies (nucleus-mcp)...');
    try {
        execSync('python3 -m pip install nucleus-mcp', { stdio: 'inherit' });
        return true;
    } catch (e) {
        console.error('[Nucleus] ERROR: Failed to install nucleus-mcp via pip.');
        console.error(e.message);
        return false;
    }
}

async function run() {
    if (!checkPython()) {
        console.error('[Nucleus] ERROR: python3 is not installed or not in PATH.');
        process.exit(1);
    }

    if (!isInstalled()) {
        if (!install()) {
            process.exit(1);
        }
    }

    // Determine which command was called
    const binName = path.basename(process.argv[1]);
    const args = process.argv.slice(2);

    let pythonArgs = [];
    if (binName === 'nucleus-init') {
        pythonArgs = ['-m', 'mcp_server_nucleus.cli', ...args];
    } else {
        pythonArgs = ['-m', 'mcp_server_nucleus', ...args];
    }

    const child = spawn('python3', pythonArgs, {
        stdio: 'inherit',
        shell: false
    });

    child.on('exit', (code) => {
        process.exit(code);
    });

    child.on('error', (err) => {
        console.error('[Nucleus] Error spawning python process:', err);
        process.exit(1);
    });
}

run();
