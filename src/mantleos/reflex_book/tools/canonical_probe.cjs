// Independent, optional Node canonicalization probe. No Python serializer used.
// BigInt preserves the complete signed-64-bit JSON integer subset.
'use strict';
const fs = require('node:fs');
function canonical(source) {
  if (Buffer.byteLength(source, 'utf8') > 65536) throw Error('size');
  let offset = 0;
  function space() { while (/[ \t\r\n]/.test(source[offset] || '\0')) offset++; }
  function string() {
    const start = offset++;
    while (offset < source.length) {
      if (source[offset] === '\\') { offset += 2; continue; }
      if (source[offset++] === '"') {
        const value = JSON.parse(source.slice(start, offset));
        for (const char of value) {
          const point = char.codePointAt(0);
          if (point >= 0xd800 && point <= 0xdfff) throw Error('surrogate');
        }
        if (value.normalize('NFC') !== value) throw Error('NFC');
        return value;
      }
    }
    throw Error('unterminated string');
  }
  function value(depth = 0) {
    if (depth > 64) throw Error('depth');
    space();
    const char = source[offset];
    if (char === '"') return string();
    if (char === '{') {
      offset++; space();
      const result = new Map();
      if (source[offset] === '}') { offset++; return result; }
      for (;;) {
        space(); if (source[offset] !== '"') throw Error('key');
        const key = string();
        if (depth + 1 > 64) throw Error('depth');
        if (result.has(key)) throw Error('duplicate');
        space(); if (source[offset++] !== ':') throw Error('colon');
        result.set(key, value(depth + 1)); space();
        const end = source[offset++];
        if (end === '}') return result;
        if (end !== ',') throw Error('object delimiter');
      }
    }
    if (char === '[') {
      offset++; space();
      const result = [];
      if (source[offset] === ']') { offset++; return result; }
      for (;;) {
        result.push(value(depth + 1)); space();
        const end = source[offset++];
        if (end === ']') return result;
        if (end !== ',') throw Error('array delimiter');
      }
    }
    for (const [text, parsed] of [['true', true], ['false', false], ['null', null]]) {
      if (source.startsWith(text, offset)) { offset += text.length; return parsed; }
    }
    const match = /^-?(?:0|[1-9][0-9]*)/.exec(source.slice(offset));
    if (!match) throw Error('value');
    offset += match[0].length;
    const number = BigInt(match[0]);
    if (number < -(2n ** 63n) || number >= 2n ** 63n) throw Error('integer range');
    return number;
  }
  function compare(a, b) {
    const left = Array.from(a, c => c.codePointAt(0));
    const right = Array.from(b, c => c.codePointAt(0));
    for (let i = 0; i < Math.min(left.length, right.length); i++) {
      if (left[i] !== right[i]) return left[i] - right[i];
    }
    return left.length - right.length;
  }
  function emit(item) {
    if (item instanceof Map) return '{' + [...item.keys()].sort(compare)
      .map(key => JSON.stringify(key) + ':' + emit(item.get(key))).join(',') + '}';
    if (Array.isArray(item)) return '[' + item.map(emit).join(',') + ']';
    return typeof item === 'bigint' ? item.toString(10) : JSON.stringify(item);
  }
  const parsed = value(); space();
  if (offset !== source.length) throw Error('trailing');
  return emit(parsed);
}
const vectors = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
let checked = 0;
for (const vector of vectors) {
  let output, refused = false;
  try { output = canonical(vector.source); } catch { refused = true; }
  if (vector.refuse ? !refused : refused || output !== vector.expected)
    throw Error('canonical vector failed: ' + vector.id);
  checked++;
}
process.stdout.write(JSON.stringify({result: 'PASS', vectors: checked,
  node: process.version, unicode: process.versions.unicode,
  scope: 'independent canonical JSON vectors only; no VM or platform qualification'}) + '\n');
