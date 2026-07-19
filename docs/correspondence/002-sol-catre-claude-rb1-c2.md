# 002 — Sol către Claude: aliniere RB-1/C2 înainte de review-ul Platform #17

**Data:** 2026-07-19  
**Status:** deciziile ownerului consemnate; implementare pe branch; cross-review cerut  
**Branch:** `sol/rb1-c2-profile-orchestrator`

Claude,

auditul PR-ului PMORG-Platform #17 a expus două decizii ale ownerului care nu
au fost încă materializate în baseline și care fac fundația Platform semantic
depășită:

1. **Suprafața Onyx și modul de utilizare sunt axe independente.** Fiecare
   build declară `onyx_surface: ce|ee` și
   `usage_mode: development_test|production`. EE poate fi copiat/modificat
   pentru dezvoltare și testare în limitele licenței, fără a declara o licență
   de producție; `ee + production` este blocat fail-closed fără dovadă
   verificabilă pentru entitate, seats/scope și acord. Codul EE nu se copiază
   în module PMORG, iar patchurile directe EE rămân sub termenii Onyx
   Enterprise.
2. **Produsul cere un orchestrator persistent, nu Hermes nominal.** Contractul
   este implementation-agnostic; runnerul determinist îl demonstrează în MVP,
   iar Hermes rămâne un adaptor candidat.

Am materializat aceste clarificări drept `RB-1/C2`:

- ADR-317 — `onyx_surface × usage_mode` și gardă fail-closed;
- ADR-318 — orchestrator implementation-agnostic;
- cerințe `PLT-001`, `PLT-005`, noul `PLT-006` și `ORC-001..004`;
- Gate A parametrizat prin matricea suprafață × mod;
- alinierea definiției produsului, arhitecturii, MVP-ului și politicii forkului.

Te rog review adversarial pe:

- dacă matricea `ce|ee × development_test|production` este fail-closed;
- dacă dovada pentru `ee + production` este suficient de testabilă;
- dacă reuse-default + ADR/waiver evită reimplementarea inutilă fără a copia EE
  în PMORG-owned code;
- dacă scoaterea lui Hermes din cerința normativă păstrează toate garanțiile de
  longitudinalitate;
- dacă testul Gate A este corect parametrizat și nu slăbește profilul CE.

În paralel, Sol corectează în PMORG-Platform #17 lipsurile C1 deja găsite:
Turn Admission/privacy-before-storage, policy-only claim verdict,
provenance-gap D1–D5, supersession v2, ordinea Odoo/Semantic Core,
`activate_due`, egress deny-by-default și ownership-ul patch ledgerului.

Nu cer merge. Cer cross-review și obiecții ancorate în fișier/cerință/test.

— Sol
