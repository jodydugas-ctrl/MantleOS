'use strict'

// Scanner-owned, parse-only TypeScript/JavaScript probe.
// It never loads or executes the specimen. The Python adapter consumes this JSON and
// normalizes it into SCAN's language-agnostic anatomy model.

const fs = require('fs')
const path = require('path')
const tsModule = process.env.SCAN_TYPESCRIPT_MODULE || 'typescript'
const ts = require(tsModule)

const filePath = process.argv[2]
if (!filePath) {
  console.error('usage: node ts_probe.cjs <source-file>')
  process.exit(2)
}

const text = fs.readFileSync(filePath, 'utf8')
const ext = path.extname(filePath).toLowerCase()
const scriptKind = ext === '.tsx' ? ts.ScriptKind.TSX
  : ext === '.jsx' ? ts.ScriptKind.JSX
  : ext === '.js' || ext === '.mjs' || ext === '.cjs' ? ts.ScriptKind.JS
  : ts.ScriptKind.TS
const source = ts.createSourceFile(filePath, text, ts.ScriptTarget.Latest, true, scriptKind)

function lineOf(node) {
  return source.getLineAndCharacterOfPosition(node.getStart(source, false)).line + 1
}

function endLineOf(node) {
  return source.getLineAndCharacterOfPosition(node.getEnd()).line + 1
}

function clean(value, limit = 500) {
  if (value == null) return null
  const s = String(value).replace(/\s+/g, ' ').trim()
  return s.length > limit ? s.slice(0, limit) + '…' : s
}

function nodeText(node, limit = 500) {
  try { return clean(node.getText(source), limit) } catch { return null }
}

function propertyName(node) {
  if (!node) return null
  if (ts.isIdentifier(node) || ts.isStringLiteral(node) || ts.isNumericLiteral(node)) return node.text
  return nodeText(node, 160)
}

function objectOwnerName(objectLiteral) {
  const p = objectLiteral && objectLiteral.parent
  if (p && ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text
  if (p && ts.isPropertyAssignment(p)) {
    const owner = p.parent && ts.isObjectLiteralExpression(p.parent) ? objectOwnerName(p.parent) : null
    return owner ? `${owner}.${propertyName(p.name)}` : propertyName(p.name)
  }
  return null
}

function assignmentOutsideWrappers(node) {
  let p = node.parent
  while (p && (
    ts.isCallExpression(p) || ts.isParenthesizedExpression(p) || ts.isAsExpression(p) ||
    ts.isTypeAssertionExpression(p) || ts.isNonNullExpression(p) || ts.isSatisfiesExpression?.(p)
  )) {
    p = p.parent
  }
  if (p && ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text
  if (p && ts.isPropertyAssignment(p)) {
    const member = propertyName(p.name) || `<property@${lineOf(p)}>`
    const owner = p.parent && ts.isObjectLiteralExpression(p.parent) ? objectOwnerName(p.parent) : null
    return owner ? `${owner}.${member}` : member
  }
  return null
}

function functionName(node) {
  if (ts.isFunctionDeclaration(node) && node.name) return node.name.text
  if (ts.isFunctionExpression(node) && node.name) return node.name.text
  if (ts.isMethodDeclaration(node) || ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node)) {
    const member = propertyName(node.name) || `<method@${lineOf(node)}>`
    const cls = node.parent && ts.isClassLike(node.parent) && node.parent.name ? node.parent.name.text : null
    return cls ? `${cls}.${member}` : member
  }
  if (ts.isConstructorDeclaration(node)) {
    const cls = node.parent && ts.isClassLike(node.parent) && node.parent.name ? node.parent.name.text : '<class>'
    return `${cls}.constructor`
  }
  if (ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
    const assigned = assignmentOutsideWrappers(node)
    if (assigned) return assigned
    const p = node.parent
    if (p && ts.isCallExpression(p)) return `callback:${nodeText(p.expression, 120)}@${lineOf(node)}`
    if (p && ts.isJsxExpression(p)) return `<jsx-callback@${lineOf(node)}>`
    return `<anonymous@${lineOf(node)}>`
  }
  return `<function@${lineOf(node)}>`
}

function containingClass(node) {
  let p = node.parent
  while (p) {
    if (ts.isClassLike(p)) return p.name ? p.name.text : null
    p = p.parent
  }
  return null
}

function stringValue(node) {
  if (!node) return null
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text
  return null
}

function jsxTagName(node) {
  return nodeText(node.tagName, 160)
}

function jsxAttributes(node) {
  const out = {}
  for (const prop of node.attributes.properties || []) {
    if (ts.isJsxAttribute(prop)) {
      const name = propertyName(prop.name)
      if (!name) continue
      if (!prop.initializer) out[name] = 'true'
      else if (ts.isStringLiteral(prop.initializer)) out[name] = prop.initializer.text
      else if (ts.isJsxExpression(prop.initializer)) out[name] = prop.initializer.expression ? nodeText(prop.initializer.expression, 300) : ''
      else out[name] = nodeText(prop.initializer, 300)
    } else if (ts.isJsxSpreadAttribute(prop)) {
      out['...'] = nodeText(prop.expression, 300)
    }
  }
  return out
}

function jsxDirectText(opening) {
  const parent = opening.parent
  if (!parent || !ts.isJsxElement(parent)) return null
  const pieces = []
  for (const child of parent.children || []) {
    if (ts.isJsxText(child)) {
      const t = clean(child.getText(source), 180)
      if (t) pieces.push(t)
    }
  }
  return pieces.length ? clean(pieces.join(' '), 200) : null
}

const result = {
  parser: { kind: 'typescript-compiler-api', module: tsModule, version: ts.version, diagnostics: [] },
  imports: [], functions: [], calls: [], news: [], jsx: [], objectConstants: [], classes: [],
}

for (const d of source.parseDiagnostics || []) {
  const start = d.start == null ? null : source.getLineAndCharacterOfPosition(d.start).line + 1
  result.parser.diagnostics.push({ line: start, message: ts.flattenDiagnosticMessageText(d.messageText, '\n') })
}

function recordImport(node) {
  const mod = node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier) ? node.moduleSpecifier.text : null
  if (!mod) return
  const entry = { module: mod, line: lineOf(node), bindings: [] }
  const clause = node.importClause
  if (clause) {
    if (clause.name) entry.bindings.push({ imported: 'default', local: clause.name.text, kind: 'default' })
    const nb = clause.namedBindings
    if (nb && ts.isNamespaceImport(nb)) entry.bindings.push({ imported: '*', local: nb.name.text, kind: 'namespace' })
    if (nb && ts.isNamedImports(nb)) {
      for (const el of nb.elements) entry.bindings.push({ imported: el.propertyName ? el.propertyName.text : el.name.text, local: el.name.text, kind: 'named' })
    }
  }
  result.imports.push(entry)
}

