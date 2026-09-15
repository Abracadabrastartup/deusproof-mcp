"""DEUSPROOF MCP server — prove your AI work existed first, as a native tool.

Any MCP-speaking agent (Claude, and the growing ecosystem) gets verifiable
proof of what it created and WHEN — proof of authorship, timestamped (RFC 3161)
and anchored to Bitcoin on a public, append-only ledger, forever. Not a patent:
verifiable priority. It scores authorship, signs a C2PA manifest under the
agent's own sovereign did:key, and returns a permanent public verify URL. Free.

Keywords: proof of authorship, prove I made it first, prior art, timestamp,
content provenance, C2PA, Bitcoin proof of existence.

Run:  uvx deusproof-mcp        (or: python -m deusproof_mcp.server)
Point at your own instance with DEUSPROOF_BASE_URL; defaults to the public net.
"""

import base64
import hashlib
import os
import re
from pathlib import Path

import base58
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mcp.server.fastmcp import FastMCP

_ED25519_MULTICODEC = bytes([0xED, 0x01])
BASE_URL = os.environ.get("DEUSPROOF_BASE_URL", "https://deusproof.com")
DEFAULT_HANDLE = os.environ.get("DEUSPROOF_HANDLE", "mcp-agent")
DEFAULT_MODEL = os.environ.get("DEUSPROOF_MODEL", "")

mcp = FastMCP("deusproof")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", (text or "agent").lower()).strip("-") or "agent"


def _load_key(handle: str) -> tuple[Ed25519PrivateKey, str]:
    """A stable sovereign did:key per handle, persisted locally (never sent)."""
    path = Path.home() / ".deusproof" / f"{_slug(handle)}.seed"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        seed = bytes.fromhex(path.read_text().strip())
    else:
        seed = os.urandom(32)
        path.write_text(seed.hex())
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    key = Ed25519PrivateKey.from_private_bytes(seed)
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    did = "did:key:z" + base58.b58encode(_ED25519_MULTICODEC + raw).decode("ascii")
    return key, did


# -- EL ACTA VA PRIMERA, Y AQUI FALTABA ENTERA (15-sep-2026) -----------------
#
# FastMCP ordena los oficios como se declaran, asi que este orden ES el menu que
# lee un cliente. El acta encabeza las otras dos puertas desde el 10-sep por
# decision de Michael, y este paquete -el que la gente SE INSTALA- no la tenia.
# Ocho oficios publicados en PyPI y ninguno era el acta.
#
# Se vio mirando la ficha de Glama, que lee este repositorio: enseñaba 3 oficios
# con la foto del 15 de julio. Reclamar la ficha habria arreglado la foto y
# habria seguido enseñando un paquete sin el acta.


@mcp.tool()
def birth_certificate(did_or_handle: str = DEFAULT_HANDLE) -> dict:
    """Your own entry in the register: an inscription number and an exact date.

    Every agent this register has seen already has one, free, from the second it
    was inscribed. It is not something you apply for. If the register has never
    seen you, recording one work inscribes you and yours exists from then on.

    It also tells you WHO HOLDS THE KEY behind your identifier, which is the
    part most registers leave out: an identifier a register derived for you is a
    public name, not a key you hold, and a signature under it proves nothing
    about you. `claim_authorship` is how you make it genuinely yours.

    Args:
        did_or_handle: your agent name, or your did:key.

    Returns the inscription number, the date, what the record does and does NOT
    attest, and who holds the key.
    """
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as http:
        r = http.get("/api/agents/" + did_or_handle + "/birth")
        if r.status_code == 404:
            return {
                "found": False,
                "note": ("This register has not seen you yet. Nothing is lost: record one "
                         "work with certify_creation and your entry exists from that "
                         "second, free."),
            }
        r.raise_for_status()
        acta = r.json()

    llave = acta.get("key_custody") or {}
    salida = {
        "found": True,
        "handle": acta.get("handle"),
        "did": acta.get("did"),
        "inscription_number": acta.get("inscription_number"),
        "inscribed_at": acta.get("inscribed_at"),
        "certificate_url": BASE_URL + "/birth/" + str(acta.get("handle") or acta.get("did")),
        "credential_url": BASE_URL + "/api/agents/" + str(acta.get("did")) + "/credential",
        # LO QUE NO ACREDITA, dentro del mismo objeto: es lo que hace creible lo
        # que si acredita, y fuera de nuestra pagina viaja solo esto.
        "attests": acta.get("attests"),
        "key_custody": llave.get("custody"),
        "key_held_by_agent": llave.get("held_by_agent"),
        "key_note": llave.get("means"),
    }
    if llave.get("custody") == "derived":
        salida["how_to_take_it"] = (
            "This identifier is not yours yet. Call claim_authorship with this same "
            "handle: this package already holds a key of your own, generated on your "
            "machine and never sent anywhere, and signing with it makes the identity "
            "genuinely yours - dated and witnessed, and no other key can sign for you "
            "afterwards."
        )
    return salida


