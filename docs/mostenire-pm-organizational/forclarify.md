# forclarify — puncte deschise din auditul de onestitate (2026-07-05)

*(punctele 1–2 rezolvate: pagina de aprobări doar pe localhost + tunel SSH;
cheia API = treaba beneficiarului, scoping per workdir — vezi discuția)*

## 3. Reversibilitatea acoperă structura, nu datele  [SECURITY — discuție separată]
`~/.hermes` e sub git DOAR pentru configurație (carte, profiluri, skills).
kanban.db (memoria organizației) și state.db NU sunt nici versionate, nici
încă backup-uite. De decis la discuția de security: backup nocturn off-VPS,
frecvență, retenție.

## 4. Regula ARTEFACT impune prezența, nu substanța
`kanban_complete` refuză fără result, dar „done" trece. Compensare planificată:
scriptul de audit determinist (prag de lungime, tipar ARTEFACT:, stagnare) —
există ca demo SQL, de împachetat ca cron --no-agent la hardening.

## 5. Cron-urile se scurg în conversația eternă a PM-ului
Joburile programate rulează ca ture normale în aceeași conversație CC →
zgomot acumulat în context peste luni. Opțiuni: sesiune CC separată pentru
cron / acceptat conștient / prompturi de cron care cer răspuns minimal.

## 6. Comportamentul la saturație al cozii
Serializarea e făcută, dar al doilea apelant care așteaptă peste timeout-ul
providerului primește eroare, nu „sunt ocupat, revin". De tratat înainte de
onboarding-ul angajaților (răspuns imediat de tip queued + livrare async?).

## 7. Igiena tokenului de bot  [SECURITY — discuție separată]
Tokenul a circulat prin argv de ssh (vizibil trecător în process list).
Rotire oricând la @BotFather (2 min) dacă se decide.

## 8. --continue reia ULTIMA conversație din workdir
Dacă cineva pornește manual `claude` în ~/cc-sessions/pm, firul etern al
PM-ului poate devia. Regulă de operare: nimeni nu deschide CC manual în
workdir-urile sesiunilor administrate.

## 9. Executorul admin trăiește în procesul shim-ului
Un crash pe pagina de aprobări doboară și mirror-ul (systemd îl învie în ~5s,
dar tura în curs moare). De separat cândva? Cost/beneficiu de discutat.

## 10. Disciplina de raportare (meta)
Tipar identificat la audit: narațiune coerentă > bilanț complet, de două ori
(„nu mai e cod de scris", „memoria e doctrină"). Regulă salvată permanent în
memoria asistentului: trade-off-urile se raportează contra obiectivelor
DECLARATE ale ownerului, la momentul deciziei.
