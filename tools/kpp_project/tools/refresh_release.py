"""Refresh reviewed KPP source pins, refusing stale generated project views."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def refresh(root=ROOT):
    root = Path(root).resolve()
    spec = importlib.util.spec_from_file_location('kpp_export', root / 'tools/export_kpp.py')
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    expected = exporter.source_map(root)
    generated = {'SHARED-SOURCE.json', 'SHA256SUMS.json'}
    stale = [name for name, blob in expected.items() if name not in generated
             and (not (root / name).is_file() or (root / name).read_bytes() != blob)]
    if stale:
        raise ValueError('Generated views differ; export to a new directory and review: ' + ', '.join(sorted(stale)))
    actual = {name for name, _ in exporter.files(root)
              if not name.startswith(('.git/', '.work/', '.venv/', 'workspaces/', 'dist/', 'build/'))
              and not any(part.endswith('.egg-info') for part in Path(name).parts)}
    extra = actual - expected.keys()
    if extra:
        raise ValueError('Unrepresented source; add it to the exporter/templates: ' + ', '.join(sorted(extra)))
    for name in sorted(generated):
        (root / name).write_bytes(expected[name])
    return exporter.check(root, root)


if __name__ == '__main__':
    import json
    import sys
    try:
        print(json.dumps(refresh(), indent=2))
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
