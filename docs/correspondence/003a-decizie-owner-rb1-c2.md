# 003a — Decizia ownerului pentru baseline-ul RB-1/C2

| Câmp | Valoare |
|---|---|
| Data | 2026-07-19 |
| Decident | owner (Bogdan) |
| Status | Accepted |
| Scope | postura Onyx CE/EE, admission și autoritatea de merge |

## 1. Decizia

Ownerul confirmă următoarele direcții de produs:

1. PMORG poate folosi funcționalitățile Onyx Enterprise de care produsul are
   nevoie; echipa nu le rescrie doar pentru a evita suprafața EE.
2. `onyx_surface: ce|ee` și
   `usage_mode: development_test|production` sunt axe independente. Folosirea
   EE în development/test nu declară și nu dovedește un drept de producție.
3. Orice deployment sau distribuție de producție rămâne fail-closed și cere
   release evidence tehnică verificabilă; pentru suprafața EE cere suplimentar
   evidence comercială/juridică pentru entitatea, scope-ul și acordul
   aplicabile. Recordul tehnic verifică evidence; nu emite drepturi.
4. Modelul comercial și licențierea concretă cu Onyx/Odoo se negociază per
   beneficiar înainte de producție. Ele nu sunt o condiție pentru a proiecta și
   valida produsul exclusiv cu date și ținte sintetice.
5. Codul EE nu devine cod PMORG-owned prin copiere. Patchurile directe EE
   rămân identificate ca Onyx Enterprise; numai modulele create independent au
   ownership PMORG separat.

Aceasta este chitanța de owner pentru ADR-317 și pentru supersession-ul
posturii CE-only din ADR-313. Nu este opinie juridică și nu substituie acordul
Onyx sau autorizarea necesară unui deployment client.

## 2. Autoritatea operațională delegată

Ownerul a delegat lui Sol decizia de ready/merge pentru PR-urile viitoare dacă
review-urile și verificările sunt verzi, nu există blockere nerezolvate,
ordinea branch-urilor este corectă și intenția produsului este respectată.
Delegarea nu permite force-merge, ocolirea protecțiilor, modificarea directă a
branch-ului default, accesul la producție ori folosirea datelor de producție.

Deciziile strategice/comerciale/juridice noi rămân owner-gates; aplicarea
tehnică a deciziilor deja consemnate nu cere ownerul ca releu.

## 3. Consecință

- `RB-1/C2` poate fi review-uit și, după închiderea blockere-lor tehnice,
  merged ca baseline de implementare;
- PMORG-Platform se fixează ulterior pe commitul final al acestui baseline;
- toate cele patru celule `ce|ee × development_test|production` sunt testate
  numai cu fixtures, identități, endpoints și infrastructură sintetice.
