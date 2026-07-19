# PMORG v3 — definiția produsului

| Câmp | Valoare |
|---|---|
| Status | Accepted — requirements baseline `RB-1/C2` |
| Versiune | `3.0-baseline.3` |
| Data | 2026-07-19 |
| Bază de implementare | fork guvernat al Onyx, cu profil de livrare CE sau licensed-EE declarat; tagul și SHA-ul se fixează la bootstrap |
| Ancoră de domeniu | Odoo 19 Community, cu revizia exactă fixată în manifestul fiecărui build |

## 1. Definiție

> **PMORG este un operator organizațional persistent, Odoo-first, construit pe
> baza Onyx, care transformă inițiativele în rezultate verificate și păstrează
> o memorie organizațională ancorată, temporală și validată.**

PMORG:

1. primește sau identifică o inițiativă;
2. discută cu persoanele relevante;
3. clarifică obiectivul, constrângerile și criteriile de succes;
4. generează un plan și taskuri;
5. identifică responsabili și termene și obține confirmări;
6. urmărește execuția zile sau luni;
7. observă lipsa progresului, contradicțiile și blocajele;
8. inițiază conversații, adaptează planul și escaladează;
9. verifică rezultatul și închide bucla;
10. păstrează proveniența, autoritatea, istoria și lecțiile validate.

„Persistent” înseamnă că inițiativa, obligațiile, starea de așteptare și
următoarea acțiune supraviețuiesc restarturilor, schimbării agentului și
trecerii timpului. Nu înseamnă o conversație sau un proces LLM permanent.

Unitatea centrală este **inițiativa**. Taskurile, conversațiile, claims și
execuțiile sunt mijloacele prin care inițiativa ajunge la un rezultat.

## 2. Ce se schimbă în v3

V3 este o nouă generație de implementare a aceluiași produs, nu un produs cu
altă intenție.

- Onyx devine codebase-ul, workspace-ul cognitiv și baza de UI, chat,
  knowledge, RAG, agenți și actions. Capabilitățile CE sau EE existente se
  folosesc conform profilului de livrare declarat; PMORG nu le rescrie numai
  pentru a evita o dependență EE.
- PMORG Semantic Core devine un bounded context obligatoriu în produs, nu un
  add-on opțional și nici un simplu index Onyx.
- Odoo rămâne ontologia executabilă, registrul muncii formale și sursa
  adevărului operațional curent.
- Un orchestrator persistent coordonează procesele în timp; Onyx-PMORG execută
  pași cognitivi limitați și explicabili. Hermes este o implementare candidată,
  nu o cerință a produsului.
- Communication Gateway normalizează identitatea, conversațiile și
  livrarea pentru canalele externe.

Prin urmare, produsul nu este „Onyx + un plugin PMORG” și nici patru produse
lipite. Este **PMORG Platform**, construită dintr-un fork guvernat Onyx, cu
Odoo și orchestratorul persistent ca sisteme contractuale distincte.

## 3. Promisiunea de business

- Fiecare inițiativă activă are o stare observabilă și fie o acțiune
  următoare programată, fie o stare explicită `blocked`, `paused` sau
  `degraded`.
- Fiecare responsabilitate și angajament primește un statut explicit în
  termenul configurat de politică.
- Fiecare blocaj produce o intervenție, o escaladare sau o explicație
  explicită pentru inacțiune.
- Fiecare schimbare importantă de plan este explicabilă retrospectiv.
- Niciun rezultat nu este închis fără criterii, dovezi și autoritatea cerută.
- O informație contradictorie nu este ascunsă și o informație nouă nu șterge
  istoria pe care o înlocuiește.
- O schimbare materială formală fără proveniență consemnată produce o
  suspiciune măsurabilă și o buclă de clarificare, nu o acuzație.

## 4. Modelul produsului

```text
PMORG Platform (fork Onyx)
+ Semantic Core și memoria organizațională
+ Odoo și modulele/anchor packs active
+ orchestratorul persistent sau runnerul contractual
+ Communication Gateway și canalele autorizate
+ politici, identități și date
= operatorul unei organizații concrete
```

PMORG este agnostic față de organizația concretă — industrie, dimensiune,
structură și set de module — dar Odoo-first. Specificul organizației intră
prin module Odoo, anchor packs, roluri, permisiuni, politici și date, nu prin
fork-uri per client.

Același build trebuie să funcționeze în cel puțin trei profiluri sintetice:

1. organizație minimală, cu Project;
2. servicii profesionale, cu Project și Employees;
3. distribuție, cu Project, Employees și Inventory.

Un modul absent înseamnă că vocabularul său operațional este indisponibil.
LLM-ul nu îl poate inventa și nici activa.

## 5. Cele trei lumi semantice

PMORG separă explicit:

| Lume | Conținut | Regulă |
|---|---|---|
| Evidență deschisă | conversații, documente, observații și formulări libere | poate conține orice termen, inclusiv neclar sau extern |
| Memorie organizațională | claims, decizii, angajamente și lecții validate | necesită proveniență, ancorare, autoritate și temporalitate |
| Lume operațională închisă | entități, stări și acțiuni formale Odoo | există numai prin registry, ACL și politici active |

