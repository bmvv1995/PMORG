# GO-LIVE — pașii de instalare pe server

> Ghid practic pentru ducerea produsului unificat pe serverul viu
> (204.168.208.233 sau unul curat). Presupune repo-ul acesta clonat pe server.
> Ordinea contează: memoria aterizează inertă, conducta se deschide la final,
> prin decizie explicită (PLAN-INTEGRARE etapa 5).

## 0. Precondiții pe server

- `tmux`, `git`, `python3` (+venv), `claude` (autentificat)
- PostgreSQL 16 cu extensiile `pgvector` și `unaccent`
  (`apt install postgresql-16 postgresql-16-pgvector`)
- `hermes` — dacă lipsește, installer-ul îl instalează singur din PyPI
- repo-urile `cc-bridge`, `hermes-ops-mcp`, `hermes-ontology` în `$HOME`
  (ca până acum), plus acest repo (`~/PMORG`)

## 1. Instalarea

```bash
cd ~/PMORG/components/pm-organizational
./install.sh                # idempotent; wizard pentru secrete la final
```

Ce face în plus față de instalarea veche:
- instalează **memoria (aipm)**: rol + bază PostgreSQL, migrări, serviciu
  systemd `aipm`, token de autentificare generat, **backup zilnic** cu
  retenție (`aipm-backup.timer`, 03:30);
- instalează **hook-ul de sedimentare** (`aipm-sediment`) în profilul pm
  și **lista de intimitate** (`~/.hermes/profiles/pm/privacy-denylist.txt`);
- leagă uneltele de memorie ale PM-ului (`aipm_recall`, `aipm_reports`,
  `aipm_review_queue`) prin `.mcp.json`.

Memoria pornește **inertă**: `INGEST_ENABLED=false`, `ODOO_ADAPTER=fake`.

## 2. Completează secretele aipm (`~/PMORG/.env`)

```
LLM_API_KEY=...            # extracția (DeepSeek/Anthropic/compatibil)
EMBED_API_KEY=...          # embeddings (Jina)
```

Apoi: `systemctl --user restart aipm`.

## 3. Trecerea pe Odoo real (când ești gata)

1. Creează userul de serviciu Odoo `aipm` per `aipm/README.md` §Deploy
   (grupurile exacte sunt acolo; fără drepturi de administrare).
2. În `~/PMORG/.env`: `ODOO_ADAPTER=xmlrpc`, `ODOO_RPC_PASSWORD=...`.
3. `systemctl --user restart aipm`; verifică `curl -s localhost:8090/api/health`
   → `"odoo": true`.
4. La prima pornire cursorul de chatter se așază la zi — istoricul NU se
   ingestează (backfill = decizie separată, vezi aipm/README).

## 4. Vama: identitățile reale

Mapările cont-Telegram → persoană-Odoo intră **prin migrare** (decizia D1).
Creează `aipm/migrations/0008_identity_seed.sql` (numărul următor liber) după
modelul:

```sql
INSERT INTO identity_map (channel, channel_id, partner_res_id, display_name, approved_by)
VALUES ('telegram', '<telegram_id_patron>', <res.partner id>, 'Nume Real', 'owner');
```

Apoi `python -m aipm.migrations.migrate` (sau restart aipm — migrează
installer-ul la re-rulare). Cine nu e în mapă nu devine autor — rămâne gol
de cunoaștere înregistrat, vizibil în raportul `external_recurring`.

## 5. Lista de intimitate

Completează `~/.hermes/profiles/pm/privacy-denylist.txt` cu termenii
„niciodată la AI" (un termen/expresie pe linie; prinde flexiunile —
„salariu" oprește și „salariului"). Fișierul e versionat în git-ul
organizației. Atenție: Hermes grupează mesajele trimise în rafală într-un
singur tur — un termen interzis blochează întregul lot.

## 6. Deschiderea conductei de sedimentare (decizia finală)

Abia după 2–5 de mai sus:

```bash
sed -i 's/^INGEST_ENABLED=false/INGEST_ENABLED=true/' ~/PMORG/.env
systemctl --user restart aipm
systemctl --user restart hermes-gateway-pm   # încarcă hook-ul
```

Verificare: trimite pe Telegram un mesaj de lucru → `SELECT * FROM ingest_log
WHERE source_type='gateway'` arată `done`; un mesaj cu termen interzis →
`privacy_blocked` fără conținut.

## 7. Livrarea proactivă

După configurarea Telegram:

```bash
pm cron create "0 8 * * *" --name aipm-digest --no-agent \
    --script aipm-digest.py --deliver telegram
```

(scriptul e instalat de installer în `~/.hermes/scripts/`; digestul nu
retrimite ce a livrat deja).

## Verificări rapide după instalare

```bash
systemctl --user status aipm aipm-backup.timer
curl -s localhost:8090/api/health          # pg/odoo/ingest/auth
ls ~/aipm-backups/                          # după primul 03:30
pytest ~/PMORG/aipm/tests -q                # suita completă (cere PG local)
```

## Rămase deliberat după go-live

- crearea `project.project` în Odoo la crearea board-ului (etapa 2, partea
  amânată — cere Odoo real);
- bucla de contestare a chitanțelor (decizia D4 se rediscută la go-live);
- trunchierea la 500 de caractere a hook-ului (limită stock Hermes —
  candidat de contribuție upstream).
