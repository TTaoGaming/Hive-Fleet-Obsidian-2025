#!/usr/bin/env node
/**
 * Scan Markdown files for ```mermaid code blocks and validate syntax
 * using mermaid's parser API. Fails fast on first error.
 *
 * Requires: npm i mermaid@^10 (installed in CI step)
 */

import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');

/** Recursively list Markdown files */
function* walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      const skip = ['.git', 'node_modules', '.venv'].some(s => p.toLowerCase().includes(s));
      if (!skip) yield* walk(p);
    } else if (e.isFile()) {
      if (p.toLowerCase().endsWith('.md') || p.toLowerCase().endsWith('.markdown')) {
        yield p;
      }
    }
  }
}

function extractMermaidBlocks(markdown) {
  const re = /```mermaid\n([\s\S]*?)\n```/g; // capture minimal
  const blocks = [];
  let m;
  while ((m = re.exec(markdown)) !== null) {
    blocks.push(m[1]);
  }
  return blocks;
}

let failures = 0;

const { mermaidAPI } = await import('mermaid');
mermaidAPI.initialize({ startOnLoad: false, theme: 'default' });

for (const file of walk(repoRoot)) {
  const text = fs.readFileSync(file, 'utf8');
  const blocks = extractMermaidBlocks(text);
  if (!blocks.length) continue;
  blocks.forEach((code, idx) => {
    try {
      // parse throws on syntax errors
      mermaidAPI.parse(code);
    } catch (err) {
      failures++;
      console.error(`Mermaid parse error in ${file} [block #${idx + 1}]:\n${(err && err.message) || err}`);
    }
  });
}

if (failures) {
  console.error(`Mermaid validation failed: ${failures} block(s) with errors.`);
  process.exit(1);
}

console.log('Mermaid validation PASS');
