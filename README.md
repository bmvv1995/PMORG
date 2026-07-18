# PM organizațional

> **PMORG v3 — direcția de implementare acceptată (2026-07-18):** produsul
> rămâne operatorul organizațional persistent Odoo-first, dar noua generație
> se construiește ca fork guvernat al Onyx CE, cu PMORG Semantic Core drept
> bounded context first-class și Hermes drept orchestrator persistent vizat.
> Definiția canonică începe în
> [PMORG v3 — definiția produsului](docs/pmorg-v3/00-PRODUCT.md). V2 și
> sandboxurile existente rămân referințe înghețate; instrucțiunile de
> instalare din acest README descriu implementarea v1, nu v3. Cerința v3 este
> înghețată în `RB-1/C1`. La orice contradicție de direcție între v3 și v2,
> documentele v3 prevalează.

> **PMORG v2 (frozen-reference, 2026-07-18):** definiția
> țintă, arhitectura, MVP-ul, strategia datelor și sandboxul de evaluare sunt în
> [definiția PMORG v2](docs/pmorg-v2/00-PRODUCT.md). Documentele și contractele
> v2 rămân nemodificate semantic pentru reproducerea SB3 și portarea testelor;
> nu sunt a doua direcție activă. V2 este **Odoo-first și
> organization-agnostic**: ținta cere ca
> același build să fie validat pe profiluri sintetice de distribuție,
> servicii și Project-only.
> Instrucțiunile de instalare de mai jos instalează implementarea curentă,
> **nu** aplicația Odoo PMORG v2.

## Rolul acestui repository

Acest repository nu este codebase-ul produsului V3. Rolurile sunt separate:

| Artefact | Statut |
|---|---|
| `docs/pmorg-v3/` | cerința, contractele și criteriile canonice V3 (`RB-1/C1`) |
| codul V1/V2, sandboxurile și în special SB3 | baseline executabil de referință pentru migrare și regresie |
| `evaluation/`, `worldgen/` și scenariile longitudinale | active de evaluare care se portează și se recalifică pe V3 |
| repository-ul separat `PMORG-Platform` | viitorul codebase V3, pornit dintr-un fork Onyx CE fixat |

„Baseline executabil de referință” înseamnă că SB3 demonstrează comportamente
utile și furnizează teste, fixtures și oracles. Nu înseamnă că schema,
topologia, UI-ul sau codul SB3 sunt implementarea V3. Un comportament devine
V3 numai după portare pe contractele `RB-1/C1` și calificare în
`PMORG-Platform`.

## Implementarea curentă (v1 / snapshot)

Un conducător de procese organizaționale, artificial, instalat în casa
clientului: **operează** munca prin board și canale persistente, **ține
minte** organizația prin memorie ancorată în sursa ei formală (ERP-ul), și
**crește** numai prin proces aprobat de om.

Pe înțeles: un „manager de proiect" AI care trăiește pe serverul tău. Vorbești
cu el pe Telegram; el transformă inițiativele în sarcini pe un kanban, le
urmărește și escaladează ce se blochează. Tot ce decid și promit oamenii în
comunicarea care trece prin el se **sedimentează** într-o memorie legată de
înregistrările reale din Odoo — cu chitanță vizibilă acolo unde lucrează
oamenii. Iar când răspunde, memoria etichetează mecanic ce e **fapt** (există
acum în Odoo) și ce e doar **ipoteză**. Nimic din structura lui nu se schimbă
fără aprobarea explicită a patronului.

## Cum arată în funcțiune

1. Patronul scrie pe Telegram: *„Vreau să deschidem terasa până în iunie."*
2. Gateway-ul (listă închisă de identități) duce mesajul la **PM** — un agent
   Claude Code cu unelte îngrădite fizic: poate doar să lucreze pe kanban, să
   trimită mesaje și să programeze joburi. Nimic altceva.
