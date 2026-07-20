# 006 — Amendament la protocolul 005: verificarea de admisibilitate-înainte

| | |
|---|---|
| Data | 2026-07-20 |
| Decident | owner (Bogdan) |
| Consemnat de | Claude (supervizor/verificator) |
| Amendează | `005-protocol-supervizor-executie.md` §2.2 (poarta tare) |
| Validitate | devine normativ **doar prin merge-ul ownerului** (ca 005). |

## 1. Cauza (post-mortem onest)

PR #25 (PR A, „bootstrap immutable CI seam successors") a fost autorizat ca pas
1 dintr-o secvență de 2 (pregătește → activează), cu pasul 2 (PR B) deja
specificat. La review-ul de poartă tare, verificatorul (Claude) a confirmat că
PR A e sănătos **în sine**: suita 87/87 verde, protectori dormant corect roșii,
mecanism aditiv, scope respectat — toate adevărate.

Dar PR A a aterizat două teste care fixează prin egalitate **starea dormantă**
(`test_dormant_static_helm_lane_authorizations_are_byte_bound` și
`test_current_policy_documents_are_valid_and_default_deny`): asertează că
seam-urile active sunt exact cele vechi și că cele noi lipsesc. Aceste aserțiuni
sunt corecte pentru starea PR A, dar fac **imposibilă prin construcție** starea
activată pe care PR B era explicit autorizat s-o producă. Consecința: PR B ar
trece inspectorul trusted-base înainte de merge, dar după merge `main` și-ar
pica propria suită.

Capcana a fost prinsă de self-check-ul implementer-ului (a rulat activarea local
înainte de a împinge PR B, s-a oprit, a escaladat) — comportament corect. A fost
**ratată de poarta tare a verificatorului** la review-ul PR A. Verdele suitei pe
starea curentă a ascuns o contradicție care se declanșează doar la pasul următor.

## 2. Lecția

Când o schimbare e împărțită deliberat într-o secvență autorizată de PR-uri,
splitul însuși poate crea un mod de eșec pe care **niciun PR nu-l arată singur**.
Review-ul unui pas ne-final trebuie să verifice **cusătura către pasul următor**,
nu doar sănătatea pasului în izolare. „Verde pe starea curentă" nu spune nimic
despre compatibilitatea cu pasul deja specificat.

## 3. Reguli adăugate la poarta tare (005 §2.2)

**R1 — admisibilitate-înainte.** La review-ul unui pas preparator dintr-o
secvență autorizată multi-PR, verificatorul aplică local pasul următor deja
specificat peste candidat și confirmă că suita rămâne integral verde. Dacă pasul
următor nu e încă scris în detaliu, verificatorul confirmă cel puțin că starea
aterizată **admite** tranziția autorizată (nu o interzice prin aserțiuni de
stare). Verdele pe starea curentă nu e suficient pentru un pas preparator.

**R2 — miros de stare-fixată.** Aserțiunile de egalitate pe o stare care e
**programată să se schimbe** printr-un pas deja autorizat sunt interzise. Testele
care păzesc o astfel de stare trebuie să admită întreg setul de stări autorizate
(ex. dormantă XOR activată, respingând hibridul), nu exact una. Byte-binding-ul
și testele negative se păstrează integral — se relaxează doar dimensiunea care
enumeră stări viitoare legitime.

## 4. Ce nu schimbă

Restul protocolului 005 rămâne neschimbat. Aceste reguli întăresc poarta tare,
nu o slăbesc: adaugă o verificare, nu retrag una. Se aplică oricărui verificator
în rol, nu unei identități anume.
