"""Offline concurrent code/Qt discovery with an equivalent serial baseline."""
import argparse
import json
from pathlib import Path
import statistics

from mantleos import kernel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / 'specimen'
    ui = source / 'ui'
    ui.mkdir(parents=True)
    # Synthetic code is only read. No imports or UI handlers are executed.
    for n in range(24):
        (source / f'module_{n:02}.py').write_text(''.join(
            f'def operation_{i}(value):\n    return value + {i}\n\n' for i in range(8)), encoding='utf-8')
        (ui / f'Window_{n:02}.ui').write_text(
            f'<ui><widget class="QMainWindow" name="Window{n}"><action name="save">'
            '<property name="text"><string>Save</string></property></action>'
            '<addaction name="save"/></widget></ui>', encoding='utf-8')
    runs = []
    for iteration in range(3):
        # Alternate first runner to reduce a consistent filesystem warming bias.
        for mode in (('serial','parallel') if iteration % 2 == 0 else ('parallel','serial')):
            result = kernel.scan('scan.discover', {
                'source':str(source),'gui_root':str(ui),'identity':'synthetic-discovery-example',
                'output':str(output / f'{mode}-{iteration}'),'execution':mode}, permit=True)['observation']['result']
            runs.append(result)
    assert len({r['source']['snapshot_revision'] for r in runs}) == 1
    assert len({r['scans']['code']['graph_digest'] for r in runs}) == 1
    means = {mode:statistics.mean(r['run']['seconds'] for r in runs if r['execution'] == mode + '-read-only')
             for mode in ('serial','parallel')}
    report = {'result':'PASS','scope':'Synthetic 24 Python / 24 Qt UI files; three fresh-workspace runs per mode',
              'evidence_equal':True,'mean_seconds':means,'serial_over_parallel':means['serial'] / means['parallel'],
              'specimen_executed':False,'limitation':'Measured local timing, not a general speedup guarantee',
              'runs':[{'execution':r['execution'],'run':r['run']} for r in runs]}
    (output / 'report.json').write_text(json.dumps(report,indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
