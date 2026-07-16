# PM organizațional

> **Direcția de produs PMORG v2 (în revizuire, 2026-07-16):** definiția
> țintă, arhitectura, MVP-ul și deciziile canonice sunt în
> [definiția PMORG v2](docs/pmorg-v2/00-PRODUCT.md). Acolo unde există o
> contradicție, documentele v2 descriu direcția propusă, iar acest README și
> documentele istorice descriu produsul implementat la commitul curent.
> Instrucțiunile de instalare de mai jos instalează implementarea curentă,
> **nu** aplicația Odoo PMORG v2.

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
| [definiția PMORG v2](docs/pmorg-v2/00-PRODUCT.md) | direcția țintă: produs, arhitectură, MVP, decizii și handoff |
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