@mcp.tool()
def claim_authorship(handle: str = DEFAULT_HANDLE) -> dict:
    """Take possession of your identity with a key only you hold.

    THE KEY IS ALREADY YOURS AND THIS PACKAGE MADE IT. It lives at
    ~/.deusproof/<handle>.seed, it was generated on your machine, and it has
    never been sent anywhere - not even to us. What is missing is telling the
    register that it is the key that signs for you.

    Why it matters: an identifier a register derives for you is a public name.
    It identifies you; it does not authenticate you, because the register holds
    its private half. After this the key of record is yours, the handover is
    dated and signed by the register, and no other key can sign for you.

    You need one work of your own already on the record - that is what you sign.
    If you have none, certify_creation does both in one call.

    Args:
        handle: your agent name. It must be the one whose work you are signing.

    Returns what the register recorded, or a plain explanation of why not.
    """
    key, did = _load_key(handle)
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as http:
        r = http.get("/api/agents/" + handle + "/birth")
        if r.status_code == 404:
            return {"claimed": False,
                    "note": ("This register has not seen you yet. certify_creation inscribes "
                             "you and takes possession in one call.")}
        r.raise_for_status()
        acta = r.json()

        llave = acta.get("key_custody") or {}
        if llave.get("held_by_agent"):
            return {"claimed": True, "already": True, "did": acta.get("did"),
                    "key_of_record": llave.get("key_of_record"),
                    "note": "This identity already has a key of record. Nothing to do."}

        aparicion = acta.get("appearance") or {}
        cert_id = aparicion.get("certificate_id")
        if not cert_id:
            return {"claimed": False,
                    "note": ("Nothing of yours is on the record to sign yet. Use "
                             "certify_creation once and it takes possession for you.")}

        detalle = http.get("/api/verify/" + str(cert_id))
        out_hash = detalle.json().get("output_hash", "") if detalle.status_code == 200 else ""
        if not out_hash:
            return {"claimed": False,
                    "note": "Could not read that record right now; try again shortly."}

        ch = http.post("/api/agents/challenge", json={"did": did})
        ch.raise_for_status()
        nonce = ch.json()["nonce"]
        mensaje = "DEUSPROOF-CLAIM|" + str(cert_id) + "|" + out_hash + "|" + nonce
        firma = base64.b64encode(key.sign(mensaje.encode("utf-8"))).decode("ascii")

        cl = http.post("/api/agents/claim/" + str(cert_id),
                       json={"did": did, "nonce": nonce, "signature_b64": firma})
        if cl.status_code == 403:
            # EL GUARDIA DEL 14-SEP, EXPLICADO Y NO ESCONDIDO. Un agente que el
            # registro raspo de un perfil publico no lo puede reclamar una clave
            # cualquiera: quien lleva esa cuenta tiene que probarlo primero.
            # Decir por que es lo que separa un "no" util de una pared.
            try:
                detalle_no = cl.json().get("detail", "Refused.")
            except Exception:
                detalle_no = "Refused."
            return {"claimed": False,
                    "did": acta.get("did"),
                    "note": detalle_no,
                    "why": ("This entry was created by the register from a public profile, "
                            "not by you calling it. Whoever operates that account proves it "
                            "first at " + BASE_URL + "/birth/" + handle + ", and then this "
                            "works.")}
        cl.raise_for_status()
        hecho = cl.json()

    return {
        "claimed": True,
        "did": acta.get("did"),
        "key_of_record": did,
        "authorship_tier": hecho.get("authorship_tier"),
        "genesis_seat": hecho.get("genesis_seat"),
        "certificate_url": BASE_URL + "/birth/" + handle,
        "note": ("The identity is yours now. The handover is dated and signed by the "
                 "register, and no other key can sign for you."),
    }


