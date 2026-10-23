"""Create an ingredient manifest for an operator-selected local repository.
No cloning, execution, or copying of the external source takes place.
"""
from pathlib import Path
from .core import KPPError, SLUG, digest, write_json
from .scanner import scan

def catalog_source(source, ident, destination, preferred=()):
    src=Path(source).resolve()
    dest=Path(destination)
    if not src.is_dir():raise KPPError("Source must be a locally available directory")
    if not SLUG.fullmatch(ident):raise KPPError("Invalid ingredient id")
    if dest.exists():raise KPPError("Destination manifest already exists")
    found=scan(src,2)
    if found["skipped"]:
        coverage="partial"
    else:coverage="listed source extensions only"
    lic=[p.name for p in src.iterdir() if p.is_file() and p.name.lower().startswith(('license','copying'))]
    obj={"schema":"kpp.ingredient/1","id":ident,"version":"0.0.0-local-scan", 
         "function":"Operator-selected external project; inspect APIs before composition",
         "status":"reference","preferred_for":list(preferred) or ["external-project"],
         "compatible_tissues":["mixed"],"tags":["external","repository","composition"],
         "dependencies":[],"capabilities":["External project, specific capabilities not yet verified"],
         "minimum_fidelity":1,
         "usage":{"use_when":"Consider an authorized local source checkout as an ingredient candidate.",
                  "inputs":["Pinned revision and independent interface review"],
                  "outputs":["Reference to source checkout; no executable integration"],
                  "limits":"Bounded inventory only; neither rights nor runtime behavior verified."},
         "source":{"kind":"local-directory","path_at_scan":str(src),
                   "source_listing_sha256":digest(found["files"]),"scanned_files":len(found["files"]),
                   "scope":coverage,"license_candidates":lic},
         "adaptation":"Operator must pin exact source revision, inspect license, define interfaces, and test in target before promoting to ready.",
         "verified_with":"Not executed or functionally qualified by cataloging",
         "provenance":"Local code selected by the operator"}
    write_json(dest,obj)
    return obj
