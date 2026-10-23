"""Bounded native JS/TS lexical structure, never a compiler or evaluator.

Recognized token patterns retain exact source hashes. Unsupported lexical goals
fail to a module-only record rather than inventing declarations/call sites.
"""
from dataclasses import dataclass
import re
import time
from .common import ScanError, digest, sha

MAX_TOKENS = 60000
MAX_DEPTH = 256
MAX_FINGERPRINT_BYTES = 16000000
NAME = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")
IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
NUMBER = re.compile(r"(?:0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|(?:\d[\d_]*)(?:\.[\d_]*)?(?:[eE][+-]?[\d_]+)?n?)")
OPERATORS = sorted(("===", "!==", "=>", "?.", "...", "**", "++", "--", "==", "!=", "<=", ">=", "&&", "||", "??", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<", ">>>", ">>", "&&=", "||=", "??="), key=len, reverse=True)
CONTROL = {"if", "for", "while", "switch", "catch", "with", "function", "typeof", "delete", "void", "return", "throw", "new", "super", "import"}
LIMITATIONS = [
    "Native bounded lexical structure, not a JavaScript/TypeScript compiler, syntax certification or type checker.",
    "Token-pattern declarations and call sites only; overload/type resolution, dynamic dispatch and runtime behavior remain UNKNOWN.",
    "JSX, interpolated templates, decorators, escaped/non-ASCII identifiers and ambiguous lexical contexts require optional specialist analysis.",
]


class UnsupportedLexical(ScanError):
    pass


@dataclass(frozen=True)
class Token:
    value: str
    kind: str
    start: int
    end: int
    line: int
    end_line: int


def tokenize(text, deadline):
    if any(character in text for character in ('\v','\f','\x85','\x1c','\x1d','\x1e')):
        raise UnsupportedLexical('Unsupported control/line-segmentation character; module bytes retained')
    tokens, i, line = [], 0, 1
    size = len(text)
    def emit(value, kind, start, end, start_line):
        if len(tokens) >= MAX_TOKENS: raise ScanError("Native JS/TS token budget exceeded")
        tokens.append(Token(value, kind, start, end, start_line, line))
    while i < size:
        if i % 1024 == 0 and time.monotonic() > deadline: raise ScanError("Native JS/TS deadline exceeded")
        char = text[i]
        if char in "\n\r\u2028\u2029":
            if char == "\r" and i + 1 < size and text[i + 1] == "\n": i += 1
            line += 1; i += 1; continue
        if char in " \t\ufeff": i += 1; continue
        if text.startswith("#!", i) and i == 0:
            while i < size and text[i] not in "\n\r\u2028\u2029": i += 1
            continue
        if text.startswith("//", i):
            while i < size and text[i] not in "\n\r\u2028\u2029": i += 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0: raise ScanError("Unterminated JS/TS block comment")
            part = text[i:end + 2]
            line += len(part.splitlines()) - 1 + int(part.endswith(("\n", "\r", "\u2028", "\u2029")))
            i = end + 2; continue
        start, start_line = i, line
        if char in "'\"`":
            quote = char; i += 1
            while i < size:
                if text[i] == "\\":
                    if i + 1 >= size: raise ScanError("Unterminated JS/TS string escape")
                    if text[i + 1] in "\r\n\u2028\u2029":
                        line += 1
                        if text[i + 1] == "\r" and i + 2 < size and text[i + 2] == "\n": i += 1
                    i += 2; continue
                if quote == "`" and text.startswith("${", i):
                    raise UnsupportedLexical("Interpolated template lexical goals are not parsed natively")
                if text[i] == quote:
                    i += 1; break
                if text[i] in "\r\n\u2028\u2029":
                    if quote != "`": raise ScanError("Unescaped newline in JS/TS string")
                    if text[i] == "\r" and i + 1 < size and text[i + 1] == "\n": i += 1
                    line += 1
                i += 1
            else: raise ScanError("Unterminated JS/TS string or template")
            emit(text[start:i], "string" if quote != "`" else "template", start, i, start_line); continue
        if char == "/":
            previous = tokens[-1] if tokens else None
            # Only unambiguous expression prefixes permit opaque regex literals.
            regex_prefix = previous is None or previous.value in {"=", "(", "[", ",", ":", ";", "!", "&&", "||", "??", "=>", "return", "throw", "case"}
            division_suffix = previous is not None and (previous.kind in {"number", "string", "template"} or
                               previous.kind == "identifier" and previous.value not in CONTROL)
            if regex_prefix:
                i += 1; in_class = False
                while i < size:
                    if text[i] in "\r\n\u2028\u2029": raise ScanError("Unterminated JS/TS regex literal")
                    if text[i] == "\\": i += 2; continue
                    if text[i] == "[": in_class = True
                    elif text[i] == "]": in_class = False
                    elif text[i] == "/" and not in_class:
                        i += 1
                        while i < size and text[i].isascii() and text[i].isalpha(): i += 1
                        break
                    i += 1
                else: raise ScanError("Unterminated JS/TS regex literal")
                emit(text[start:i], "regex", start, i, start_line); continue
            if not division_suffix: raise UnsupportedLexical("Ambiguous regex/division lexical goal needs a specialist parser")
        if char == "<" and i + 1 < size and (text[i + 1] in "/>" or
                text[i + 1].isalpha() and re.match(r"<[^\r\n;{}]{1,256}>",text[i:i + 258])):
            raise UnsupportedLexical("JSX or angle-bracket type syntax is not parsed natively")
        if char in "@#\\" or ord(char) > 127 or char in "\v\f":
            raise UnsupportedLexical("Unsupported identifier, decorator or whitespace lexical form")
        match = IDENTIFIER.match(text, i)
        if match:
            i = match.end(); emit(match.group(), "identifier", start, i, start_line); continue
        match = NUMBER.match(text, i)
        if match:
            i = match.end(); emit(match.group(), "number", start, i, start_line); continue
        operator = next((value for value in OPERATORS if text.startswith(value, i)), None)
        value = operator or char
        if not operator and char not in "{}()[];:,.?~!+-*/%=&|^<>":
            raise UnsupportedLexical("Unsupported JS/TS lexical character")
        i += len(value); emit(value, "punctuation", start, i, start_line)
    return tokens


def paired(tokens):
    pairs, stack = {}, []
    for i, token in enumerate(tokens):
        value = token.value
        if token.kind != "punctuation": continue
        if value in "({[":
            stack.append((value, i))
            if len(stack) > MAX_DEPTH: raise ScanError("Native JS/TS delimiter depth exceeded")
        elif value in ")}]":
            if not stack or stack[-1][0] != {')':'(', '}':'{', ']':'['}[value]:
                raise ScanError("Mismatched JS/TS delimiters")
            _, start = stack.pop(); pairs[start] = i; pairs[i] = start
    if stack: raise ScanError("Unclosed JS/TS delimiter")
    return pairs


class Extractor:
    def __init__(self, path, data, builder, deadline=None):
        self.path, self.data, self.b = path, data, builder
        self.deadline = min(time.monotonic() + 5, deadline) if deadline is not None else time.monotonic() + 5
        self.tokens = tokenize(data.decode("utf-8-sig"), self.deadline)
        self.pairs = paired(self.tokens)
        self.fingerprint_bytes = 0
        self.declarations, self.loops, self.ignored = [], [], set()
        self.heads = set()

    def value(self, index):
        return self.tokens[index].value if 0 <= index < len(self.tokens) else ""

    def fingerprint(self, start, end, *, rename=None):
        values = [[token.kind, "<declaration>" if rename == i else token.value] for i, token in enumerate(self.tokens[start:end + 1], start)]
        self.fingerprint_bytes += sum(len(value[1]) + 20 for value in values)
        if self.fingerprint_bytes > MAX_FINGERPRINT_BYTES: raise ScanError("Native JS/TS fingerprint budget exceeded")
        return digest(values)

    def statement_end(self, start):
        if self.value(start) == "{": return self.pairs[start]
        i = start
        while i < len(self.tokens):
            if i - start > 4096: raise ScanError("Native JS/TS statement budget exceeded")
            if self.value(i) == ";": return i
            if self.value(i) in ("(", "[", "{"): i = self.pairs[i] + 1
            elif self.value(i) == "}": return max(start, i - 1)
            else: i += 1
        return len(self.tokens) - 1

    def body_after(self, end_parameters):
        i = end_parameters + 1
        if self.value(i) == ":":
            i += 1
            while i < len(self.tokens) and self.value(i) not in ("{", ";", "=", "=>"):
                if i - end_parameters > 256: raise ScanError("Native JS/TS annotation budget exceeded")
                if self.value(i) in ("(", "["): i = self.pairs[i] + 1
                else: i += 1
            if self.value(i) == "{" and self.value(self.pairs[i] + 1) == "{": i = self.pairs[i] + 1
        return i if self.value(i) == "{" else None

    def discover(self):
        count = len(self.tokens)
        # Type-only islands cannot create runtime call or loop records.
        for i, token in enumerate(self.tokens):
            if i in self.ignored: continue
            if token.value in {"interface", "type"} and NAME.fullmatch(self.value(i + 1)) and self.value(i - 1) != ".":
                end = self.statement_end(i + 2)
                if token.value == "interface":
                    start = next((j for j in range(i + 2, min(count, i + 258)) if self.value(j) == "{"), None)
                    if start is None: raise UnsupportedLexical("Unsupported TypeScript interface declaration")
                    end = self.pairs[start]
                self.declarations.append({"start":i,"end":end,"kind":"type","name":self.value(i + 1),"name_index":i + 1,"body":None})
                self.ignored.update(range(i, end + 1))
        for i, token in enumerate(self.tokens):
            if i in self.ignored: continue
            if token.value in ('function','class','for','while','do','return','await','try','throw','import','export','const','let','var','interface','type') and self.value(i - 1) not in ('.','?.') and self.value(i + 1) == ':':
                raise UnsupportedLexical('Keyword property/label context requires specialist disambiguation')
            if token.value == "function" and self.value(i - 1) not in (".", "?."):
                if self.value(i + 1) == '(' and self.value(i - 1) not in ('=','(',':','return','[','default','yield'):
                    raise UnsupportedLexical('Keyword-named method context requires specialist disambiguation')
                j = i + 1 + int(self.value(i + 1) == "*")
                name_index = j if NAME.fullmatch(self.value(j)) else None
                name = self.value(j) if name_index is not None else "<anonymous>"
                j += int(name_index is not None)
                if self.value(j) != "(": raise UnsupportedLexical("Unsupported native function declaration")
                end_params = self.pairs[j]; body = self.body_after(end_params)
                self.heads.add(j)
                if body is None:
                    raise UnsupportedLexical("Ambient/overload function or unsupported return annotation")
                self.declarations.append({"start":i,"end":self.pairs[body],"kind":"function","name":name,"name_index":name_index,"body":body,"params":(j,end_params)})
            elif token.value == "class" and self.value(i - 1) not in (".", "?."):
                if self.value(i + 1) == '(':
                    raise UnsupportedLexical('Keyword-named class method requires specialist disambiguation')
                j = i + 1; name_index = j if NAME.fullmatch(self.value(j)) else None
                body = next((k for k in range(j, min(count, j + 256)) if self.value(k) in ("{", ";")), None)
                if body is None or self.value(body) != "{": raise UnsupportedLexical("Unsupported native class declaration")
                self.declarations.append({"start":i,"end":self.pairs[body],"kind":"class","name":self.value(j) if name_index is not None else "<anonymous-class>","name_index":name_index,"body":body})
            elif token.value == "=>":
                previous = i - 1
                start_params = self.pairs[previous] if self.value(previous) == ")" else previous
                if self.value(previous) != ")" and not NAME.fullmatch(self.value(previous)):
                    raise UnsupportedLexical("Unsupported native arrow parameters")
                if self.value(previous) != ")" and self.value(previous - 1) == ":":
                    raise UnsupportedLexical("Annotated arrow lexical form needs specialist analysis")
                self.heads.add(start_params)
                body = i + 1; end = self.statement_end(body)
                # Expression bodies stop at their containing punctuation.
                if self.value(body) != "{":
                    j = body
                    while j <= end:
                        if self.value(j) in (",", ")", "]", "}", ";"): end = max(body, j - 1); break
                        j = self.pairs[j] + 1 if self.value(j) in ("(", "[", "{") else j + 1
                    if self.tokens[end].end_line > self.tokens[body].line and self.value(end + 1) not in (";", ",", ")", "]", "}"):
                        raise UnsupportedLexical("Multiline arrow termination is not established natively")
                name_index = start_params - 2 if self.value(start_params - 1) == "=" and NAME.fullmatch(self.value(start_params - 2)) else None
                self.declarations.append({"start":start_params,"end":end,"kind":"function","name":self.value(name_index) if name_index is not None else "<arrow>","name_index":name_index,"body":body,"params":(start_params,previous)})
        # Methods recognized only as direct children of a class body.
        for declaration in list(self.declarations):
            if declaration["kind"] != "class": continue
            i = declaration["body"] + 1
            while i < declaration["end"]:
                if NAME.fullmatch(self.value(i)) and self.value(i + 1) == "(" and i + 1 not in self.heads:
                    end_params = self.pairs[i + 1]; body = self.body_after(end_params)
                    if body is not None:
                        self.heads.add(i + 1)
                        self.declarations.append({"start":i,"end":self.pairs[body],"kind":"function","name":self.value(i),"name_index":i,"body":body,"params":(i + 1,end_params)})
                        i = self.pairs[body] + 1; continue
                if self.value(i) in ("(", "[", "{"): i = self.pairs[i] + 1
                else: i += 1
        for i, token in enumerate(self.tokens):
            if i in self.ignored or token.value not in ("for", "while", "do"): continue
            if i + 1 in self.heads: continue
            if self.value(i - 1) in (".", "?."): continue
            if token.value == "do":
                end = self.statement_end(i + 1); repeat = i + 1
                if self.value(end + 1) == "while":
                    self.ignored.add(end + 1)
                    if self.value(end + 2) != "(": raise ScanError("Malformed do/while")
                    end = self.pairs[end + 2]
                self.loops.append({"start":i,"end":end,"repeat":repeat,"kind":"do"}); continue
            j = i + 1 + int(token.value == "for" and self.value(i + 1) == "await")
            if j in self.heads: continue
            if self.value(j) != "(": raise ScanError("Malformed JS/TS loop header")
            end_header = self.pairs[j]; body = end_header + 1; end = self.statement_end(body)
            repeat = j if token.value == "while" else body
            if token.value == "for":
                k = j + 1
                while k < end_header:
                    if self.value(k) == ";": repeat = k + 1; break
                    k = self.pairs[k] + 1 if self.value(k) in ("(", "[", "{") else k + 1
            self.loops.append({"start":i,"end":end,"repeat":repeat,"kind":token.value})

    def enclosing(self, index, declarations=None):
        values = [d for d in (self.declarations if declarations is None else declarations) if d["body"] is not None and d["body"] < index <= d["end"] and "id" in d]
        return min(values, key=lambda d:d["end"] - d["body"])["id"] if values else self.b.module

    def function_owner(self, index):
        return self.enclosing(index, [d for d in self.declarations if d["kind"] == "function"])

    def add(self, kind, name, start, end, **attributes):
        owner = self.enclosing(start)
        repeated = [loop for loop in self.loops if loop["repeat"] <= start <= loop["end"] and loop.get("owner") == self.function_owner(start) and "id" in loop]
        token, last = self.tokens[start], self.tokens[end]
        result = self.b.add(kind, name, token.line, last.end_line, owner, len(repeated),
                            syntax_sha256=self.fingerprint(start,end), recognition="BOUNDED_TOKEN_PATTERN", analysis_origin="native", **attributes)
        for loop in repeated:
            self.b.edges.append({"id":digest([loop["id"],result,"inside_loop"]),"src":loop["id"],"dst":result,"kind":"inside_loop","evidence":"STATIC_SYNTAX"})
        return result

    def extract(self):
        self.discover()
        if self.tokens:
            fingerprint = self.fingerprint(0,len(self.tokens) - 1)
            self.b.nodes[0].update(syntax_sha256=fingerprint,relocation_sha256=fingerprint,end_line=self.tokens[-1].end_line)
        self.b.nodes[0]["attributes"].update(analysis_origin="native",recognition="BOUNDED_TOKEN_PATTERN")
        for declaration in sorted(self.declarations,key=lambda d:(d["start"],-d["end"])):
            start, end = declaration["start"], declaration["end"]
            owner = self.enclosing(start)
            declaration["id"] = self.b.add(declaration["kind"],declaration["name"],self.tokens[start].line,self.tokens[end].end_line,owner,0,
                syntax_sha256=self.fingerprint(start,end),relocation_sha256=self.fingerprint(start,end,rename=declaration["name_index"]),
                signature_sha256=self.fingerprint(start,(declaration["body"] or end) - 1,rename=declaration["name_index"]),
                recognition="BOUNDED_TOKEN_PATTERN",analysis_origin="native")
        for loop in sorted(self.loops,key=lambda item:item["start"]):
            loop["owner"] = self.function_owner(loop["start"])
            loop["id"] = self.add("loop",loop["kind"],loop["start"],loop["end"],nested_depth=1 + sum(
                other["start"] < loop["start"] <= other["end"] and other.get("owner") == loop["owner"] for other in self.loops))
        for i, token in enumerate(self.tokens):
            if time.monotonic() > self.deadline: raise ScanError("Native JS/TS deadline exceeded")
            if i in self.ignored: continue
            if token.value in ("const", "let", "var") and NAME.fullmatch(self.value(i + 1)):
                self.add("variable",self.value(i + 1),i,i + 1,declaration_kind=token.value)
            if token.value in ("import", "export") and self.value(i - 1) not in (".", "?.") and i + 1 not in self.heads:
                if i + 1 >= len(self.tokens): raise ScanError("Incomplete JS/TS import/export")
                if self.value(i + 1) == "(":
                    self.add("import","<dynamic>",i,self.pairs[i + 1],module="",dynamic=True)
                else:
                    if token.value == "export" and self.value(i + 1) not in ("{", "*", "type"): continue
                    literal = i + 1 if self.tokens[i + 1].kind == "string" else None
                    j = i + 1
                    while literal is None and j + 1 < len(self.tokens) and j - i <= 256:
                        if self.value(j) == "from" and self.tokens[j + 1].kind == "string": literal = j + 1; break
                        if self.value(j) in (";", "=", "function", "class", "const", "let", "var"): break
                        j = self.pairs[j] + 1 if self.value(j) in ("{", "[", "(") else j + 1
                    if literal is not None:
                        value = self.value(literal)[1:-1]
                        self.add("import",value if "\\" not in value else "<escaped-specifier>",i,literal,module=value if "\\" not in value else "",dynamic=False)
            if token.value in ("return", "await", "try", "throw") and self.value(i - 1) not in (".", "?.") and i + 1 not in self.heads:
                self.add({"throw":"raise"}.get(token.value,token.value),token.value,i,i)
            if token.value != "(" or i in self.heads or i == 0: continue
            j = i - 1
            if self.value(j) == "?.": j -= 1
            if not NAME.fullmatch(self.value(j)) or self.value(j) in CONTROL: continue
            start = j
            while start >= 2 and self.value(start - 1) in (".", "?.") and NAME.fullmatch(self.value(start - 2)): start -= 2
            # Type annotations and object method signatures are not call sites.
            if self.value(self.pairs[i] + 1) in ("{", ":"): continue
            name = "".join(self.value(k) for k in range(start,j + 1))
            self.add("call",name,start,self.pairs[i],shadowed=True,target_resolution="UNRESOLVED",expression=name + "(...)")
        result = self.b.result("typescript",LIMITATIONS)
        result["coverage"] = "BOUNDED_LEXICAL_STRUCTURE"
        return result


def extract_javascript(path, data, *, deadline=None):
    from .adapters import Builder
    builder = Builder(path,sha(data))
    try:
        return Extractor(path,data,builder,deadline).extract()
    except UnsupportedLexical as error:
        # Discard provisional records after any unsupported lexical context.
        builder = Builder(path,sha(data))
        builder.nodes[0]["attributes"].update(analysis_origin="native",recognition="MODULE_BYTES_ONLY")
        result = builder.result("typescript",[str(error),*LIMITATIONS])
        result["coverage"] = "BOUNDED_LEXICAL_STRUCTURE"
        return result
