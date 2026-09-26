import argparse, asyncio, json
from pathlib import Path
from . import __version__
from .core import scan_mcp_snapshot,audit_inventory,compile_capsule,verify_capsule,inventory_lock,diff_inventory_lock,authorize_call
from .discovery import discover_stdio, discover_streamable_http, discover_config_server
from .config import sanitize_mcp_config
from .adapters import adapt_capabilities, SUPPORTED_SOURCE_FORMATS
from .manifest import scan_manifest
from .evidence import build_execution_evidence, verify_execution_evidence
from .live_probe import LiveProbeError, probe_kavi_bridge

def load(p): return json.loads(Path(p).read_text())
def save(v,p):
    text=json.dumps(v,indent=2,sort_keys=True)+"\n"
    if p: Path(p).write_text(text)
    else: print(text,end="")

def main():
    ap=argparse.ArgumentParser(prog="kcc",allow_abbrev=False); ap.add_argument("--version",action="version",version=__version__)
    sub=ap.add_subparsers(dest="cmd",required=True)
    for name in ("scan","audit"):
        p=sub.add_parser(name); p.add_argument("input"); p.add_argument("-o","--output")
    p=sub.add_parser("compile"); p.add_argument("inventory"); p.add_argument("--intent",required=True); p.add_argument("--policy",required=True); p.add_argument("-o","--output")
    p=sub.add_parser("verify"); p.add_argument("capsule"); p.add_argument("--inventory",required=True)
    p=sub.add_parser("lock"); p.add_argument("inventory"); p.add_argument("-o","--output")
    p=sub.add_parser("diff"); p.add_argument("lock"); p.add_argument("--inventory",required=True)
    p=sub.add_parser("authorize"); p.add_argument("capsule"); p.add_argument("--capability",required=True); p.add_argument("--operation"); p.add_argument("--parameters")
    p=sub.add_parser("discover-stdio"); p.add_argument("command"); p.add_argument("args",nargs="*"); p.add_argument("--server-name"); p.add_argument("-o","--output"); p.add_argument("--lock-output")
    p=sub.add_parser("discover-http"); p.add_argument("url"); p.add_argument("--server-name"); p.add_argument("-o","--output"); p.add_argument("--lock-output")
    p=sub.add_parser("discover-config"); p.add_argument("input"); p.add_argument("server"); p.add_argument("-o","--output"); p.add_argument("--lock-output")
    p=sub.add_parser("config-summary"); p.add_argument("input"); p.add_argument("-o","--output")
    p=sub.add_parser("manifest"); p.add_argument("input"); p.add_argument("--format",required=True,choices=SUPPORTED_SOURCE_FORMATS); p.add_argument("--namespace",required=True); p.add_argument("--server"); p.add_argument("-o","--output")
    p=sub.add_parser("scan-manifest"); p.add_argument("input"); p.add_argument("-o","--output")
    p=sub.add_parser("evidence-bind"); p.add_argument("capsule"); p.add_argument("--execution-id",required=True); p.add_argument("--evidence",required=True); p.add_argument("--capability"); p.add_argument("--operation"); p.add_argument("-o","--output")
    p=sub.add_parser("evidence-verify"); p.add_argument("input")
    p=sub.add_parser("probe-kavi",allow_abbrev=False); p.add_argument("--endpoint",required=True); p.add_argument("--token-env",default="KAVI_DISPATCH_TOKEN"); p.add_argument("--timeout",type=float,default=10.0); p.add_argument("-o","--output")
    a=ap.parse_args()
    if a.cmd=="scan": save(scan_mcp_snapshot(load(a.input)),a.output)
    elif a.cmd=="audit": save(audit_inventory(load(a.input)),a.output)
    elif a.cmd=="compile": save(compile_capsule(load(a.inventory),load(a.intent),load(a.policy)),a.output)
    elif a.cmd=="verify":
        r=verify_capsule(load(a.capsule),load(a.inventory)); save(r,None)
        raise SystemExit(0 if r["valid"] else 1)
    elif a.cmd=="lock": save(inventory_lock(load(a.inventory)),a.output)
    elif a.cmd=="diff":
        r=diff_inventory_lock(load(a.lock),load(a.inventory)); save(r,None)
        raise SystemExit(0 if r["clean"] else 2)
    elif a.cmd=="discover-stdio":
        r=asyncio.run(discover_stdio(a.command,a.args,server_name=a.server_name))
        if a.lock_output: save(inventory_lock(r["inventory"]),a.lock_output)
        save(r,a.output)
    elif a.cmd=="discover-http":
        r=asyncio.run(discover_streamable_http(a.url,server_name=a.server_name))
        if a.lock_output: save(inventory_lock(r["inventory"]),a.lock_output)
        save(r,a.output)
    elif a.cmd=="discover-config":
        r=asyncio.run(discover_config_server(load(a.input),a.server))
        if a.lock_output: save(inventory_lock(r["inventory"]),a.lock_output)
        save(r,a.output)
    elif a.cmd=="config-summary":
        save(sanitize_mcp_config(load(a.input)),a.output)
    elif a.cmd=="manifest":
        save(adapt_capabilities(
            a.format,
            load(a.input),
            namespace=a.namespace,
            source_metadata={"input":Path(a.input).name},
            server=a.server,
        ),a.output)
    elif a.cmd=="scan-manifest":
        save(scan_manifest(load(a.input)),a.output)
    elif a.cmd=="evidence-bind":
        capsule=load(a.capsule)
        refs=load(a.evidence)
        if isinstance(refs,dict): refs=refs.get("evidence",[])
        save(build_execution_evidence(
            a.execution_id,
            capsule["capsule_id"],
            refs,
            capability_id=a.capability,
            operation=a.operation,
        ),a.output)
    elif a.cmd=="evidence-verify":
        r=verify_execution_evidence(load(a.input)); save(r,None)
        raise SystemExit(0 if r["valid"] else 4)
    elif a.cmd=="probe-kavi":
        try:
            r=probe_kavi_bridge(
                a.endpoint,
                token_env=a.token_env,
                timeout=a.timeout,
            )
            save(r,a.output)
        except LiveProbeError as e:
            save({
                "status":"blocked",
                "code":e.code,
                "message":str(e),
                "secret_material_in_artifact":False,
            },None)
            raise SystemExit(5)
    else:
        params=json.loads(a.parameters) if a.parameters else {}
        r=authorize_call(load(a.capsule),a.capability,a.operation,params); save(r,None)
        raise SystemExit(0 if r["allowed"] else 3)
