# PLAN DE INTEGRARE — ordinea etapelor și deciziile

> Datat 8 iulie 2026. Judecat contra [`INTENT-UNIFICARE.md`](INTENT-UNIFICARE.md).
> Pornește de la starea reală a codului: cele două produse există și funcționează
> separat; nimic de aici nu e un defect, ci lista de construit pentru a le lega.
> Fiecare etapă se închide printr-un test verificabil, scris înaintea implementării.

## Deciziile consemnate (2026-07-08, owner)

- **D1 — Identitatea.** Cine e *parte la conversație* (autorul unui mesaj) trebuie
  identificat cert: tabel de corespondență cont Telegram → persoană din Odoo,
  obligatoriu înainte de a deschide sedimentarea. Cine e *doar pomenit* în text
  rămâne pe mecanismul existent (candidați propuși + confirmare umană în coada de
  verificare); un tabel și pentru mențiuni se rediscută după primele săptămâni de
  utilizare reală.
- **D2 — Filtrul de intimitate stă la intrare** (în gateway-ul Telegram), înaintea
  oricărei scrieri durabile — nu doar în aipm. Altfel mesajele brute rămân scrise
  în jurnalele intermediare de pe server și filtrul e doar de formă.
- **D3 — Angajamentele încheiate.** Marcare automată doar derivată din starea Odoo
  (înregistrarea-ancoră s-a închis); pentru rest, marcare umană în ecranul de
  verificare. Niciodată marcare automată pe judecata AI.
- **D4 — Confirmările în Odoo (chitanțele) înainte de go-live.** Se acceptă că
  deocamdată nu le vede nimeni (oamenii nu lucrează încă în Odoo); fără dublare pe
  Telegram — ar crea două locuri de adevăr. Se rediscută la go-live.

## Etapele, în ordine

Ordinea nu e negociabilă intern: 1–4 sunt temelia, 5 deschide prima conductă,
6–10 aduc valoarea. Etapele 6–7 nu depind de 2–5 și pot merge în paralel cu ele.

### 1. Instalarea memoriei împreună cu restul produsului

Installer-ul (`components/pm-organizational/install.sh`) nu cunoaște azi aipm.
De adăugat: verificarea dependențelor (PostgreSQL + pgvector), rularea migrărilor,
serviciu systemd pentru aipm, generarea unui token de autentificare ne-gol
(default-ul gol de azi lasă API-ul deschis), `ODOO_ADAPTER` setat explicit.
Bucla de ingest se instalează **oprită** — memoria aterizează goală și inertă.

*Criteriu de ieșire:* pe un server curat, după instalare serviciul aipm rulează,
migrat, cu token real; ingest oprit; un smoke-test HTTP trece.

*Stare: implementat 2026-07-08* (`install-aipm.sh` + `INGEST_ENABLED` +
backup zilnic; criteriul de ieșire verificat cap-coadă pe un mediu curat cu
PostgreSQL 16 + pgvector: provizionare, migrări, serviciu, health cu
`ingest=oprit`/`auth=da`, 401 fără token, backup restaurabil).

### 2. Tabelul de identități (D1) + proiectele din Odoo

Tabel `identity_map` (cont Telegram → `res.partner`/`hr.employee`), populat prin
migrare cu `approved_by` — același tipar ca inventarul de ancore din
`aipm/migrations/0002_seed.sql`. Autor mapat = identitate fixată determinist, fără
ghicire LLM; autor nemapat = gol de cunoaștere înregistrat (mecanismul
`external_entity` existent), niciodată o identitate inventată. Mențiunile din text
rămân pe rezoluția existentă cu confirmare umană (D1).

În paralel, precondiția din INTENT: proiectele conduse de PM primesc înregistrare
`project.project` în Odoo (installer-ul creează azi doar board-ul kanban), ca
angajamentele lor să aibă unde se ancora.

*Criteriu de ieșire:* pe datele de test cu omonime („Ion Georgescu" există de 3
ori), un autor mapat se fixează fără apel de ghicire; un autor nemapat nu produce
niciun fapt cu autor, ci un gol înregistrat; tabelul se poate scrie doar prin
migrare, nu din runtime.

