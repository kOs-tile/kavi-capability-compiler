from __future__ import annotations

import copy
import gzip
import os
import sys
import tarfile
from pathlib import Path


def normalize(path: Path, epoch: int) -> None:
    tmp=path.with_name(path.name+".canonical.tmp")
    with tarfile.open(path,"r:gz") as source:
        members=sorted(source.getmembers(),key=lambda item:item.name)
        with tmp.open("wb") as raw:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                fileobj=raw,
                compresslevel=9,
                mtime=epoch,
            ) as compressed:
                with tarfile.open(
                    fileobj=compressed,
                    mode="w",
                    format=tarfile.PAX_FORMAT,
                ) as target:
                    for member in members:
                        item=copy.copy(member)
                        item.uid=0
                        item.gid=0
                        item.uname=""
                        item.gname=""
                        item.mtime=epoch
                        item.pax_headers={}
                        payload=source.extractfile(member) if member.isfile() else None
                        try:
                            target.addfile(item,payload)
                        finally:
                            if payload is not None:
                                payload.close()
    os.replace(tmp,path)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: normalize_sdist.py SDIST SOURCE_DATE_EPOCH")
    path=Path(sys.argv[1])
    if not path.name.endswith(".tar.gz") or not path.is_file():
        raise SystemExit(f"not an sdist tar.gz: {path}")
    try:
        epoch=int(sys.argv[2])
    except ValueError as exc:
        raise SystemExit("SOURCE_DATE_EPOCH must be an integer") from exc
    if epoch < 0:
        raise SystemExit("SOURCE_DATE_EPOCH must be non-negative")
    normalize(path,epoch)


if __name__=="__main__":
    main()
