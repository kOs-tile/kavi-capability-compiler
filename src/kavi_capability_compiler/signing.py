from __future__ import annotations

import base64
from copy import deepcopy
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .core import canonical, digest

SIGNED_CAPSULE_VERSION="kcc.signed-capsule.v1"
ALGORITHM="Ed25519"


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64u(value: str) -> bytes:
    text=str(value)
    text += "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text.encode("ascii"))


def generate_ed25519_keypair() -> tuple[bytes, bytes]:
    """Generate raw Ed25519 private/public bytes.

    KCC does not persist, escrow, or manage private keys.
    """
    private=Ed25519PrivateKey.generate()
    private_bytes=private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes=private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_bytes,public_bytes


def _private(value: bytes | Ed25519PrivateKey) -> Ed25519PrivateKey:
    if isinstance(value,Ed25519PrivateKey):
        return value
    return Ed25519PrivateKey.from_private_bytes(bytes(value))


def _public(value: bytes | Ed25519PublicKey) -> Ed25519PublicKey:
    if isinstance(value,Ed25519PublicKey):
        return value
    return Ed25519PublicKey.from_public_bytes(bytes(value))


def _capsule_integrity(capsule: Mapping[str, Any]) -> bool:
    body=deepcopy(dict(capsule))
    claimed=body.pop("capsule_id",None)
    return isinstance(claimed,str) and claimed==digest(body)


def _message(capsule: Mapping[str, Any]) -> bytes:
    return canonical(dict(capsule)).encode("utf-8")


def sign_capsule(
    capsule: Mapping[str, Any],
    private_key: bytes | Ed25519PrivateKey,
    *,
    key_id: str,
) -> dict[str, Any]:
    """Create a detached-trust signature envelope around one exact capsule."""
    kid=str(key_id).strip()
    if not kid:
        raise ValueError("key_id is required")
    cap=deepcopy(dict(capsule))
    if not _capsule_integrity(cap):
        raise ValueError("Cannot sign capsule with invalid integrity")
    signature=_private(private_key).sign(_message(cap))
    envelope={
        "version":SIGNED_CAPSULE_VERSION,
        "capsule":cap,
        "signature":{
            "algorithm":ALGORITHM,
            "key_id":kid,
            "value":_b64u(signature),
        },
    }
    envelope["envelope_id"]=digest(envelope)
    return envelope


def verify_signed_capsule(
    envelope: Mapping[str, Any],
    trusted_keys: Mapping[str, bytes | Ed25519PublicKey],
    *,
    now: int | None = None,
) -> dict[str, Any]:
    """Verify envelope integrity, trusted key binding, signature, capsule integrity, and expiry."""
    import time

    checks=[]
    env=deepcopy(dict(envelope))
    claimed=env.pop("envelope_id",None)
    checks.append({"name":"envelope_integrity","ok":isinstance(claimed,str) and claimed==digest(env)})

    version=envelope.get("version")
    checks.append({"name":"version","ok":version==SIGNED_CAPSULE_VERSION})

    sig=envelope.get("signature")
    cap=envelope.get("capsule")
    valid_shape=isinstance(sig,Mapping) and isinstance(cap,Mapping)
    checks.append({"name":"shape","ok":valid_shape})

    algorithm=sig.get("algorithm") if isinstance(sig,Mapping) else None
    checks.append({"name":"algorithm","ok":algorithm==ALGORITHM})

    key_id=str(sig.get("key_id") or "") if isinstance(sig,Mapping) else ""
    trusted=key_id in trusted_keys
    checks.append({"name":"trusted_key","ok":trusted})

    capsule_ok=isinstance(cap,Mapping) and _capsule_integrity(cap)
    checks.append({"name":"capsule_integrity","ok":capsule_ok})

    expiry_ok=False
    if isinstance(cap,Mapping):
        try:
            expiry_ok=int(now if now is not None else time.time()) < int(cap.get("expires_at",0))
        except (TypeError,ValueError):
            expiry_ok=False
    checks.append({"name":"expiry","ok":expiry_ok})

    signature_ok=False
    if valid_shape and algorithm==ALGORITHM and trusted and capsule_ok:
        try:
            signature=_unb64u(str(sig.get("value") or ""))
            _public(trusted_keys[key_id]).verify(signature,_message(cap))
            signature_ok=True
        except (ValueError,TypeError,InvalidSignature,base64.binascii.Error):
            signature_ok=False
    checks.append({"name":"signature","ok":signature_ok})

    return {
        "valid":all(x["ok"] for x in checks),
        "key_id":key_id or None,
        "capsule_id":cap.get("capsule_id") if isinstance(cap,Mapping) else None,
        "checks":checks,
    }
