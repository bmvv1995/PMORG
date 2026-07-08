# Analiza externă #2 a specificației v0.2 — raport integral

> 6 iulie 2026. Analist: sesiune separată (Claude Desktop, contextul
> propriu al Patronului), pe specificația v0.2. Structură: A coerență
> (#1–#9), B completitudine (#10–#18), C oportunitate de piață,
> D riscuri de adopție. Verdictul proprietarilor: toate cele 18 acceptate
> (#5 cu mecanism de aliasuri; #13 cu mecanismul de ștergere ca decizie
> deschisă D7). Datele despre AI Act: neverificate independent — de
> confirmat cu opinie juridică. Încorporate în v0.3.

---

Am parcurs v0.2 integral. Verdict scurt: arhitectura de bază e solidă și neobișnuit de onestă — separarea agent-judecă / infrastructură-execută / auditor-verifică, plicul ca garanție de construcție cu detecția retrogradată corect la obiectiv (O2), autoritatea faptelor exclusiv din metadate (L6, care omoară o clasă întreagă de otrăvire a memoriei) și cursorul care trăiește în depozit (ștergerea se auto-vindecă) sunt decizii mature. Defectele găsite sunt punctuale, nu structurale. Riscurile mari sunt de adopție, nu de arhitectură. Mai jos, constatările numerotate ca să le poți referi în v0.3.

## A. Coerență — defecte concrete

#1 — `proiect_inchis` nu există. §3.12 cere închiderea proiectului „doar Patron, prin cerere", dar lista închisă din §3.6 nu conține tipul. Prin propria regulă („alt conținut = respins la depunere"), cererea ar fi respinsă mecanic. Defect direct.

#2 — Confirmarea de export din FL8 n-are tip de cerere. FL8 cere confirmare pe C5 pentru citiri în masă, dar §3.6 nu definește tipul. Aceeași clasă de defect ca #1. Adaugă `export_memorie` sau un tip generic `confirmare_operatiune`.

#3 — Punctul de aplicare al porții contrazice L11. C7e spune explicit: UN SINGUR punct de filtrare, la scrierea în jurnal. L11 spune că apelurile către model sunt „sub poarta de intimitate". Dacă Puntea livrează PM-ului mesajul viu, pre-jurnal, conținutul sensibil pleacă la furnizorul de model neredactat — și L11 promite mai mult decât garantează. Două rezolvări posibile: (a) fluxul devine „jurnalizează întâi, livrează versiunea post-poartă" pentru orice conținut către orice agent; (b) reformulezi L11 onest. Recomand (a) — păstrează „un singur punct" și face L11 adevărată.

#4 — Heartbeat-ul omoară sarcinile umane. Pe calea 2b lease-ul e la PM și omul nu emite heartbeat, dar regula Ceasornicarului „heartbeat lipsă > durata_maxima → eșec" nu face distincția. Fără o excepție explicită, sarcinile umane în `running` sunt eșuate mecanic. Separă: heartbeat/durata_maxima doar pe calea executantului AI; calea omului are FL3 (N_tacere).

#5 — T10 pică prin construcție dacă maparea pe ancore e LLM. Testul cere egalitate mecanică de mulțimi (ancore active, perechi ancoră–sursă.ref) între două rulări. Consolidatorul e probabilistic — două treceri peste aceleași jurnale nu garantează aceeași mapare. Testul ține doar dacă faci normativ în FL9 ce e implicit în design: maparea pe registru e deterministă (potrivire lexicală pe cârlig-frază + normalizare), iar LLM-ului îi rămâne exclusiv formularea enunțului. E filozofia CLARIX aplicată aici — dar trebuie scrisă, nu presupusă.

#6 — „Execuția atomică" e afirmată, nu proiectată. `angajat_plecat` atinge trei sisteme: C2 (reasignări), allowlist-ul C3, commit-ul C6. „Integral sau deloc" peste trei substrate cere o strategie explicită per tip (staging → validare → commit → flip, sau compensare jurnalizată). Fără ea, T2 pe execuții structurale nu e garantabil.

#7 — Matricea de drepturi e mai largă decât mecanica. PM „citește tot", dar uneltele lui sunt C2/C5-depunere/C7-citire. Și nicăieri nu scrie regula care contează cel mai mult: niciun agent nu are unealtă cu cale către fișierele de secrete. O propoziție + poarta care prinde lexical formate de secrete (defense-in-depth) închid subiectul.

#8 — Modelul de concurență al PM-ului e corect dar nescris. Ceasornicarul poate porni sesiuni de lucru în paralel; PM-ul e de facto un agent fără memorie inter-sesiune, coerent exclusiv prin digest + C2 + C6. E o proprietate bună (stare partajată, nu minte partajată) — afirm-o explicit, altfel implementatorul o va „repara" greșit cu vreo memorie de sesiune.

#9 — Regula „digest ≤ consolidare + 24h" n-are forțare. Reciclarea se face „în fereastra de inactivitate" — dacă fereastra nu apare (conversație continuă), regula e încălcată fără mecanism. Definește fallback-ul: reciclare forțată la drenajul cozii sau după prima cerere încheiată post-termen.

## B. Completitudine — lipsuri

#10 — Ciclul de viață al executantului AI are doar naștere. Există `executant_nou` și `acces_nou`, dar nu există dezactivare, modificare (model, plafon) sau revocare de unelte. Câmpul `activ` din §3.4 n-are cerere care să-l stingă.

#11 — „Catalogul de acțiuni de ritm" e referit, nedefinit. `ritm_nou` trimite la un catalog care nu apare nicăieri; nici anularea/modificarea unui ritm nu există. Definește-l ca pe §3.13: închis, versionat în C6.

#12 — Nu există buton roșu. Nicio pauză de urgență declanșabilă de Patron fără medierea PM-ului (scenarii: cont de canal compromis, PM aberant, factură care explodează). Mecanic e ieftin: un flag în infrastructură, setabil de pe C5, verificat de runtime la orice pornire de sesiune și de Ceasornicar la fiecare tact — suspendă pornirile noi și expiră lease-urile AI. Pentru încrederea la vânzare („pot să-l opresc oricând?") e aproape obligatoriu.

#13 — GDPR vs L5 e nerezolvat și e blocant de piață. Jurnale doar-adăugare, păstrate nelimitat, cu mesajele angajaților, intră în conflict cu minimizarea, retenția și dreptul la ștergere. Specul are nevoie de: politică de retenție declarată + un mecanism de ștergere la fel de mecanic ca restul sistemului — crypto-shredding cu cheie per persoană sau rescriere de jurnal jurnalizată ea însăși, ca excepție definită și auditabilă a L5. Fără asta, orice client cu un DPO te oprește la due diligence.

#14 — Jurnalul mesajelor n-are proprietar. §3.10 e model, C7e presupune că mesajele sunt jurnalizate, dar Consolidatorul citește „C2, C6, transcripte C1" — mesajele nu apar în listă. Atribuie explicit persistența mesajelor unei componente.

#15 — Testele lipsesc exact pe legile cele mai vândabile. Nu există test pentru: L6 (mesaj de angajat care pretinde o decizie a Patronului → gol, nu fapt), L8 (conținutul oprit nu apare în niciun jurnal + marcajul vizibil există), FL8 (dump cerut prin chat → sumar + cerere C5), și injecție la nivel de executant (instrucțiune ostilă în comentariu de sarcină → tratată ca date; T4 acoperă doar PM-ul).

#16 — L1 merită un audit compensator. L1 e „prin construcție", dar construcția e configurația unui runtime terț — un bug al runtime-ului rupe legea în tăcere. Compensare deterministă și ieftină: Auditorul scanează zilnic transcriptele C1 pentru apeluri de unelte în afara grantului per rol. Transformă încrederea în config într-un invariant verificat. Extinde contractul C8.

#17 — Poarta lexicală în română cere normalizare morfologică acum, nu la D6. Fără lemmatizare și tratarea diacriticelor, lista de termeni scapă flexiuni banale („salariului", „salariile", „concediul medical"). Nu e problema semantică din D6 — e o cerință a variantei lexicale curente. Ai deja stiva pentru asta.

#18 — Tenancy ambiguu. C7a spune „per client", C9 și §6 sugerează un VPS = un client. O propoziție care fixează single-tenant elimină ambiguitatea și simplifică povestea de securitate.

Mărunte, de menționat fără număr: `respins_ocupat` e stare terminală, deci mesajul se pierde dacă omul nu retrimite — asumă explicit sau adaugă re-încercare; „model ⊂ listă" nu spune unde trăiește lista (C6, presupun); înfometarea cozii generale sub activitate susținută a Patronului e by design — scrie-o ca proprietate asumată, T7 o testează doar parțial.

## C. Oportunitate de piață

Categoria ta nu e „framework de agenți" (LangGraph/CrewAI et al.) și nu e „guardrails" (filtre peste model). E o a treia categorie, aproape goală: organizația agentică guvernată prin construcție — unde produsul vândut sunt Legile, nu agentul. Perechea Lege/Obiectiv din §5 e limbaj de vânzare gata făcut: nimeni pe piață nu distinge onest între „garantat mecanic" și „măsurat statistic". Asta e exact axa ta „AI ancorat vs AI decor", dar cu un obiect verificabil în spate. Publicarea L1–L12 ca manifest tehnic / standard deschis ar fi un artefact de marketing coerent cu ce faci deja.

Contextul regulator lucrează pentru tine, cu o nuanță de timing. PM-ul tău alocă sarcini angajaților și le monitorizează tăcerea și performanța — teritoriul Annex III pct. 4 din AI Act, unde contextele de angajare acoperite includ explicit alocarea de sarcini și monitorizarea lucrătorilor. Vestea proaspătă: Consiliul UE a dat undă verde finală pachetului de simplificare pe 29 iunie 2026, după votul Parlamentului din 16 iunie, cu publicarea în Jurnalul Oficial așteptată în curând, iar obligațiile pentru sistemele high-risk de tip Annex III se amână de la 2 august 2026 la 2 decembrie 2027. Asta îți dă ~17 luni de pistă în care arhitectura ta — jurnalizare, supraveghere umană, management de risc, păstrarea înregistrărilor, exact obligațiile regimului high-risk — se vinde ca „conformitate prin arhitectură", nu ca un cost. Două detalii tactice: obligațiile de transparență din Art. 50 rămân aplicabile de la 2 august 2026 — angajații trebuie informați că interacționează cu un AI, deci FL6 (onboarding) ar trebui să includă formal declararea asta, un câștig de conformitate aproape gratuit; și sistemele plasate pe piață înainte de noile termene evită obligațiile high-risk până la o modificare substanțială — argument pentru a fi pe piață devreme, nu târziu. Cere totuși o opinie juridică pe clasificare înainte de a construi mesajul pe ea.

Suveranitatea e al doilea picior: self-hosted, single-tenant, L11 cu excepția declarată onest — e pitch-ul anti-SaaS-american pentru piața UE/RO. Dar self-hosted înseamnă ops, deci oferta managed-VPS nu e opțională, e condiție de existență a segmentului non-tehnic.

Al treilea picior e cultural și e subestimat: modelul „Patron ca unică autoritate de aprobare" mapează perfect pe IMM-ul românesc patron-centric. Acasă e feature; în organizații delegative e plafon. Praguri de delegare pe clasa de pericol sunt evoluția firească de v2 — nu dilua acum, dar pune-o pe roadmap explicit ca să nu pară limitare de gândire.

GTM: consultanțe/MSP ca vehicul (propria practică e canalul zero), vertical HoReCa întâi cu Parcul La Țară ca design partner care doguje sistemul, și șabloane per vertical (registru + constituție pre-populate) ca răspuns la cold start. C10 plus cheia de facturare per director înseamnă că economia unitară e instrumentată nativ — licență + trecere de tokens cu plafon, marjă vizibilă per client din prima zi.

## D. Riscuri de adopție

1. UX-ul C5 pentru un Patron non-tehnic e fricțiunea practică numărul unu. Loopback + tunel criptat e corect ca securitate și fatal ca instalare dacă Patronul e pe telefon. Fără o cale zero-config (mesh VPN configurat de instalator sau companion mobil cu cheie legată de dispozitiv), produsul moare înainte de prima aprobare.

2. Oboseala de aprobare golește stratul uman de sens. Dacă Patronul ștampilează, C5 devine teatru și modelul de securitate rămâne fără componenta umană. Proiectează suprafața pentru decizie sub 30 de secunde (evidențierea pericolelor ajută) și raportează latența deciziilor la praguri mai mici decât cele 3 zile ale Auditorului.

3. Cold start-ul lumii închise. Zero-invenție înseamnă „nu există în registru" toată prima săptămână — corect epistemologic, frustrant comercial. Sămânța agresivă la aliniere plus șabloanele verticale decid churn-ul, iar registrul de goluri trebuie prezentat ca progres vizibil, nu ca listă de eșecuri.

4. Amnezia percepută. Reciclarea sesiunii face ca PM-ul să „uite" conversația de ieri dacă n-a devenit fapt sau inițiativă. Calitatea digestului e, practic, produsul. Setează așteptarea explicit din onboarding: ține minte fapte, nu discuții.

5. Angajații. Alocare de sarcini + escaladare pe tăcere + transcripte = senzație de supraveghere. Onboarding-ul FL6 trebuie să explice plicul, poarta și cine răspunde (Patronul), altfel apar canale din umbră — și fiecare canal din umbră e o gaură în memoria organizațională. Busy-ul la 90 de secunde împinge exact în direcția asta.

6. Dependența de furnizor. C1 e configurație peste un runtime terț (pe care se sprijină L1 — vezi #16), iar deriva de model recalibrează O1–O3. Fallback multi-model merită măcar statut de decizie deschisă nouă.

7. Prețul promisiunii „garantat prin construcție". O singură încălcare demonstrată a unei Legi arde întregul brand de onestitate — care e diferențiatorul tău principal. Auditul compensator (#16) și testele L6/L8 (#15) sunt polița de asigurare, nu nice-to-have.

## Priorități pentru v0.3

Defectele mecanice întâi, pentru că se rezolvă cu propoziții, nu cu cod: #1, #2, #4, #5, #6. Apoi decizia de arhitectură #3 (punctul porții), care schimbă fluxul Punții. Apoi #12 și #13 — nu sunt features, sunt condiții de vânzare în UE. Restul intră în ciclul normal.
