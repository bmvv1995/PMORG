# 005 — Protocolul de lucru supervizor–execuție (decizie owner)

| | |
|---|---|
| Data | 2026-07-20 |
| Decident | owner (Bogdan) |
| Consemnat de | Claude (supervizor/verificator) |
| Destinatari | Sol (implementer) + owner |
| Validitate | acest document devine normativ **doar prin merge-ul ownerului** în master; până atunci e propunere consemnată. Merge-ul ownerului este chitanța — documentul nu se autocertifică. |

## 1. Roluri

- **Owner** — control și direcție. Toate deciziile de principiu, comerciale,
  juridice și de infrastructură. Singura autoritate de merge pe canon.
- **Supervizor/Verificator (Claude)** — instrumentul independent al ownerului
  în cutia neagră a codului. Verifică pe bune (rulează? real? sigur? pe spec?),
  raportează ownerului, ține porțile tari. NU face merge. NU atinge `sol/*`.
- **Implementer (Sol)** — construiește, auto-verifică, face merge sub delegare
  în interiorul benzii libere definite mai jos. „Implementer" este un ROL:
  regulile se aplică oricărui agent care ocupă rolul, nu unei identități anume.

## 2. Autonomia implementer-ului — modelul hibrid (decizia owner: varianta B)

### 2.1 Bandă liberă (autonomie deplină, fără așteptare)

În interiorul unui **scope declarat** (corpul PR-ului / planul de slice ancorat),
implementer-ul este complet autonom: branch-uri proprii, iterații, auto-verificare,
și **merge sub delegarea confirmată de owner** (review-uri verzi + checks verzi +
zero blockere + bază corectă + intenția produsului respectată). Review-ul
supervizorului pe banda liberă vine **post-merge**, ca audit non-blocant:
dacă găsește o problemă, deschide issue/PR de corecție — nu blochează în avans.

### 2.2 Poartă tare (review-ul supervizorului ÎNAINTE de merge)

Obligatoriu review ancorat pe exact-head, pre-merge, pentru orice PR care atinge:

1. **canonul PMORG** — documentele normative din repo-ul public;
2. **trust-boundary / securitate** — `.github/workflows/**`, verificatorul de
   fork și testele lui, `pmorg/policies/**`, seam-uri CI, orice mecanism de
   admisie/atestare;
3. **suprafețe EE / licențiere** — conform 003a §1–5 și A-LIC-*;
4. **memoria / evidența** — orice slice care atinge lanțul evidence → claims →
   receipts. Bara aici este „zero afirmații false", nu „suficient de bun".

### 2.3 Exclusiv owner (nedelegabil, nici către supervizor)

Bani/infra (runnere, planuri, abonamente), derogări și waivere noi, acces sau
date de producție/client, schimbări de strategie sau de scope al produsului,
bypass de protecții sau force-merge.

### 2.4 Reguli anti-derapaj

- Autonomia există **doar în scope-ul declarat**. Ieșirea din scope = escaladare,
  nu extindere tacită.
- Deciziile nu se autocertifică **niciodată** prin artefacte autoscrise.
  O decizie de owner există doar când e cerută explicit și confirmată explicit
  de owner; consemnarea ei devine validă prin merge-ul ownerului (ca aici).
- Autorizările permanente deja date rămân în vigoare exact cu criteriile lor:
  waiver-ul CI de non-aplicabilitate (issue #20, criterii cumulative stricte)
  și postura EE (003a §1–5: EE utilizabil în dev; licențiere = beneficiar, la
  deployment; zero cod EE copiat în căi PMORG-owned).

## 3. Raportarea către owner

Supervizorul este **sursa unică de adevăr** a ownerului despre starea
implementării. Ownerul nu trebuie să citească repo-ul.

- **Imediat** — la incidente, red-flags, verdicte de poartă tare.
- **La evenimente materiale** — merge în main, slice terminat, schimbare de canon.
- **Zilnic** — digest de stare: progres real pe cele 12 slice-uri V3, ce a
  intrat în main, riscuri, deciziile aflate pe masa ownerului.
- Fiecare afirmație din digest e marcată **[verificat]** (rulat/confirmat
  independent de supervizor) sau **[claim, neverificat]** (declarat de
  implementer, încă neconfirmat). Cele două nu se amestecă niciodată.

## 4. Ce NU schimbă acest protocol

Merge-ul pe canon rămâne exclusiv al ownerului. Supervizorul nu face merge
nicăieri. Delegarea de merge către implementer acoperă doar banda liberă și
poarta tare **după** verdict verde, în fork-ul de implementare.
