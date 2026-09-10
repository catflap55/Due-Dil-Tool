/**
 * Due Diligence Workstation — local UI (no login).
 */

const MODULE_DEFS = [
  { id: "identifiers", label: "Identifier checks (local)" },
  { id: "identity", label: "Company identity" },
  { id: "vat", label: "VAT status (HMRC / VIES)" },
  { id: "financial", label: "Financial summary (filings)" },
  { id: "psc", label: "PSC / beneficial ownership (UK)" },
  { id: "insolvency", label: "Insolvency / Gazette" },
  { id: "courts", label: "Court findings (official links)" },
  { id: "sanctions", label: "Sanctions & watchlists (official links)" },
  { id: "registers", label: "Public registers" },
  { id: "credit_proxy", label: "Credit score proxy" },
  { id: "news", label: "News headlines (NewsAPI, optional)" },
  { id: "open_bris", label: "Open BRIS (optional)" },
];

const KEY_FIELDS = [
  ["companies_house", "Companies House API key", "https://developer.company-information.service.gov.uk/"],
  ["hmrc_client_id", "HMRC client ID", "https://developer.service.hmrc.gov.uk/"],
  ["hmrc_client_secret", "HMRC client secret", ""],
  ["newsapi", "NewsAPI.org key (optional)", "https://newsapi.org/"],
  ["open_bris", "Open BRIS key (optional)", ""],
];

let lastReport = null;

