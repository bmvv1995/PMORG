# INTENT — AI-PM pe fundația Odoo

> Documentul de arhitectură al proiectului AI-PM (nume de lucru): un AI ca Project Manager
> organizațional, ancorat în Odoo. Sintetizează filozofia validată în laboratorul nous,
> fără drifturile parcursului. Acesta e punctul de plecare — nu istoricul.

## Problema fundamentală

Organizațiile își înregistrează activitatea cu precizie: taskuri, termene, pontaje, facturi.
Dar munca reală de management trăiește în golul dintre înregistrări — decizii, angajamente,
context, „de ce"-uri. ERP-ul știe *ce* s-a întâmplat. Nu știe *de ce*, cine s-a angajat la ce,
și ce a dus la rezultat.

LLM-urile sunt capabile să umple acest gol conversațional — dar sunt negovernate. Fără o
ancoră formală, un AI care vorbește despre organizație **speculează**, iar speculația
prezentată cu încredere e mai periculoasă decât ignoranța.

**Întrebarea centrală:** cum construiești un AI-PM care înțelege organizația — și o poate
asista activ — fără să-i inventeze realitatea?

## Moștenirea nous: șase principii

Acestea sunt distilate din laboratorul nous (chatbot ancorat ontologic, speță: bibliotecă).
Domeniul a fost întotdeauna irelevant; pattern-ul e universal.

**P1 — Ancorarea.** Un fapt este o înregistrare în sursa formală. Orice afirmație a AI-ului
despre starea organizației trimite la o înregistrare Odoo. Ce nu e ancorat nu e fapt —
e ipoteză, și circulă etichetat ca ipoteză.

**P2 — Autoritatea inversată.** AI-ul nu decide; produce materie primă — candidați, scoruri,
propuneri, draft-uri. Validarea aparține sistemului formal și omului. AI analizează, explică,
propune; managementul decide.

**P3 — Veto pe acțiune, nu pe conversație.** Lecția cea mai scumpă din nous: rigiditatea a
venit din prompturi, nu din ancorare. Conversația e liberă — caldă, creativă, cu personalitate
(definită separat, ca *politică de agent*). Poarta formală se aplică în exact două momente:
când se afirmă un fapt și când se execută o acțiune.

**P4 — Trasabilitatea.** Orice acțiune sau blocare are un lanț vizibil:
acțiune → regulă → sursă → autor. Întrebarea organizațională corectă nu e „cine a greșit?",
ci „cum a permis sistemul asta?" — și sistemul trebuie să poată răspunde.

**P5 — Evoluția guvernată.** Ce nu poate fi mapat devine gap; gap-urile recurente devin
propuneri; propunerile trec prin poarta umană; sistemul crește. Rata schimbării e inversă
autorității stratului: datele curg liber, regulile se schimbă ocazional, principiile rar.

**P6 — Poarta umană e o experiență de UI.** Guvernanța pe care omul nu o vede nu există.
Propunerea, evidența, dezbaterea și butonul de decizie sunt interfață, nu API. Nicio
capabilitate a sistemului nu e „gata" până nu are o față vizibilă.

## Driftul eliminat conștient

Ce lăsăm în urmă din parcursul nous, ca decizie, nu ca uitare:

- **Dezbaterea de stack** (GraphDB vs RDFox, Nemo, SOML, Fuseki). Irelevantă aici: fundația
  formală nu se mai construiește — există deja și se numește Odoo.
- **Construcția de ontologie proprie** și domeniul-sandbox (biblioteca). Laboratorul și-a
  făcut treaba; nu portăm codul, portăm principiile și mecanismele validate.
- **Personalitatea ca gând ulterior.** În nous, politica de agent a rămas neconstruită și
  vocea sistemului a devenit un funcționar de ghișeu. Aici se proiectează de la început.

Ce reținem ca mecanisme validate: maparea cu scoruri de încredere + praguri pe tip de
acțiune; bucla gap → propunere → decizie umană; provenance (evidența deciziilor);
învățarea din deciziile anterioare ale omului.

## De ce Odoo e fundația

Orice ERP este deja o ontologie — entități (proiect, task, angajat, client, factură),
relații (un task aparține unui proiect), reguli (nu facturezi fără livrare) — doar că
modelul e îngropat în cod. Nu construim ontologia: **o folosim**. Odoo e kernelul —
sursa de adevăr despre ce există și ce e permis. AI-PM-ul nu înlocuiește Odoo;
îl face inteligibil și îi adaugă stratul care îi lipsește: memoria lui „de ce".

## Decizia de fundație: Odoo-first, generic la cusătură

Gândim generic **doar la cusătură**; construim strict pe Odoo. Decizie luată la 2026-07-07,
ca să nu fie redeschisă implicit:

- **Contractul de ancoră.** Produsul (conversație, memorie, poartă, UI) vorbește cu E1
  printr-un contract unic: ce tipuri de entități există, ce structură au, caută înregistrări,
  citește, scrie cu provenance. Prima și singura implementare: **adaptorul Odoo**.
- **Adaptorul e discovery-driven.** Odoo e auto-descriptiv la runtime (`ir.model`,
  `ir.model.fields`): ontologia se citește singură. Stratul de produs nu hardcodează
  NICIODATĂ nume de modele Odoo — aceeași disciplină pe care nous a avut-o cu SPARQL
  (zero hardcodări de domeniu).
