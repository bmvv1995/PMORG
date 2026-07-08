// AI-PM Conversație — randare EXCLUSIV prin textContent/createElement (anti-XSS, plan §8).
// innerHTML cu date dinamice este INTERZIS. Fără handlere inline (CSP default-src 'self').
"use strict";

const thread = document.getElementById("thread");
const composer = document.getElementById("composer");
const input = document.getElementById("input");
const send = document.getElementById("send");

let sessionId = null;
let lastCaptureCheck = new Date().toISOString();
const seenCaptures = new Set();

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text; // niciodată innerHTML
  return node;
}

function addMessage(role, text) {
  const msg = el("div", `msg ${role}`, text);
  thread.appendChild(msg);
  msg.scrollIntoView({ behavior: "smooth", block: "end" });
  return msg;
}

function renderClaims(container, claims) {
  if (!claims || !claims.length) return;
  for (const claim of claims) {
    const line = el("div", "claim-line");
    line.appendChild(el("span", `badge ${claim.status === "fact" ? "fact" : ""}`,
      claim.status === "fact" ? "fapt" : "ipoteză"));
    line.appendChild(document.createTextNode(" " + claim.text + " "));
    const chips = el("span", "claims");
    for (const s of claim.support) {
      if (s.type === "odoo") {
        const chip = el("a", "chip" + (s.deleted ? " deleted" : ""));
        chip.textContent = (s.deleted ? "⚠ ștearsă · " : "") + `${s.anchor_code} #${s.res_id}` +
          (s.field ? ` · ${s.field}=${s.value}` : "");
        if (s.url && !s.deleted) { chip.href = s.url; chip.target = "_blank"; chip.rel = "noopener"; }
        chips.appendChild(chip);
      } else {
        chips.appendChild(el("span", "chip", `memorie · ${s.kind || "item"}`));
      }
    }
    line.appendChild(chips);
    container.appendChild(line);
  }
}

function toast(text) {
  const t = el("div", "toast", text);
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 5000);
}

async function pollCaptures() {
  // capturile de memorie apar asincron (plan A.§3) — polling ~30s după fiecare mesaj
  if (!sessionId) return;
  const deadline = Date.now() + 30000;
  const tick = async () => {
    if (Date.now() > deadline) return;
    try {
      const resp = await fetch(
        `/api/memory?session_id=${encodeURIComponent(sessionId)}&since=${encodeURIComponent(lastCaptureCheck)}`
      );
      if (resp.ok) {
        const data = await resp.json();
        for (const item of data.items) {
          if (!seenCaptures.has(item.id)) {
            seenCaptures.add(item.id);
            toast(`📌 Consemnat: ${item.title}`);
          }
        }
      }
    } catch (e) { /* rețea — reîncercăm la următorul tick */ }
    setTimeout(tick, 2500);
  };
  setTimeout(tick, 2500);
}

composer.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  send.disabled = true;
  addMessage("user", message);
  const thinking = addMessage("assistant", "…");
  // message_uuid generat de CLIENT, reutilizabil la retry (I4)
  const messageUuid = crypto.randomUUID();
  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId, message_uuid: messageUuid }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    sessionId = data.session_id;
    thinking.textContent = data.answer_ro;
    if (data.degraded) thinking.appendChild(el("div", "claim-line", "⚠ recall degradat (fără căutare semantică)"));
    renderClaims(thinking, data.claims);
    pollCaptures();
  } catch (err) {
    thinking.textContent = `Eroare: ${err.message}. Retrimite mesajul.`;
  } finally {
    send.disabled = false;
    input.focus();
  }
});

input.focus();
