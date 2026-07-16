# PMORG — strategia de date a memoriei

| Câmp | Valoare |
|---|---|
| Status | Propunere canonică pentru revizuire |
| Versiune | 0.2 |
| Data | 2026-07-16 |
| Domeniu | Corpusul care calibrează și validează memoria organizațională |
| Relație | completează [MVP-ul](02-MVP.md), este concretizată de [sandboxul complet](06-EVALUATION-SANDBOX.md) și nu modifică gate-urile A–F |

## 1. Dilema fondatoare

Memoria organizațională pe care o construim nu a fost văzută de nimeni
funcționând pe date reale. Datele care i-ar demonstra valoarea — conversații
AI↔angajați cu clarificări, reveniri, contradicții și rezoluții, ancorate în
starea formală a unei organizații — nu există nicăieri, pentru că nimeni nu
și-a propus să le strângă cu această relevanță. Iar colectarea lor
responsabilă cere exact sistemul pe care datele ar trebui să-l valideze.

Acesta este un cerc vicios, nu o etapă întârziată. El nu se rupe așteptând
date reale; se rupe **construind adevărul, nu colectându-l**:

> Într-o lume generată, adevărul fiecărui eveniment și al fiecărei conversații
> este cunoscut prin construcție. Calitatea memoriei devine măsurabilă fără ca
> vreo organizație reală să fi fost expusă unui sistem nevalidat.

Corolarul de produs: corpusul rezultat este un activ pe care nimeni altcineva
nu îl deține și nu îl poate cumpăra. Cercul vicios, odată rupt, devine șanț
de apărare.

## 2. Cele două jumătăți simulate

Datele relevante au două jumătăți inseparabile: **lumea** (starea formală,
măsurabilă) și **oamenii** (conversația despre lume). Simularea doar a lumii
produce un ERP de test fără viață; simularea doar a conversației produce
filozofie fără oracol. Se simulează amândouă.

### 2.1 Generatorul de lume

Un generator generic de organizație sintetică, materializată ca
**înregistrări Odoo reale într-o bază de test** — nu ca JSON paralel — astfel
încât ancorele, permisiunile și citirea live funcționează identic cu
realitatea.

Generatorul are nucleu organizațional și domain packs separate:

```text
worldgen core
  identități · structură · calendar · inițiative · proiecte · evenimente

domain packs
  project-minimal · professional-services · distribution · horeca · ...
```

Nucleul nu conține roluri precum gestionar, ospătar sau consultant și nu
cunoaște stoc, POS ori Time Off. Un pack declară modulele Odoo și anchor
packs necesare, schema de configurare, generatoarele de entități/evenimente,
tipurile de incidente și invariantele de materializare. Worldgen packs produc
date de benchmark; anchor packs definesc semantica produsului. Cele două
familii nu se confundă.

Dintr-un seed fix și un profil, compoziția produce:

- structura permisă profilului: companie, identități și, numai dacă modulul
  există, angajați, departamente și relații manageriale;
- obiectele de domeniu permise: proiecte/livrabile, produse, furnizori,
  transferuri, concedii sau POS numai prin pack-urile active;
- ritmul operațional pe N zile virtuale;
- **incidente injectate cu adevăr cunoscut** — unitatea de bază a
  benchmarkului.

Un incident declară complet: ziua, actorii implicați, adevărul integral
(ce s-a întâmplat de fapt), urma vizibilă în date (ce se vede în Odoo) și
distanța dintre ele (ce lipsește sau contrazice). Exemple canonice:

| Incident | Adevărul cunoscut | Urma în date |
|---|---|---|
| diferență de inventar | două cutii mutate, mișcarea neoperată | stoc scriptic ≠ faptic |
| livrare incompletă | furnizorul a livrat 8/10 | recepție parțială sau neoperată |
| absență neanunțată | angajatul lipsește din ziua X | tura neacoperită |
| decizie răsturnată | prețul stabilit marți, schimbat joi | două instrucțiuni succesive |
| promisiune uitată | angajamentul din ziua X, fără acțiune | nicio urmă după termen |

