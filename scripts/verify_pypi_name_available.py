from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

PROJECT="kavi-capability-compiler"
URL=f"https://pypi.org/pypi/{PROJECT}/json"


def main() -> None:
    request=urllib.request.Request(
        URL,
        headers={"User-Agent":"kavi-capability-compiler-release-preflight/0.1"},
    )
    try:
        with urllib.request.urlopen(request,timeout=15) as response:
            status=response.status
            payload=response.read(4096)
    except urllib.error.HTTPError as exc:
        if exc.code==404:
            print(json.dumps({
                "validation":"kcc.pypi-name-preflight.v1",
                "project":PROJECT,
                "available_for_first_publish":True,
                "status":404,
                "pass":True,
            },sort_keys=True))
            return
        raise SystemExit(f"PyPI project preflight returned HTTP {exc.code}") from exc
    except Exception as exc:
        raise SystemExit(f"PyPI project preflight failed closed: {type(exc).__name__}") from exc

    if status==200:
        try:
            data=json.loads(payload)
            observed=data.get("info",{}).get("name")
        except Exception:
            observed=None
        raise SystemExit(
            f"PyPI project name is already registered (HTTP 200, project={observed or PROJECT})"
        )
    raise SystemExit(f"Unexpected PyPI project preflight status: {status}")


if __name__=="__main__":
    main()
