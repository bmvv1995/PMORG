// AI-PM Verificare — textContent-only (anti-XSS), fără handlere inline (CSP).
"use strict";

const needsReviewBox = document.getElementById("needs-review");
const untrustedBox = document.getElementById("untrusted");

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function toast(text) {
  const t = el("div", "toast", text);
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 5000);
}

async function post(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
  return data;
}

function anchorRow(item, anchor) {
  const row = el("div", "claim-line");
  const chip = el("a", "chip");
  chip.textContent = `${anchor.role} · ${anchor.label_ro} #${anchor.odoo_res_id}` +
    ` · încredere ${Number(anchor.confidence).toFixed(2)}` +
    (anchor.needs_review ? " · DE VERIFICAT" : "") +
    (anchor.mention_text ? ` · „${anchor.mention_text}”` : "");
  chip.href = anchor.url; chip.target = "_blank"; chip.rel = "noopener";
  row.appendChild(chip);

  const actions = el("span", "claims");
  const mkBtn = (label, fn, danger) => {
    const b = el("button", danger ? "danger" : "", label);
    b.addEventListener("click", async () => {
      b.disabled = true;
      try { await fn(); toast("Salvat."); load(); }
      catch (e) { toast(`Eroare: ${e.message}`); b.disabled = false; }
    });
    actions.appendChild(b);
  };
  if (anchor.needs_review || anchor.resolved_by === "auto") {
    mkBtn("Confirmă", () => post(`/api/review/anchor/${anchor.id}`, { action: "confirm" }));
    mkBtn("Realocă…", async () => {
      const resId = prompt("res_id-ul corect din Odoo:");
      if (!resId) throw new Error("anulat");
      await post(`/api/review/anchor/${anchor.id}`, { action: "reassign", res_id: Number(resId) });
    });
  }
  mkBtn("Șterge ancora", () => post(`/api/review/anchor/${anchor.id}`, { action: "remove" }), true);
  row.appendChild(actions);
  return row;
}

function card(item, { withReceiptButton }) {
  const c = el("div", "card");
  c.appendChild(el("h3", null, `${item.kind}: ${item.title}`));
  c.appendChild(el("div", "meta",
    `${item.created_at} · sursă: ${item.source_type} (${item.source_ref})` +
    ` · încredere extracție ${item.extract_confidence}` +
    (item.due_at ? ` · termen: ${item.due_at}` : "") +
    (item.receipt ? ` · chitanță: mail.message #${item.receipt.mail_message_id}` : " · FĂRĂ chitanță")));
  c.appendChild(el("div", null, item.body));
  if (item.quote) c.appendChild(el("div", "meta", `„${item.quote}”`));
  for (const anchor of item.anchors) c.appendChild(anchorRow(item, anchor));
  if (!item.anchors.length) c.appendChild(el("div", "empty", "Fără ancore — ipoteză neancorată."));

  const actions = el("div", "actions");
  const hasSubject = item.anchors.some((a) => a.role === "subject");
  if (withReceiptButton && !item.receipt) {
    const b = el("button", null, "Postează chitanța");
    if (!hasSubject) { b.disabled = true; b.title = "Fără subject rezolvat (409)"; }
    b.addEventListener("click", async () => {
      b.disabled = true;
      try {
        const r = await post(`/api/memory/${item.id}/post-receipt`);
        toast(`Chitanță: ${r.outcome} (mail.message #${r.mail_message_id})`);
        load();
      } catch (e) { toast(`Eroare: ${e.message}`); b.disabled = !hasSubject; }
    });
    actions.appendChild(b);
  }
  const retract = el("button", "danger", "Retractează");
  retract.addEventListener("click", async () => {
    if (!confirm("Retractezi amintirea?")) return;
    try { await post(`/api/memory/${item.id}/retract`); toast("Retractat."); load(); }
    catch (e) { toast(`Eroare: ${e.message}`); }
  });
  actions.appendChild(retract);
  c.appendChild(actions);
  return c;
}

async function load() {
  const resp = await fetch("/api/review/queue");
  if (!resp.ok) {
    needsReviewBox.replaceChildren(el("div", "empty", `Eroare HTTP ${resp.status}`));
    return;
  }
  const data = await resp.json();
  needsReviewBox.replaceChildren(
    ...(data.needs_review.length
      ? data.needs_review.map((i) => card(i, { withReceiptButton: true }))
      : [el("div", "empty", "Nimic de verificat.")]));
  untrustedBox.replaceChildren(
    ...(data.untrusted.length
      ? data.untrusted.map((i) => card(i, { withReceiptButton: true }))
      : [el("div", "empty", "Toate amintirile au chitanță.")]));
}

load();
