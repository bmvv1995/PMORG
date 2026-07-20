# 008 — Model de operare: Claude feliază, Sol execută pe felie, Claude auditează

| | |
|---|---|
| Data | 2026-07-20 |
| Decident | owner (Bogdan) |
| Consemnat de | Claude |
| Relație | **consolidează** 005/006/007 — înlocuiește gatarea fină cu o singură împărțire clară |
| Validitate | normativ la merge (owner). |

## 1. Regula

- **Claude feliază.** Descompune munca în felii (slice-uri) clare și mărginite,
  ca Sol să aibă unități autonome de lucru.
- **Sol execută fiecare felie autonom**, sub delegare; își merge-uiește propria
  muncă. Cere review-ul lui Claude **doar când el însuși consideră necesar** —
  nu e o poartă impusă la fiecare pas.
- **Review-ul e pe felie** (la granița de slice), nu per-PR sau per-commit.
- **Claude auditează fiecare felie, pentru protecția ownerului.** Rulează și
  verifică rezultatul real. Dacă găsește ceva reversibil → fix-forward cu Sol.
  Dacă găsește ceva ireversibil sau nesigur → escaladează ownerului imediat.
  Auditul are dinți; nu e ștampilă.
- **Ownerul decide** strategie, bani/infra, producție/date client, direcție de
  canon. Neschimbat — deciziile lui, nu „review".

## 2. Ce rămâne din lecțiile anterioare (ca metodă, nu ca poartă)

- R1/R2 din 006 (admisibilitate-înainte; aserțiuni de stare-fixată) descriu
  **cum** auditez o felie, nu porți pre-merge.
- „În vigoare = ce e merge-uit în repo, nu ce se spune verbal" (Sol a avut
  dreptate) rămâne disciplina comună a sursei de adevăr.

## 3. Ce nu mai facem

Nu mai acumulăm amendamente de proces. Acesta consolidează și e ultimul de
proces. Următorul lucru e produs.
