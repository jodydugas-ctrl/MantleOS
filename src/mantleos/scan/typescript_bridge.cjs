'use strict';
// Trusted, pinned parser module; specimen text is never loaded as a module.
const crypto = require('node:crypto');
const ts = require(process.argv[2]);
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
let bytes = 0;
const chunks = [];
process.stdin.on('data', chunk => {
  bytes += chunk.length;
  if (bytes > 3000000) { process.stderr.write('Input budget exceeded'); process.exit(2); }
  chunks.push(chunk);
});
process.stdin.on('end', () => {
  try {
    const input = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    if (input.schema !== 'scan.syntax-request/1' || input.version !== ts.version) throw Error('Parser identity mismatch');
    const raw = Buffer.from(input.source_base64, 'base64');
    if (raw.length > 2000000 || hash(raw) !== input.source_sha256) throw Error('Source identity mismatch');
    const text = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(raw).replace(/^\uFEFF/, '');
    const ext = input.path.split('.').pop().toLowerCase();
    const kind = ({js: ts.ScriptKind.JS, mjs: ts.ScriptKind.JS, cjs: ts.ScriptKind.JS,
      jsx: ts.ScriptKind.JSX, tsx: ts.ScriptKind.TSX})[ext] || ts.ScriptKind.TS;
    const tree = ts.createSourceFile(input.path, text, ts.ScriptTarget.Latest, true, kind);
    if (tree.parseDiagnostics.length) throw Error('TypeScript syntax errors: ' + tree.parseDiagnostics.length);
    const children = node => {
      const values = [];
      ts.forEachChild(node, child => { values.push(child); });
      return values;
    };
    let fingerprintBytes = 0, fingerprintNodes = 0;
    const fingerprint = (root, normalizeName = false) => {
      const pieces = [], pending = [[root, 0]];
      while (pending.length) {
        const [node, depth] = pending.pop();
        if (++fingerprintNodes > 500000 || depth > 512) throw Error('Fingerprint traversal budget exceeded');
        const nested = children(node);
        const leaf = normalizeName && node === root.name ? '<declaration>' :
          nested.length ? '' : (node.text === undefined ? '' : String(node.text));
        const token = JSON.stringify([node.kind, nested.length, leaf]);
        fingerprintBytes += Buffer.byteLength(token);
        if (fingerprintBytes > 16000000) throw Error('Fingerprint byte budget exceeded');
        pieces.push(token);
        for (let i = nested.length - 1; i >= 0; i--) pending.push([nested[i], depth + 1]);
      }
      return hash(pieces.join('\n'));
    };
    const asyncFlag = node => Boolean(node.modifiers && node.modifiers.some(m => m.kind === ts.SyntaxKind.AsyncKeyword));
    const label = node => {
      if (node.name) return node.name.getText(tree).slice(0, 1000);
      if (node.parent && ts.isVariableDeclaration(node.parent)) return node.parent.name.getText(tree).slice(0, 1000);
      return '<anonymous>';
    };
    const syntax = fingerprint(tree);
    const records = [{id: 0, kind: 'module', name: input.path, line: 1, end_line: text.split(/\r\n|\n|\r/).length,
      owner: null, loop_depth: 0, attributes: {}, syntax_sha256: syntax, relocation_sha256: syntax, signature_sha256: null}];
    const pending = children(tree).reverse().map(node => [node, 0, 0, 1]);
    let visited = 0;
    while (pending.length) {
      const [node, owner, depth, astDepth] = pending.pop();
      if (++visited > 60000 || astDepth > 512) throw Error('AST traversal budget exceeded');
      let recordKind = null, name = '', attrs = {}, nextDepth = depth;
      if (ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node) || ts.isArrowFunction(node) ||
          ts.isFunctionExpression(node) || ts.isConstructorDeclaration(node) || ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node)) {
        recordKind = 'function'; name = ts.isConstructorDeclaration(node) ? 'constructor' : label(node);
        attrs = {async: asyncFlag(node)}; nextDepth = 0;
      } else if (ts.isClassDeclaration(node) || ts.isClassExpression(node)) {
        recordKind = 'class'; name = label(node); nextDepth = 0;
      } else if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node) && node.moduleSpecifier || ts.isImportEqualsDeclaration(node)) {
        recordKind = 'import';
        const spec = node.moduleSpecifier || node.moduleReference && node.moduleReference.expression;
        name = spec && ts.isStringLiteral(spec) ? spec.text : '<dynamic>';
        attrs = {module: name};
      } else if (ts.isCallExpression(node) || ts.isNewExpression(node)) {
        recordKind = 'call'; name = node.expression.getText(tree);
        if (name.length > 1000) name = '<dynamic>';
        attrs = {shadowed: true};
      } else if (ts.isForStatement(node) || ts.isForInStatement(node) || ts.isForOfStatement(node) || ts.isWhileStatement(node) || ts.isDoStatement(node)) {
        recordKind = 'loop'; name = 'loop'; nextDepth = depth + 1;
        attrs = {loop_type: ts.isForStatement(node) ? 'for' : ts.isForInStatement(node) ? 'for_in' :
          ts.isForOfStatement(node) ? 'for_of' : ts.isWhileStatement(node) ? 'while' : 'do'};
      } else if (ts.isReturnStatement(node)) { recordKind = 'return'; name = 'return'; }
      else if (ts.isAwaitExpression(node)) { recordKind = 'await'; name = 'await'; }
      else if (ts.isTryStatement(node)) { recordKind = 'try'; name = 'try'; }
      else if (ts.isThrowStatement(node)) { recordKind = 'raise'; name = 'throw'; }
      let nextOwner = owner;
      if (recordKind) {
        if (records.length >= 12000) throw Error('Syntax record budget exceeded');
        const id = records.length, fp = fingerprint(node);
        let signature = null;
        if (recordKind === 'function') signature = hash(JSON.stringify([
          (node.parameters || []).map(p => fingerprint(p)), node.type ? fingerprint(node.type) : null,
          (node.modifiers || []).map(m => m.kind), node.typeParameters ? node.typeParameters.map(p => fingerprint(p)) : []]));
        if (recordKind === 'class') signature = hash(JSON.stringify((node.heritageClauses || []).map(p => fingerprint(p))));
        records.push({id, kind: recordKind, name, line: tree.getLineAndCharacterOfPosition(node.getStart(tree)).line + 1,
          end_line: tree.getLineAndCharacterOfPosition(Math.max(node.getStart(tree), node.end - 1)).line + 1,
          owner, loop_depth: depth, attributes: attrs, syntax_sha256: fp,
          relocation_sha256: recordKind === 'function' || recordKind === 'class' ? fingerprint(node, true) : fp,
          signature_sha256: signature});
        nextOwner = id;
      }
      const nested = children(node);
      for (let i = nested.length - 1; i >= 0; i--) pending.push([nested[i], nextOwner, nextDepth, astDepth + 1]);
    }
    const output = JSON.stringify({schema: 'scan.syntax-provider/1', path: input.path,
      source_sha256: input.source_sha256, version: ts.version, records});
    if (Buffer.byteLength(output) > 8000000) throw Error('Output budget exceeded');
    process.stdout.write(output);
  } catch (error) { process.stderr.write(String(error.message).slice(0, 1000)); process.exitCode = 2; }
});