function el(id) {
  return document.getElementById(id);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function eelReady() {
  return typeof eel !== "undefined" && typeof eel.ping === "function";
}

async function loadCountries() {
  const rows = await eel.get_country_list()();
  const sel = el("country_code");
  sel.innerHTML = "";
  rows.forEach((r) => {
    const o = document.createElement("option");
    o.value = r.code;
    o.textContent = r.code + " — " + r.name;
    sel.appendChild(o);
  });
  sel.value = "GB";
  toggleVatFields();
}

function toggleVatFields() {
  const cc = el("country_code").value;
  el("uk-vat-wrap").hidden = cc !== "GB";
  el("eu-vat-wrap").hidden = cc === "GB";
}

function buildModuleBoxes() {
  const host = el("module-checkboxes");
  host.innerHTML = "";
  MODULE_DEFS.forEach((m) => {
    const wrap = document.createElement("label");
    wrap.className = "mod";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = m.id !== "news" && m.id !== "open_bris";
    cb.dataset.mod = m.id;
    wrap.appendChild(cb);
    wrap.appendChild(document.createTextNode(m.label));
    host.appendChild(wrap);
  });
}

function collectModules() {
  const mods = {};
  MODULE_DEFS.forEach((m) => {
    const cb = document.querySelector(`input[data-mod="${m.id}"]`);
    mods[m.id] = !!(cb && cb.checked);
  });
  return mods;
}

function showView(name) {
  el("view-main").hidden = name !== "main";
  el("view-settings").hidden = name !== "settings";
  el("nav-main").classList.toggle("is-on", name === "main");
  el("nav-settings").classList.toggle("is-on", name === "settings");
  if (name === "settings") refreshSettings();
}

function setStatus(msg) {
  el("form-status").textContent = msg || "";
}

function renderLinks(list) {
  if (!list || !list.length) return "";
  return (
    '<div class="links">' +
    list
      .map(
        (l) =>
          `<a href="${escapeHtml(l.href)}" target="_blank" rel="noopener">${escapeHtml(l.name)}</a>` +
          (l.note ? `<span class="muted"> — ${escapeHtml(l.note)}</span>` : "")
      )
      .join("") +
    "</div>"
  );
}

function renderFindings(findings) {
  if (!findings || !findings.length) return "";
  return (
    '<div class="kv">' +
    findings
      .map(
        (f) =>
          `<div><dt>${escapeHtml(f.label)}</dt><dd>${f.ok ? "" : "⚠ "}${escapeHtml(f.detail)}</dd></div>`
      )
      .join("") +
    "</div>"
  );
}

function moduleBody(key, m) {
  const data = m.data || {};
  if (key === "identifiers") return renderFindings(data.findings);
  if (key === "sanctions" || key === "registers") return renderLinks(data.links);
  if (key === "identity" && data.profile) {
    const p = data.profile;
    const addr = p.registered_office_address || {};
    const rows = [
      ["Name", p.company_name],
      ["Number", p.company_number],
      ["Status", p.company_status],
      ["Incorporated", p.date_of_creation],
      ["Type", p.type],
      ["SIC", (p.sic_codes || []).join(", ")],
      ["Office", [addr.address_line_1, addr.locality, addr.postal_code].filter(Boolean).join(", ")],
    ].filter((x) => x[1]);
    return (
      '<div class="kv">' +
      rows.map(([k, v]) => `<div><dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd></div>`).join("") +
      "</div>"
    );
  }
  if (key === "psc" && Array.isArray(data.items)) {
    if (!data.items.length) return '<p class="muted">No PSC records returned.</p>';
    return (
      '<div class="kv">' +
      data.items
        .map((it) => {
          const ctrl = (it.natures_of_control || []).join(", ");
          return `<div><dt>${escapeHtml(it.name || "Person")}</dt><dd>${escapeHtml(ctrl || "—")}</dd></div>`;
        })
        .join("") +
      "</div>"
    );
  }
  if (key === "insolvency" || key === "courts") {
    const links = [];
    if (data.gazette_search_url) links.push({ name: "The Gazette search", href: data.gazette_search_url });
    if (data.companies_house_profile_url)
      links.push({ name: "Companies House profile", href: data.companies_house_profile_url });
    if (data.search_url) links.push({ name: "Case law search", href: data.search_url });
    return renderLinks(links) || `<p class="muted">${escapeHtml(m.summary || "")}</p>`;
  }
  return `<p>${escapeHtml(m.summary || "")}</p>`;
}

function renderDashboard(report) {
  lastReport = report;
  el("empty-state").hidden = true;
  el("dashboard").hidden = false;
  const sample = !!(report.sample || (report.red_flags || []).some((f) => f.code === "SAMPLE_DOSSIER"));
  el("sample-banner").hidden = !sample;
  el("dossier-kicker").textContent = (report.country_code || "") + (sample ? " · sample" : "");
  el("dossier-title").textContent = report.query_name || "Subject";
  const bits = [];
  if (report.company_number) bits.push("No. " + report.company_number);
  if (report.timestamp_iso) bits.push(String(report.timestamp_iso).replace("T", " ").slice(0, 19) + " UTC");
  if (report.cached) bits.push("from local cache");
  el("dossier-meta").textContent = bits.join(" · ");

  const scoreBox = el("score-box");
  if (report.credit_proxy_score != null) {
    scoreBox.hidden = false;
    el("score-value").textContent = Number(report.credit_proxy_score).toFixed(0);
  } else scoreBox.hidden = true;

  const flags = el("flag-list");
  flags.innerHTML = "";
  (report.red_flags || []).forEach((f) => {
    const d = document.createElement("div");
    d.className = "flag " + (f.severity || "info");
    d.innerHTML = `<b class="sev-${escapeHtml(f.severity)}">${escapeHtml(f.severity)} · ${escapeHtml(
      f.code
    )}</b><span>${escapeHtml(f.explanation || "")}</span>`;
    flags.appendChild(d);
  });
  if (!(report.red_flags || []).length) {
    flags.innerHTML = '<p class="muted">No automated flags on this run.</p>';
  }

  const out = el("modules-out");
  out.innerHTML = "";
  const order = MODULE_DEFS.map((m) => m.id);
  const keys = Object.keys(report.modules || {}).sort((a, b) => order.indexOf(a) - order.indexOf(b));
  keys.forEach((k) => {
    const m = report.modules[k];
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = `
      <div class="card-top">
        <h3>${escapeHtml(k.replace(/_/g, " "))}</h3>
        <span class="pill ${m.ok ? "" : "bad"}">${m.ok ? "Clear" : "Needs attention"}</span>
      </div>
      <p class="muted">${escapeHtml(m.source || "")}</p>
      ${m.error ? `<p class="flag warning">${escapeHtml(m.error)}</p>` : ""}
      ${moduleBody(k, m)}
      <details>
        <summary>Technical detail</summary>
        <pre>${escapeHtml(JSON.stringify(m.data || {}, null, 2))}</pre>
      </details>
    `;
    out.appendChild(card);
  });
}

async function runPayload(payload) {
  setStatus("Running checks…");
  el("dashboard").style.opacity = "0.55";
  try {
    const res = await eel.dd_run(payload)();
    if (!res.ok) {
      setStatus(res.error || "Run failed");
      return;
    }
    renderDashboard(res.report);
    setStatus("Dossier ready.");
    await loadHistory();
  } catch (err) {
    setStatus("Could not reach the local app. Keep the Start window open.");
    console.error(err);
  } finally {
    el("dashboard").style.opacity = "";
  }
}

async function runSample() {
  setStatus("Opening sample dossier…");
  try {
    const res = await eel.dd_run_sample()();
    if (!res.ok) {
      setStatus(res.error || "Sample failed");
      return;
    }
    renderDashboard(res.report);
    setStatus("Sample dossier — demonstration only.");
  } catch (err) {
    setStatus("Could not reach the local app. Keep the Start window open.");
  }
}

async function loadHistory() {
  try {
    const r = await eel.settings_recent_searches()();
    const host = el("history-list");
    const items = (r.ok && r.items) || [];
    if (!items.length) {
      host.innerHTML = '<p class="muted">No inquiries yet.</p>';
      return;
    }
    host.innerHTML = "";
    items.slice(0, 8).forEach((it) => {
      const snap = it.query_snapshot || {};
      const b = document.createElement("button");
      b.type = "button";
      b.innerHTML = `<strong>${escapeHtml(snap.name || "Inquiry")}</strong><small>${escapeHtml(
        (snap.country || "") + (snap.registration ? " · " + snap.registration : "")
      )}</small>`;
      b.addEventListener("click", () => {
        const form = el("dd-form");
        form.company_name.value = snap.name || "";
        form.registration_number.value = snap.registration || "";
        if (snap.country) {
          el("country_code").value = snap.country;
          toggleVatFields();
        }
        form.company_name.focus();
      });
      host.appendChild(b);
    });
  } catch (_e) {
    /* still starting */
  }
}

async function refreshSettings() {
  const rk = await eel.settings_key_mask()();
  const box = el("api-keys-form");
  box.innerHTML = "";
  KEY_FIELDS.forEach(([name, label, href]) => {
    const row = document.createElement("label");
    const hint =
      rk.ok && rk.has_value[name] ? "Saved on this computer — type a new value to replace, or leave blank." : "Not set";
    row.innerHTML = `<span>${escapeHtml(label)}</span>
      <input data-key="${name}" type="password" autocomplete="off" placeholder="${escapeHtml(hint)}" />
      ${href ? `<a class="muted" href="${href}" target="_blank" rel="noopener">Get a key</a>` : ""}`;
    box.appendChild(row);
  });

  const cfg = await eel.settings_get_config()();
  const w = (cfg.ok && cfg.config.scoring_weights) || {};
  const host = el("weights-sliders");
  host.innerHTML = "";
  Object.keys(w).forEach((k) => {
    const div = document.createElement("label");
    div.innerHTML = `<span>${escapeHtml(k.replace(/_/g, " "))} (<span data-wv="${k}">${w[k]}</span>)</span>
      <input type="range" min="0" max="100" step="1" value="${w[k]}" data-w="${k}" />`;
    const range = div.querySelector("input");
    range.addEventListener("input", () => {
      div.querySelector("[data-wv]").textContent = range.value;
    });
    host.appendChild(div);
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  buildModuleBoxes();
  el("nav-main").addEventListener("click", () => showView("main"));
  el("nav-settings").addEventListener("click", () => showView("settings"));
  el("country_code").addEventListener("change", toggleVatFields);
  el("btn-sample").addEventListener("click", runSample);

  el("dd-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    await runPayload({
      company_name: fd.get("company_name"),
      registration_number: (fd.get("registration_number") || "").trim() || null,
      country_code: fd.get("country_code"),
      uk_vat_number: (fd.get("uk_vat_number") || "").trim() || null,
      eu_vat_input: (fd.get("eu_vat_input") || "").trim() || null,
      modules: collectModules(),
      use_cache: fd.get("use_cache") === "on",
    });
  });

  el("btn-export").addEventListener("click", async () => {
    el("export-msg").textContent = "Writing PDF…";
    const r = await eel.dd_export_pdf()();
    el("export-msg").textContent = r.ok ? "Saved: " + r.path : r.error || "Failed";
  });
  el("btn-csv").addEventListener("click", async () => {
    el("export-msg").textContent = "Writing CSV…";
    const r = await eel.dd_export_csv()();
    el("export-msg").textContent = r.ok ? "Saved: " + r.path : r.error || "Failed";
  });

  el("btn-save-keys").addEventListener("click", async () => {
    const inputs = document.querySelectorAll("#api-keys-form input[data-key]");
    for (const inp of inputs) {
      await eel.settings_set_api_key(inp.dataset.key, inp.value.trim())();
    }
    el("keys-msg").textContent = "Saved on this computer.";
    await refreshSettings();
  });
  el("btn-save-config").addEventListener("click", async () => {
    const cfg = await eel.settings_get_config()();
    if (!cfg.ok) return;
    const base = cfg.config;
    const weights = { ...base.scoring_weights };
    document.querySelectorAll("#weights-sliders input[data-w]").forEach((inp) => {
      weights[inp.dataset.w] = parseFloat(inp.value);
    });
    base.scoring_weights = weights;
    const r = await eel.settings_set_config(base)();
    el("weights-msg").textContent = r.ok ? "Weights saved." : r.error;
  });
  el("btn-clear-cache").addEventListener("click", async () => {
    const r = await eel.settings_clear_cache()();
    el("cache-msg").textContent = r.ok ? `Removed ${r.removed} cached runs.` : r.error;
    await loadHistory();
  });

  const params = new URLSearchParams(location.search);
  if (params.get("view") === "settings") {
    showView("settings");
  }

  if (!eelReady()) {
    setStatus("Waiting for the local app… keep the Start window open.");
    return;
  }
  await loadCountries();
  await loadHistory();
  if (params.get("view") === "settings") {
    await refreshSettings();
  }
  if (params.get("demo") === "1") {
    await runSample();
  }
});
