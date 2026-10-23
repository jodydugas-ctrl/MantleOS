"""Thin Body launcher: repository source or exact exported library snapshot."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
if (ROOT/'runtime_lib/mantleos/application.py').is_file():
    sys.path.insert(0,str(ROOT/'runtime_lib'))
else:
    for ancestor in ROOT.parents:
        if (ancestor/'src/mantleos/application.py').is_file():
            sys.path.insert(0,str(ancestor/'src')); break
    else:
        raise RuntimeError('No qualified MantleOS runtime is available')
from mantleos.application import main
if __name__=='__main__': main(body=ROOT)
