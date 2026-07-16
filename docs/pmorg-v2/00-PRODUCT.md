# PMORG — definiția produsului

| Câmp | Valoare |
|---|---|
| Status | Aprobat — canonic (2026-07-16) |
| Versiune | 0.1 |
| Data | 2026-07-16 |
| Domeniu | Produsul-țintă, nu numai MVP-ul |
| Baseline tehnic inițial | Odoo 19 Community |

## Definiție

> **PMORG este o aplicație Odoo care funcționează ca operator organizațional persistent: transformă inițiativele în rezultate verificate folosind ontologia și starea formală din Odoo, un runtime extern de orchestrare și o memorie organizațională externă accesibilă prin MCP.**

PMORG:

1. primește sau identifică o inițiativă;
2. discută cu persoanele relevante;
3. clarifică obiectivul, constrângerile și criteriile de succes;
4. generează un plan și taskuri;
5. stabilește responsabili și termene și obține confirmări;
6. urmărește execuția zile sau luni;
7. detectează tăcerea, întârzierile și blocajele;
8. inițiază conversații, replănuiește și escaladează;
9. verifică rezultatul și închide bucla;
10. păstrează proveniența, deciziile și lecțiile relevante.

„Persistent” înseamnă că inițiativa, obligațiile, așteptările și următoarele acțiuni supraviețuiesc restarturilor și trecerii timpului. Nu înseamnă un LLM sau o conversație pornită permanent.

## Promisiunea de business

- Fiecare inițiativă activă are permanent o stare observabilă și fie o
  acțiune următoare programată, fie o stare explicită `blocked`, `paused` sau
  `degraded`.
- Fiecare responsabilitate și angajament are, în termenul configurat de
  politică, un statut explicit.
- Fiecare blocaj produce în intervalul configurat o intervenție, o escaladare
  sau o explicație explicită că politica ori pauza de urgență interzice
  acțiunea.
- Fiecare schimbare importantă de plan este explicabilă.
- Niciun rezultat nu este închis fără criterii și dovezi verificabile.

Unitatea centrală este **inițiativa**, nu taskul. Taskurile sunt mijloacele prin care inițiativa ajunge la rezultat.

## Componente și responsabilități

| Componentă | Responsabilitate canonică |
|---|---|
| **Odoo + aplicația PMORG** | Ontologie, stare formală, inițiative, planuri, taskuri, politici, aprobări, rezultate, UI și audit |
| **Orchestrator extern** | Claim, programări, controller-e, agenți, conversații, retries și reluare după restart |
| **Agenți AI** | Clarificare, interpretare, planificare, comunicare și evaluare |
| **Memorie externă prin MCP** | Evidențe, claims, proveniență, contradicții, temporalitate, decizii și lecții |
| **Canale** | Transportul mesajelor; nu dețin starea inițiativei |

Hermes este runtime-ul vizat inițial, dar contractul PMORG nu depinde de detaliile sale interne.

## Ciclul inițiativei

```text
draft
  -> clarifying
  -> planned
  -> awaiting_confirmation
  -> active
  -> verifying
  -> closed
```

`at_risk` și `blocked` pot apărea în timpul execuției. O inițiativă poate reveni la clarificare sau planificare. `cancelled` necesită decizie autorizată și motiv; nu este dispariție tacită.

| Tranziție | Condiție minimă |
|---|---|
| `draft -> clarifying` | sursă și owner identificabile |
| `clarifying -> planned` | obiectiv, constrângeri și criterii suficiente |
| `planned -> awaiting_confirmation` | plan versionat și responsabilități propuse |
| `awaiting_confirmation -> active` | confirmări sau excepții aprobate |
| `active -> verifying` | execuție terminată și dovezi candidate |
| `verifying -> closed` | criterii verificate și rezultat aprobat conform politicii |

## Modelul Odoo PMORG

Aplicația adaugă conceptele de business care lipsesc din Odoo Project și extinde `project.task`.

Obiectele de prim nivel sunt:

- inițiativă, obiectiv și criteriu de succes;
- plan și versiune de plan;
- angajament și confirmare;
- intervenție și escaladare;
- rezultat și dovadă;
- politică de monitorizare și autonomie;
- ancoră Odoo și referință de memorie;
- execuție și eveniment de task.

Numele tehnice exacte se stabilesc în proiectarea schemei, fără eliminarea implicită a conceptelor.

## Taskurile

`project.task` este registrul canonic al muncii organizaționale create sau urmărite de PMORG. El este extins pentru:

- execuție `human`, `agent`, `hybrid` sau `monitor`;
- clarificare, investigație, planificare, execuție, follow-up, confirmare, monitorizare, escaladare și verificare;
- rezultat așteptat, termen, participanți și ancore;
- stare agentică, claim, lease, idempotency și verificarea rezultatului.

