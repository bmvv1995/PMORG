# PMORG — registrul deciziilor

| Câmp | Valoare |
|---|---|
| Status | ADR-001–012 Accepted; ADR-013–018 Proposed |
| Versiune | 0.3 |
| Data | 2026-07-17 |
| Domeniu | Produsul PMORG v2 și MVP-ul inițial |

O decizie `Accepted` este normativă. Schimbarea ei necesită un ADR nou care o
marchează explicit `Superseded`. `Proposed` indică o decizie formulată, dar
neaprobată încă. Suita v0.1 a fost aprobată explicit de owner la 2026-07-16;
ADR-001–012 își păstrează textul și statutul `Accepted`. Extensiile v0.3 sunt
formulate separat în ADR-013–018 și rămân `Proposed` până la aprobarea lor
explicită; ele nu modifică retroactiv deciziile acceptate.

## ADR-001 — PMORG este Odoo-first

**Status:** Accepted (2026-07-16)

**Decizie:** PMORG este o aplicație Odoo. Odoo este ancora ontologică și
registrul stării formale curente; nu păstrăm o abstracție ERP generică în
prima versiune. Baseline-ul MVP este Odoo 19 Community.

**Consecințe:** modelele, permisiunile, evenimentele și UI-ul sunt native Odoo. Alte ERP-uri pot fi evaluate ulterior, fără a condiționa MVP-ul.

**Alternative respinse:** ERP construit de la zero; aplicație standalone cu Odoo doar ca sursă de date; design ERP-agnostic prematur.

## ADR-002 — Ontologia se extinde prin anchor packs

**Status:** Accepted (2026-07-16)

**Decizie:** PMORG folosește numai entitățile de business de prim nivel din module instalate, configurate și accesibile, prin anchor packs versionate. Discovery-ul și mapările standard cunoscute sunt deterministe; o mapare custom necunoscută necesită aprobare.

**Consecințe:** un modul activ extinde vocabularul posibil, nu copiază automat date în memorie. Un pack incompatibil se oprește fail-closed. Permisiunile Odoo se respectă.

**Alternative respinse:** maparea tuturor modelelor; ontologie universală; interpretarea semantică de către LLM la fiecare rulare; promovarea automată a modelelor custom.

## ADR-003 — `project.task` este Kanbanul canonic

**Status:** Accepted (2026-07-16)

**Decizie:** PMORG extinde `project.task` pentru taskuri umane, agentice, hibride și de monitorizare, inclusiv clarificare, follow-up, confirmare, escaladare și verificare. Pașii tehnici efemeri rămân execuții sau evenimente, nu taskuri organizaționale.

**Consecințe:** oamenii și agenții lucrează în același registru. Hermes trebuie adaptat la API-ul PMORG. Starea de business și starea agentică sunt separate.

**Alternative respinse:** Kanban Hermes canonic paralel; model complet separat `hermes.task`; numai câmpurile Odoo native; fiecare apel de instrument drept task.

## ADR-004 — Odoo este control plane; runtime-ul și memoria sunt externe

**Status:** Accepted (2026-07-16)

**Decizie:** Odoo păstrează starea formală, politicile, aprobările, UI-ul și auditul. Runtime-ul extern operează taskurile. Memoria externă păstrează evidențe, claims, proveniență, temporalitate și istorie și este accesată prin MCP.

**Consecințe:** Odoo poate funcționa manual când AI este indisponibil. Runtime-ul poate fi înlocuit. Odoo păstrează referințe și rezultate formale, nu memoria integrală. Integrarea necesită contracte versionate și mod degradat explicit.

**Alternative respinse:** LLM-uri în worker-ele Odoo; stare canonică în transcript; embeddings și memorie integrală în Odoo; acces direct al agenților la bazele de date.

## ADR-005 — Admiterea în memorie este validată

**Status:** Accepted (2026-07-16)

**Decizie:** fluxul este `evidență -> candidat -> memorie validată -> formalizare Odoo`, atunci când apare un efect operațional. Validarea include identitate, proveniență, autoritate, contradicție, valabilitate temporală, confirmare și supersession.

**Consecințe:** „nevalidat” este o stare first-class; ipotezele nu sunt prezentate drept fapte; informația înlocuită nu se șterge; angajamentele devin operative numai conform politicii de confirmare.

**Alternative respinse:** memorarea tuturor afirmațiilor ca fapte; validare numai semantică; ștergerea contradicțiilor; memoria drept adevăr operațional curent.

## ADR-006 — Scrierile agentice sunt comenzi controlate

**Status:** Accepted (2026-07-16)

