# PMORG — registrul deciziilor

| Câmp | Valoare |
|---|---|
| Status | Propunere canonică pentru revizuire |
| Versiune | 0.1 |
| Data | 2026-07-16 |
| Domeniu | Produsul PMORG v2 și MVP-ul inițial |

O decizie `Accepted` este normativă. Schimbarea ei necesită un ADR nou care o
marchează explicit `Superseded`. `Proposed` indică o decizie formulată, dar
neaprobată încă. La această revizie, toate ADR-urile rămân `Proposed` până la
aprobarea explicită a suitei de documente v2; nu se implementează ca și cum ar
fi deja normative.

## ADR-001 — PMORG este Odoo-first

**Status:** Proposed

**Decizie:** PMORG este o aplicație Odoo. Odoo este ancora ontologică și
registrul stării formale curente; nu păstrăm o abstracție ERP generică în
prima versiune. Baseline-ul MVP este Odoo 19 Community.

**Consecințe:** modelele, permisiunile, evenimentele și UI-ul sunt native Odoo. Alte ERP-uri pot fi evaluate ulterior, fără a condiționa MVP-ul.

**Alternative respinse:** ERP construit de la zero; aplicație standalone cu Odoo doar ca sursă de date; design ERP-agnostic prematur.

## ADR-002 — Ontologia se extinde prin anchor packs

**Status:** Proposed

**Decizie:** PMORG folosește numai entitățile de business de prim nivel din module instalate, configurate și accesibile, prin anchor packs versionate. Discovery-ul și mapările standard cunoscute sunt deterministe; o mapare custom necunoscută necesită aprobare.

**Consecințe:** un modul activ extinde vocabularul posibil, nu copiază automat date în memorie. Un pack incompatibil se oprește fail-closed. Permisiunile Odoo se respectă.

**Alternative respinse:** maparea tuturor modelelor; ontologie universală; interpretarea semantică de către LLM la fiecare rulare; promovarea automată a modelelor custom.

## ADR-003 — `project.task` este Kanbanul canonic

**Status:** Proposed

**Decizie:** PMORG extinde `project.task` pentru taskuri umane, agentice, hibride și de monitorizare, inclusiv clarificare, follow-up, confirmare, escaladare și verificare. Pașii tehnici efemeri rămân execuții sau evenimente, nu taskuri organizaționale.

**Consecințe:** oamenii și agenții lucrează în același registru. Hermes trebuie adaptat la API-ul PMORG. Starea de business și starea agentică sunt separate.

**Alternative respinse:** Kanban Hermes canonic paralel; model complet separat `hermes.task`; numai câmpurile Odoo native; fiecare apel de instrument drept task.

## ADR-004 — Odoo este control plane; runtime-ul și memoria sunt externe

**Status:** Proposed

**Decizie:** Odoo păstrează starea formală, politicile, aprobările, UI-ul și auditul. Runtime-ul extern operează taskurile. Memoria externă păstrează evidențe, claims, proveniență, temporalitate și istorie și este accesată prin MCP.

**Consecințe:** Odoo poate funcționa manual când AI este indisponibil. Runtime-ul poate fi înlocuit. Odoo păstrează referințe și rezultate formale, nu memoria integrală. Integrarea necesită contracte versionate și mod degradat explicit.

**Alternative respinse:** LLM-uri în worker-ele Odoo; stare canonică în transcript; embeddings și memorie integrală în Odoo; acces direct al agenților la bazele de date.

## ADR-005 — Admiterea în memorie este validată

**Status:** Proposed

**Decizie:** fluxul este `evidență -> candidat -> memorie validată -> formalizare Odoo`, atunci când apare un efect operațional. Validarea include identitate, proveniență, autoritate, contradicție, valabilitate temporală, confirmare și supersession.

**Consecințe:** „nevalidat” este o stare first-class; ipotezele nu sunt prezentate drept fapte; informația înlocuită nu se șterge; angajamentele devin operative numai conform politicii de confirmare.

**Alternative respinse:** memorarea tuturor afirmațiilor ca fapte; validare numai semantică; ștergerea contradicțiilor; memoria drept adevăr operațional curent.

## ADR-006 — Scrierile agentice sunt comenzi controlate

**Status:** Proposed

**Decizie:** PMORG expune exclusiv suprafața de comenzi versionată în
`01-ARCHITECTURE.md`, secțiunea „Contractele Odoo, evenimente și canale”.
Aceasta acoperă claim/execution, progres și așteptare, propuneri și aprobări,
dovezi și verificarea rezultatului. Fiecare comandă aplică autorizare,
politică de autonomie, tranziții valide, control de versiune, idempotency și
audit.

