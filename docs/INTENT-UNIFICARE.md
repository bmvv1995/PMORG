# INTENT — unificarea produsului „PM organizațional"

> Datat 8 iulie 2026. Documentul unifică cele două linii construite separat:
> **linia de proces** (PM pe Claude Code + Hermes, definită 2026-07-06 în
> specificația v0.3) și **linia de memorie** (aipm, implementată 2026-07-07,
> ancorată în Odoo). Unificarea a fost precedată de o analiză de
> compatibilitate: cele două linii codifică aceeași doctrină — puterea
> îngrădită structural, lume închisă, autoritatea de la oameni — deci
> integrarea e o problemă de joncțiune, nu de reconciliere.

## Produsul, într-o frază

Un conducător de procese organizaționale, artificial, instalat în casa
clientului, care **operează** munca prin board și canale persistente,
**ține minte** organizația prin memorie ancorată în sursa ei formală (ERP),
și **crește** numai prin proces aprobat de om.

## Componentele și rolul unic al fiecăreia

Fiecare componentă are o singură treabă. Suprapunerea de competență e
interzisă prin construcție, nu prin disciplină.

| Componentă | Rolul unic | Ce NU este |
|---|---|---|
| **Creierul** — PM pe Claude Code | orchestrator: primește inițiative, desface în sarcini, urmărește, escaladează; unelte îngrădite fizic (MCP, deny-all built-ins) | nu e autor de fapte; nu scrie în memorie; nu își schimbă propria constituție |
| **Corpul de proces** — Hermes | kanban cu gări structurale (unealta operațională a PM-ului), gateway Telegram (canale persistente, listă închisă de identități), ceas (cron cu livrare), ritual de aprobare cu executor separat | nu e registrul durabil al organizației; istoria lui e operațională, nu memorie |
| **Memoria** — aipm | sedimentarea: extrage decizii/angajamente/„de ce"-uri din comunicarea oamenilor, le ancorează la înregistrări Odoo reale, lasă chitanță în chatter, răspunde cu claims validate mecanic (fapt doar ce există acum în sursă) | nu e autoritate pe starea curentă — își retrogradează singură conținutul la ipoteză |
| **Sursa formală** — Odoo | singura ancoră legitimă a lumii organizației; lumea închisă de entități (angajați, proiecte, parteneri, comenzi, produse) | nu e motorul de proces al PM-ului; nu primește scrieri de la AI în afara chitanței |

Imaginea de ansamblu: **kanban-ul e aparatul circulator, aipm e
sedimentarea, Odoo e scheletul lumii, PM-ul e singurul cititor al tuturor.**

## Principiile unificării

Moștenite din ambele linii; unde liniile divergeau, aici e forma împăcată.

- **P1 — Autoritatea inversată.** AI-ul propune (candidați, scoruri,
  extrageri); pragurile și oamenii decid. Faptele memorate au autori umani;
  PM-ul e exclusiv consumator de memorie. Textul produs de PM însuși nu
  devine fapt — cel mult intră marcat distinct, printr-o decizie explicită.
- **P2 — Lume închisă la fiecare etaj.** Agenți și board-uri (listă Hermes),
  ancore (inventar aipm, guvernat prin migrare), identități (listă de acces
  gateway). „Nu e în listă" = „nu există" — la toate etajele, sistemul știe
  și când NU știe.
- **P3 — Adevărul curent se citește pe viu.** Starea procesului = kanban,
  direct; starea lumii = Odoo, direct; memoria = exclusiv context istoric,
  forțat de cod la rang de ipoteză. Componentele își împart tăcerile: niciuna
  nu vorbește în teritoriul alteia.
