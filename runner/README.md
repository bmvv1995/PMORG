# Runner determinist PMORG (Gate C, parțial)

Client pur al contractului [07-CONTRACTS](../docs/pmorg-v2/07-CONTRACTS.md):
fără reguli de business, fără LLM, fără canale reale. Politicile și
tranzițiile trăiesc în Odoo.

## Componente

- `pmorg_runner/client.py` — clientul XML-RPC al `pmorg.orchestrator.api`
  (anvelopă completă, idempotency keys);
- `pmorg_runner/clock.py` — ceas virtual: timpul avansează doar explicit;
- `pmorg_runner/channel.py` — canal simulat cu participanți scriptați și
  identitate structurală;
- `run_smoke.py` — scenariul smoke 02-MVP §8 (14 verificări).

## Rulare (sandbox sb3)

```bash
# bază proaspătă cu lumea sintetică Delta Distribution
docker compose run --rm odoo odoo -d pmorg_smoke -i pmorg_core \
    --stop-after-init --with-demo
docker compose restart odoo

python3 run_smoke.py --db pmorg_smoke   # exit 0 = toate verificările PASS
```

## Limitare asumată

Pașii de memorie din scenariu (evidență → claim → validare, pașii 6–8 din
02-MVP §8) sunt STUB: se consemnează doar `record_evidence_reference` la
nivel de contract. Devin reali la Gate B (memoria `aipm` expusă prin MCP).
Scenariul rămâne suita de acceptanță pentru Hermes (Gate F): același traseu,
alt client.