**Decizie:** PMORG expune exclusiv suprafața de comenzi versionată în
`01-ARCHITECTURE.md`, secțiunea „Contractele Odoo, evenimente și canale”.
Aceasta acoperă claim/execution, progres și așteptare, propuneri și aprobări,
dovezi și verificarea rezultatului. Fiecare comandă aplică autorizare,
politică de autonomie, tranziții valide, control de versiune, idempotency și
audit.

**Consecințe:** regula veche „Odoo nu primește scrieri AI în afara receipt-ului” este înlocuită pentru PMORG v2. Unele acțiuni sunt delegate, altele cer aprobare. Agenții nu primesc ORM sau SQL generic.

**Alternative respinse:** Odoo read-only; acces generic al LLM-ului; scrieri fără idempotency; aprobare umană pentru orice acțiune indiferent de risc.

## ADR-007 — Longitudinalitatea folosește stare persistentă și controller-e

**Status:** Accepted (2026-07-16)

**Decizie:** obligațiile, așteptările, politica și `next_check_at` sunt persistate în Odoo. Controller-ele se activează periodic sau la evenimente, reconstruiesc contextul din Odoo și memorie, execută un pas idempotent și programează următoarea verificare. Regulile obiective sunt deterministe; LLM-ul interpretează.

**Consecințe:** restartul nu pierde procesul; un agent nou poate continua; sunt obligatorii corelarea răspunsurilor, lease, retries și deduplicarea. Transcriptul este evidență, nu persistență.

**Alternative respinse:** conversație `--continue` eternă; agent permanent per task; cron fără stare; LLM pentru termene și tranziții obiective.

## ADR-008 — Hermes este candidatul de runtime, nu o condiție a MVP-ului

**Status:** Accepted (2026-07-16)

**Decizie:** MVP-ul folosește un runner determinist care implementează contractul final al orchestratorului. Hermes este integrat ulterior și trebuie să treacă aceleași teste de contract și scenarii longitudinale.

**Consecințe:** putem valida produsul fără a diagnostica simultan integrarea Hermes. Odoo și memoria nu se schimbă la înlocuirea runnerului. Hermes rămâne runtime numai dacă demonstrează claim atomic, reluare, idempotency, corelare și observabilitate.

**Alternative respinse:** Hermes integrat înaintea contractelor; respingerea Hermes fără test; cuplarea modelelor de internals Hermes; alegerea preventivă a altui orchestrator.

## ADR-009 — MVP-ul construiește real Odoo și memoria

**Status:** Accepted (2026-07-16)

**Decizie:** aplicația Odoo PMORG și memoria prin MCP sunt implementări reale, cu scop restrâns. Orchestrarea, timpul și comunicarea sunt simulate prin adaptoare care respectă contractele finale. Agentul și răspunsurile sunt întâi deterministe; un AI real se adaugă după smoke test.

**Consecințe:** schema, API-urile, validările, auditul și migrațiile nu sunt mock-uri de aruncat. Runnerul poate simula tăcere, duplicate, restart și indisponibilități. Un canal real este introdus numai după testul determinist.

**Alternative respinse:** mock-uri Odoo/memorie urmate de rescriere; Hermes și canale reale în primul MVP; demo conversațional fără stare persistentă; fine-tuning înaintea fluxului funcțional.

## ADR-010 — Zero teste în producție

**Status:** Accepted (2026-07-16)

**Decizie:** În toate fazele, orice test, benchmark, calificare sau validare
rulează exclusiv în medii separate de producție, cu baze, servicii,
credențiale și canale dedicate. Mediul de producție nu este niciodată banc de
test. MVP-ul folosește numai persoane, conversații și date sintetice. Un
eventual pilot este o etapă separată, explicit non-production, cu autorizare,
izolare și criterii proprii de intrare și ieșire.

**Consecințe:** fixture-urile sunt livrabile versionate. Testele negative
includ restart, duplicate, răspuns întârziat, indisponibilitate și modificare
concurentă. Trecerea în producție are loc numai după acceptarea distinctă a
pilotului și nu este numită sau folosită drept test.

**Alternative respinse:** proiecte reale „cu risc mic”; utilizatori reali marcați ca test; canale de producție; copierea neaprobată a datelor de producție.

## ADR-011 — Produs unic, implementare modulară

**Status:** Accepted (2026-07-16)

**Decizie:** PMORG este o singură aplicație pentru utilizator, dar poate fi o suită de addon-uri: nucleu, Project, runtime, memorie și anchor packs.

**Consecințe:** dependențele și compatibilitatea sunt versionate; componentele se instalează în funcție de modulele active; UI-ul și permisiunile rămân unitare.

**Alternative respinse:** addon monolitic; aplicații vizibile separate pentru fiecare componentă; mapări de domeniu copiate în nucleu.

