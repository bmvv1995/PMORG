# PMORG — strategia de date a memoriei

| Câmp | Valoare |
|---|---|
| Status | Propunere canonică pentru revizuire |
| Versiune | 0.1 |
| Data | 2026-07-16 |
| Domeniu | Corpusul care calibrează și validează memoria organizațională |
| Relație | completează [MVP-ul](02-MVP.md); nu modifică gate-urile A–F |

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

Un editor/generator de organizație sintetică HoReCa, materializată ca
**înregistrări Odoo reale într-o bază de test** — nu ca JSON paralel — astfel
încât ancorele, permisiunile și citirea live funcționează identic cu
realitatea.

Generatorul produce, dintr-un seed fix și un profil:

- structura: companie, angajați, departamente, funcții, relații manageriale;
- catalogul: produse, rețete/consumuri, furnizori, liste de prețuri;
- ritmul operațional pe N zile virtuale: cicluri de achiziție, recepții,
  mișcări de stoc, sesiuni POS cu curbe realiste (zi/săptămână/sezon),
  facturi și scadențe, ture și absențe;
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

Profilurile (bistro mic, restaurant mediu, lanț) sunt **date de configurare,
nu cod**. Parametrii de realism sunt inițial estimați; ulterior pot fi
calibrați dintr-un profil statistic anonimizat al unei organizații reale
(volume, ritmuri, frecvențe de incident) — niciodată din copii de
înregistrări. ADR-010 rămâne lege.

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

1. variantele scriptate determinist rămân instrumentul testelor de substrat
   (Gate C–D); personas LLM sunt instrumentul corpusului (Gate E);
2. realismul stilistic se calibrează pe transcrieri în care un om real joacă
   rolurile în primele sandboxuri — LLM-urile nejucate „vorbesc prea bine";
3. este interzisă derivarea unei persona din o persoană reală identificabilă;
4. persona nu are acces la starea Odoo dincolo de fișa ei — știe ce ar ști
   omul, nu ce știe baza de date.

## 3. Corpusul măsurabil

Fiecare rulare produce corpus: conversații + starea lumii la fiecare moment +
adevărul injectat. Pe el, fiecare funcție a memoriei primește o metrică:

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

Modelul este suita de rezoluție `aipm` (poartă: 100% pe cazurile `must`,
≥85% total), generalizată la toate funcțiile din §3, cu praguri proprii per
funcție stabilite la prima calibrare.

Regula permanentă existentă se extinde:

> Orice eroare a memoriei observată pe o instanță reală (pilot) — clarificare
> ratată, contradicție înghițită, recall irelevant, etichetă greșită — devine
> caz nou în suită, cu adevărul consemnat manual.

Astfel bucla se închide: sintetic → calibrare → pilot → cazuri reale → suita
crește → recalibrare. Pilotul nu mai este primul contact al memoriei cu
realitatea, ci sursa cozii de distribuție pe care sinteticul nu o acoperă.

## 5. Poziția în arhitectură și gate-uri

- Generatorul de lume este **supersetul fixture-urilor** din MVP: datasetul
  Delta Distribution devine primul profil generat, minim. Gate C–D rulează pe
  lumi generate cu conversații scriptate.
- Personas LLM sunt instrumentul **Gate E**: modelul real este evaluat pe
  aceleași lumi, iar outputul lui nu poate ocoli validările deterministe.
- Un **sandbox** = seed de lume × profil × configurație (politici de
  autonomie, monitorizare, praguri de ancorare) × set de personas. Fiecare
  sandbox se încheie cu un verdict scris: configurația, scorurile pe funcții,
  decizia rezultată.
- Memoria **nu ingestează lumea**: principiul „zero copii locale, Odoo citit
  live" rămâne neschimbat. Lumea generată are trei roluri externe memoriei —
  schelet (ancore), oracol (validarea claims), semnal (evenimente despre care
  conversația există).

```text
generator de lume (adevăr injectat)
  → personas cu adevăr privat (clarificări, reveniri, contradicții)
    → corpus scorabil (fiecare schimb are ground truth)
      → calibrarea memoriei pe cifre
        → pilot → cazurile reale intră în suită → recalibrare
```

## 6. A doua viață a corpusului

Corpusul (conversații + extracții corecte + verdicte + starea lumii) este
simultan set de evaluare și, dacă devine necesar, set de antrenare pentru un
eventual fine-tuning de model. Nu se decide acum dacă fine-tuningul propriu-zis
va avea loc; se decide că **formatul corpusului îl face posibil fără muncă
suplimentară**. „Pregătit de fine-tuning" înseamnă: corpusul există, e
versionat și are adevăr per exemplu.

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
4. Ce model joacă personas la Gate E și la ce cost per lume simulată.
5. Criteriul de „realism suficient" al unui profil înainte de a avea profilul
   statistic real.
6. Unde trăiește generatorul: în repo (`worldgen/`) sau ca proiect separat cu
   lumile ca artefacte versionate.