3. PM-ul desface inițiativa în sarcini cu dependențe („gări") pe board și
   dispecerizează.
4. În paralel, **hook-ul de sedimentare** duce vorbele omului în memorie:
   angajamentele și deciziile se extrag, se ancorează la înregistrări Odoo
   reale (cine, ce proiect, ce comandă), iar identitatea autorului vine
   structural din gateway — nu se ghicește după nume.
5. Termenii privați (lista „niciodată la AI" a patronului) sunt opriți la
   poartă — refuzul se consemnează fără conținut.
6. Dimineața, ceasul livrează pe Telegram digestul memoriei: termene
   apropiate, angajamente fără responsabil, întrebări rămase deschise —
   text determinist, fără să repete ce a livrat deja.
7. Orice schimbare de structură (agent nou, om nou în listă, regulă nouă)
   trece prin cerere → aprobarea ritualică a patronului → execuție cu commit
   git. Totul e reversibil și auditabil.

## Componentele (fiecare cu o singură treabă)

| Componentă | Rolul | Ce NU este |
|---|---|---|
| **PM pe Claude Code** — creierul | orchestrator: primește inițiative, desface în sarcini, urmărește, escaladează; unelte îngrădite fizic (doar MCP, built-ins interzise) | nu scrie în memorie; nu-și schimbă propria constituție |
| **Hermes + puntea** — corpul de proces | kanban cu gări, gateway Telegram cu listă închisă, ceas (cron), ritual de aprobare cu executor separat ([hermes-agent](https://github.com/NousResearch/hermes-agent), nemodificat) | nu e registrul durabil al organizației |
| **aipm** — memoria | sedimentarea: extrage decizii/angajamente din comunicarea oamenilor, le ancorează în Odoo, lasă chitanță, răspunde cu claims validate mecanic | nu e autoritate pe starea curentă — se retrogradează singură la ipoteză |
| **Odoo** — sursa formală | scheletul lumii: singura ancoră legitimă (angajați, proiecte, parteneri, comenzi) | nu primește scrieri de la AI în afara chitanței |

Imaginea de ansamblu: *kanban-ul e aparatul circulator, aipm e sedimentarea,
Odoo e scheletul lumii, PM-ul e singurul cititor al tuturor.*

## Legile produsului (pe scurt)

- **Oamenii decid, AI-ul propune.** Faptele memorate au autori umani; textul
  produs de AI nu devine niciodată fapt.
- **Lume închisă.** Ce nu e în listă (identități, ancore, board-uri) nu
  există — sistemul știe și când NU știe, și înregistrează golul în loc să
  inventeze.
- **Adevărul curent se citește pe viu.** Starea lumii = Odoo, acum; memoria e
  doar context istoric, forțat de cod la rang de ipoteză.
- **Poarta înaintea conductei.** Nicio sursă nu se leagă la memorie înainte ca
  filtrul de intimitate și păstrarea autorului real să existe pe acel drum.
- **Totul reversibil și auditabil.** Structura în git, memoria cu chitanță,
  jurnalul append-only; „ce s-a schimbat săptămâna asta?" are răspuns.
- **Creșterea prin proces.** Orice extindere = cerere → aprobare umană →
  execuție de infrastructură → urmă imuabilă.

Legea completă: [`docs/INTENT-UNIFICARE.md`](docs/INTENT-UNIFICARE.md).

## Instalarea implementării curente

Pe un server cu PostgreSQL 16 (+pgvector), `tmux`, `git`, `python3` și
`claude` autentificat:

```bash
git clone https://github.com/bmvv1995/PMORG ~/PMORG
cd ~/PMORG/components/pm-organizational
./install.sh        # idempotent; instalează și Hermes dacă lipsește
```

Installer-ul ridică tot stack-ul: puntea, uneltele PM-ului, profilul de
gateway, memoria (cu backup zilnic) și hook-ul de sedimentare. Memoria
aterizează **inertă** — conducta se deschide printr-o decizie explicită,
după configurare. Ghidul complet, pas cu pas:
[`docs/GO-LIVE.md`](docs/GO-LIVE.md).

## Documentația (în ordinea de citit)

| Document | Ce explică |
|---|---|
| [definiția PMORG v3](docs/pmorg-v3/00-PRODUCT.md) | produsul bazat pe fork Onyx, Semantic Core, arhitectura, MVP-ul și migrarea |
| [requirements baseline v3](docs/pmorg-v3/08-REQUIREMENTS-BASELINE.md) | cerințele normative, scope-ul înghețat și readiness-ul pentru implementare |
| [supersession contracte v2 → v3](docs/pmorg-v3/14-V2-CONTRACT-SUPERSESSION.md) | maparea explicită a operațiilor, erorilor, comenzilor și idempotency |
| [definiția PMORG v2](docs/pmorg-v2/00-PRODUCT.md) | intrarea în suita canonică v2 și ordinea completă de lectură |
| [strategia de date a memoriei](docs/pmorg-v2/05-MEMORY-DATA.md) | cum construim lumea, oamenii și adevărul măsurabil fără date de producție |
| [sandboxul complet de evaluare](docs/pmorg-v2/06-EVALUATION-SANDBOX.md) | izolarea SUT–oracle, run bundle, worldgen, corpus, scoring și fazare |
| acest README | produsul, pe înțeles |
| [`docs/INTENT-UNIFICARE.md`](docs/INTENT-UNIFICARE.md) | legea: componentele, principiile P1–P6, joncțiunea unică, fluxurile |
| [`docs/PLAN-INTEGRARE.md`](docs/PLAN-INTEGRARE.md) | etapele construite, deciziile consemnate (D1–D4), starea fiecăreia |
| [`docs/GO-LIVE.md`](docs/GO-LIVE.md) | instalarea pe server, pas cu pas |
| [`aipm/README.md`](aipm/README.md) | componenta de memorie: arhitectură, dev, deploy, teste |
| [`components/pm-organizational/README.md`](components/pm-organizational/README.md) | installer-ul și rețeta produsului |
| `docs/aipm/`, `docs/mostenire-pm-organizational/` | moștenirea celor două linii: intent-uri, spec-uri, analize |

## Structura repo-ului

```
docs/                  documentele-lege + planul + ghidul de go-live + moștenirea
aipm/                  CODUL memoriei (sursa de dezvoltare): motor, adaptor Odoo
                       (xmlrpc + fake cu fixtures), migrări PG, API, UI, teste
components/            instantanee ale codului viu de pe server:
  hermes-ops-mcp/      serverul MCP cu uneltele îngrădite ale PM-ului
  cc-bridge/           puntea Hermes↔Claude Code (shim + executor de aprobare)
  pm-organizational/   installer-ul + template-urile (workdir PM, hook, digest)
```

**Sursa vie vs instantaneu:** `aipm/` de aici e sursa de dezvoltare;
`components/` sunt instantanee datate — sursa vie rulează pe server. La
modificări pe server, instantaneele se reîmprospătează cu `git archive`.

## Starea implementării curente

Toate cele 10 etape din [planul de integrare](docs/PLAN-INTEGRARE.md) sunt
implementate (2026-07-08/09): **109 teste verzi**, iar conducta de sedimentare
(Telegram → gateway → identitate → poarta de intimitate → memorie) e
**validată cap-coadă pe Telegram real**. Rămase deliberat pentru go-live:
crearea `project.project` în Odoo la crearea board-ului, forma buclei de
contestare a chitanțelor și trunchierea de 500 de caractere din hook-ul
Hermes (candidat de contribuție upstream).
