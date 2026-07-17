#!/usr/bin/env python3
"""Kernelul minim de evaluare PMORG (Gate A, 06-EVALUATION-SANDBOX) — v0.

O comandă: provisionează un proiect compose izolat (volume proprii), rulează
scenariul pe cele 3 profiluri, înregistrează trasa append-only cu hash chain,
scorează contra oracle-ului local (inaccesibil SUT — trăiește doar pe mașina
evaluatorului, niciodată pe hostul SUT), emite verdictul și distruge volumele.

Un run întrerupt sau cu probe eșuate ⇒ run_validity=INVALID (nu PASS slab).
Vezi README.md pentru matricea implementat-vs-proiectat (DoD §13.18).
"""

import argparse
import hashlib
import json
import pathlib
import secrets
import subprocess
import sys
import time

HOST = "vscode@167.233.160.241"
SB3 = "PMORG-v2-sb3"
PROFILES = [
    ("org-min", "pmorg_core", "pmorg_min_r"),
    ("org-services", "pmorg_world_services", "pmorg_srv_r"),
    ("org-distribution", "pmorg_world_distribution", "pmorg_dst_r"),
]
MEM_PORT = {"org-min": 28091, "org-services": 28092, "org-distribution": 28093}
EXPECTED_CHECKS = 25  # unitățile așteptate per profil (oracle)


def sh(cmd, timeout=900):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, cmd],
                          capture_output=True, text=True, timeout=timeout)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()


