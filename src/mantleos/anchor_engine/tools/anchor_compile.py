"""Translate supported, pinned LLM-first Blueprints to standalone Python."""
import argparse
import hashlib
from pathlib import Path
from mantleos.anchor_engine.tools.anchor_runtime import AnchorExecutionError, program_stdout
from mantleos.anchor_engine.tools.anchor_notepad import Rejection, compile_python

ROOT=Path(__file__).resolve().parents[1]

def translate(source):
    lines=source.splitlines()
    if len(lines)<2: raise AnchorExecutionError('Missing profile declaration')
    if lines[1] == 'STATUS: EXPERIMENTAL EMIT_TEXT/0.2':
        output=program_stdout(source).encode('utf-8')
        return ('# Generated from pinned '+lines[1].split()[-1]+'; document literals remain data.\n'
                '# Source SHA-256: '+hashlib.sha256(source.encode('utf-8')).hexdigest()+'\n'
                'import sys\n'
                'if __name__ == "__main__":\n'
                '    sys.stdout.buffer.write('+repr(output)+')\n')
    if lines[1]=='STATUS: RELEASE CANDIDATE NOTEPAD_LLM/1.3':
        primer=(ROOT/'templates/primer_notepad_llm_v1.txt').read_text('utf-8')
        molecules=(ROOT/'templates/notepad_llm_v1_molecules.txt').read_text('utf-8')
        return compile_python(source,primer,molecules)
    raise AnchorExecutionError('Unsupported profile; no inferred compiler semantics')

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('blueprint',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args(argv)
    try:
        result=translate(args.blueprint.read_text('utf-8'))
        with args.output.open('x',encoding='utf-8',newline='\n') as stream: stream.write(result)
    except (AnchorExecutionError,Rejection,OSError,UnicodeError) as error:
        parser.exit(1,f'FAIL: {error}\n')
    return 0

if __name__=='__main__': raise SystemExit(main())