- **P4 — Poarta înaintea conductei.** Nicio sursă nouă nu se leagă la
  memorie înainte ca poarta de intimitate (lista „niciodată la AI") și
  păstrarea autorului real să existe pe acea conductă. Ce a intrat o dată
  nu mai poate fi ne-știut retroactiv.
- **P5 — Totul reversibil și auditabil.** Structura în git (constituții,
  migrări, commit per schimbare aprobată); memoria cu chitanță vizibilă în
  sistemul oamenilor; „ce s-a schimbat săptămâna asta?" are răspuns de o
  linie în fiecare componentă.
- **P6 — Creșterea prin proces.** Executant nou, ancoră nouă, regulă nouă,
  sursă nouă de ingest = cerere → aprobare umană → execuție de infrastructură
  → înregistrare imuabilă. Nimic din acestea la discreția runtime-ului.

## Joncțiunea unică: vama dintre lumi

Singurul loc unde cele două lumi închise se ating și trebuie să se
recunoască: **tabela de corespondență** între lumea Hermes (oameni pe
Telegram, proiecte pe board-uri) și lumea Odoo (EMPLOYEE, PROJECT, PARTNER).
Mică, explicită, versionată, schimbată doar prin procesul de aprobare (P6).
O entitate prezentă pe board dar absentă din Odoo e un gol de cunoaștere
înregistrat (mecanismul entităților externe din aipm), nu o invenție.

Condiție practică: proiectele conduse de PM există ca înregistrări
`project.project` în Odoo — ca angajamentele și deciziile lor să aibă
ancoră și chitanțele un chatter pe care se uită cineva.

## Fluxurile de integrat

1. **Conducta de sedimentare**: comunicarea oamenilor care trece prin PM
   (Telegram, comentarii și artefacte de pe kanban) → ingest aipm, cu autor
   real păstrat cap-coadă și poartă de intimitate la intrare (P4). Kanban-ul
   nu se ingestează ca registru — se ingestează *vorbele oamenilor* din el.
2. **Uneltele de memorie ale PM-ului** (read-only, prin MCP): întreabă
   memoria (răspuns cu claims fapt/ipoteză), rapoartele aipm (termene
   apropiate, angajamente fără urmă, întrebări rămase deschise), starea
   cozii de verificare.
3. **Livrarea proactivă**: rapoartele aipm nu așteaptă să fie cerute —
   ceasul Hermes le duce pe Telegram pe ritmul stabilit; coada de verificare
   a ancorării se escaladează către patron pe suprafața lui privată.
4. **Chitanța ca buclă socială**: consemnările aipm apar în chatter-ul Odoo,
   unde oamenii le văd și le pot contesta; contestarea e date de lucru, nu
   comandă.

## Ce se retrogradează explicit (amendamente la moștenire)

Consemnate ca decizii, ca liniile vechi să nu se contrazică în tăcere:

- **Board-ul nu mai e „registrul muncii" durabil** (spec v0.3, F2/L3 în
  litera veche): rămâne unealta operațională a PM-ului, cu gările și legea
  artefactului intacte *ca mecanică de proces*; adevărul durabil se
  sedimentează în aipm, ancorat în Odoo.
- **Substratul de memorie nu mai e text-în-git**: aipm (PostgreSQL+pgvector)
  preia rolul, pentru că ține garanțiile de lume închisă, proveniență și
  auditabilitate de patron (chitanța în chatter bate fișierele-text pentru
  un patron ne-developer). Garanția de reconstruibilitate din jurnal rămâne
  DATORIE deschisă a aipm (vezi necunoscutele).
- **Casa proiectului** se mută din `~/aipm` (decizia din 2026-07-07) în
  repo-ul de unificare: aipm s-a dovedit componentă, nu produs.

Rămân moștenire valabilă, neatinsă: manifestul; definiția funcțională
F1–F7 (mai puțin litera F2 de mai sus); legile de proces din spec v0.3
(runtime îngrădit, aprobarea rituală, auditul determinist, pauza de urgență);
regulile de lucru (hotărâri vs interpretări, sinteza externă, amplificare
înainte de clarificare, teste scrise înaintea deciziilor).

## Necunoscute deschise (fiecare se închide printr-un test scris dinainte)

1. **Valabilitate/înlocuire în aipm**: un angajament înlocuit de o decizie
   ulterioară rămâne azi `active` lângă ea; fără mecanism de expirare,
   memoria acumulează adevăruri expirate care devin ipoteze false.
2. **Jurnalizarea chat-ului aipm**: azi in-memory; reconstruibilitatea din
   surse e ținută doar pe jumătate (chatter da, chat nu).
3. **Identitatea expeditorului prin punte** (problema cunoscută A1):
   conducta de sedimentare e blocată până când autorul real supraviețuiește
   drumului Telegram → gateway → mirror → PM.
4. **Chitanțele în faza pre-go-live**: până când oamenii trăiesc în Odoo,
   bucla socială a chitanței e mută — se acceptă ca atare sau se dublează
   temporar pe Telegram?
5. **Suita de evaluare a răspunsurilor** (sora celei de rezoluție): poarta
   de calitate pentru recall, nu doar pentru ancorare.

## Mediul de integrare și test

- **Server** (204.168.208.233): stack-ul de proces viu — Hermes (board,
  gateway pm, cron), puntea către Claude Code, uneltele MCP ale PM-ului.
- **Odoo populat cu date reale** (instanța horeca, per SPEC aipm §0):
  lumea de ancore există — integrarea se testează pe date adevărate,
  nu pe fixtures.
- **aipm**: rulabil pe fixtures (`ODOO_ADAPTER=fake`) pentru testele
  deterministe și pe `xmlrpc` contra instanței reale pentru validare.

Pasul următor după acest document: **planul de integrare** — ordinea
construcției joncțiunilor și conductelor de mai sus, cu criterii de ieșire
verificabile per etapă, judecat contra acestui INTENT.