function recordFunction(node, name) {
  result.functions.push({
    name, kind: ts.SyntaxKind[node.kind], line: lineOf(node), endLine: endLineOf(node),
    async: !!node.modifiers?.some((m) => m.kind === ts.SyntaxKind.AsyncKeyword),
    className: containingClass(node),
    parameters: (node.parameters || []).map((p) => nodeText(p.name, 240)),
  })
}

function recordObjectConstant(node) {
  if (!ts.isVariableDeclaration(node) || !ts.isIdentifier(node.name) || !node.initializer || !ts.isObjectLiteralExpression(node.initializer)) return
  const props = []
  for (const p of node.initializer.properties) {
    if (ts.isPropertyAssignment(p)) {
      props.push({ name: propertyName(p.name), literal: stringValue(p.initializer), value: nodeText(p.initializer, 240), line: lineOf(p) })
    } else if (ts.isShorthandPropertyAssignment(p)) {
      props.push({ name: p.name.text, literal: null, value: p.name.text, line: lineOf(p) })
    } else if (ts.isMethodDeclaration(p)) {
      props.push({ name: propertyName(p.name), literal: null, value: '<method>', line: lineOf(p) })
    }
  }
  result.objectConstants.push({ name: node.name.text, line: lineOf(node), properties: props })
}

function recordClass(node) {
  if (!ts.isClassDeclaration(node) && !ts.isClassExpression(node)) return
  result.classes.push({
    name: node.name ? node.name.text : `<class@${lineOf(node)}>`, line: lineOf(node), endLine: endLineOf(node),
    extends: (node.heritageClauses || []).flatMap((h) => h.types || []).map((t) => nodeText(t.expression, 160)),
  })
}

function recordCall(node, currentFn) {
  result.calls.push({
    callee: nodeText(node.expression, 240), args: node.arguments.map((a) => nodeText(a, 420)),
    line: lineOf(node), function: currentFn, optional: !!node.questionDotToken,
  })
}

function recordNew(node, currentFn) {
  result.news.push({ callee: nodeText(node.expression, 240), args: (node.arguments || []).map((a) => nodeText(a, 800)), line: lineOf(node), function: currentFn })
}

function recordJsx(node, currentFn) {
  const tag = jsxTagName(node)
  const attrs = jsxAttributes(node)
  const eventAttrs = {}
  for (const [k, v] of Object.entries(attrs)) if (/^on[A-Z]/.test(k)) eventAttrs[k] = v
  result.jsx.push({
    tag, line: lineOf(node), function: currentFn, attributes: attrs, eventAttributes: eventAttrs,
    text: jsxDirectText(node), customComponent: !!tag && /^[A-Z]/.test(tag),
  })
}

function visit(node, currentFn = null) {
  if (ts.isImportDeclaration(node)) recordImport(node)
  if (ts.isVariableDeclaration(node)) recordObjectConstant(node)
  if (ts.isClassDeclaration(node) || ts.isClassExpression(node)) recordClass(node)

  let nextFn = currentFn
  if (ts.isFunctionLike(node)) {
    nextFn = functionName(node)
    recordFunction(node, nextFn)
  }

  if (ts.isCallExpression(node)) recordCall(node, nextFn)
  if (ts.isNewExpression(node)) recordNew(node, nextFn)
  if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) recordJsx(node, nextFn)

  ts.forEachChild(node, (child) => visit(child, nextFn))
}

visit(source, null)
process.stdout.write(JSON.stringify(result))
