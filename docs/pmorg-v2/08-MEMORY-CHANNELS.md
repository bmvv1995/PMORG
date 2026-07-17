# PMORG — extinderea canonică a memoriei: canale și detectorul golului

| Câmp | Valoare |
|---|---|
| Status | Temă de proiect — vie; se cristalizează iterativ pe pilot |
| Versiune | 0.1 |
| Data | 2026-07-18 |
| Domeniu | Sursele memoriei (conducte noi) + detectorul de informație întunecată |
| Pornire | după convergența memoriei sub contractul v2 (excepție: L1/F1, vezi §6) |

## 1. Tema și cercul pe care îl închide

Memoria aude doar canalele autorizate. Restul organizației — telefonul,
discuția informală, mesajul pe canalul nelegat — produce decizii care nu se
reflectă nicăieri în universul cunoscut de date. Până acum, acest gol era
nemăsurabil prin definiție: ce nu a fost înregistrat nu lasă urme în sine.

Teza proiectului: **golul lasă urme la graniță.** O decizie luată în întuneric
produce efecte în lumea formală (Odoo) și referințe în conversațiile de pe
canalele acoperite. Detectând sistematic *efectele fără cauză consemnată* și
*referințele fără obiect*, golul devine vizibil, interogabil și — prin metrica
de acoperire — măsurabil.

Cercul care se închide: efect formal ← proveniență ← conversație ← canal ←
act de management ← feedback măsurabil → migrarea comunicării spre canalele
acoperite → mai multă proveniență. Mutarea deciziilor pe canale autorizate
este un act pur de management; acest proiect îi dă instrumentul de feedback
permanent fără de care actul nu se poate îmbunătăți iterativ.

## 2. Principii invariante

1. **Detectorul suspectează, nu acuză.** Un gap este o suspiciune cu fereastră
   temporală declarată, formulată ca întrebare către un om — niciodată verdict.
2. **Determinist detectează; omul explică; LLM cel mult narează.** Fiecare
   clasă de detecție este un query pe date existente, reproductibil.
3. **Răspunsul omului devine memorie.** „Am decis la telefon cu X" se
   consemnează ca claim cu autor, ancoră și dată — golul se închide
   *îmbogățind* memoria. Detectorul este astfel și canal de ingest:
   recoltează deciziile întunecate întrebând despre ele.
