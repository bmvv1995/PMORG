# Conducta email (tema 08, L2-email) — evaluarea Onyx + bridge funcțional

## Verdictul evaluării Onyx (fork bmvv1995/onyx, 2026-07-18)

**Derivare, nu dependență.** Conectorul IMAP Onyx (MIT) e solid pe partea
plictisitoare (decodare headere MIME, checkpointing per mailbox, HTML→text),
dar îi lipsesc exact piesele de care conducta PMORG are nevoie:

| Are Onyx | Lipsește din Onyx (adăugat aici) |
|---|---|
| imaplib + SSL, paginare, checkpoint per mailbox | threading (`References`/`In-Reply-To`) — corelarea firelor |
| decodare headere MIME (preluată, cu atribuire) | reply-stripping + tăierea semnăturii |
| parsing HTML (bs4) | poarta de intimitate (denylist ÎNAINTE de stocare) |
| perm-sync (irelevant aici) | identitatea structurală (email → pmorg.identity din Odoo) |
| — | carantina expeditorului nemapat |
| — | fereastra de context pe fir (perechea „Da.") |

Nota: conectorul Onyx e hardcodat SSL — n-ar fi putut nici măcar să se
conecteze la serverul de test. Platforma Onyx întreagă rămâne candidat
pentru stratul de evidență brută (RAG peste documente), decizie separată.

## Rezultat: 9/9 pe benchmark-ul email (grefier = gpt-5.6-sol)

Cazuri: angajament simplu; **reply cu citat imbricat — fără dublă
contorizare**; semnătură+disclaimer ignorate; HTML-only; **perechea pe fir:
„Da." al lui Victor → angajamentul LUI, cu termenul din întrebarea Anei**
(fereastra de context, items doar din mesajul curent); colocvial fără
diacritice; expeditor nemapat → carantină; termen din denylist → refuz
consemnat fără conținut.

Rulare: greenmail (SMTP 3025/IMAP 3143) → `seed_mailbox.py` →
`imap_bridge.py <cases.json>` (identitate: Odoo pmorg_min_c2; memorie:
adaptorul org-min; LLM prin env).

## Rămase pentru producție (consemnat, nu ascuns)

IDLE/polling incremental cu checkpoint persistent (tiparul Onyx e bun de
preluat), OAuth pentru Gmail real, fereastra de context ca parametru de
schemă (azi: marcatori în source_text), rezoluția completă de ancore pe
entitățile din corp (azi: ancora = identitatea autorului).
