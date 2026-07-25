"use strict";
/* Project Atlas AI — research console. Vanilla JS, no build step; talks to the
   same REST API documented at /docs. */

// ---- tiny DOM helper (textContent by default → safe from injection) ----
function h(tag, props, children) {
  const el = document.createElement(tag);
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (v == null) continue;
      if (k === "class") el.className = v;
      else if (k === "html") el.innerHTML = v;
      else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v);
    }
  }
  for (const c of [].concat(children || [])) {
    if (c == null) continue;
    el.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
  }
  return el;
}
const $ = (sel) => document.querySelector(sel);

async function getJSON(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try { const b = await res.json(); detail = b.detail || JSON.stringify(b); } catch (_) {}
    throw new Error(`HTTP ${res.status} — ${detail}`);
  }
  return res.json();
}

const fmtPct = (x, d = 1) => `${x >= 0 ? "" : ""}${x.toFixed(d)}%`;
const money = (x) => "₹" + Math.round(x).toLocaleString("en-IN");

// ---- theme ----
(function initTheme() {
  const saved = localStorage.getItem("atlas-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  $("#theme-toggle").addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme");
    const isDark = cur ? cur === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    const next = isDark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("atlas-theme", next);
  });
})();

// ---- classification helpers ----
function actionClass(action) {
  if (["BUY", "ACCUMULATE"].includes(action)) return "buy";
  if (["SELL", "REDUCE", "AVOID"].includes(action)) return "sell";
  return "hold";
}
function sigClass(strength) {
  if (strength.includes("BULLISH")) return "bull";
  if (strength.includes("BEARISH")) return "bear";
  return "neu";
}
function scoreColor(score) {
  if (score >= 55) return "var(--bull)";
  if (score <= 45) return "var(--bear)";
  return "var(--neu)";
}
const prettySignal = (s) => s.replace(/_/g, " ").toLowerCase();

// ---- meta / disclaimer ----
async function loadMeta() {
  try {
    const m = await getJSON("/api");
    const pill = $("#mode-pill");
    pill.textContent = m.adapter_mode === "mock" ? "MOCK DATA" : "LIVE DATA";
    pill.className = "pill " + (m.adapter_mode === "mock" ? "pill-mock" : "pill-real");
    $("#footer-disclaimer").textContent = m.disclaimer;
  } catch (_) { /* non-fatal */ }
}

// ---- recommendation ----
function statCard(label, value, sub, meterPct, meterColor) {
  const v = h("div", { class: "v" }, sub ? [String(value), h("small", null, " " + sub)] : String(value));
  const children = [h("div", { class: "l" }, label), v];
  if (meterPct != null) {
    children.push(h("div", { class: "meter" }, h("span", { style: `width:${Math.max(0, Math.min(100, meterPct))}%;background:${meterColor || "var(--accent)"}` })));
  }
  return h("div", { class: "stat" }, children);
}

function renderAgents(reports) {
  const rows = reports.map((r) => {
    const lead = r.signals[0];
    const bar = h("div", { class: "scorebar" }, h("span", { style: `width:${r.score}%;background:${scoreColor(r.score)}` }));
    const cell = h("div", { class: "scorecell" }, [bar, h("span", { class: "scoreval" }, r.score.toFixed(0))]);
    const sig = lead
      ? h("span", { class: "sig " + sigClass(lead.strength) }, `${lead.name} · ${prettySignal(lead.strength)}`)
      : "";
    return h("tr", null, [
      h("td", { class: "agent" }, r.agent),
      h("td", null, cell),
      h("td", null, sig),
    ]);
  });
  const table = h("table", null, [
    h("thead", null, h("tr", null, [h("th", null, "Agent"), h("th", null, "Score / 100"), h("th", null, "Lead signal")])),
    h("tbody", null, rows),
  ]);
  return h("div", { class: "agents" }, table);
}

function evidenceList(items, counter) {
  return h("ul", { class: "ev-list" + (counter ? " counter" : "") },
    items.map((t) => h("li", null, t)));
}