*Stare: implementat 2026-07-08, cu o parte rămasă.* Migrarea
`0003_identity_map.sql` (identity_map + project_map), `engine/identity.py`
(lookup determinist), cablarea în `pipeline.ingest_message(author_key=...)`;
criteriul de ieșire e suita `test_identity_map.py` (autor mapat fixat cu zero
apeluri LLM; nemapat → gol `autor:telegram:<id>`; API-ul nu are nicio rută de
scriere spre vamă). **Rămas:** crearea `project.project` în Odoo la crearea
board-ului — cere Odoo real, se face la trecerea pe `xmlrpc` (pre-go-live).

### 3. Identitatea expeditorului supraviețuiește drumului (fosta „problemă A1")

Azi identitatea se pierde: gateway-ul știe cine scrie (allowlist), dar puntea
(`cc-mirror-shim`) transmite doar textul, iar memoria primește autor anonim
(`chat_source.py` scrie hardcodat „utilizator"). Legătura se face **la gateway**,
unde contul e deja autentificat — nu prin text injectat în conversație, care ar fi
falsificabil („From: altcineva"). Puntea rămâne transport, oarbă la identitate.

*Criteriu de ieșire:* un mesaj de pe un cont din allowlist ajunge în memorie cu
autorul = persoana mapată din tabelul etapei 2; un text care pretinde alt autor
nu poate păcăli sistemul.

*Stare: implementat 2026-07-08, prin hook stock Hermes (fără modificare
Hermes).* Descoperire-cheie: Hermes ([NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent))
are un sistem de hooks la gateway; evenimentul `agent:start` livrează
structural `user_id`-ul real (post-allowlist) + textul. Hook-ul
`aipm-sediment` (template în pm-organizational, instalat de installer) trimite
`author_key=telegram:<user_id>` către `POST /api/ingest/gateway`; identitatea
trece prin vamă (etapa 2), nu prin text spoofabil. Limită stock: textul e
trunchiat la 500 de caractere (candidat de contribuție upstream). Criteriul de
ieșire = `test_gateway_pipe.py`. **Rămas:** testul cap-coadă pe Telegram real
(bot de test + allowlist).

### 4. Filtrul de intimitate la intrare (D2)

Lista „niciodată la AI" + potrivirea pe forme flexionate românești (diacritice,
declinări), ca bibliotecă deterministă folosită la gateway, înaintea oricărei
scrieri durabile — inclusiv jurnalele punții, nu doar memoria. Determinist: două
rulări pe același text dau același rezultat.

*Criteriu de ieșire:* un mesaj cu un termen interzis (inclusiv flexionat) nu apare
în nicio scriere durabilă de pe server; test rulat de două ori, același rezultat.

*Stare: implementat 2026-07-08 pe conducta memoriei; perimetru restrâns
consemnat.* `engine/privacy.py`: determinist (pliere diacritice + prefix de
cuvânt pentru flexiuni RO + expresii multi-cuvânt), lista ownerului în
`~/.hermes/profiles/pm/privacy-denylist.txt` (versionată în git-ul
organizației, P5); refuzul se consemnează FĂRĂ conținut și fără termeni.
**Perimetru:** hook-urile Hermes sunt observatori — nu pot bloca mesajul spre
agent, deci transcriptul Claude Code primește textul brut pe calea LLM;
filtrarea completă la intrare ar cere o schimbare upstream în Hermes.
Poarta de aici apără memoria (conducta aipm), litera plină a D2 rămâne
deschisă ca decizie (acceptare perimetru vs. contribuție upstream).

### 5. Deschiderea sedimentării (prima conductă)

Abia acum se pornește ingestul din conversațiile care trec prin PM. Cablarea e
mică — capetele există de ambele părți; etapele 2–4 sunt condiția, nu cablarea.

*Criteriu de ieșire:* test cap-coadă pe date de test: mesaj pe Telegram → fapt
memorat cu autor corect și ancoră corectă; rulat de două ori → același rezultat,
fără dubluri.

*Stare: implementat 2026-07-08; deschiderea rămâne decizie explicită.*
Migrarea 0007 (`source_type='gateway'`, status `privacy_blocked`),
`ingest/gateway_source.py` (poarta ÎNAINTEA conductei; idempotență prin
source_ref derivat din chat+sesiune+text), `POST /api/ingest/gateway`
(409 cât timp `INGEST_ENABLED=false` — conducta se deschide prin decizie,
nu prin default). Verificat pe viu în sandbox: hook → aipm → refuz de poartă
consemnat fără conținut / accept idempotent. Extracția completă e dovedită
cu FakeLLM; pe server cere `LLM_API_KEY` în .env-ul aipm.

*Validat pe Telegram REAL (2026-07-09, bot de test + gateway Hermes stock
în sandbox):* mesajul ownerului cu termen interzis („salariul", flexionat) →
`privacy_blocked`, fără nicio urmă de conținut în jurnal; mesajul curat →
`accepted` cu identitatea reală (`telegram:<id>` prin vamă); ultima verigă
(fapt memorat) cere doar cheia LLM. **Constatare de produs:** Hermes grupează
mesajele sosite în rafală într-un singur tur de agent — hook-ul primește
textul combinat, deci un termen interzis blochează întregul lot; de documentat
pentru owner (comportament corect al porții, dar cu granularitate de lot).

### 6. Suita de evaluare a răspunsurilor

Perechea suitei de rezoluție care există deja (`tests/resolution_cases/`): cazuri
etalon pentru întrebare → răspuns, cu prag de trecere. Fără ea, o schimbare de
model sau de prag degradează răspunsurile fără să observe nimeni.

*Criteriu de ieșire:* suita rulează în CI pe adaptorul fake; cazurile obligatorii
trec 100%; o regresie plantată intenționat o face roșie.

### 7. Uneltele de memorie ale PM-ului

Trei unelte noi în serverul MCP (`hermes-ops-mcp`): întreabă memoria, cere un
raport, vezi coada de verificare — toate doar-citire. Cere un endpoint nou de
interogare pură: cel existent (`/api/chat`) scrie un rând cu autor anonim la
fiecare întrebare, deci nu poate fi refolosit ca atare.

*Criteriu de ieșire:* PM-ul întreabă memoria prin MCP și numărul de rânduri din
memorie rămâne neschimbat (zero scrieri).

*Stare: implementat 2026-07-08.* `POST /api/recall` (citire pură, fără ingest) +
trei unelte în `hermes-ops-mcp`: `aipm_recall`, `aipm_reports`,
`aipm_review_queue`, cu suprafață de citire fixă (`READ_ENDPOINTS`) și token
citit din `.env`-ul aipm (`AIPM_ENV_FILE`, setat de installer în `.mcp.json`).
Criteriul de ieșire = `test_recall_readonly.py`; lanțul MCP→HTTP→aipm verificat
pe viu prin protocolul stdio.

### 8. Închiderea angajamentelor (D3)

Un angajament rămâne azi „activ" pentru totdeauna. Felia automată: derivat din
starea Odoo — ancora s-a închis, angajamentul nu mai apare ca activ (reversibil,
nu scrie adevăr nou). Felia umană: buton de „încheiat/înlocuit" în ecranul de
verificare. Itemii încheiați ies din rapoarte și din răspunsuri.

*Criteriu de ieșire:* un angajament cu înregistrarea Odoo închisă dispare din
„termene apropiate"; marcarea umană există și e auditabilă.

*Stare: implementat 2026-07-08 (fără butonul de UI).* Migrarea 0005
(closed_field/closed_values pe anchor_type, guvernate prin migrare; audit
resolved_by/at), derivarea live în due_soon + commitments_missing (Odoo picat
→ nimic exclus pe orb, raport declarat `degraded`), `POST
/api/memory/{id}/resolve` (om, 409 la re-rezolvare). Criteriul de ieșire =
`test_commitment_closing.py`. **Rămas:** butonul „încheiat" în pagina /review
(UI) și, opțional, extinderea derivării live în selecția recall.

### 9. Rapoartele ajung singure pe Telegram

Rapoartele există (`aipm/reports/queries.py`) dar întorc JSON și așteaptă să fie
cerute. De adăugat: un digest text determinist (fără LLM) + un jurnal de trimitere
ca aceleași restanțe să nu fie retrimise zilnic. Ceasul Hermes rămâne doar
programator și transport.

*Criteriu de ieșire:* cron-ul livrează digestul pe Telegram; a doua rulare în
aceeași zi nu repetă aceleași itemi.

*Stare: implementat 2026-07-08 (partea aipm + scriptul de cron).* Migrarea
0006 (report_sent), `reports/digest.py` (text RO determinist, fără LLM;
termen schimbat = element nou; degradarea Odoo declarată în text), `POST
/api/reports/digest` (mark/preview), scriptul `aipm-digest.py` pe tiparul
audit-board (`pm cron create "0 8 * * *" --no-agent --script aipm-digest.py
--deliver telegram`). Criteriul de ieșire = `test_digest.py` + rulare dublă
pe viu (a doua tace). **Rămas:** crearea efectivă a cron-ului pe server
(după configurarea Telegram) și al doilea digest, al cozii de verificare,
către patron (cere chat_id-ul lui prin vamă).

### 10. Jurnalul conversației cu memoria

Firul de chat al aipm trăiește azi doar în memorie de proces și piere la restart.
Tabel append-only pentru ambele replici, în carantină (nu devine niciodată suport
de fapt). Partea scrisă de utilizator se jurnalizează doar după etapa 4.

*Criteriu de ieșire:* „ce a răspuns memoria săptămâna asta" are răspuns dintr-o
interogare; jurnalul supraviețuiește restartului.

*Stare: implementat 2026-07-08 pentru latura de asistent.* Migrarea
`0004_chat_turn.sql` (append-only impus prin trigger, în carantină — nu e
memorie, nu susține claims); `recall.answer` jurnalizează fiecare răspuns;
criteriul de ieșire = `test_chat_journal.py`. Latura de utilizator rămâne
nejurnalizată până la poarta de intimitate (etapa 4), conform P4.

### Chitanțele: rămân pe modul manual (D4)

Nicio construcție acum. `RECEIPT_MODE` rămâne pe manual, omul din ecranul de
verificare e poarta. Se redeschide subiectul la go-live, când oamenii lucrează în
Odoo și bucla de contestare devine reală.

## Datorii operaționale (nu blochează ordinea, se rezolvă pe parcurs)

1. **Backup pentru PostgreSQL-ul memoriei** — azi inexistent, deși memoria a
   devenit registrul durabil al organizației. Pierderea volumului = pierderea a
   tot ce s-a memorat. Prioritate imediat după etapa 1.
2. **Plafon de cost LLM** — fiecare mesaj ingestat = apeluri LLM + embeddings,
   fără limită; un chatter aglomerat devine factură nelimitată.
3. **Secretele** — cheia API e scrisă în clar într-un director neacoperit de
   gitignore-ul existent; token/parole fără rotație.
4. **Provizionarea Odoo verificată** — userul dedicat aipm și drepturile lui sunt
   azi pas manual din spec, neverificat de installer; eșuează tăcut.
5. **Semnal de degradare** — când Odoo e picat, memoria retrogradează tăcut toate
   faptele la ipoteze; răspunsul trebuie să spună explicit că e degradat.
6. **Reîmprospătarea instantaneelor** — `components/` sunt copii datate ale
   codului de pe server; orice hotfix pe server le învechește tăcut. De stabilit
   un ritual de reîmprospătare la fiecare modificare.

## Ce NU s-a decis încă

- Tabelul de mențiuni (persoane doar pomenite) — se revede după utilizare reală (D1).
- Forma buclei de contestare a chitanțelor la go-live (D4).
- Detecția asistată de AI a angajamentelor-candidat la închidere — doar după
  etapa 6 (suita de evaluare), și tot cu decizie umană.
