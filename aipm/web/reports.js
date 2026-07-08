// AI-PM Rapoarte — textContent-only (anti-XSS), fără handlere inline (CSP).
"use strict";

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function itemCard(item) {
  const c = el("div", "card");
  c.appendChild(el("h3", null, item.title));
  c.appendChild(el("div", "meta",
    `${item.kind} · ${item.created_at}` + (item.due_at ? ` · termen: ${item.due_at}` : "")));
  c.appendChild(el("div", null, item.body));
  const chips = el("div", "claims");
  for (const a of item.anchors || []) {
    const chip = el("a", "chip", `${a.role} · ${a.label_ro} #${a.odoo_res_id}`);
    chip.href = a.url; chip.target = "_blank"; chip.rel = "noopener";
    chips.appendChild(chip);
  }
  c.appendChild(chips);
  return c;
}

function fill(boxId, items, emptyText) {
  const box = document.getElementById(boxId);
  box.replaceChildren(...(items.length ? items.map(itemCard) : [el("div", "empty", emptyText)]));
}

async function post(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
}

async function load() {
  const get = async (code) => (await fetch(`/api/reports/${code}`)).json();

  const due = await get("due_soon");
  fill("due_soon", due.items, "Nicio scadență apropiată.");

  const missing = await get("commitments_missing");
  const box = document.getElementById("commitments_missing");
  box.replaceChildren();
  box.appendChild(el("h2", null, "— fără termen"));
  for (const i of missing.missing_due) box.appendChild(itemCard(i));
  if (!missing.missing_due.length) box.appendChild(el("div", "empty", "Toate au termen."));
  box.appendChild(el("h2", null, "— fără responsabil (owner)"));
  for (const i of missing.missing_owner) box.appendChild(itemCard(i));
  if (!missing.missing_owner.length) box.appendChild(el("div", "empty", "Toate au responsabil."));

  const stale = await get("stale_questions");
  fill("stale_questions", stale.items, "Nicio întrebare stagnantă.");

  const ext = await get("external_recurring");
  const extBox = document.getElementById("external_recurring");
  extBox.replaceChildren();
  if (!ext.items.length) extBox.appendChild(el("div", "empty", "Nicio entitate externă recurentă."));
  for (const e of ext.items) {
    const c = el("div", "card");
    c.appendChild(el("h3", null, `„${e.normalized_text}” · ${e.mentions} mențiuni`));
    c.appendChild(el("div", "meta",
      "Nu există în Odoo. Dacă e reală, creeaz-o manual ca partener; amintirile vechi NU se re-ancorează (§1.7)."));
    const actions = el("div", "actions");
    for (const [label, status] of [["Am creat partener", "created"], ["Ignoră", "dismissed"]]) {
      const b = el("button", status === "dismissed" ? "danger" : "", label);
      b.addEventListener("click", async () => {
        b.disabled = true;
        try {
          await post(`/api/reports/external/${encodeURIComponent(e.normalized_text)}/status`, { status });
          load();
        } catch (err) { b.disabled = false; }
      });
      actions.appendChild(b);
    }
    c.appendChild(actions);
    extBox.appendChild(c);
  }
}

load();