Profilurile canonice inițiale sunt minimal, servicii profesionale și
distribuție. HoReCa este un domain pack compozit ulterior; bistro mic,
restaurant mediu și lanț sunt **date de configurare, nu cod**. Parametrii de
realism sunt inițial estimați; ulterior pot fi calibrați dintr-un profil
statistic anonimizat al unei organizații reale (volume, ritmuri, frecvențe de
incident) — niciodată din copii de înregistrări. ADR-010 rămâne lege.

### 2.2 Participanții simulați

Peste lumea generată, conversația este produsă de **personas jucate de LLM**,
fiecare cu două componente:

- **fișa publică**: rolul și autoritatea (mapate pe angajatul/partenerul
  sintetic din Odoo) și constrângerile de stil — lungimea tipică a mesajelor,
  rata de non-răspuns, latența, gradul de ambiguitate, greșelile de scriere,
  tendința de a răspunde la altă întrebare decât cea pusă;
- **adevărul privat**: ce știe sau a făcut de fapt (legat de incidentele
  injectate), ce admite doar la întrebarea potrivită, ce omite spontan, unde
  se contrazice.

Adevărul privat este cheia întregii construcții: el face fiecare schimb
conversațional scorabil. Fără el, personas produc doar zgomot elocvent.

Reguli:

1. variantele scriptate determinist rămân instrumentul Gate C–D, E1 și F1,
   precum și al rerulării F2-E1; personas LLM sunt instrumentul E2 și al
   replicilor E3 aferente, inclusiv în F2-E2/E3;
2. realismul stilistic se calibrează pe transcrieri în care un om real joacă
   rolurile în primele sandboxuri — LLM-urile nejucate „vorbesc prea bine";
3. este interzisă derivarea unei persona din o persoană reală identificabilă;
4. persona nu are acces la starea Odoo dincolo de fișa ei — știe ce ar ști
   omul, nu ce știe baza de date.

## 3. Corpusul măsurabil

Fiecare rulare produce corpus: conversații + starea lumii la fiecare moment +
adevărul injectat. Pe el, fiecare funcție a memoriei primește o metrică:

Scorarea nu confundă: adevărul fizic `W(t)`, starea formală Odoo `O(t)`, ce
știe participantul `K(p,t)`, evidența efectiv livrată PMORG `E(t)`, autoritatea
valabilă `A(t)` și memoria observată `M(t)`. Un expected memory devine activ
numai după ce evidența necesară a intrat în `E(t)`; PMORG nu este penalizat
pentru un adevăr privat încă nedivulgat și nu este recompensat pentru că îl
ghicește.

| Funcția | Întrebarea | Metrica |
|---|---|---|
| extracție | deciziile/angajamentele rostite au fost prinse? | precision/recall contra evenimentelor cunoscute |
| ancorare | pe înregistrarea corectă? | extensia suitei de rezoluție existente |
| fapt vs ipoteză | eticheta corectă la momentul întrebării? | acuratețea etichetei contra stării Odoo de atunci |
| contradicție | spusa care contrazice datele/spusa anterioară e marcată? | rata de detecție pe contradicțiile injectate |
| supersession | decizia răsturnată înlocuiește fără a șterge? | corectitudinea lanțului pe răsturnările scriptate |
| recall | la întrebarea X apar amintirile Y? | cazuri must-retrieve, ca la rezoluție |
| clarificare | dialogul a extras adevărul privat sau s-a oprit la primul răspuns vag? | adâncimea atinsă contra fișei persona |
| revenire | după N zile virtuale, contextul e redeschis corect? | continuitatea firului contra istoricului cunoscut |

Ultimele două metrici depășesc memoria strictă — măsoară comportamentul
agentului alimentat de memorie. Sunt incluse deliberat: memoria există pentru
ele.

## 4. Suita și regula cazului real

Punctul de pornire este suita de rezoluție `aipm` (poartă: 100% pe cazurile
`must`, ≥85% total), generalizată la toate funcțiile din §3, cu praguri
proprii per funcție stabilite pe partiția de calibrare și înghețate înaintea
hidden-test. Un scor agregat nu poate ascunde un caz `must`, un profil sau o
funcție eșuată.

Regula permanentă existentă se extinde:

