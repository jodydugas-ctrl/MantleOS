'use strict';
// Python-backed persistent protocol adapter; no independent JS Anchor semantics.
const {spawn} = require('node:child_process');
const path = require('node:path');
const child = spawn(process.env.PYTHON || 'python3', [path.join(__dirname, 'bridge.py')], {stdio: 'inherit'});
child.on('error', error => { console.error(error.message); process.exitCode = 1; });
child.on('exit', (code, signal) => { process.exitCode = code === null ? 1 : code; });
