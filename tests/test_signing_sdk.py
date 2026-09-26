import copy

from kavi_capability_compiler import Guard, adapt_capabilities, compile_capsule, scan_manifest
from kavi_capability_compiler.runtime import AuthorityDenied
from kavi_capability_compiler.signing import generate_ed25519_keypair, sign_capsule, verify_signed_capsule


def _capsule():
    manifest=adapt_capabilities(
        "generic",
        {"tools":[{"name":"get_record","description":"Get record","input_schema":{"type":"object"}}]},
        namespace="records",
    )
    inv=scan_manifest(manifest)
    cid=inv["capabilities"][0]["id"]
    cap=compile_capsule(inv,{"capabilities":[cid],"ttl_seconds":60},{"default":"allow"},now=100)
    return cap,cid


def test_signed_capsule_requires_external_trust_key():
    cap,cid=_capsule()
    private,public=generate_ed25519_keypair()
    env=sign_capsule(cap,private,key_id="root-1")
    assert verify_signed_capsule(env,{"root-1":public},now=101)["valid"]
    assert not verify_signed_capsule(env,{},now=101)["valid"]


def test_tamper_wrong_key_and_expiry_fail_closed():
    cap,cid=_capsule()
    private,public=generate_ed25519_keypair()
    _,wrong_public=generate_ed25519_keypair()
    env=sign_capsule(cap,private,key_id="root-1")

    assert not verify_signed_capsule(env,{"root-1":wrong_public},now=101)["valid"]

    tampered=copy.deepcopy(env)
    tampered["capsule"]["task"]="tampered"
    assert not verify_signed_capsule(tampered,{"root-1":public},now=101)["valid"]

    assert not verify_signed_capsule(env,{"root-1":public},now=1000)["valid"]


def test_signed_guard_rechecks_signature_and_expiry_before_dispatch():
    cap,cid=_capsule()
    private,public=generate_ed25519_keypair()
    env=sign_capsule(cap,private,key_id="root-1")
    guard=Guard.from_signed(env,{"root-1":public},now=101)
    assert guard.signed

    decision=guard.authorize(cid,now=101)
    assert decision["allowed"]

    expired=guard.authorize(cid,now=1000)
    assert not expired["allowed"]
    assert expired["reason"]=="signed_capsule_invalid"
