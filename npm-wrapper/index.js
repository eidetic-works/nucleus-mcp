#!/usr/bin/env node

// child_process is required to bridge npm-distributed wrapper → python package.
// Every call site below uses a hardcoded command string (no user-string concat
// into a shell) and the spawn() invocation explicitly sets shell:false.
// See SECURITY.md § "npm-wrapper subprocess invocations" for per-call rationale.
const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

/**
 * Nucleus-MCP NPX Wrapper
 * This script ensures the Python package is installed and then executes it.
 */

// Probe: does python3 exist on PATH? Hardcoded command, stdio:'ignore' (no
// output capture), no user input. Bounded subprocess — safe.
function checkPython() {
    try {
        execSync('python3 --version', { stdio: 'ignore' });
        return true;
    } catch (e) {
        return false;
    }
}

// Probe: is the python package importable? Hardcoded command, stdio:'ignore'.
// No user input. Bounded subprocess — safe.
function isInstalled() {
    try {
        execSync('python3 -m mcp_server_nucleus --help', { stdio: 'ignore' });
        return true;
    } catch (e) {
        return false;
    }
}

// Install the python package from PyPI. Hardcoded command + hardcoded package
// name — no user input flows into the command string. stdio:'inherit' streams
// pip's output to the user's terminal. By-design behavior of an npm-wrapper
// over a python package; equivalent to `npm install` for native dependencies.
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

// Defense-in-depth: reject CLI args containing null bytes. shell:false on the
// spawn() below already prevents shell injection, but a null byte in argv can
// truncate strings inside execve() on some platforms. Cheap belt-and-suspenders.
function validateArgs(args) {
    for (const arg of args) {
        if (typeof arg !== 'string' || arg.indexOf('\0') !== -1) {
            console.error('[Nucleus] ERROR: invalid CLI argument (null byte or non-string).');
            process.exit(2);
        }
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
    validateArgs(args);

    let pythonArgs = [];
    if (binName === 'nucleus-init') {
        pythonArgs = ['-m', 'mcp_server_nucleus.cli', ...args];
    } else {
        pythonArgs = ['-m', 'mcp_server_nucleus', ...args];
    }

    // User-supplied CLI args ARE forwarded into the python process, but as
    // discrete argv entries — shell:false guarantees no shell interpretation.
    // The python CLI itself parses argv via argparse; any vulnerability there
    // belongs to the python package, not this wrapper. Bounded subprocess.
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
