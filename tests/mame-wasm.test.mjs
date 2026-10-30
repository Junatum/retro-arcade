import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

// Compile the REAL 17 MiB MAME binary with the JS engine used by CI.
// This runs without any game ROM, mocks, network request or new build output.
test('bundled MAME WebAssembly validates and compiles without copyrighted ROMs', async () => {
  const wasm = await readFile(new URL('../web/mame/mame.wasm', import.meta.url));
  assert.deepEqual([...wasm.subarray(0, 8)], [0, 97, 115, 109, 1, 0, 0, 0]);
  const compiled = await WebAssembly.compile(wasm);
  const exports = WebAssembly.Module.exports(compiled);
  assert.ok(exports.some(entry => entry.kind === 'memory'));
  assert.ok(exports.some(entry => entry.kind === 'function'));
  assert.ok(WebAssembly.Module.imports(compiled).length > 0);
});

// The VM executes MAME's real C++ entry point and verifies its registered
// driver list; no test game data or copyrighted ROMs are present.
test('MAME native ROM-free CLI boot queries pacman and galaxian drivers', {timeout: 25000}, async () => {
  const run = promisify(execFile);
  const {stdout} = await run(process.execPath,
    [fileURLToPath(new URL('./mame-node-probe.cjs', import.meta.url))],
    {timeout: 20000, maxBuffer: 1024 * 1024});
  assert.match(stdout, /PASS: real MAME JS\/WASM, memory FS and selected driver listing/);
});