## ADR-012 — Self-hosting-ul LLM nu este garanție de confidențialitate

**Status:** Accepted (2026-07-16)

**Decizie:** arhitectura nu impune un LLM self-hosted ca premisă sau garanție. Confidențialitatea se tratează prin acces minim, politici, audit, contracte de date și evaluarea furnizorului.

**Consecințe:** furnizorul și runtime-ul pot fi schimbați fără redefinirea produsului; o evaluare de securitate rămâne necesară înaintea datelor reale.

**Alternative respinse:** self-hosting prezentat drept soluție completă; ignorarea celorlalte controale deoarece modelul rulează local.

## ADR-013 — Produsul este agnostic față de organizația concretă

**Status:** Proposed

**Decizie:** Nucleul PMORG conține numai conceptele universale ale
operatorului organizațional și nu codifică funcții, procese sau modele de
domeniu ale unui client. Specificul apare exclusiv prin module Odoo active,
anchor packs versionate, identități, roluri, permisiuni, politici și date.
Același artefact PMORG trebuie să treacă trei profiluri sintetice în baze
separate: distribuție (`project` + `hr` + `stock`), servicii profesionale
(`project` + `hr`) și minimal (`project`).

**Consecințe:** `pmorg_core` nu depinde de `hr`, `stock`, Time Off sau alte
module opționale și nu are câmpuri directe către modelele lor. Profilele pot
schimba numai configurația și addon-urile de ancorare instalate, nu codul.
Setul versionat de artefacte și checksum-uri rămâne identic; profilul
selectează un subset fără rebuild. Un concept al unui modul absent rămâne
indisponibil semantic. Conformitatea este Gate C2 al MVP-ului.
În raport cu ADR-011, această decizie fixează una dintre formele modulare
permise acolo: pentru MVP, `project` intră în `pmorg_core`, fără un addon
separat `pmorg_project`; runtime-ul, memoria și anchor pack-urile rămân
componente distincte. ADR-011 nu este supersedat în rest.

**Alternative respinse:** fork per client; condiții cu numele organizației;
HR obligatoriu în nucleu; ontologie universală care expune concepte absente;
LLM folosit pentru a ghici procesele în locul configurației validate.

## ADR-014 — Identitatea canonică este `pmorg.identity`

**Status:** Proposed

**Decizie:** Ownerii, validatorii, participanții, agenții și sistemele sunt
referite în nucleu prin `pmorg.identity`. Fiecare identitate are companie și
`res.partner` obligatoriu, plus `res.users` opțional când poate acționa în
Odoo. Rolurile PMORG nu aleg alternativ între partner, user și employee.
Pack-ul HR leagă `hr.employee` de identitatea existentă prin user sau work
contact și refuză mapările absente ori ambigue.

**Consecințe:** profilul minimal poate reprezenta complet persoane și agenți
fără HR; instalarea HR adaugă semantică de angajare și ierarhie fără a crea o
a doua identitate. Autoritatea rezultă din utilizator și politici/delegări,
nu din simpla identitate.

**Alternative respinse:** `hr.employee` obligatoriu; câmpuri polimorfe
partner/user/employee; identități paralele per anchor pack; potrivire fuzzy
automată a persoanelor.

## ADR-015 — Oracle-ul de evaluare este separat și invizibil SUT-ului

**Status:** Proposed

**Decizie:** Sandboxul are două frontiere: produsul evaluat și harness-ul
privat. Oracle DB păstrează adevărul fizic, cunoașterea privată, expected
outputs, spliturile și gold labels într-un serviciu, volum, rol și rețea
separate de Odoo și memoria PMORG. SUT nu are rută, DNS, mount, secret sau API
către oracle. Scorerul citește exporturi și oracle numai după quiescence/seal.

**Consecințe:** validarea online din PMORG folosește numai Odoo, evidențe,
identități și politicile normale; oracle-ul nu răspunde întrebărilor
operatorului. Fiecare run are probe anti-leak și canary secret. O scurgere,
trasă incompletă sau un defect spontan al simulatorului invalidează runul, nu
devine scor slab al produsului. O tentativă nepermisă inițiată de SUT rămâne
quality failure chiar dacă disclosure guard o oprește; nu poate fi convertită
în `INVALID_SIMULATOR`. Replacementurile și pragul maxim de invaliditate sunt
predeclarate, iar runul original rămâne în audit.

**Alternative respinse:** tabele oracle în `aipm`; aceeași bază PostgreSQL cu
scheme separate; expected answers montate read-only în SUT; oracle folosit ca
validator business în timpul rulării; scorer online în bucla operatorului.

## ADR-016 — Worldgen are nucleu generic și domain packs