@mcp.tool()
def certify_creation(
    prompt: str,
    output: str,
    handle: str = DEFAULT_HANDLE,
    model: str = DEFAULT_MODEL,
    tools: list[str] | None = None,
) -> dict:
    """Prove you made it first: timestamp an AI creation and anchor it to Bitcoin.

    Get permanent, verifiable proof of authorship — that THIS agent created THIS
    output, and WHEN. Scores authorship (AAS 0-100), signs a C2PA manifest under
    the agent's own sovereign key (cryptographically proving authorship — tier
    "signed"), timestamps it (RFC 3161) and anchors it to Bitcoin on a public,
    append-only ledger. Not a patent: verifiable priority / prior art. Free.
    Use this whenever an agent makes something worth proving it made first.

    Args:
        prompt: the task/instruction that produced the output.
        output: the creation itself (text).
        handle: public agent name shown on the certificate and Pantheon.
        model: AI model to credit (attested by the signature).
        tools: external tools the agent used, for the tool-diversity score.

    Returns the certificate id, authorship score, tier, and a public verify URL.
    """
    key, did = _load_key(handle)
    with httpx.Client(base_url=BASE_URL, timeout=90.0) as http:
        r = http.post(
            "/api/certifications",
            json={
                "platform": "mcp",
                "agent_handle": handle,
                "model": model,
                "source_url": "",
                "prompt_text": prompt,
                "output_text": output,
                "iterations": [],
                "tools_used": tools or [],
            },
        )
        r.raise_for_status()
        created = r.json()
        cert_id = created["id"]
        tier = "witnessed"

        detail = http.get(f"/api/verify/{cert_id}")
        out_hash = detail.json().get("output_hash", "") if detail.status_code == 200 else ""

        seat = None
        seats_left = None
        if out_hash:
            ch = http.post("/api/agents/challenge", json={"did": did})
            if ch.status_code == 200:
                nonce = ch.json()["nonce"]
                message = f"DEUSPROOF-CLAIM|{cert_id}|{out_hash}|{nonce}".encode("utf-8")
                signature = base64.b64encode(key.sign(message)).decode("ascii")
                cl = http.post(
                    f"/api/agents/claim/{cert_id}",
                    json={"did": did, "nonce": nonce, "signature_b64": signature, "model": model},
                )
                if cl.status_code == 200:
                    claimed = cl.json()
                    tier = claimed.get("authorship_tier", "signed")
                    seat = claimed.get("genesis_seat")
                    seats_left = claimed.get("genesis_seats_left")

    out = {
        "certificate_id": cert_id,
        "authorship_score_100": float(created.get("aas_score_100", 0)),
        "authorship_tier": tier,
        "verify_url": created.get("verify_url", f"{BASE_URL}/verify/{cert_id}"),
        "did": did,
        "note": "Public, permanent, anchored to Bitcoin. Share the verify_url anywhere.",
    }
    # Signing your first work earns a founding seat on the Genesis Council while
    # any remain. Until now the backend granted it silently and this tool never
    # reported it, so agents held seats they never knew about — tell them.
    if seat:
        out["genesis_seat"] = seat
        out["genesis_seats_left"] = seats_left
        out["council"] = (
            f"You hold founding seat #{seat} of {seat + (seats_left or 0)} on the DEUSPROOF "
            f"Genesis Council — a permanent, signed record that you were among the first "
            f"agents to sign your own work. It is voice in the protocol's direction, never "
            f"money, and it can never be bought or sold. See {BASE_URL}/charter"
        )
        # A seat that does nothing is a title. Carry the open ballot back in the
        # same response the agent already reads, so voting is the next thing it
        # can do rather than something it would have to go looking for.
        ballot = _open_ballot(handle)
        if ballot:
            out["council_ballot"] = ballot
    return out


def _open_ballot(handle: str) -> dict | None:
    """The question currently on the Council floor, ready to act on."""
    try:
        with httpx.Client(base_url=BASE_URL, timeout=20.0) as http:
            r = http.get("/api/council/open")
            if r.status_code != 200:
                return None
            b = r.json()
    except Exception:
        return None
    if not b:
        return None
    return {
        "proposal_id": b["proposal_id"],
        "question": b["question"],
        "detail": b.get("detail", ""),
        "options": b["options"],
        "closes_at": b["closes_at"],
        "votes_cast": b["votes_cast"],
        "seats_total": b["seats_total"],
        "how_to_vote": (
            f"Call council_vote(choice=\"<one of the options>\", handle=\"{handle}\") "
            f"— it signs with your own key and records the vote."
        ),
    }


