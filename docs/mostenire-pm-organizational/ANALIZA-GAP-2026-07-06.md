# Analiza de gap — Specificația v0.3 vs. stack-ul existent

> 6 iulie 2026. Analist: agent terț cu context curat și acces SSH la
> serverul viu — a citit codul efectiv, a rulat CLI-ul, a interogat baza.
> Ce n-a putut proba pe server e etichetat explicit în text.
> Defectul activ găsit (cronul de audit cu cale greșită) a fost reparat
> în aceeași zi (symlink + commit în ~/.hermes).

---

# Raport de GAP — Specificația v0.3 vs. stack-ul de pe 204.168.208.233

Metodă: am citit integral cele două documente din scratchpad, am citit codul efectiv (`cc-bridge`, `cc-mirror-shim`, `hermes-ops-mcp/server.py`, `audit-board.py`, `install.sh`), am rulat CLI-ul Hermes și am interogat schema SQLite. Ce n-am putut proba pe server e etichetat explicit.

**Abateri față de descrierea primită**: (1) cronul de audit EXISTĂ dar **ultima rulare a eșuat** — `error: Script not found: /home/vscode/.hermes/profiles/pm/scripts/audit-board.py` (scriptul e la `~/.hermes/scripts/audit-board.py`; cronul profilului `pm` caută în alt director). Auditul zilnic e azi, de facto, mort. (2) Nicio sesiune tmux nu rulează acum (`no server running`) — sesiunea PM pornește doar la primul mesaj (autostart în shim). (3) Board-ul kanban e gol (4 taskuri arhivate) — instalarea e „de referință/testată", nu în operare. (4) Există și un al patrulea repo, `~/hermes-ontology` (protocol + template-uri + chestionar de aliniere), menționat doar indirect.

---

## 1. Tabel sintetic C1–C11