**Consecințe:** regula veche „Odoo nu primește scrieri AI în afara receipt-ului” este înlocuită pentru PMORG v2. Unele acțiuni sunt delegate, altele cer aprobare. Agenții nu primesc ORM sau SQL generic.

**Alternative respinse:** Odoo read-only; acces generic al LLM-ului; scrieri fără idempotency; aprobare umană pentru orice acțiune indiferent de risc.

## ADR-007 — Longitudinalitatea folosește stare persistentă și controller-e

**Status:** Proposed

**Decizie:** obligațiile, așteptările, politica și `next_check_at` sunt persistate în Odoo. Controller-ele se activează periodic sau la evenimente, reconstruiesc contextul din Odoo și memorie, execută un pas idempotent și programează următoarea verificare. Regulile obiective sunt deterministe; LLM-ul interpretează.

**Consecințe:** restartul nu pierde procesul; un agent nou poate continua; sunt obligatorii corelarea răspunsurilor, lease, retries și deduplicarea. Transcriptul este evidență, nu persistență.

**Alternative respinse:** conversație `--continue` eternă; agent permanent per task; cron fără stare; LLM pentru termene și tranziții obiective.

## ADR-008 — Hermes este candidatul de runtime, nu o condiție a MVP-ului

**Status:** Proposed

**Decizie:** MVP-ul folosește un runner determinist care implementează contractul final al orchestratorului. Hermes este integrat ulterior și trebuie să treacă aceleași teste de contract și scenarii longitudinale.

**Consecințe:** putem valida produsul fără a diagnostica simultan integrarea Hermes. Odoo și memoria nu se schimbă la înlocuirea runnerului. Hermes rămâne runtime numai dacă demonstrează claim atomic, reluare, idempotency, corelare și observabilitate.

**Alternative respinse:** Hermes integrat înaintea contractelor; respingerea Hermes fără test; cuplarea modelelor de internals Hermes; alegerea preventivă a altui orchestrator.

## ADR-009 — MVP-ul construiește real Odoo și memoria

**Status:** Proposed

**Decizie:** aplicația Odoo PMORG și memoria prin MCP sunt implementări reale, cu scop restrâns. Orchestrarea, timpul și comunicarea sunt simulate prin adaptoare care respectă contractele finale. Agentul și răspunsurile sunt întâi deterministe; un AI real se adaugă după smoke test.

**Consecințe:** schema, API-urile, validările, auditul și migrațiile nu sunt mock-uri de aruncat. Runnerul poate simula tăcere, duplicate, restart și indisponibilități. Un canal real este introdus numai după testul determinist.

**Alternative respinse:** mock-uri Odoo/memorie urmate de rescriere; Hermes și canale reale în primul MVP; demo conversațional fără stare persistentă; fine-tuning înaintea fluxului funcțional.

## ADR-010 — Zero teste în producție

**Status:** Proposed

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

**Status:** Proposed

**Decizie:** PMORG este o singură aplicație pentru utilizator, dar poate fi o suită de addon-uri: nucleu, Project, runtime, memorie și anchor packs.

**Consecințe:** dependențele și compatibilitatea sunt versionate; componentele se instalează în funcție de modulele active; UI-ul și permisiunile rămân unitare.

**Alternative respinse:** addon monolitic; aplicații vizibile separate pentru fiecare componentă; mapări de domeniu copiate în nucleu.

## ADR-012 — Self-hosting-ul LLM nu este garanție de confidențialitate

**Status:** Proposed

**Decizie:** arhitectura nu impune un LLM self-hosted ca premisă sau garanție. Confidențialitatea se tratează prin acces minim, politici, audit, contracte de date și evaluarea furnizorului.

**Consecințe:** furnizorul și runtime-ul pot fi schimbați fără redefinirea produsului; o evaluare de securitate rămâne necesară înaintea datelor reale.

**Alternative respinse:** self-hosting prezentat drept soluție completă; ignorarea celorlalte controale deoarece modelul rulează local.

## Întrebări rămase deschise

1. Schema și numele tehnice exacte ale modelelor.
2. Mașina de stare agentică și relația cu stage-urile Odoo.
3. Semnăturile, payload-urile și codurile de eroare exacte pentru API-ul de
   orchestrare deja delimitat.
4. Contractul MCP și comportamentul la indisponibilitatea memoriei.
5. Împărțirea tehnică dintre nucleu și anchor packs Project/Employees din
   MVP.
6. Matricea inițială de autonomie și aprobări.
7. Criteriile măsurabile de acceptare a Hermes.
8. Canalul real folosit după MVP-ul determinist.