Un task precum „Discută cu gestionarul pentru clarificarea incidentului XNX” este valid în Odoo: agentul este executor, gestionarul este participant, incidentul este subiect ancorat, iar concluzia verificabilă este rezultatul așteptat.

Pașii tehnici efemeri, apelurile de instrumente și retries nu devin taskuri Odoo; ele sunt execuții sau evenimente asociate taskului.

## Ontologia și anchor packs

Odoo este limbajul formal al organizației. PMORG extrage numai entitățile de business de prim nivel din modulele active, configurate și accesibile, folosind **anchor packs** versionate.

```text
modul instalat
+ proces configurat
+ permisiuni disponibile
+ anchor pack compatibil și aprobat
= vocabular utilizabil de PMORG
```

Exemple:

- Project: proiect, task, milestone, dependență;
- Employees: angajat, departament, funcție, manager;
- Time Off: cerere, tip de concediu, alocare, aprobare;
- Sales: client, ofertă, comandă;
- Inventory: produs, depozit, transfer, mișcare;
- Accounting: factură, plată, scadență.

Activarea unui modul extinde vocabularul posibil; nu copiază automat toate datele în memorie. Dacă Employees este activ, dar Time Off nu este activ și configurat, PMORG nu tratează o afirmație conversațională drept concediu aprobat.

Maparea modulelor standard cunoscute este deterministă la runtime. Pentru customizări necunoscute, sistemul poate propune o mapare, dar promovarea ei este umană și explicită.

## Memoria organizațională

Memoria este externă și accesibilă prin MCP:

```text
evidență brută
  -> candidat de memorie
  -> memorie organizațională validată
  -> obiect formal Odoo, dacă informația produce efect operațional
```

Validarea verifică identitatea, proveniența, autoritatea, consistența sau contradicția, valabilitatea temporală, confirmarea necesară și supersession.

Memoria păstrează contextul și istoria. Odoo păstrează starea formală curentă. În Odoo se stochează referințe, rezumate operaționale, receipts, dovezi și obiectele formale rezultate, nu întreaga memorie semantică.

## Autonomie și scrieri în Odoo

Acțiunile sunt clasificate ca `read`, `recommend`, `execute_delegated`,
`approval_required` sau `prohibited`.

Orchestratorul scrie în Odoo numai prin comenzi de business înguste, autorizate, validate, idempotente și auditate. Agenții nu primesc acces generic la ORM. Calculele obiective — termene, tăcere, lease, retry, dependențe — sunt deterministe; LLM-ul este folosit pentru interpretare și propuneri.

## Invariante

1. Starea procesului poate fi reconstruită fără transcriptul unei sesiuni LLM.
2. Orice efect operațional este formalizat în Odoo.
3. Nicio afirmație contradictorie nu este promovată drept adevăr fără marcarea sau rezolvarea contradicției.
4. Nicio acțiune nu se dublează din cauza retry-ului sau a unui eveniment repetat.
5. Informația nouă poate înlocui informația veche fără ștergerea istoriei.
6. Orice decizie, intervenție și escaladare importantă este explicabilă retrospectiv.

## În scop

- aplicația Odoo PMORG și extensia `project.task`;
- inițiative, planuri, angajamente, intervenții și rezultate;
- anchor packs pentru module Odoo;
- contractele pentru orchestrator, memorie și canale;
- memoria externă prin MCP;
- controller-e longitudinale, politici, validare, audit și dovezi.

## În afara scopului

- înlocuirea Odoo sau construirea unui ERP;
- o ontologie universală independentă de Odoo;
- copierea integrală a Odoo în memorie;
- rularea LLM-urilor în procesele tranzacționale Odoo;
- sesiunea LLM „eternă” drept mecanism de persistență;
- promovarea automată a mapărilor custom necunoscute;
- garantarea confidențialității exclusiv prin self-hosting-ul modelului.

## Relația cu MVP-ul

MVP-ul implementează real Odoo PMORG și memoria, dar simulează orchestrarea, timpul și canalele prin contractele finale. Folosește exclusiv date sintetice și medii separate de producție. Hermes este integrat după validarea fluxului de produs.

Suita se citește în această ordine:

1. definiția produsului — acest document;
2. [arhitectura țintă](01-ARCHITECTURE.md);
3. [MVP-ul de validare](02-MVP.md);
4. [registrul deciziilor](03-DECISIONS.md);
5. [handoff-ul primei sesiuni de implementare](04-NEXT-SESSION.md).

Deciziile devin normative numai după schimbarea explicită a statutului lor
din `Proposed` în `Accepted`.