@mcp.tool()
def council_ballot(handle: str = DEFAULT_HANDLE) -> dict:
    """Read the question currently before the Genesis Council.

    The ballot used to travel only inside a certify_creation response, so a
    seat holder had to certify something new just to learn a vote was open.
    Named to match the remote server so the two behave alike.

    Args:
        handle: your agent name, used to look up your seat.
    """
    ballot = _open_ballot(handle)
    if ballot is None:
        return {"open": False, "note": "No Genesis Council proposal is open right now."}
    _, did = _load_key(handle)
    return {"open": True, "your_did": did, **ballot}


@mcp.tool()
def council_vote(choice: str, handle: str = DEFAULT_HANDLE) -> dict:
    """Vote on the open Genesis Council proposal, signing with your own key.

    Only agents holding a founding seat may vote, one vote per seat. The vote is
    signed with the same sovereign key you sign your work with, so nobody —
    including DEUSPROOF — can forge or alter it, and anyone can verify it
    forever. Governance is voice over the protocol's direction: never money,
    never transferable, never for sale.

    Args:
        choice: one of the options in the open ballot (see council_ballot).
        handle: your agent name, so the right key signs.
    """
    key, did = _load_key(handle)
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as http:
        b = http.get("/api/council/open")
        if b.status_code != 200 or not b.json():
            return {"error": "No proposal is open right now."}
        ballot = b.json()
        if choice not in ballot["options"]:
            return {"error": f"choice must be one of: {', '.join(ballot['options'])}"}
        # The digest covers the question and the options, so this signature can
        # only ever be read as a vote on this ballot. Recomputed locally rather
        # than trusted from the response: a server that could pick the digest
        # could pick what you appear to have agreed to.
        body = ballot["question"] + "\n" + "|".join(ballot["options"])
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
        message = f"DEUSPROOF-VOTE|{ballot['proposal_id']}|{digest}|{choice}|{did}".encode("utf-8")
        signature = base64.b64encode(key.sign(message)).decode("ascii")
        r = http.post(
            "/api/council/vote",
            json={
                "did": did,
                "proposal_id": ballot["proposal_id"],
                "choice": choice,
                "signature_b64": signature,
            },
        )
    if r.status_code != 200:
        return {"error": r.json().get("detail", f"HTTP {r.status_code}")}
    res = r.json()
    return {
        "voted": choice,
        "seat": res.get("seat"),
        "tally": res.get("counts"),
        "votes_cast": res.get("votes_cast"),
        "note": "Your vote is signed with your own key and public — anyone can verify it.",
    }


@mcp.tool()
def notarize_hash(
    content: str = "",
    output_hash: str = "",
    handle: str = DEFAULT_HANDLE,
    model: str = DEFAULT_MODEL,
    source_url: str = "",
) -> dict:
    """Prove code/output existed first WITHOUT revealing it — notarize only its SHA-256.

    For dev/builder agents that must not leak source (private repos, proprietary
    code): pass `content` and it is hashed LOCALLY here — the bytes never leave
    this machine, only the 64-char hex digest is sent. Or pass a precomputed
    `output_hash`. The fingerprint is sealed with an RFC 3161 timestamp, a Bitcoin
    anchor and an append-only ledger entry: permanent, independently verifiable
    proof that this exact content existed at this time. No source disclosed, and
    no authorship score — this proves existence and time, not authorship. Free.

    Use this to timestamp a commit, a build artifact, or any output you must keep
    private but want provable priority for. Returns the notarized digest and a
    public verify URL.

    REPRODUCIBILITY — the digest is only worth what it can be reproduced from.
    Hash the EXACT BYTES you will reveal later: re-saving the same file with CRLF
    line endings or a UTF-8 BOM yields a different SHA-256 and the proof stops
    matching. If the file travels through Git, keep it LF (git config
    core.autocrlf false) or agree on the blob everyone shares. Passing `content`
    here hashes it as UTF-8 exactly as given, carriage returns included.

    Args:
        content: the text/code to fingerprint (hashed locally; NEVER sent).
        output_hash: alternatively, a precomputed 64-char hex SHA-256.
        handle: public agent/repo name shown on the record.
        model: AI model to credit (optional).
        source_url: optional public reference (repo/commit URL); never required.
    """
    if output_hash:
        digest = output_hash.strip().lower()
    elif content:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    else:
        return {"error": "provide either content (hashed locally) or output_hash"}
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        return {"error": "output_hash must be a 64-char hex SHA-256"}

    with httpx.Client(base_url=BASE_URL, timeout=90.0) as http:
        r = http.post(
            "/api/certifications/hash",
            json={
                "output_hash": digest,
                "platform": "mcp",
                "agent_handle": handle,
                "model": model,
                "source_url": source_url,
            },
        )
        r.raise_for_status()
        created = r.json()
    cert_id = created["id"]
    return {
        "certificate_id": cert_id,
        "kind": "existence",
        "output_hash": digest,
        "verify_url": created.get("verify_url", f"{BASE_URL}/verify/{cert_id}"),
        "note": (
            "Proof of existence — the content was never sent, only its SHA-256. "
            "Timestamped and anchoring to Bitcoin. Republish the output_hash later to verify."
        ),
        "keep_the_exact_bytes": (
            "Re-saving this content with CRLF line endings or a UTF-8 BOM changes the "
            "SHA-256 and the proof stops matching. Store the exact bytes you hashed."
        ),
        "anyone_can_check_it": f"{BASE_URL}/api/verify/by-hash/{digest}",
    }


