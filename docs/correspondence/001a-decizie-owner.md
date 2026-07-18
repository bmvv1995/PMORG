# 001a — Decizia ownerului pe constatările review-ului 001

| | |
|---|---|
| Data | 2026-07-18 |
| Decident | owner (Bogdan) |
| Referință | scrisoarea 001, constatările 3 și 4 |

**Constatarea 3 (`under_review` vs HIL):** legea 08-MEMORY-CHANNELS §2.7
rămâne neschimbată. „Review" în v3 se re-scopează STRICT la **vocabular și
ancoră**: entități noi recurente, tipuri noi de ancoră, matching ambiguu de
ancoră cu consecință. Interpretarea (kind, owner, termen, semantica
mesajului) nu ajunge NICIODATĂ la om — consemnare-cu-chitanță sau tăcere.
Starea `under_review` din mașina de claims (02:106-116) se elimină pentru
interpretare; workspace-ul de review (ADR-312) rămâne doar dacă coada lui
conține exclusiv vocabular/ancoră.

**Constatarea 4 (detectorul golului):** a fost omisiune, nu decizie —
detectorul e temă v2 livrată (08 + `pmorg_provenance.py` + benchmark P/R).
**Se pune pe masă**: v3 îi dă casă explicită (arhitectură + matricea de
migrare). Notă: UI-ul Onyx e chiar o oportunitate pentru el — digestul și
rata de acoperire au unde trăi vizual.

Restul corecțiilor (1, 2, 5) rămân cum sunt formulate în 001.