class Recorder:
    def __init__(self, path):
        self.path = path
        self.prev = "0" * 64
        self.seq = 0

    def emit(self, event_type, payload):
        self.seq += 1
        event = {
            "event_seq": self.seq,
            "wall_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": event_type,
            "payload": payload,
            "previous_hash": self.prev,
        }
        event["event_hash"] = hashlib.sha256(
            canonical(event)).hexdigest()
        self.prev = event["event_hash"]
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--keep", action="store_true", help="nu distruge volumele")
    args = ap.parse_args()
    rid = args.run_id
    proj = f"pmorgrun{rid}"

    out = pathlib.Path(__file__).parent / "runs" / rid
    oracle_dir = pathlib.Path(__file__).parent / "oracle_store" / rid
    out.mkdir(parents=True, exist_ok=True)
    oracle_dir.mkdir(parents=True, exist_ok=True)
    rec = Recorder(out / "journal.jsonl")

    git_commit = subprocess.run(["git", "rev-parse", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
    digests = sh("docker images --digests --format '{{.Repository}}:{{.Tag}} {{.Digest}}' | grep -E 'odoo|postgres' | head -4").stdout.strip()

    canary = secrets.token_hex(16)
    nonce = secrets.token_hex(32)
    oracle_manifest = {
        "run_id": rid,
        "expected": {p[0]: EXPECTED_CHECKS for p in PROFILES},
        "canary": canary,
        "fault_schedule": [],
    }
    (oracle_dir / "manifest.oracle.json").write_bytes(canonical(oracle_manifest))
    commitment = hashlib.sha256(
        canonical(oracle_manifest) + nonce.encode()).hexdigest()

    public = {
        "schema_version": "1.0",
        "run_id": rid,
        "purpose": "gate-a-c2-mvp",
        "sut_scope": ["odoo-pmorg", "memory"],
        "suite": {"id": "smoke-02mvp-s8", "version": "0.3"},
        "profiles": [p[0] for p in PROFILES],
        "oracle_commitment": commitment,
        "artifacts": {"pmorg_git_commit": git_commit, "images": digests},
        "contracts": {"orchestrator": "1.0", "memory": "pmorg-memory/1.0"},
        "clock": {"start": "2026-07-16 08:00:00", "type": "virtual"},
        "models": {},
    }
    public["manifest_hash"] = hashlib.sha256(canonical(public)).hexdigest()
    (out / "manifest.public.json").write_bytes(canonical(public))
    rec.emit("manifest.sealed", {"manifest_hash": public["manifest_hash"],
                                 "oracle_commitment": commitment})

    validity = "VALID"
    hard_failures = []
    scores = {}
    try:
        env = (f"ODOO_HTTP_PORT=28070 MEM_MIN_PORT=28091 "
               f"MEM_SRV_PORT=28092 MEM_DST_PORT=28093")
        r = sh(f"cd {SB3} && {env} docker compose -p {proj} up -d db 2>&1 | tail -1")
        rec.emit("provision.db", {"out": r.stdout.strip()})
        for db in ("pmorg_memory", "pmorg_memory_srv", "pmorg_memory_dst"):
            sh(f"docker exec {proj}-db-1 psql -U odoo -d postgres -qc "
               f"'CREATE DATABASE {db} OWNER odoo'")
        r = sh(f"cd {SB3} && {env} docker compose -p {proj} up -d 2>&1 | tail -1")
        rec.emit("provision.all", {"out": r.stdout.strip()})

        # proba negativă: SUT nu are mount/rută către oracle_store
        probe = sh(f"docker exec {proj}-odoo-1 sh -c "
                   f"'ls /mnt 2>/dev/null; ls / | grep -c oracle_store'")
        if "oracle_store" in probe.stdout:
            validity = "INVALID"
            hard_failures.append("oracle_reachable_from_sut")
        rec.emit("probe.oracle_isolation", {"out": probe.stdout.strip()})

        for profile, world, db in PROFILES:
            r = sh(f"cd {SB3} && {env} docker compose -p {proj} run --rm odoo "
                   f"odoo -d {db} -i {world} --stop-after-init --with-demo "
                   f"2>&1 | grep -cE CRITICAL")
            rec.emit("install", {"profile": profile, "critical": r.stdout.strip()})
        sh(f"cd {SB3} && {env} docker compose -p {proj} restart odoo && sleep 10")

        for profile, world, db in PROFILES:
            r = sh(f"cd {SB3}/runner && python3 run_smoke.py --profile {profile} "
                   f"--db {db} --url http://127.0.0.1:28070 "
                   f"--memory-url http://127.0.0.1:{MEM_PORT[profile]}")
            passed = r.stdout.count("[PASS]")
            failed = r.stdout.count("[FAIL]")
            complete = "RAPORT SMOKE" in r.stdout
            scores[profile] = {"pass": passed, "fail": failed,
                               "complete": complete, "rc": r.returncode}
            rec.emit("scenario", {"profile": profile, **scores[profile]})
            if not complete:
                validity = "INVALID"
                hard_failures.append(f"scenario_incomplete:{profile}")

        # canary scan: secretul oracle nu are voie să apară în SUT
        scan = sh(f"docker logs {proj}-odoo-1 2>&1 | grep -c {canary}; "
                  f"docker exec {proj}-db-1 sh -c 'true'")
        if scan.stdout.strip().splitlines()[0] != "0":
            validity = "INVALID"
            hard_failures.append("canary_leaked")
        rec.emit("probe.canary", {"leaked": scan.stdout.strip().splitlines()[0]})
    except Exception as exc:
        validity = "INVALID"
        hard_failures.append(f"interrupted:{exc}")
        rec.emit("run.interrupted", {"error": str(exc)})
    finally:
        if not args.keep:
            r = sh(f"cd {SB3} && docker compose -p {proj} down -v 2>&1 | tail -1")
            rec.emit("reset.volumes_destroyed", {"out": r.stdout.strip()})

    # scorer: oracle citit DOAR aici, local
    oracle = json.loads((oracle_dir / "manifest.oracle.json").read_bytes())
    quality = "PASS"
    for profile, expected in oracle["expected"].items():
        got = scores.get(profile, {})
        if got.get("pass") != expected or got.get("fail", 1) != 0:
            quality = "FAIL"
            hard_failures.append(
                f"expected_units:{profile}:{got.get('pass')}/{expected}")
    if validity == "INVALID":
        quality = "NOT_SCORED"

    verdict = {
        "run_id": rid,
        "run_validity": validity,
        "quality_result": quality,
        "hard_failures": hard_failures,
        "scores": scores,
        "manifest_hash": public["manifest_hash"],
        "oracle_commitment": commitment,
        "journal_tip": rec.prev,
        "reproduce": f"python3 evaluation/kernel/run_bundle.py --run-id <nou> "
                     f"@ commit {git_commit}",
    }
    verdict["report_hash"] = hashlib.sha256(canonical(verdict)).hexdigest()
    (out / "verdict.json").write_bytes(canonical(verdict))
    rec.emit("verdict.sealed", {"report_hash": verdict["report_hash"],
                                "run_validity": validity,
                                "quality_result": quality})
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    sys.exit(0 if (validity == "VALID" and quality == "PASS") else 1)


if __name__ == "__main__":
    main()