4. **Materialitatea este guvernată**, nu ghicită: registru `model+câmp →
   material` în stilul inventarului de ancore, modificat prin migrare;
   respingerile umane („trivial") alimentează calibrarea, cu aprobare umană.
5. **Oboseala este eșec de design.** Plafon de gaps pe digest, ordonate după
   materialitate × vechime; restul se acumulează tăcut, vizibile la cerere.
6. **Agregat înaintea individului.** Sănătate de proces, nu dosar de
   persoană; clasa D5 vine ultima și doar agregată.
7. **HIL = exclusiv vocabular** (2026-07-18, decis de owner): omul intră în
   flux DOAR pentru extinderea lumii cunoscute — entitate nouă recurentă sau
   tip nou de ancoră. Interpretarea (kind, owner, termen, ancorarea pe
   instanțe existente) e integral automată: consemnare-cu-chitanță dacă e
   sigură, tăcere dacă nu. `needs_review` nu e coadă umană; zero adnotare pe
   fluxul de mesaje. Tăcerea e sigură pentru că detectorul prinde orice
   consecință materială.
8. **Detectorul e autocalibratorul vocabularului**: explicațiile golurilor
   sunt semnal tare pentru entități noi (legate de efecte reale, nu de simple
   mențiuni), aglomerările de goluri pe modele neacoperite propun tipuri/
   pack-uri noi (sistemul propune, ownerul promovează — ADR-002), explicațiile
   devin cazuri de benchmark (regula cazului real), respingerile calibrează
   materialitatea. Complexitatea interpretării se mută într-un singur loc
   determinist și măsurabil; restul componentelor au voie să fie simple și
   conservatoare.
9. **Poarta înaintea conductei** (lege moștenită): nicio sursă nouă fără
   identitate structurală a autorului și filtru de intimitate pe acel drum.

## 3. Obiectul: gap-ul de proveniență și clasele de detecție

Model nou în planul de control: `pmorg.provenance.gap` — clasa, ancorele,
dovada efectului (id-uri de tracking/eveniment), fereastra verificată,
status `open / explained / dismissed`, referința de memorie care l-a închis,
scorul de materialitate. Detectoarele rulează ca controllere episodice
(01-ARCHITECTURE §7).

| # | Clasa | Semnalul determinist |
|---|---|---|
| D1 | Efect fără cauză | câmp material schimbat în Odoo fără item de memorie ancorat în fereastră; sursa: tracking-ul nativ Odoo, deja ingestat de poller |
| D2 | Angajament rezolvat în întuneric | commitment scadent + stare formală rezolvată/contrazisă, fără conversație de închidere |
| D3 | Referință-fantomă | marcaj „cum am stabilit…” în conversație (flag nou în schema grefierului) + recall negativ pe ancoră |
| D4 | Inițiativă fără urmă | tranziții de stare fără evenimente de conversație corelate |
| D5 | Actor întunecat | identitate activă formal, absentă conversațional N săptămâni — doar agregat |

## 4. Metrica și măsurabilitatea

**Rata de acoperire** = schimbări materiale cu proveniență consemnată / total
schimbări materiale, pe săptămână — în digest, ca instrument de management.
Secundare: timp până la explicare, gaps deschise pe vechime.

Detectorul primește benchmark propriu prin mașinăria de corpus
(05-MEMORY-DATA): worldgen injectează decizii întunecate cu adevăr cunoscut
(efect fără conversație în ziua N), detectorul e scorat precision/recall
contra manifestului oracle, în sandbox, înaintea organizației reale.

## 5. Livrabilele

**L1 — detectorul golului** (fazat, fiecare fază utilă singură):
F1 = D1 + modelul de gap + secțiunea de digest + bucla răspuns→memorie;
F2 = D3 + D2 (cer extensia grefierului ⇒ după convergență);
F3 = rata de acoperire + calibrarea materialității prin feedback;
F4 = D5 agregat.

**L2 — conducte noi**, în ordinea suprafeței reale de comunicare a
organizației-pilot (WhatsApp/Telegram/telefonic mult, email puțin):

1. **Telegram** — există, validat în v1 (gateway, identități, poartă);
2. **WhatsApp** — prin Business API (calea legitimă; puntea pe conturi
   personale = decizie separată, conștientă de termeni);
3. **Vocea** — voice notes prin STT; problema dură: maparea vorbitorului la
   `pmorg.identity`; autor nemapat ⇒ evidență în carantină, nu claim;
4. **Email** — ultimul; identitate tare, corelare nativă, relevanță mică
   pentru pilotul actual.

Fiecare conductă: ID extern + hash, corelare, poartă de intimitate, profil de
încredere per sursă (praguri de admitere proprii), activare doar prin decizie
explicită a ownerului — canalul aterizează inert.

## 6. Dependențe și ordine

Conductele noi și F2 se leagă la memoria unificată (convergența aipm sub
contractul v2 — precondiție). **Excepție deliberată: L1/F1** rulează pe
infrastructura existentă (tracking Odoo + memoria curentă) și poate porni
imediat după convergență sau chiar în paralel cu ea, fiind pur control-plane.

## 7. Ce rămâne deliberat necristalizat

Pragurile de materialitate per câmp, lățimea ferestrelor de atribuire,
formulările întrebărilor din digest, plafonul zilnic, etica exactă a D5 și
alegerea finală WhatsApp Business vs punte — toate se calibrează pe pilot,
prin bucla de feedback permanent care este chiar obiectul temei. Documentul
se revizuiește pe măsură ce tema se cristalizează; deciziile devenite stabile
se promovează în ADR-uri.
