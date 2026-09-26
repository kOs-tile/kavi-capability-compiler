import argparse, json
from pathlib import Path
from . import __version__
from .core import scan_mcp_snapshot,audit_inventory,compile_capsule,verify_capsule

def load(p): return json.loads(Path(p).read_text())
def save(v,p):
    text=json.dumps(v,indent=2,sort_keys=True)+"\n"
    if p: Path(p).write_text(text)
    else: print(text,end="")

def main():
    ap=argparse.ArgumentParser(prog="kcc"); ap.add_argument("--version",action="version",version=__version__)
    sub=ap.add_subparsers(dest="cmd",required=True)
    for name in ("scan","audit"):
        p=sub.add_parser(name); p.add_argument("input"); p.add_argument("-o","--output")
    p=sub.add_parser("compile"); p.add_argument("inventory"); p.add_argument("--intent",required=True); p.add_argument("--policy",required=True); p.add_argument("-o","--output")
    p=sub.add_parser("verify"); p.add_argument("capsule"); p.add_argument("--inventory",required=True)
    a=ap.parse_args()
    if a.cmd=="scan": save(scan_mcp_snapshot(load(a.input)),a.output)
    elif a.cmd=="audit": save(audit_inventory(load(a.input)),a.output)
    elif a.cmd=="compile": save(compile_capsule(load(a.inventory),load(a.intent),load(a.policy)),a.output)
    else:
        r=verify_capsule(load(a.capsule),load(a.inventory)); save(r,None)
        raise SystemExit(0 if r["valid"] else 1)
