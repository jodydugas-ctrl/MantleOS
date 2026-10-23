"""Per-file interface declarations for SCAN; no traversal or source execution.

The .ui declaration mapping retains the MIT-licensed KPP inventory contract.
All readers consume bytes captured by the shared scanner exactly once.
"""
from html.parser import HTMLParser
import re
import time
import xml.etree.ElementTree as ET

from .common import ScanError, sha


def extract_interface(path, data, *, deadline=None):
    from .adapters import Builder
    builder = Builder(path, sha(data))

    def check():
        if deadline is not None and time.monotonic() >= deadline:
            raise ScanError('Interface extraction time budget exceeded')

    if path.lower().endswith(('.html', '.htm')):
        class Controls(HTMLParser):
            def handle_starttag(self, tag, attrs):
                check()
                if tag in {'form', 'input', 'button', 'textarea', 'select', 'a', 'dialog'}:
                    values = dict(attrs)
                    if len(builder.nodes) > 10000:
                        raise ScanError('HTML surface record budget exceeded')
                    item = {'tag': tag, 'id': values.get('id'), 'type': values.get('type'), 'name': values.get('name')}
                    line = self.getpos()[0]
                    builder.add('visible-interface', values.get('id') or tag, line, line,
                                builder.module, 0, html_control=item)
        parser = Controls()
        parser.feed(data.decode('utf-8-sig'))
        parser.close()
    else:
        decoded = data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
        if re.search(r'<!\s*(DOCTYPE|ENTITY)', decoded, re.I):
            raise ScanError('Interface XML DTD/entity declarations are unsupported')
        try:
            tree = ET.fromstring(decoded)
        except ET.ParseError as error:
            raise ScanError('Malformed interface UI XML') from error
        if tree.tag != 'ui':
            raise ScanError('Unsupported interface UI root')
        count = visited = 0

        def walk(node, parent, depth, owner):
            nonlocal count, visited
            check()
            visited += 1
            if depth > 64 or visited > 50000:
                raise ScanError('Interface XML structure budget exceeded')
            named = node.get('name') or node.tag
            locator = parent + '/' + named
            kind = {'widget': 'widget', 'action': 'action', 'actiongroup': 'action-group',
                    'addaction': 'action-placement', 'connection': 'connection', 'tabstop': 'tab-order'}.get(node.tag)
            if kind:
                props = {p.get('name'): ''.join(p.itertext()).strip() for p in node.findall('property')}
                count += 1
                if count > 10000:
                    raise ScanError('Interface declarations exceed scan entry limit')
                entry = {'id': path + '#' + str(count), 'file': path, 'path': locator,
                         'kind': kind, 'class': node.get('class', ''),
                         'label': props.get('text') or props.get('title') or props.get('windowTitle') or node.text and node.text.strip() or named,
                         'shortcut': props.get('shortcut', ''), 'properties': props,
                         'declaration': {c.tag: (c.text or '').strip() for c in node if c.tag in ('sender', 'signal', 'receiver', 'slot')},
                         'observation': 'static', 'confidence': 'declaration-only',
                         'disposition': 'required', 'depth': 1, 'anchor_ids': []}
                if any(not isinstance(entry[key], str) or not entry[key].strip() or len(entry[key]) > 2048
                       for key in ('id', 'path', 'label')):
                    raise ScanError('Interface declaration locator/label exceeds supported bounds')
                # XML source line numbers are unavailable; do not invent them.
                owner = builder.add(kind, named, None, None, owner, 0, interface_entry=entry)
            for child in node:
                walk(child, locator, depth + 1, owner)

        walk(tree, '', 0, builder.module)
    check()
    return builder.result('interface', ['Static interface declarations only; handlers, runtime behavior and visual conformance are unobserved.'])
