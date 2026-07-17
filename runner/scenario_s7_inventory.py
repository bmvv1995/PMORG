#!/usr/bin/env python3
"""Gate D — S7: anchor pack Inventory, mișcare sintetică verificată (dst)."""

import sys
import uuid

from pmorg_runner.client import OdooApiClient
from pmorg_runner.memory_client import MemoryClient

RUN = uuid.uuid4().hex[:8]
CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(bool(cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not cond else ""))


def main():
    api = OdooApiClient("http://127.0.0.1:18070", "pmorg_dst", "admin",
                        "admin", actor_id="harness-s7")
    mem_dst = MemoryClient("http://127.0.0.1:18093")
    mem_min = MemoryClient("http://127.0.0.1:18091")

    company = api.execute("res.company", "search",
                          [["name", "=", "Delta Distribution Test SRL"]],
                          limit=1)[0]
    api.execute("res.users", "write", [api.uid], {"company_ids": [(4, company)]})
    tmpl = api.execute("product.template", "search",
                       [["name", "=", "Cutii ambalaj — TEST"]], limit=1)
    product = api.execute("product.product", "search",
                          [["product_tmpl_id", "=", tmpl[0]]], limit=1)[0]
    def find_internal():
        return api.execute("stock.picking.type", "search",
                           [["code", "=", "internal"],
                            ["company_id", "=", company]], limit=1,
                           context={"active_test": False})

    ptype = find_internal()
    if not ptype:
        api.execute("stock.warehouse", "create",
                    {"name": "Depozit Delta TEST", "code": "DLT",
                     "company_id": company})
        ptype = find_internal()
    check("S7: tipul de transfer intern există pentru compania sintetică",
          ptype)
    pt = api.execute("stock.picking.type", "read", [ptype[0]],
                     ["default_location_src_id", "default_location_dest_id"])[0]
    src = pt["default_location_src_id"][0]
    dst = pt["default_location_dest_id"][0] or src

    picking = api.execute("stock.picking", "create", {
        "picking_type_id": ptype[0], "company_id": company,
        "location_id": src, "location_dest_id": dst,
        "origin": f"GD-S7-{RUN}",
    })
    move = api.execute("stock.move", "create", {
        "picking_id": picking,
        "product_id": product, "product_uom_qty": 5,
        "location_id": src, "location_dest_id": dst, "company_id": company,
    })
    api.execute("stock.picking", "action_confirm", [picking])
    state = api.execute("stock.picking", "read", [picking], ["state"])[0]
    check("S7: transferul sintetic e creat și confirmat",
          state["state"] in ("confirmed", "assigned", "waiting"))

    ev = mem_dst.ok("memory_capture_evidence",
                    external_id=f"gd-s7-{RUN}",
                    source="gd", author_ref="gd:gestionar",
                    content="Am mutat 5 cutii; transferul e pe drum.")
    claim = mem_dst.ok("memory_propose_claim",
                       statement="Transfer de 5 cutii inițiat (GD-S7)",
                       author_ref="gd:gestionar",
                       evidence_ids=[ev["evidence_id"]],
                       anchors=[
                           {"anchor_type": "INVENTORY_TRANSFER",
                            "model": "stock.picking", "res_id": picking,
                            "role": "subject"},
                           {"anchor_type": "INVENTORY_MOVE",
                            "model": "stock.move", "res_id": move,
                            "role": "mentions"},
                       ])
    check("S7: claim ancorat la transferul și mișcarea reale",
          claim["status"] == "candidate")
    recall = mem_dst.ok("memory_recall",
                        anchor={"anchor_type": "INVENTORY_TRANSFER",
                                "model": "stock.picking", "res_id": picking})
    check("S7: recall pe ancora de transfer regăsește claim-ul",
          any(c["id"] == claim["claim_id"] for c in recall["claims"]))

    check("S7: profilul minimal REFUZĂ ancora de inventar (fail-closed)",
          mem_min.expect_error("memory_propose_claim",
                               "MEM_ANCHOR_TYPE_UNKNOWN",
                               statement="x", author_ref="gd:x",
                               evidence_ids=[1],
                               anchors=[{"anchor_type": "INVENTORY_TRANSFER",
                                         "model": "stock.picking",
                                         "res_id": picking}]))

    failed = CHECKS.count(False)
    print(f"===== S7: {len(CHECKS)} verificări, {failed} eșuate =====")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