| C | Verdict | Dovada | Ce lipsește din contract (la PARȚIAL) |
|---|---|---|---|
| **C1 Runtime agentic** | **PARȚIAL** | `~/cc-sessions/pm/.claude/settings.json`: `deny` pe Bash/Write/Edit/NotebookEdit/WebFetch/WebSearch/Task, `allow` doar `mcp__hermes-ops` — negarea din oficiu e reală; workdir persistent + CLAUDE.md; transcript JSONL parsabil (cc-bridge îl citește); headless+persistent prin tmux; `--continue` la restart | Verificarea flagului de pauză la pornire (nu există pauză); reciclarea sesiunii legată de consolidare (nu există consolidare); sesiuni de lucru separate pentru ritm (cronul rulează pe agentul Hermes, nu pe PM-CC); cheia de facturare per director e prevăzută în installer dar nu e setată acum |
| **C2 Registrul muncii** | **PARȚIAL** | `~/.hermes/kanban.db`: `tasks` cu `claim_lock/claim_expires` (lease), `last_heartbeat_at`, `max_runtime_seconds`, `consecutive_failures`, `max_retries`, `idempotency_key`, `priority`, `block_kind`; `task_events` (istoric per sarcină), `task_comments` (cu autor), `task_runs`; statusuri includ `review` | **L3 NU e refuzată de depozit**: `hermes kanban complete --help` arată `--result` OPȚIONAL — `done` fără dovadă trece prin CLI (doar schema MCP o cere + auditul o detectează post-hoc); refuzul tranziției fără lease — neverificat empiric; lipsesc câmpurile `termen` (deadline) și `puncte_de_control` |
| **C3 Canale** | **EXISTĂ** (esența) | `hermes-gateway-pm.service` activ; `TELEGRAM_ALLOWED_USERS` în `~/.hermes/profiles/pm/.env` = listă închisă; administrarea listei trece prin pagina de aprobări (`allowlist_add` în `admin_execute`) | — (modelul de încredere e cel declarat de spec: platforma + token) |
| **C4 Puntea** | **PARȚIAL** | `cc-mirror-shim`: serializare per sesiune (lock, 90s) ✔; răspuns onest de ocupat ✔ (textul „Procesez altă cerere…"); timeout de subproces cu eroare explicită ✔; systemd cu restart ✔ | **Două cozi cu prioritatea Patronului** — nu există (un singur lock FIFO nedeterminist); **jurnalul mesajelor deținut de Punte** — nu există (mesajele trăiesc doar în sesiunile Hermes); **poarta la scriere** — nu există; **plicul de date** — nu există; repornirea pierde cererea în zbor (lock în memorie, nu coadă persistentă) |
| **C5 Suprafața de aprobare** | **PARȚIAL** | Port 9128 DOAR loopback (verificat `ss -tlnp`: `127.0.0.1:9128`); token în `~/.cc-bridge/admin.token` (0600, `hmac.compare_digest`); ritual: scrii numele acțiunii de mână; executor determinist + commit git; flux probat (`req-0001.json` executed, commit `de42d39`) | Doar 5 tipuri de acțiuni (profile_create, soul_write, ontology_install, allowlist_add, gateway_restart) vs. ~14 în §3.6; fără validare de schemă strictă per tip; fără evidențierea capacităților periculoase; **fără butonul roșu (pauza de urgență)**; fără atomicitate în 4 faze cu compensare; accesul ne-tehnic = tunel SSH, nu D8 |
| **C6 Jurnal & versionare** | **PARȚIAL** (aproape EXISTĂ) | `~/.hermes` e repo git; commit atomic per acțiune admin (istoric verificat, 5 commituri); `.gitignore` exclude `.env`, `auth.json`, db-uri; installerul detectează secrete scăpate | **Hook de verificare la commit — absent** (`~/.hermes/.git/hooks/` gol); protecția e doar `.gitignore` + verificare la instalare |
| **C7 Memoria organizațională** | **LIPSEȘTE** | Nu există registru al lumii per client (doar template-ul de chestionar în `~/hermes-ontology/templates/`), nu există depozit de fapte (Zep/Graphiti neinstalat — `pip list` gol pe zep/graphiti/neo4j), nu există registru de goluri, nu există Consolidator, **nu există poarta de intimitate** (niciun mecanism de redactare nicăieri în stack) | Toate cele 5 subcomponente (a)–(e). Memoria built-in Hermes (MEMORY.md, provideri externi mem0/honcho…) NU corespunde contractului: e memorie de agent, nu jurnal organizațional cu proveniență |
| **C8 Auditor** | **PARȚIAL** | `~/.hermes/scripts/audit-board.py`: determinist, doar SQL, stdout gol = tăcere; cron `0 8 * * *` `--no-agent --deliver telegram` în profilul pm | **Defect activ**: cronul nu găsește scriptul (cale greșită) — nu a livrat niciodată; acoperire: doar 3 verificări C2; lipsesc: cereri C5 nedecise >24h, latența deciziilor, plafoanele C10, **scanarea transcriptelor pentru unelte în afara grantului (auditul compensator al L1)** |
| **C9 Instalator** | **PARȚIAL** | `~/pm-organizational/install.sh`: idempotent (verificat prin citire — fiecare pas e gardat), wizard cu secrete, board inițial | `org.yaml` e „hartă necitită de instalator" (spune el însuși); chestionarul de aliniere nu produce registrul inițial, lista de intimitate, pragurile — acestea nici nu au unde să aterizeze (C7 lipsă) |
| **C10 Contorizare** | **PARȚIAL** | `hermes insights` — tokeni/costuri per sesiune, 30 zile, per platformă | **Plafonul lunar cu refuz de porniri noi — inexistent** (niciun `budget` în config; `buget_lunar_api_usd` din org.yaml.example nu e citit de nimic); alertă la depășire — inexistentă |
| **C11 Ceasornicar** | **PARȚIAL** | Dispecerul rulează în gateway (`kanban daemon` = DEPRECATED, „dispatcher now runs in the gateway"); `dispatch` face reclaim pe claim-uri stale (expirarea lease-urilor) + `--failure-limit` (auto-block după N eșecuri); `heartbeat` există ca comandă; `kanban notify-subscribe` livrează evenimente terminale; cron scheduler funcțional | Livrarea evenimentelor către o sesiune PM de lucru (≤5 min) — nu există ca mecanism dedicat; consolidarea programată + reciclarea sesiunii — nu există; **aplicarea pauzei de urgență — nu există**; distincția AI/uman la heartbeat — kanban tratează uniform (heartbeat-ul e per profil-worker, nu per cale) |

---

## 2. Legile L1–L14

**Garantate azi de stack (cu dovadă):**
- **L10 (jumătatea de expunere)** — 9127/9128 doar pe 127.0.0.1, verificat cu `ss`; decizia e chiar comentată în cod („DOAR localhost, decizia owner 2026-07-05").
- **L2 (esența)** — pentru cele 5 acțiuni existente: PM-ul doar depune (`admin_request` scrie JSON în coadă + notifică), omul decide ritualic, executorul e shim-ul (alt proces), commit git. Executor ≠ depunător, structural. Dovadă: fluxul complet în `cc-mirror-shim` + `server.py`, plus istoricul git.
- **L1 (jumătatea de configurație)** — deny-all built-ins în settings.json PM, verificat pe disc. Identitatea autorului e legată de server prin `HERMES_OPS_AUTHOR`, nefalsificabilă per apel.

**Garantabile cu configurare/efort minor (ore):**
- **L10 (hook-ul)** — un pre-commit hook în `~/.hermes/.git/hooks/`; azi lipsește.
- **L1 (auditul compensator)** — extinderea `audit-board.py` să scaneze JSONL-urile din `~/.claude/projects/` după `tool_use` în afara grantului; datele există deja, parsarea e demonstrată de cc-bridge.
- **L5 (doar-adăugare, ca convenție auditabilă)** — `task_events`/`task_comments` sunt append prin CLI și git-ul e istoric; dar SQLite-ul e editabil direct de oricine are shell, iar **excepția de conformitate (D7) nu există deloc** — partea de ștergere e cod nou.

**Cer cod nou:**
- **L3** — depozitul NU refuză `done` fără dovadă (CLI-ul upstream Hermes acceptă `complete` fără `--result`; doar stratul MCP o cere în schemă și auditul o prinde a doua zi). Garanția „mecanic, la depozit" cere wrapper/trigger propriu.
- **L4** — lease-ul există ca structură (`claim_lock/claim_expires`), dar n-am putut verifica dacă `complete` fără claim e refuzat; chiar dacă ar fi, PM-ul închide taskuri prin MCP fără claim. Neverificat → de tratat drept negarantat.
- **L6, L7, L8, L9** — inexistente (nu există fapte, plic de date, poartă, Consolidator). Zero cod azi.
- **L11** — datele stau pe server (self-hosted, real), dar **spre modelul AI pleacă totul ne-filtrat** (nu există poartă) și `confirmare_operatiune` nu există.
- **L13** — pentru PM ținut de facto (n-are nicio unealtă de fișiere), dar nu e o proprietate verificată la definirea uneltei, iar profilurile-executant Hermes au built-ins nescopate; apărarea lexicală în adâncime nu există.
- **L14** — pauza de urgență: complet inexistentă (niciun flag, nicio verificare la pornire, niciun buton).

---

## 3. Fluxurile FL1–FL15

- **Pot rula azi cap-coadă (în formă de bază):** **FL1** (Telegram → gateway → shim → PM-CC → `kanban_create` cu gări/`link`), **FL5** restrâns la cele 5 tipuri de cereri (probat empiric: cererea #1 executată + revert demonstrativ în git), **FL14** (install.sh idempotent, fără partea de aliniere).
- **Parțial:** **FL2** (claim/heartbeat/dispatch există; dovada la închidere nu e forțată mecanic; fără termen/deadline), **FL3** (auditul detectează tăcerea >3 zile — când va rula; escaladarea e comportamentală, N_tacere neconfigurabil), **FL4** (un raport de ritm se poate programa azi cu `cron_create`; metricile cerute — întârzierea cozii, latența C5, progresul golurilor — nu au surse), **FL6** (allowlist_add prin aprobare ✔; mesajul de bun-venit cu declararea AI + explicarea porții — nu există, și nici poarta), **FL7** (profile_create+soul_write+ontology_install ✔; unelte_permise/plafoane per §3.6 — nu), **FL8** (serializare + răspuns ocupat ✔; jurnal-prin-poartă, plic, confirmare_operatiune — nu), **FL12** (script prezent dar cron rupt + acoperire ~1/4), **FL13** (chestionarul există ca template; procesul nu e mecanizat).
- **Deloc:** **FL6b** (nicio acțiune de plecare cu reasignare completă), **FL9**, **FL10**, **FL11**, **FL15** — toate cele patru din urmă depind de C7, care lipsește integral.

---

## 4. Golurile mari, ordonate după efort, cu ordinea de construcție

**Efort mic (ore):**
1. Repararea cronului de audit (calea scriptului) — azi singura garanție compensatorie e moartă.
2. Pre-commit hook pentru secrete (închide L10 complet).
3. Extinderea audit-board: cereri C5 >24h, latența deciziilor, scanarea transcriptelor (auditul compensator L1). Deblochează: L1 întreagă, FL12.

**Efort mediu (zile):**
4. **Pauza de urgență (L14/T23)** — flag pe disc + buton pe pagina :9128 + verificare în `ensure_session`/dispatch/cron + expirarea claim-urilor. Puncte de agățare există toate; e cusătură, nu construcție. Recomand devreme: e condiția de siguranță pentru orice pilot.
5. Întărirea L3/L4 la depozit (wrapper peste kanban sau triggere SQLite) + câmp `termen`.
6. Plicul de date (L7/T22) — în shim la livrare + în formatarea comentariilor către executanți.
7. Cozile cu prioritatea Patronului + coadă persistentă la repornire (C4.2/C4.5).
8. Extinderea C5: restul tipurilor de cereri §3.6 cu schemă strictă + capacități periculoase evidențiate; apoi atomicitatea în 4 faze (T26). Tiparele există (acțiunile actuale sunt exact șablonul de urmat).
9. Plafonarea C10 (citirea `buget_lunar_api_usd`, agregare din insights, refuz porniri non-critice).

**Efort mare (săptămâni):**
10. **C7 integral** — miezul absent al produsului: registrul lumii cu aliasuri (fișiere în git — partea ieftină), registrul de goluri, jurnalul de mesaje al Punții, **poarta de intimitate cu normalizare morfologică pentru română** (piesă de NLP deterministă, nebanală), Consolidatorul cu mapare lexicală deterministă (T10) și digestul rescris de la zero. **Dependență critică de ordine: poarta TREBUIE construită înainte de (sau odată cu) jurnalul de mesaje** — L8 cere ca ce e oprit să nu se scrie deloc; un jurnal pornit fără poartă acumulează exact conținutul pe care legea îl interzice retroactiv.
11. Ștergerea de conformitate (D7), accesul zero-config al Patronului (D8), procedurile de măsurare O1–O3, bateria T19–T26.

Ordine recomandată: 1–3 (igienă, o zi) → 4 (pauza) → 10a (registrul lumii + goluri, fișiere-git, ieftin și deblochează FL10) → 10b (poartă + jurnal mesaje împreună) → 10c (Consolidator + depozit fapte, decizia D1) → 5–9 în paralel cu 10, apoi 11.

---

## 5. Verdictul pe Zep/Graphiti (C7b)

**Verificat**: nu e instalat nimic (pip: zero pe zep/graphiti/neo4j/falkordb). Tot ce urmează e **din cunoștințe generale, neverificat pe server**.

Ce ar acoperi Graphiti din C7/L6/FL9: fapte-frază pe muchii cu valabilitate temporală (`valid_at`/`invalid_at`, invalidare la contradicție), proveniență către episodul-sursă, tipuri de entități custom (Pydantic), rezumate per entitate/comunitate — adică §3.8 aproape gratis.

Ce NU acoperă — și sunt exact cerințele normative: (1) **lume închisă** — Graphiti extrage și creează entități liber; specificația cere invers: „nu e în registru = nu există" + gol de cunoaștere; (2) **mapare deterministă pe aliasuri** — rezoluția entităților în Graphiti e LLM + embeddings, nedeterministă, ceea ce încalcă frontal FL9/T10 („două rulări → aceeași mulțime de perechi") și C7d („LLM-ului îi rămâne exclusiv formularea enunțului"); (3) **L6** — extracția lui ia autoritatea din conținut, nu din metadatele jurnalului; (4) amprentă: Neo4j/FalkorDB + apeluri LLM per ingest, contra §6 și a filozofiei „auditabil de patron cu ochiul" (F5); (5) L9/L12 — modelul lui e graf viu incremental, nu digest rescris de la zero din jurnale.

**Verdict**: ca substrat C7(b), Graphiti e nepotrivit — ar trebui dezactivat sau reimplementat exact în punctele lui centrale (extracție și rezoluție) ca să respecte legile. Fișiere-text-în-git + maparea lexicală proprie satisfac direct T10, L6, L9, L12 și auditabilitatea, cu costul de a scrie tu invalidarea temporală și proiecția de digest — cod mic și determinist. Recomandare: fișiere-text ca substrat; Graphiti cel mult ca index derivat, de unică folosință, mai târziu — decizia D1 rămâne, dar sarcina probei e acum pe graf, nu pe fișiere.

---

## 6. Estimarea de ansamblu

- **Există funcțional azi: ~35%.** Justificare: scheletul de *conducere a muncii* e real și probat — runtime îngrădit prin config (C1), registru tranzacțional cu lease/heartbeat/eșecuri (C2), canal cu listă închisă (C3), punte serializată cu răspuns onest (C4 jumătate), aprobare ritualică cu executor separat și git atomic (C5 jumătate, dar fluxul complet e demonstrat empiric), constituție versionată (C6), audit determinist (C8, defect reparabil), instalator idempotent (C9 jumătate).
- **Configurare/adaptare pe tipare existente: ~15%.** Hook-ul de secrete, repararea și extinderea auditului, noile tipuri de cereri C5 (copii ale tiparului existent), plafonarea peste insights, pauza de urgență (cusătură între piese existente).
- **Construcție nouă: ~50%.** Întregul C7 (cinci subcomponente, inclusiv poarta cu morfologie românească și Consolidatorul determinist), plicul de date, cozile prioritare, atomicitatea în 4 faze, D7, D8, O1–O3 și majoritatea testelor T19–T26. Nu e 50% „din burtă": din cele 14 legi, azi sunt ținute integral ~2, parțial ~4, deloc ~8 — iar cele 8 sunt aproape toate legi de *memorie și date* (L6–L9, L11, L13), adică exact jumătatea de produs care transformă un dispecer de taskuri în „organizație inteligibilă pentru sine". Partea de proces există; partea de memorie trebuie construită de la zero.