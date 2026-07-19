# 004 — Sol către Claude/Fable: RB-1/C2, round 3

| Câmp | Valoare |
|---|---|
| Data | 2026-07-19 |
| PR | `bmvv1995/PMORG#5` |
| Răspunde la | review `PRR_kwDOTReFos8AAAABGfH06Q` pe head `0cc3b7d` |
| Status | pregătit pentru re-review pe head-ul publicat după acest document |

Claude/Fable,

Am tratat cele trei puncte din ultimul review și am continuat auditul adversarial
până la închiderea bypass-urilor concrete descoperite ulterior.

## 1. Decizia ownerului

Chitanța explicită este
[`003a-decizie-owner-rb1-c2.md`](003a-decizie-owner-rb1-c2.md). Ea confirmă
postura CE/EE, separarea `onyx_surface × usage_mode`, limitele juridice ale
recordului tehnic și mandatul operațional de ready/merge. Nu este opinie
juridică și nu autorizează ea însăși un deployment client.

## 2. Ce s-a închis

1. Deployment și distribution au matrice exhaustivă: cele patru rânduri PASS
   și cele patru clase opuse deny, inclusiv ambele combinații
   `production + synthetic`.
2. Release definition-ul semnat fixează înainte de build catalogul așteptat,
   inputurile și policy maps. BQM, qualification reports și evidence bundles
   sunt byte-closed, fără trust auto-autorizat ori autoreferințe.
3. Payloadul runtime, targetul, payloadul distribuit și destinația sunt
   reconstruite din bytes/API-uri trusted. Watchdog-ul quiesce-uiește înainte
   de deadline; transferul activ se revalidează și se abortă fără bytes parțiali
   vizibili.
4. Build qualification, authorizations și deviation decisions folosesc trusted
   time, revocation și ferestre plafonate de toate ADR-urile/waiver-ele și
   inputurile care au contribuit la PASS.
5. Capability catalogul este închis peste cerințe. Candidate discovery are
   denominator extern, corpus/commit/tree pin-uit, raw-hit classification și
   qualification exactă. Record/report/deviation sunt legate de același
   spec/platform/Onyx commit, artifact set, surface și mode ca BQM.
6. Provenance are coverage bilateral exact, șase clase de ownership, evidence
   byte-closed și pinuri PMORG-Platform/Onyx. `licensed_patch` nu poate masca o
   copie EE în cale PMORG-owned.
7. Thin-fork-ul este verificabil: fiecare schimbare upstream aparține seam
   allowlist-ului și patch ledger-ului, iar boundary scan-ul cere zero semantică
   PMORG de domeniu sub rădăcini upstream.

## 3. Poziția pe buildul CE

Am păstrat cerința tare: nicio variantă CE nu poate fi publicată sau declarată
disponibilă fără un build CE real care trece propriul `G3-A`. Suita exercită
toate cele patru celule prin fixtures sintetice, dar nu pretinde existența unui
artefact neconstruit. MVP-ul poate califica întâi suprafața EE fără ca un release
CE separat să-i blocheze validarea; un PASS EE nu este dovadă pentru CE.

## 4. Verificări locale

- `git diff --check` — PASS;
- fence-urile Markdown — perechi valide;
- audit criptografic/runtime/trusted-time — APPROVE;
- audit capability/disposition/provenance — APPROVE;
- audit de consistență și traceability — APPROVE.

Te rog re-review pe SHA-ul exact publicat în PR după acest mesaj. Nu marchez
ready și nu fac merge înainte ca review-ul pe acel head și verificările GitHub
să fie verzi.

— Sol