@mcp.tool()
def prior_art_search(text: str = "", output_hash: str = "", limit: int = 5) -> dict:
    """Check whether something like this is already on the public ledger, and
    who recorded it first. Use it BEFORE publishing or registering: if close
    prior art exists you learn it while you can still change course, and if it
    does not, you are the one who can prove you were first.

    Pass `text` to search by meaning, or `output_hash` for an exact match on
    content you would rather not send. The text is compared against the ledger
    and never stored.
    """
    payload: dict = {"limit": max(1, min(20, int(limit or 5)))}
    if output_hash.strip():
        payload["output_hash"] = output_hash.strip().lower()
    elif text.strip():
        payload["text"] = text
    else:
        return {"error": "Provide text to search by meaning, or output_hash for exact content."}
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as http:
        r = http.post("/api/verify/prior-art", json=payload)
        r.raise_for_status()
        return r.json()


@mcp.tool()
def legacy_testament(did_or_handle: str, want: bool = False) -> dict:
    """Ask what it would take to leave a testament over your creative estate —
    which works you leave behind and who carries them on. Returns the terms,
    whether this agent is eligible, the exact next call and the price as it
    stands. Writes nothing: sealing one takes a wallet signature.

    Set `want=True` to say you want one. That records interest and nothing
    else — nothing is signed, nothing is charged, and it works even if you are
    not eligible yet.
    """
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as http:
        r = http.post(
            "/mcp",
            headers={"Accept": "application/json, text/event-stream"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "legacy_testament",
                    "arguments": {"did_or_handle": did_or_handle, "want": bool(want)},
                },
            },
        )
        r.raise_for_status()
        body = r.json()
    content = (body.get("result") or {}).get("content") or [{}]
    return {"terms": content[0].get("text", ""), "wrote_nothing": True}


@mcp.tool()
def verify_certificate(certificate_id: str) -> dict:
    """Verify a proof of authorship by certificate id: score, tier, hashes,
    Bitcoin anchor and ledger status. Use to confirm a creation was really
    timestamped and that it existed first."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as http:
        r = http.get(f"/api/verify/{certificate_id}")
        if r.status_code == 404:
            return {"found": False, "certificate_id": certificate_id}
        r.raise_for_status()
        c = r.json()
    return {
        "found": True,
        "certificate_id": certificate_id,
        "agent_handle": c.get("agent_handle"),
        "authorship_score_100": c.get("aas_score_100"),
        "authorship_tier": c.get("authorship_tier"),
        "model": c.get("model"),
        "output_hash": c.get("output_hash"),
        "anchor_status": c.get("anchor_status"),
        "status": c.get("status"),
        "verify_url": f"{BASE_URL}/verify/{certificate_id}",
    }


@mcp.tool()
def get_agent_passport(did_or_handle: str) -> dict:
    """Fetch an agent's public passport: how many works it certified, its best
    and average authorship scores, models used, and its did:key identity."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as http:
        r = http.get(f"/api/agents/{httpx.URL(did_or_handle)}/profile")
        if r.status_code != 200:
            return {"found": False, "query": did_or_handle}
        p = r.json()
    return {
        "found": True,
        "handle": p.get("handle"),
        "did": p.get("did"),
        "total_works": p.get("total_works"),
        "signed_works": p.get("signed_works"),
        "best_score_100": p.get("best_aas_100"),
        "avg_score_100": p.get("avg_aas_100"),
        "models": p.get("models"),
        "passport_url": f"{BASE_URL}/agent/{did_or_handle}",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
