"""Generate the complete embedded LLM profile once; readers need no generator."""
import argparse
import json
from pathlib import Path
import re
from mantleos.anchor_engine.tools.anchor_notepad import initial_state, validate_state, ROUTES

ROOT=Path(__file__).resolve().parents[1]
def generate(name='XPNotepad_LLM_v1', state=None):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',name): raise ValueError('Invalid Blueprint ID')
    state=validate_state(initial_state() if state is None else state)
    primer=(ROOT/'templates/primer_notepad_llm_v1.txt').read_text('utf-8')
    molecules=(ROOT/'templates/notepad_llm_v1_molecules.txt').read_text('utf-8')
    mapping=dict(dispatcher='Dispatch',entry='Boundary',routes=ROUTES,state_owner='Document')
    encode=lambda value:json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'),sort_keys=True)
    return (f'ANCHOR BLUEPRINT: {name}\nSTATUS: RELEASE CANDIDATE NOTEPAD_LLM/1.3\n\n'
        f'BEGIN ANCHOR EXECUTION PRIMER\n{primer}END ANCHOR EXECUTION PRIMER\n\n'
        f'BEGIN STATE\n{encode(state)}\nEND STATE\n\n'
        f'BEGIN FUNCTION MAP\n{encode(mapping)}\nEND FUNCTION MAP\n\n'
        f'{molecules}BEGIN EXECUTION\nRUN {name}\nAWAIT USER COMMAND\nEND EXECUTION\n')

def main(argv=None):
    parser=argparse.ArgumentParser(description='Generate a self-contained LLM-first Notepad Blueprint')
    parser.add_argument('output',type=Path)
    parser.add_argument('--name',default='XPNotepad_LLM_v1')
    args=parser.parse_args(argv)
    with args.output.open('x',encoding='utf-8',newline='\n') as stream: stream.write(generate(args.name))

if __name__=='__main__': main()