Fluxul normal este:

```text
sursă → evidență → claim candidat → validare → memorie validată
                                      ↓
                         efect formal Odoo, dacă este necesar
```

RAG-ul, embeddings și memoria personală generică Onyx pot ajuta la găsire și
context. Ele nu transformă singure un text în adevăr organizațional.

## 6. Invariante de produs

1. Odoo spune ce este formal adevărat acum și ce efect operațional există.
2. Semantic Core spune ce s-a observat, cine a afirmat, ce a fost validat și
   cum s-a schimbat în timp.
3. Niciun output LLM nu devine fapt sau comandă doar pentru că a fost generat.
4. Nicio mutație nu ocolește comenzi de business autorizate, versionate,
   idempotente și auditate.
5. Orice claim organizațional are evidență, autor, scope, timp și statut.
6. Closed world-ul operațional este derivat determinist din Odoo și anchor
   packs; necunoscutul rămâne necunoscut.
7. Starea procesului se reconstruiește fără transcriptul sau sesiunea unui
   anumit model.
8. Retry-ul, restartul și evenimentele duplicate nu produc efecte duble.
9. Indexul de căutare este reconstruibil; ledgerul semantic și starea Odoo
   nu sunt.
10. Același artefact PMORG funcționează în organizații diferite fără cod
    specific clientului.
11. Orice verdict de evaluare este invalid dacă SUT poate citi oracle-ul,
    gold labels sau scorerul.
12. **Niciun test, benchmark sau pilot nu rulează în producție.**
13. Interpretarea memoriei este automată; omul guvernează numai vocabularul și
    matching-ul de ancoră ambiguu cu consecință.
14. Privacy/secrets gate rulează după identitate și înaintea oricărei stocări,
    indexări sau execuții cognitive.
15. Efectele materiale fără proveniență sunt detectate determinist și intră în
    rata de acoperire; un gap rămâne suspiciune, nu verdict despre o persoană.

## 7. În scop

- fork-ul Onyx-PMORG și experiența unitară de produs;
- Semantic Core, ledgerul semantic și proiecțiile sale de căutare;
- integrarea Odoo, aplicația/addon-urile PMORG și anchor packs;
- inițiative, planuri, taskuri, angajamente, intervenții și rezultate;
- orchestration contract, runnerul determinist și adaptoare de orchestrator (Hermes opțional);
- Communication Gateway și adaptoare de canal;
- politici de autonomie, aprobări, audit, observabilitate și moduri degradate;
- sandboxul, datele sintetice și corpusul de evaluare.

## 8. În afara scopului inițial

- construirea sau înlocuirea ERP-ului;
- o ontologie universală independentă de Odoo;
- copierea integrală a Odoo în Onyx ori în Semantic Core;
- acces ORM/SQL generic pentru agenți;
- o sesiune LLM permanentă drept mecanism de urmărire;
- mapări custom promovate automat de model;
- fine-tuning înaintea unei suite măsurabile;
- confidențialitate pretins garantată numai printr-un LLM self-hosted;
- date, persoane, credențiale sau canale de producție în evaluare.

## 9. Relația cu v2 și implementările existente

PMORG v2 și sandboxurile SB2/SB3 rămân referințe înghețate. V3 preia
invariantele, comportamentele utile, scenariile și testele, dar nu presupune că
schema `aipm`, addon-urile prototip sau topologia lor sunt producție-ready.
Wire contractele v2 sunt superseded explicit pentru v3; portarea se face prin
[mapare și teste de contract](14-V2-CONTRACT-SUPERSESSION.md), nu prin copiere
nediferențiată sau aliasuri tăcute.

Documentele v3 sunt normative pentru noua generație acolo unde contrazic
direcția v2. Implementarea curentă v1/v2 nu trebuie descrisă ca v3.

## 10. Ordinea de lectură

1. definiția produsului — acest document;
2. [requirements baseline](08-REQUIREMENTS-BASELINE.md);
3. [deciziile](03-DECISIONS.md);
4. [arhitectura](01-ARCHITECTURE.md);
5. [modelul de domeniu și Semantic Core](02-DOMAIN-MODEL.md);
6. [contractele v1](09-CONTRACTS.md);
7. [supersession-ul contractelor v2](14-V2-CONTRACT-SUPERSESSION.md);
8. [state machines și politicile](11-STATE-MACHINES-POLICIES.md);
9. [scenariul canonic XNX](10-XNX-REFERENCE-SCENARIO.md);
10. [MVP-ul](04-MVP.md);
11. [criteriile de acceptare și trasabilitatea](12-ACCEPTANCE-TRACEABILITY.md);
12. [evaluarea](06-EVALUATION.md);
13. [matricea de migrare v2 → v3](05-V2-MIGRATION-MATRIX.md);
14. [politica fork-ului Onyx](07-ONYX-UPSTREAM-POLICY.md);
15. [profilurile organizaționale de conformitate](13-ORGANIZATION-PROFILES.md).