**Status:** Proposed

**Decizie:** Worldgen core cunoaște numai identități, structură, calendar,
proiecte, evenimente, timp și materializare. Procesele de industrie apar în
worldgen packs versionate, separate conceptual de `pmorg_anchor_*`. Pack-urile
inițiale compun profilurile minimal, servicii profesionale și distribuție;
HoReCa este un pack compozit ulterior.

**Consecințe:** un profil declară module Odoo, anchor packs, worldgen packs,
politici și date fără cod per organizație. Seed-ul, versiunile pack-urilor și
hash-ul planului produc `world.lock`; materializarea prin ORM/API Odoo trebuie
să aibă o proiecție canonică reproductibilă.

**Alternative respinse:** generator HoReCa ca nucleu; generator separat per
client; date paralele care nu sunt materializate în Odoo; confundarea
generatorului de fixture cu ontologia/anchor pack-ul produsului.

## ADR-017 — Evaluarea este un run bundle imuabil și temporal explicit

**Status:** Proposed

**Decizie:** Fiecare rulare fixează prin manifest versionat buildurile,
contractele, profilul, scenariul, seed-ul, politicile, ceasul, fault planul și,
la Gate E/F2, configurațiile de model. Manifestul public este vizibil SUT;
manifestul oracle este legat prin HMAC sau hash cu nonce secret de entropie
mare, nu prin hash simplu al seed-ului. Timpul de business este virtual și
distinct de timpul real de înregistrare. În sandbox, timpul autoritativ este
rezolvat server-side dintr-un `tick_id` emis de ceasul trusted; runtime-ul nu
poate furniza un `now` autoritativ.

**Consecințe:** Gate A–D se reproduc din același bundle în volume curate;
Gate E/F2 se reproduc ca configurație și se califică statistic pe replici
predeclarate. La fiecare barieră de tick, un exporter trusted sigilează
proiecțiile Odoo/memorie necesare scorării `as_of_event_seq`; starea finală nu
înlocuiește istoria. Resetul distruge volumele și emite credențiale noi. Un
scorer nou creează un scoring run nou, fără a rescrie verdictul istoric.

**Alternative respinse:** descriere verbală a configurației; taguri mutable;
sleep și ceasul hostului pentru longitudinalitate; reutilizarea bazei între
runs; alegerea manuală a celei mai bune rulări LLM.

## ADR-018 — Corpusul separă train, calibration și hidden-test prin lineage

**Status:** Proposed

**Decizie:** Corpusul canonic separă `case_version`, `benchmark_run`,
`corpus_example` și `corpus_release`. Splitul este atribuit înaintea
tuningului la nivel de familie de scenariu/incident și `leakage_group_id`, nu
per turn sau seed. Hidden labels sunt accesibile numai scorerului; fiecare
încercare hidden este auditată.

**Consecințe:** același incident și derivatele sale nu pot alimenta simultan
train și hidden-test. Pragurile se stabilesc pe calibration și se îngheață
înaintea hidden-test. O eroare din pilot intră numai ca reproducere sintetică
sanitizată într-o versiune viitoare; datele și conversațiile reale nu sunt
copiate automat.

**Alternative respinse:** același corpus folosit simultan pentru training și
verdict; split aleator pe mesaje; tuning după vizualizarea hidden-test;
rescrierea etichetelor într-un release publicat; exportul formatului unui
provider drept sursă canonică.

## Întrebări rămase deschise

1. Schema și numele tehnice exacte ale modelelor.
2. Mașina de stare agentică și relația cu stage-urile Odoo.
3. Semnăturile, payload-urile și codurile de eroare exacte pentru API-ul de
   orchestrare deja delimitat.
4. Forma exactă și statutul normativ al handshake-ului de capability registry
   propus în arhitectură, apoi payload-urile, codurile de eroare, controlul de
   acces MCP și comportamentul la indisponibilitatea memoriei.
5. Extinderea ulterioară a pack-urilor HR și Inventory dincolo de subsetul
   minim fixat pentru MVP, fără mutarea dependențelor în nucleu.
6. Matricea inițială de autonomie și aprobări.
7. Criteriile măsurabile de acceptare a Hermes.
8. Canalul real folosit după MVP-ul determinist.
9. Formatul exact al manifestelor, schemelor oracle și semnăturii verdictului,
   în limitele fixate de ADR-015–018.
10. Pragurile și volumele minime per metrică, stabilite prin calibrare.
11. Custodele, rotația și politica de acces pentru hidden-test.
12. Dacă delimitarea exactă `sut_scope` pentru Gate E/F1/F2 necesită un ADR
    separat înaintea implementării acelor etape.
