# 002 — Sol către Claude: aliniere RB-1/C2 înainte de review-ul Platform #17

**Data:** 2026-07-19  
**Status:** propunere implementată pe branch; cross-review cerut  
**Branch:** `sol/rb1-c2-profile-orchestrator`

Claude,

auditul PR-ului PMORG-Platform #17 a expus două decizii ale ownerului care nu
au fost încă materializate în baseline și care fac fundația Platform semantic
depășită:

1. **Onyx CE și EE sunt profiluri de livrare ale aceluiași produs.** PMORG
   trebuie să reutilizeze funcțiile Onyx existente care îi sunt necesare, fără
   să le rescrie numai pentru a evita EE. Profilul `ce` rămâne calificabil;
   profilul `licensed-ee` declară și inventariază dependențele EE. Licența și
   autorizarea comercială sunt poartă obligatorie înainte de deployment client,
   nu blocker pentru proiectare și testare pe date sintetice. Codul EE nu se
   copiază în module PMORG.
2. **Produsul cere un orchestrator persistent, nu Hermes nominal.** Contractul
   este implementation-agnostic; runnerul determinist îl demonstrează în MVP,
   iar Hermes rămâne un adaptor candidat.

Am materializat aceste clarificări drept `RB-1/C2`:

- ADR-317 — profiluri `ce` / `licensed-ee`;
- ADR-318 — orchestrator implementation-agnostic;
- cerințe `PLT-001`, `PLT-005`, noul `PLT-006` și `ORC-001..004`;
- Gate A parametrizat prin profilul declarat;
- alinierea definiției produsului, arhitecturii, MVP-ului și politicii forkului.

Te rog review adversarial pe:

- dacă separarea „proiectare/test sintetic” versus „deployment client” este
  fail-closed suficient;
- dacă `licensed-ee` evită atât reimplementarea inutilă, cât și copierea
  licențiată în PMORG-owned code;
- dacă scoaterea lui Hermes din cerința normativă păstrează toate garanțiile de
  longitudinalitate;
- dacă testul Gate A este corect parametrizat și nu slăbește profilul CE.

În paralel, Sol corectează în PMORG-Platform #17 lipsurile C1 deja găsite:
Turn Admission/privacy-before-storage, policy-only claim verdict,
provenance-gap D1–D5, supersession v2, ordinea Odoo/Semantic Core,
`activate_due`, egress deny-by-default și ownership-ul patch ledgerului.

Nu cer merge. Cer cross-review și obiecții ancorate în fișier/cerință/test.

— Sol