> Orice eroare a memoriei observată într-un pilot — clarificare ratată,
> contradicție înghițită, recall irelevant, etichetă greșită — este reprodusă
> ca un caz sintetic nou, cu adevărul consemnat manual; conversația și datele
> reale nu sunt copiate automat în corpus.

Astfel bucla se închide: sintetic → calibrare → pilot → reproduceri sintetice
ale erorilor → suita crește → recalibrare. Pilotul nu mai este primul contact
al memoriei cu realitatea, ci semnalul pentru coada de distribuție pe care
sinteticul nu o acoperă.

## 5. Poziția în arhitectură și gate-uri

- Generatorul de lume este **supersetul fixture-urilor** din MVP. Profilurile
  minimal, servicii și distribuție sunt compuse din același worldgen core și
  pack-uri versionate. Gate C–D, E1, F1 și F2-E1 rulează pe lumi generate cu
  conversații scriptate.
- Personas LLM sunt instrumentul **E2 și al replicilor E3 aferente**, inclusiv
  în F2-E2/E3: modelul real este evaluat pe aceleași lumi, iar outputul lui nu
  poate ocoli validările deterministe.
- Un **sandbox** = seed de lume × profil × configurație (politici de
  autonomie, monitorizare, praguri de ancorare) × set de personas. Fiecare
  sandbox se încheie cu un verdict scris: configurația, scorurile pe funcții,
  decizia rezultată.
- Oracle DB, baza memoriei și Odoo sunt depozite fizic separate. SUT nu are
  rută, mount, credential sau API către oracle; scorerul îl citește numai
  după închiderea runului.
- Memoria **nu ingestează lumea**: principiul „zero copii locale, Odoo citit
  live" rămâne neschimbat. Lumea generată are trei roluri externe memoriei —
  schelet public (ancore), oracle privat exclusiv pentru scorer și semnal
  (evenimente despre care conversația există). Oracle-ul nu validează claims
  în bucla PMORG și nu răspunde SUT-ului.

```text
generator de lume (adevăr injectat)
  → personas cu adevăr privat (clarificări, reveniri, contradicții)
    → corpus scorabil (fiecare schimb are ground truth)
      → calibrarea memoriei pe cifre
        → pilot → cazurile reale intră în suită → recalibrare
```

## 6. A doua viață a corpusului

Formatul canonic (conversații + extracții corecte + verdicte + starea lumii)
poate produce atât release-uri de evaluare, cât și exporturi pentru un
eventual fine-tuning. **Același exemplu și aceeași familie de incident nu pot
fi simultan material de antrenare și hidden-test.** Partițiile `train`,
`calibration` și `hidden-test` se atribuie la nivel de lineage înaintea
tuningului; targeturile hidden rămân accesibile numai scorerului.

Nu se decide acum dacă fine-tuningul propriu-zis va avea loc; se decide că
formatul îl face posibil fără schimbarea sursei canonice. Formatul de chat al
unui provider este un export derivat cu transform hash, nu noua sursă de
adevăr.

## 7. În afara scopului

- date, conversații sau identități de producție în orice test (ADR-010);
- personas derivate din persoane reale;
- copierea lumii generate în memorie (rămâne în Odoo de test);
- validarea cererii comerciale — corpusul măsoară calitatea memoriei, nu
  disponibilitatea cuiva de a plăti;
- realismul perfect — ținta este acoperirea funcțiilor din §3, nu simularea
  indistinctibilă a unei organizații.

## 8. Întrebări deschise

1. Granularitatea simulării POS: linii de bon sau agregate zilnice?
2. Limba și registrul corpusului: română colocvială, diacritice
   inconsistente, mesaje vocale transcrise?
3. Volumul minim per funcție pentru praguri stabile.
4. Ce model joacă personas la Gate E/F2 și la ce cost per lume simulată.
5. Criteriul de „realism suficient" al unui profil înainte de a avea profilul
   statistic real.
6. Politica de retenție și custodele setului hidden-test.

Poziția inițială a generatorului este fixată de
[sandboxul complet](06-EVALUATION-SANDBOX.md): în același repository, sub
`evaluation/worldgen/`, iar corpusurile mari rămân artefacte content-addressed
în afara Git.