function renderRecommendation(rec) {
  const out = rec.outlook, risk = rec.risk;
  const frag = document.createDocumentFragment();

  // Head
  frag.appendChild(h("div", { class: "rec-head" }, [
    h("span", { class: "rec-sym" }, `${rec.symbol}`),
    h("span", { class: "action-badge " + actionClass(rec.action) }, rec.action),
    h("span", { class: "conv" }, `${rec.conviction} conviction · ${rec.time_horizon.replace("_", " ").toLowerCase()}`),
  ]));

  // Summary
  frag.appendChild(h("p", { class: "summary" }, rec.executive_summary));

  // Stats
  frag.appendChild(h("div", { class: "stat-grid" }, [
    statCard("Confidence", Math.round(rec.confidence * 100), "%", rec.confidence * 100, "var(--accent)"),
    statCard("Prob. favourable", Math.round(out.probability_favourable * 100), "%", out.probability_favourable * 100, out.probability_favourable >= 0.5 ? "var(--bull)" : "var(--bear)"),
    statCard("Expected CAGR", fmtPct(out.expected_cagr_pct), ""),
    statCard("90% CI", `${out.cagr_p05_pct.toFixed(1)} … ${out.cagr_p95_pct.toFixed(1)}%`, ""),
    statCard("Reward : Risk", risk.reward_to_risk.toFixed(1), ""),
    statCard("Value at risk", fmtPct(risk.value_at_risk_pct, 2), ""),
  ]));

  // Trade plan
  frag.appendChild(h("div", { class: "subhead" }, "Trade plan"));
  frag.appendChild(h("div", { class: "stat-grid" }, [
    statCard("Entry", money(risk.entry_price), ""),
    statCard("Stop loss", money(risk.stop_loss), ""),
    statCard("Target", money(risk.target_price), ""),
    statCard("Quantity", risk.quantity, "sh"),
    statCard("Position value", money(risk.position_value), ""),
    statCard("Capital at risk", money(risk.capital_at_risk), ""),
  ]));

  // Agents
  frag.appendChild(h("div", { class: "subhead" }, `Agent contributions (${rec.agent_reports.length})`));
  frag.appendChild(renderAgents(rec.agent_reports));

  // Evidence / counter
  const supporting = rec.evidence.filter((e) => !e.is_counter).map((e) => e.claim);
  const against = rec.counter_arguments && rec.counter_arguments.length
    ? rec.counter_arguments
    : rec.evidence.filter((e) => e.is_counter).map((e) => e.claim);
  frag.appendChild(h("div", { class: "eyes" }, [
    h("div", null, [h("div", { class: "subhead" }, `Supporting evidence`), evidenceList(supporting.slice(0, 8), false)]),
    h("div", null, [h("div", { class: "subhead" }, `Counter-arguments`), evidenceList(against.slice(0, 8), true)]),
  ]));

  // Catalysts + unknowns
  if (rec.catalysts && rec.catalysts.length) {
    frag.appendChild(h("div", { class: "subhead" }, "Catalysts"));
    frag.appendChild(evidenceList(rec.catalysts, false));
  }

  // Governance
  const g = rec.governance;
  frag.appendChild(h("div", { class: "subhead" }, "Governance & audit"));
  frag.appendChild(h("div", { class: "gov" }, [
    h("b", null, "id "), rec.id, "  ·  ",
    h("b", null, "pipeline "), g.pipeline_version, "  ·  ",
    h("b", null, "model "), g.model_version,
    h("br"), g.reasoning_summary,
  ]));

  const result = $("#result");
  result.textContent = "";
  result.appendChild(frag);
  result.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ---- form ----
$("#research-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("#run-btn");
  const status = $("#research-status");
  const form = e.target;
  const body = {
    symbol: form.symbol.value.trim().toUpperCase(),
    exchange: form.exchange.value,
    capital: Number(form.capital.value),
  };
  if (form.time_horizon.value) body.time_horizon = form.time_horizon.value;

  btn.disabled = true;
  status.hidden = false;
  status.className = "research-status";
  status.textContent = `Running 13 agents on ${body.symbol}…`;
  try {
    const rec = await getJSON("/api/v1/recommendations", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    status.hidden = true;
    renderRecommendation(rec);
  } catch (err) {
    status.className = "research-status err";
    status.textContent = `Could not generate research: ${err.message}`;
    $("#result").textContent = "";
  } finally {
    btn.disabled = false;
  }
});

// ---- fleet ----
async function loadFleet() {
  const wrap = $("#fleet");
  wrap.appendChild(h("div", { class: "loading" }, "Loading agent fleet…"));
  try {
    const s = await getJSON("/api/v1/status");
    $("#fleet-summary").textContent = "";
    $("#fleet-summary").append(
      h("span", { class: "kv" }, [h("b", null, String(s.agent_count)), " agents"]),
      h("span", { class: "kv" }, [h("b", null, String(s.live_on_real_data)), " on real feeds"]),
      h("span", { class: "kv" }, ["mode ", h("b", null, s.adapter_mode)]),
      h("span", { class: "kv" }, s.cto_readiness),
    );
    wrap.textContent = "";
    for (const a of s.agents) {
      const real = a.data_basis.includes("(real)");
      wrap.appendChild(h("div", { class: "agent-card" }, [
        h("div", { class: "top" }, [
          h("span", { class: "kind" }, a.kind),
          h("span", { class: "wt" }, a.weight != null ? "w " + a.weight.toFixed(2) : "synth"),
        ]),
        h("div", { class: "role" }, a.role),
        h("div", { class: "basis" }, [
          h("span", { class: "pill " + (real ? "pill-real" : "pill-mock") }, real ? "real" : "mock"),
          a.data_basis.replace(" (real)", ""),
        ]),
      ]));
    }
  } catch (err) {
    wrap.textContent = "";
    wrap.appendChild(h("div", { class: "loading" }, "Fleet status unavailable: " + err.message));
  }
}

// ---- trends ----
function dirClass(d) { return d === "UP" ? "up" : d === "DOWN" ? "down" : "flat"; }
async function loadTrends() {
  const wrap = $("#trends");
  wrap.appendChild(h("div", { class: "loading" }, "Loading index trends…"));
  try {
    const t = await getJSON("/api/v1/trend/indices?group=all");
    wrap.textContent = "";
    for (const i of t.indices) {
      const arrow = i.direction === "UP" ? "▲" : i.direction === "DOWN" ? "▼" : "▬";
      wrap.appendChild(h("div", { class: "trend-card" }, [
        h("div", { class: "name" }, i.name),
        h("span", { class: "sym" }, i.symbol),
        h("div", { class: "chg " + dirClass(i.direction) }, `${arrow} ${i.change_pct >= 0 ? "+" : ""}${i.change_pct.toFixed(2)}%`),
        h("div", { class: "lvl" }, `last ${i.last_close.toLocaleString("en-IN")} · SMA ${i.sma.toLocaleString("en-IN")}`),
      ]));
    }
    if (!t.indices.length) wrap.appendChild(h("div", { class: "loading" }, "No index data available."));
  } catch (err) {
    wrap.textContent = "";
    wrap.appendChild(h("div", { class: "loading" }, "Trends unavailable: " + err.message + " (live feeds may be blocked in this environment)."));
  }
}

// ---- init ----
loadMeta();
loadFleet();
loadTrends();
