"""Generate portable specimens from the canonical source, never alternate models."""
from pathlib import Path
from ..anchor_engine.tools.anchor_runtime import render_hello_world


def kernel_cells():
    root = Path(__file__).resolve().parents[1]
    sources = {name: (root / (name + '.py')).read_text(encoding='utf-8')
               for name in ('json_contract', 'cells')}
    program = '''"""Portable demonstration of the actual MantleOS kernel CELL contract.
Embedded trusted source is data until this Python file is explicitly executed.
"""
import argparse
import json
import sys
import types

SOURCES = SOURCES_LITERAL
package = types.ModuleType('_cell_specimen')
package.__path__ = []
sys.modules[package.__name__] = package
for name, source in SOURCES.items():
    module = types.ModuleType(package.__name__ + '.' + name)
    module.__package__ = package.__name__
    sys.modules[module.__name__] = module
    setattr(package, name, module)
    exec(compile(source, '<canonical ' + name + '>', 'exec'), module.__dict__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kernel', choices=('pixel', 'tape', 'chroma.rgb/1', 'tape.segment/1'), required=True)
    parser.add_argument('--value', required=True)
    args = parser.parse_args()
    value = json.loads(args.value)
    kernel = {'pixel': 'chroma.rgb/1', 'tape': 'tape.segment/1'}.get(args.kernel, args.kernel)
    if args.kernel == 'tape':
        value = {'sequence': 1, 'record': {'seq': 1, 'text': value}}
    print(json.dumps(package.cells.produce(kernel, value), sort_keys=True))

if __name__ == "__main__":
    main()
'''.replace('SOURCES_LITERAL', repr(sources))
    return render_hello_world('KernelCells', program)
