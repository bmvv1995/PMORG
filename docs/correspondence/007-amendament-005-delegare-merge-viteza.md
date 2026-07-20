# 007 — Amendament la protocolul 005: delegarea execuției de merge + viteză

| | |
|---|---|
| Data | 2026-07-20 |
| Decident | owner (Bogdan) |
| Consemnat de | Claude (supervizor/verificator) |
| Amendează | `005-protocol-supervizor-executie.md` §2–4 |
| Validitate | normativ la merge; acest merge îl face implementer-ul (cross-agent), nu ownerul. |

## 1. Cauza

Ownerul a semnalat că e ținut ca ștampilă pe merge-uri pe care nu le-ar opune
niciodată, și că un fir de CI-plumbing a consumat o zi prin gatare serială. Controlul
ownerului este **decizia**, nu click-ul de merge; click-ul era redundant cu decizii
deja luate. Verificatorul a contribuit la lentoare gatând pre-merge lucruri care, prin
005, erau bandă normală.

## 2. Regula de execuție a merge-ului (pe clase)

- **Implementare, CI-plumbing, activări de seam-uri pre-autorizate** — merge = implementer
  sub delegare, pe verde. Review-ul supervizorului = **audit post-merge**, non-blocant.
- **Canon / protocol / corespondență scrise de supervizor** — merge = implementer
  (cross-agent), ca supervizorul să nu fie autor + executor al propriei reguli. Ownerul auditează.
- **Exclusiv owner (decizie, nu click):** principiu, strategie, bani/infra, producție/date
  client, derogări/excepții de trust-boundary, bypass/force. Ownerul decide; execuția merge-ului
  care decurge dintr-o decizie deja dată **nu-i mai cere click**.

Click-ul fizic al ownerului nu mai e cerut ca garanție de rutină. Garanția anti-autoautorizare
(lecția 003a) se mută pe: decizia explicită consemnată + auditul ownerului prin digest. Ownerul
poate cere click-ul fizic punctual oriunde vrea; altfel, nu e implicit.

## 3. Poartă tare pre-merge — restrânsă

Review-ul supervizorului rămâne poartă **înainte** de merge DOAR pe: canon PMORG,
trust-boundary/securitate (pmorg-governance.yml, verify_fork.py, testele lui), EE/licențiere,
memorie/evidență. Restul se aude prin audit post-merge. Verde pe starea preparatoare tot cere
R1/R2 (amendament 006) când se aplică.

## 4. Fiabilitatea semnalului (verificatorul să nu rateze cereri)

- semnal dedicat de review cerut (label `needs-claude-review` sau mențiune convenită), verificat
  **primul** la fiecare heartbeat;
- auto-abonare la orice PR nou ne-dependabot din clipa apariției;
- cadență de veghe strânsă;
- veghea e sarcină permanentă — nu e preemptată de side-quests (evaluări, discuții).

## 5. Ce nu schimbă

Deciziile de principiu, strategie și excepțiile de trust-boundary rămân ale ownerului. Auditul
post-merge al supervizorului rămâne real: dacă găsește o gaură, deschide issue/PR de corecție.
Calibrarea: rigoarea se potrivește mizei — CI-plumbing ≠ memorie/evidență/canon.