- **De ce nu „ERP generic" ca țintă de proiectare:** (1) ai construi meta-produsul
  (stratul de descoperire universal) înainte de produs; (2) ai proiecta pentru cel mai
  sărac numitor comun și ai pierde bogăția Odoo — în primul rând **chatter-ul**
  (discuțiile atașate nativ fiecărei înregistrări), care e un proto-E2 gata făcut.
- **Portabilitatea pe alt ERP = un adaptor nou, nu o rescriere.** Dacă disciplina
  anti-hardcodare se respectă, „generic ERP" devine o consecință a igienei, nu un
  proiect plătit în avans.

## Arhitectura memoriei: trei etaje

```
E3  REGULILE      guvernanță: cine poate ce, ce escaladează, ce cere confirmare
    (puține, explicite, aprobate de om, versionate)      — se schimbă RAR, prin poartă
E2  DE CE-URILE   memoria asociativă: decizii, discuții, angajamente, context
    (crește liber; fiecare amintire ANCORATĂ la înregistrări Odoo)  — crește CONTINUU
E1  FAPTELE       Odoo: starea reală — taskuri, termene, oameni, cifre
    (source of truth; citit live, NICIODATĂ duplicat)    — curge LIBER
```

- **E1 — Faptele.** Odoo, citit în timp real. Memoria AI-ului nu ține copii ale faptelor;
  altfel memoria și realitatea diverg în două săptămâni.
- **E2 — De ce-urile.** Ce Odoo nu stochează: de ce s-a mutat termenul, cine s-a angajat
  la ce în ședință, ce context a dus la decizie. Strat flexibil (aici trăiesc tehnologiile
  de memorie asociativă — Cognee sau echivalent), cu regula de aur: fiecare amintire e
  legată de entități Odoo reale. E2 **informează** conversația — nu afirmă fapte și nu
  execută nimic.
- **E3 — Regulile.** Overlay-ul de guvernanță: mic, explicit, uman-aprobat. Echivalentul
  „regulilor de business" din nous.

Ipotezele din E2 au voie să formuleze întrebări și sugestii („parcă v-ați angajat la
vineri — confirm?"), niciodată afirmații și acțiuni. Flexibilitate în percepție,
rigiditate în acțiune.

## Poarta de scriere

AI-ul **citește liber** (E1 + E2). AI-ul **scrie** — creează task, mută termen, notifică —
doar prin una din două căi:

1. **Reguli pre-aprobate** (E3): clase de acțiuni delegate explicit de om, cu praguri.
2. **Confirmare umană per acțiune**: propunerea, cu evidența ei, în fața omului.

Fiecare scriere poartă provenance: cine a cerut-o, pe ce evidență, sub ce regulă.

## Praguri: costul acțiunii dictează rigoarea

Mecanismul de scoruri din nous rămâne, remapat pe costul acțiunii:

| Acțiune | Cost | Prag de încredere |
|---|---|---|
| A răspunde la o întrebare (cu ancoră) | mic | relaxat |
| A semnala / notifica | mediu | mediu |
| A scrie în Odoo | mare | strict + regulă sau confirmare |
| A propune o regulă nouă (E3) | maxim | doar prin sesiune de guvernanță |

Sub prag → clarificare, nu ghicit. Pragurile sunt declarate în E3, nu îngropate în cod.

## Rolurile AI-ului (funcții, nu agenți)

1. **Interlocutor** — conversația cu oamenii; personalitatea vine din politica de agent.
2. **Grefier** — captează din conversații decizii, angajamente, context → E2, ancorat.
3. **Analist** — reconstruiește lanțuri: cum a ajuns proiectul aici, ce reguli au interacționat.
4. **Consilier** — transformă gap-urile recurente în propuneri pentru poarta umană.

## Cele două bucle

**Bucla operațională (zilnic):** întrebări și răspunsuri ancorate, actualizări, semnalări,
capturi de decizie. Rulează continuu, fără om în buclă la citire, cu poartă la scriere.

**Bucla de guvernanță (ritmică):** organizațiile au deja ritualurile — weekly, retro,
steering. Ele devin sesiunile în care propunerile acumulate (reguli noi, delegări,
ajustări) se dezbat și se aprobă. Ședințele produc ceva executabil. Managementul e
legiuitorul; AI-ul e consilierul care pregătește dosarele.

## Principii de dezvoltare

- **UI-first.** Fiecare capabilitate există când e vizibilă: peretele de propuneri,
  lanțul de trasabilitate, memoria consultabilă. Utilizatorul acestui proiect trăiește prin UI.
- **Anti-halucinație în orice stadiu.** Din prima zi, orice răspuns e ancorat sau etichetat
  ipoteză. Nu există fază „întâi funcționează, apoi devine onest".
- **Iterativ, cu principiul minim.** Prima victorie: citire ancorată + memorie de decizie
  pe un singur proiect real, cu poartă de scriere manuală.
- **nous rămâne laboratorul.** Donor de pattern și de mecanisme, nu bază de cod obligatorie.

## Ce NU este acest proiect

- Nu înlocuiește Odoo și nu duplică datele lui.
- Nu decide în locul oamenilor și nu automatizează managementul.
- Nu e „un chatbot cu acces la baza de date" — e un strat de inteligibilitate și memorie
  guvernată peste organizație: sistemul care știe nu doar *ce* s-a întâmplat, ci și *de ce*
  — și care poate spune oricând *de unde știe*.
