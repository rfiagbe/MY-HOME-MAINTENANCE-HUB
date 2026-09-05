/* ============================================================
   Home Maintenance Hub
   Static PWA. Reads/writes data/tasks.json + data/history.json
   in the GitHub repo via the Contents API.
   ============================================================ */
(function () {
  "use strict";

  // ---------------------------------------------------------------
  // Small utilities
  // ---------------------------------------------------------------
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /* Dates are handled as local calendar days, never UTC instants,
     so "due today" means today where the user actually lives. */
  function parseDay(s) {
    if (!s) return null;
    const p = String(s).slice(0, 10).split("-").map(Number);
    if (p.length !== 3 || p.some(isNaN)) return null;
    return new Date(p[0], p[1] - 1, p[2]);
  }
  function isoDay(dt) {
    return dt.getFullYear() + "-" +
      String(dt.getMonth() + 1).padStart(2, "0") + "-" +
      String(dt.getDate()).padStart(2, "0");
  }
  function todayDay() {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), n.getDate());
  }
  function addDays(dt, n) {
    const c = new Date(dt.getTime());
    c.setDate(c.getDate() + n);
    return c;
  }
  function dayDiff(a, b) {
    return Math.round((b.getTime() - a.getTime()) / 86400000);
  }
  function clampDay(y, m, d) {
    return Math.min(d, new Date(y, m, 0).getDate()); // m is 1-based here
  }
  function fmtDate(s) {
    const dt = parseDay(s);
    if (!dt) return "—";
    return dt.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }
  function fmtShort(s) {
    const dt = parseDay(s);
    if (!dt) return "—";
    return dt.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }
  function money(n) {
    return "$" + Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  function plural(n, one, many) {
    return n + " " + (n === 1 ? one : (many || one + "s"));
  }

  // UTF-8 safe base64 (task text contains ★, °, — and friends)
  function b64encode(str) {
    const bytes = new TextEncoder().encode(str);
    let bin = "";
    const CH = 0x8000;
    for (let i = 0; i < bytes.length; i += CH) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CH));
    }
    return btoa(bin);
  }
  function b64decode(b64) {
    const bin = atob(String(b64).replace(/\s/g, ""));
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  }

  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  let toastTimer = null;
  function toast(msg, isErr) {
    const t = $("#toast");
    t.textContent = msg;
    t.className = "toast" + (isErr ? " err" : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.add("hidden"), isErr ? 5200 : 2600);
  }

  // ---------------------------------------------------------------
  // State
  // ---------------------------------------------------------------
  const LS = {
    repo: "hmh.repo",
    branch: "hmh.branch",
    token: "hmh.token",
    cacheTasks: "hmh.cache.tasks",
    cacheHist: "hmh.cache.history"
  };

  const state = {
    tasks: null,          // full tasks.json document
    history: null,        // full history.json document
    sha: { tasks: null, history: null },
    connected: false,
    view: "dashboard",
    dirty: false
  };

  let lastLoad = 0;       // epoch ms of the last successful read, for refresh-on-focus

  function cfg() {
    return {
      repo: (localStorage.getItem(LS.repo) || "").trim(),
      branch: (localStorage.getItem(LS.branch) || "main").trim() || "main",
      token: (localStorage.getItem(LS.token) || "").trim()
    };
  }

  function guessRepoFromUrl() {
    // https://<user>.github.io/<repo>/  ->  <user>/<repo>
    const h = location.hostname.match(/^([^.]+)\.github\.io$/i);
    if (!h) return "";
    const seg = location.pathname.split("/").filter(Boolean);
    return seg.length ? h[1] + "/" + seg[0] : "";
  }

  // ---------------------------------------------------------------
  // GitHub Contents API
  // ---------------------------------------------------------------
  function ghHeaders(token) {
    return {
      "Authorization": "Bearer " + token,
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28"
    };
  }

  async function ghRead(path) {
    const c = cfg();
    const url = "https://api.github.com/repos/" + c.repo + "/contents/" +
      path + "?ref=" + encodeURIComponent(c.branch) + "&t=" + Date.now();
    const res = await fetch(url, { headers: ghHeaders(c.token), cache: "no-store" });
    if (res.status === 404) return { doc: null, sha: null };
    if (!res.ok) throw new Error("GitHub read failed (" + res.status + "): " + (await res.text()).slice(0, 180));
    const j = await res.json();
    return { doc: JSON.parse(b64decode(j.content)), sha: j.sha };
  }

  async function ghWrite(path, doc, sha, message) {
    const c = cfg();
    const url = "https://api.github.com/repos/" + c.repo + "/contents/" + path;
    const body = {
      message: message,
      content: b64encode(JSON.stringify(doc, null, 2) + "\n"),
      branch: c.branch
    };
    if (sha) body.sha = sha;
    const res = await fetch(url, {
      method: "PUT",
      headers: Object.assign(ghHeaders(c.token), { "Content-Type": "application/json" }),
      body: JSON.stringify(body)
    });
    if (!res.ok) {
      const txt = await res.text();
      const err = new Error("GitHub write failed (" + res.status + "): " + txt.slice(0, 200));
      err.status = res.status;
      throw err;
    }
    const j = await res.json();
    return j.content.sha;
  }

  // ---------------------------------------------------------------
  // Load / save
  // ---------------------------------------------------------------
  async function loadLocal() {
    const bust = "?t=" + Date.now();
    const [t, h] = await Promise.all([
      fetch("./data/tasks.json" + bust, { cache: "no-store" }).then(r => r.json()),
      fetch("./data/history.json" + bust, { cache: "no-store" }).then(r => r.json()).catch(() => ({ version: 1, entries: [] }))
    ]);
    return { tasks: t, history: h };
  }

  async function loadAll() {
    const c = cfg();
    setSync("busy", "Loading");

    if (c.repo && c.token) {
      try {
        const [t, h] = await Promise.all([ghRead("data/tasks.json"), ghRead("data/history.json")]);
        if (!t.doc) throw new Error("data/tasks.json not found in " + c.repo);
        state.tasks = t.doc;
        state.sha.tasks = t.sha;
        state.history = h.doc || { version: 1, entries: [] };
        state.sha.history = h.sha;
        state.connected = true;
        lastLoad = Date.now();
        cacheLocally();
        setSync("ok", "Synced");
        return;
      } catch (e) {
        console.warn("GitHub load failed, falling back:", e);
        toast("Couldn't reach GitHub — showing last known data. " + e.message, true);
      }
    }

    // Fallback: cached copy, then the files shipped with the site
    state.connected = false;
    const cachedT = localStorage.getItem(LS.cacheTasks);
    const cachedH = localStorage.getItem(LS.cacheHist);
    if (cachedT) {
      try {
        state.tasks = JSON.parse(cachedT);
        state.history = cachedH ? JSON.parse(cachedH) : { version: 1, entries: [] };
        setSync("idle", "Local");
        return;
      } catch (e) { /* fall through to the bundled copy */ }
    }
    const fresh = await loadLocal();
    state.tasks = fresh.tasks;
    state.history = fresh.history;
    setSync("idle", "Local");
  }

  function cacheLocally() {
    try {
      localStorage.setItem(LS.cacheTasks, JSON.stringify(state.tasks));
      localStorage.setItem(LS.cacheHist, JSON.stringify(state.history));
    } catch (e) { /* quota — not fatal */ }
  }

  /* Mark a task (or the home settings) as changed on this device, so a merge
     can tell which side is newer. Without this, two devices editing different
     tasks would clobber each other. */
  function touch(task) {
    task.updatedAt = new Date().toISOString();
  }
  function touchHome() {
    state.tasks.home.updatedAt = new Date().toISOString();
  }

  /* Union of both sides' entries. History is append-only with unique ids, so
     nothing ever has to be thrown away. */
  function mergeHistory(remote, local) {
    const seen = new Set();
    const all = [];
    (remote.entries || []).concat(local.entries || []).forEach((e) => {
      if (!e || !e.id || seen.has(e.id)) return;
      seen.add(e.id);
      all.push(e);
    });
    all.sort((a, b) =>
      String(a.date).localeCompare(String(b.date)) ||
      String(a.loggedAt || "").localeCompare(String(b.loggedAt || "")));
    return { version: remote.version || local.version || 1, entries: all };
  }

  /* Per-task merge: the remote copy supplies the catalog (titles, steps,
     schedules), and for each task the side with the newer updatedAt supplies
     the mutable state. A task this device never touched keeps the other
     device's completion instead of being overwritten. */
  function mergeTasks(remote, local) {
    const out = JSON.parse(JSON.stringify(remote));
    const lmap = {};
    (local.tasks || []).forEach((t) => { lmap[t.id] = t; });

    out.tasks.forEach((rt) => {
      const lt = lmap[rt.id];
      if (!lt) return;
      const lStamp = lt.updatedAt || "";
      const rStamp = rt.updatedAt || "";
      if (lStamp && lStamp >= rStamp) {
        rt.nextDue = lt.nextDue;
        rt.lastCompleted = lt.lastCompleted;
        rt.enabled = lt.enabled;
        rt.notes = lt.notes;
        rt.timesCompleted = Math.max(lt.timesCompleted || 0, rt.timesCompleted || 0);
        rt.updatedAt = lStamp;
      }
    });

    const rids = new Set(out.tasks.map((t) => t.id));
    (local.tasks || []).forEach((lt) => { if (!rids.has(lt.id)) out.tasks.push(lt); });

    const lh = (local.home && local.home.updatedAt) || "";
    const rh = (remote.home && remote.home.updatedAt) || "";
    if (lh && lh >= rh) out.home = local.home;
    return out;
  }

  async function mergeFromRemote() {
    const [t, h] = await Promise.all([ghRead("data/tasks.json"), ghRead("data/history.json")]);
    state.sha.tasks = t.sha;
    state.sha.history = h.sha;
    if (t.doc) state.tasks = mergeTasks(t.doc, state.tasks);
    if (h.doc) state.history = mergeHistory(h.doc, state.history);
  }

  async function pushBoth(message) {
    state.sha.tasks = await ghWrite("data/tasks.json", state.tasks, state.sha.tasks, message);
    state.sha.history = await ghWrite("data/history.json", state.history, state.sha.history, message);
  }

  async function saveAll(message) {
    cacheLocally();
    if (!state.connected) {
      setSync("idle", "Local only");
      toast("Saved on this device. Connect GitHub in Settings to sync.");
      return false;
    }
    setSync("busy", "Saving");
    try {
      await pushBoth(message);
      lastLoad = Date.now();
      setSync("ok", "Saved");
      return true;
    } catch (e) {
      // 409/422 = another device committed first. Merge its work in, then retry.
      if (e.status === 409 || e.status === 422) {
        try {
          await mergeFromRemote();
          await pushBoth(message);
          cacheLocally();
          lastLoad = Date.now();
          setSync("ok", "Saved");
          renderCurrent();          // show whatever the other device had done
          return true;
        } catch (e2) {
          setSync("err", "Save failed");
          toast("Save failed: " + e2.message, true);
          return false;
        }
      }
      setSync("err", "Save failed");
      toast("Save failed: " + e.message, true);
      return false;
    }
  }

  function setSync(kind, label) {
    const p = $("#syncPill");
    p.className = "pill pill-" + kind;
    p.textContent = label;
  }

  // ---------------------------------------------------------------
  // Scheduling  (mirrors scripts/seed_tasks.py and send_reminders.py)
  // ---------------------------------------------------------------
  function nextDueAfter(task, fromISO) {
    const s = task.schedule || {};
    const from = parseDay(fromISO) || todayDay();

    if (s.type === "once") return null;              // one-and-done

    if (s.type === "interval") {
      return isoDay(addDays(from, Math.max(1, s.days | 0)));
    }

    if (s.type === "fixed") {
      const day = s.day || 1;
      let best = null;
      for (const y of [from.getFullYear(), from.getFullYear() + 1, from.getFullYear() + 2]) {
        for (const m of s.months) {
          const cand = new Date(y, m - 1, clampDay(y, m, day));
          if (cand > from && (!best || cand < best)) best = cand;
        }
      }
      return best ? isoDay(best) : null;
    }
    return null;
  }

  function scheduleLabel(task) {
    const s = task.schedule || {};
    if (s.type === "once") return "One time";
    if (s.type === "interval") {
      const d = s.days;
      if (d <= 7) return "Weekly";
      if (d <= 15) return "Every 2 weeks";
      if (d <= 31) return "Monthly";
      if (d <= 46) return "Every 6 weeks";
      if (d <= 92) return "Quarterly";
      if (d <= 185) return "Every 6 months";
      if (d <= 370) return "Yearly";
      if (d < 1000) return "Every " + Math.round(d / 365) + " years";
      return "Every " + Math.round(d / 365) + " years";
    }
    if (s.type === "fixed") {
      const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const ms = s.months.map(m => names[m - 1]).join(" & ");
      return s.months.length === 1 ? "Every " + ms : ms + " each year";
    }
    return "—";
  }

  function isActive(task) {
    if (task.enabled === false) return false;
    if (task.requires) {
      const f = (state.tasks.home && state.tasks.home.features) || {};
      if (!f[task.requires]) return false;
    }
    return true;
  }

  function isFinished(task) {
    return (task.schedule || {}).type === "once" && !!task.lastCompleted;
  }

  function dueTasks() {
    return state.tasks.tasks
      .filter(t => isActive(t) && !isFinished(t) && t.nextDue)
      .sort((a, b) => a.nextDue.localeCompare(b.nextDue) || a.title.localeCompare(b.title));
  }

  function bucket(task, today) {
    const due = parseDay(task.nextDue);
    if (!due) return "later";
    const n = dayDiff(today, due);
    if (n < 0) return "overdue";
    if (n === 0) return "today";
    if (n <= 7) return "week";
    if (n <= 30) return "month";
    return "later";
  }

  // ---------------------------------------------------------------
  // Card rendering
  // ---------------------------------------------------------------
  function dueChip(task, today) {
    const due = parseDay(task.nextDue);
    if (!due) return { cls: "chip", text: "No date" };
    const n = dayDiff(today, due);
    if (n < 0) return { cls: "chip chip-due-over", text: plural(-n, "day") + " overdue" };
    if (n === 0) return { cls: "chip chip-due-today", text: "Due today" };
    if (n === 1) return { cls: "chip chip-due-soon", text: "Due tomorrow" };
    if (n <= 7) return { cls: "chip chip-due-soon", text: "In " + plural(n, "day") };
    return { cls: "chip", text: fmtShort(task.nextDue) };
  }

  const CAT_ICON = {
    "HVAC": "❄️",
    "Water Heater": "🔥",
    "Plumbing": "🚰",
    "Electrical & Safety": "⚡",
    "Kitchen": "🍳",
    "Laundry": "🧺",
    "Irrigation & Lawn": "🌱",
    "Exterior & Roof": "🏠",
    "Lanai & Screens": "🪟",
    "Pest & Termite": "🐜",
    "Storm & Hurricane": "🌀",
    "Warranty & Documents": "📋",
    "Interior": "🛋️",
    "Pool & Spa": "🏊",
    "Septic & Well": "💧"
  };
  function catLabel(c) {
    return (CAT_ICON[c] ? CAT_ICON[c] + " " : "") + c;
  }

  function taskCard(task, today) {
    const card = el("div", "card p-" + (task.priority || "normal"));
    if (!isActive(task)) card.classList.add("is-off");

    const main = el("div", "card-main");
    main.appendChild(el("div", "card-title", task.title));

    const meta = el("div", "card-meta");
    const dc = dueChip(task, today);
    if (isFinished(task)) {
      const c = el("span", "chip chip-pro", "✓ Done " + fmtShort(task.lastCompleted));
      meta.appendChild(c);
    } else {
      meta.appendChild(el("span", dc.cls, dc.text));
    }
    meta.appendChild(el("span", "chip", catLabel(task.category)));
    meta.appendChild(el("span", "chip", scheduleLabel(task)));
    if (task.diy === false) meta.appendChild(el("span", "chip chip-pro", "Hire a pro"));
    if (!isActive(task)) meta.appendChild(el("span", "chip", "Disabled"));
    main.appendChild(meta);

    main.addEventListener("click", () => openSheet(task.id));
    card.appendChild(main);

    if (isActive(task) && !isFinished(task)) {
      const btn = el("button", "card-check", "✓");
      btn.title = "Mark complete";
      btn.setAttribute("aria-label", "Mark " + task.title + " complete");
      btn.addEventListener("click", (e) => { e.stopPropagation(); openDone(task.id); });
      card.appendChild(btn);
    }
    return card;
  }

  // ---------------------------------------------------------------
  // Dashboard
  // ---------------------------------------------------------------
  function renderDashboard() {
    const today = todayDay();
    const all = dueTasks();
    const groups = { overdue: [], today: [], week: [], month: [], later: [] };
    all.forEach(t => groups[bucket(t, today)].push(t));

    const doneThisYear = (state.history.entries || [])
      .filter(e => e.type !== "skipped" && String(e.date).slice(0, 4) === String(today.getFullYear())).length;

    const stats = [
      { n: groups.overdue.length, l: "Overdue", c: groups.overdue.length ? "is-crit" : "" },
      { n: groups.today.length + groups.week.length, l: "This week", c: (groups.today.length + groups.week.length) ? "is-warn" : "" },
      { n: groups.month.length, l: "This month", c: "" },
      { n: doneThisYear, l: "Done in " + today.getFullYear(), c: doneThisYear ? "is-ok" : "" }
    ];
    const sr = $("#statRow");
    sr.innerHTML = "";
    stats.forEach(s => {
      const d = el("div", "stat " + s.c);
      d.appendChild(el("div", "n", String(s.n)));
      d.appendChild(el("div", "l", s.l));
      sr.appendChild(d);
    });

    const map = [
      ["Overdue", "#listOverdue", "#cOverdue", "#grpOverdue", groups.overdue, null],
      ["Today", "#listToday", "#cToday", "#grpToday", groups.today, null],
      ["Week", "#listWeek", "#cWeek", "#grpWeek", groups.week, null],
      ["Month", "#listMonth", "#cMonth", "#grpMonth", groups.month, null],
      ["Later", "#listLater", "#cLater", "#grpLater", groups.later, 12]
    ];
    map.forEach(([, listSel, cntSel, grpSel, items, limit]) => {
      const list = $(listSel);
      list.innerHTML = "";
      const shown = limit ? items.slice(0, limit) : items;
      shown.forEach(t => list.appendChild(taskCard(t, today)));
      if (limit && items.length > limit) {
        const more = el("p", "empty", "+ " + (items.length - limit) + " more — see All Tasks");
        list.appendChild(more);
      }
      $(cntSel).textContent = String(items.length);
      $(grpSel).classList.toggle("is-empty", items.length === 0);
    });

    if (!all.length) {
      $("#grpToday").classList.remove("is-empty");
      $("#listToday").innerHTML = '<p class="empty">Nothing scheduled. Check Settings to make sure tasks are enabled.</p>';
    }

    renderWarrantyBanner(today);
  }

  function renderWarrantyBanner(today) {
    const b = $("#warrantyBanner");
    const w = (state.tasks.home && state.tasks.home.warranty) || {};
    const exp = parseDay(w.workmanship1yr);
    if (!exp) { b.classList.add("hidden"); return; }
    const left = dayDiff(today, exp);
    if (left < 0 || left > 365) { b.classList.add("hidden"); return; }

    const insp = state.tasks.tasks.find(t => t.id === "warranty-11month");
    const done = insp && insp.lastCompleted;
    b.classList.remove("hidden");
    b.innerHTML =
      '<div class="banner-t">🛠 Builder warranty clock</div>' +
      "Your 1-year workmanship warranty expires <strong>" + esc(fmtDate(w.workmanship1yr)) +
      "</strong> — " + plural(left, "day") + " left. " +
      (done
        ? "Your 11-month inspection is logged. Make sure every punch-list item is submitted in writing."
        : "Book the independent 11-month inspection around month 10 so there's time to submit claims in writing.");
  }

  // ---------------------------------------------------------------
  // All tasks
  // ---------------------------------------------------------------
  function renderTasks() {
    const today = todayDay();
    const q = ($("#taskSearch").value || "").toLowerCase().trim();
    const cat = $("#catFilter").value;
    const st = $("#stateFilter").value;

    let list = state.tasks.tasks.slice();
    if (st === "active") list = list.filter(t => isActive(t));
    else if (st === "disabled") list = list.filter(t => !isActive(t));

    if (cat) list = list.filter(t => t.category === cat);
    if (q) {
      list = list.filter(t =>
        t.title.toLowerCase().includes(q) ||
        t.category.toLowerCase().includes(q) ||
        (t.equipment || "").toLowerCase().includes(q) ||
        (t.why || "").toLowerCase().includes(q)
      );
    }

    list.sort((a, b) => {
      const af = isFinished(a), bf = isFinished(b);
      if (af !== bf) return af ? 1 : -1;
      return (a.nextDue || "9999").localeCompare(b.nextDue || "9999") || a.title.localeCompare(b.title);
    });

    const box = $("#listAll");
    box.innerHTML = "";
    if (!list.length) {
      box.innerHTML = '<p class="empty">No tasks match.</p>';
    } else {
      list.forEach(t => box.appendChild(taskCard(t, today)));
    }
    $("#taskCount").textContent =
      list.length + " of " + state.tasks.tasks.length + " tasks";
  }

  function fillCategoryFilters() {
    const cats = Array.from(new Set(state.tasks.tasks.map(t => t.category))).sort();
    [["#catFilter", "All categories"], ["#histCat", "All categories"]].forEach(([sel, label]) => {
      const s = $(sel);
      const cur = s.value;
      s.innerHTML = '<option value="">' + label + "</option>";
      cats.forEach(c => {
        const o = el("option", null, c);
        o.value = c;
        s.appendChild(o);
      });
      s.value = cur;
    });
  }

  // ---------------------------------------------------------------
  // History
  // ---------------------------------------------------------------
  function renderHistory() {
    const q = ($("#histSearch").value || "").toLowerCase().trim();
    const cat = $("#histCat").value;
    const yr = $("#histYear").value;

    let rows = (state.history.entries || []).slice();

    // year filter options
    const years = Array.from(new Set(rows.map(e => String(e.date).slice(0, 4)))).sort().reverse();
    const ys = $("#histYear");
    const curY = ys.value;
    ys.innerHTML = '<option value="">All time</option>';
    years.forEach(y => { const o = el("option", null, y); o.value = y; ys.appendChild(o); });
    ys.value = curY;

    if (cat) rows = rows.filter(e => e.category === cat);
    if (yr) rows = rows.filter(e => String(e.date).slice(0, 4) === yr);
    if (q) rows = rows.filter(e =>
      (e.title || "").toLowerCase().includes(q) ||
      (e.notes || "").toLowerCase().includes(q) ||
      (e.category || "").toLowerCase().includes(q));

    rows.sort((a, b) => String(b.date).localeCompare(String(a.date)) ||
      String(b.loggedAt || "").localeCompare(String(a.loggedAt || "")));

    const spend = rows.reduce((s, e) => s + Number(e.cost || 0), 0);
    const comp = rows.filter(e => e.type !== "skipped").length;
    $("#histSummary").textContent =
      rows.length
        ? comp + " completed" + (rows.length - comp ? ", " + (rows.length - comp) + " skipped" : "") +
          (spend > 0 ? " · " + money(spend) + " logged" : "")
        : "";

    const box = $("#histList");
    box.innerHTML = "";
    if (!rows.length) {
      box.innerHTML = '<p class="empty">Nothing logged yet. Tick a task off on the Dashboard and it shows up here.</p>';
      return;
    }

    let lastYear = null;
    rows.forEach(e => {
      const y = String(e.date).slice(0, 4);
      if (y !== lastYear) {
        box.appendChild(el("div", "hist-year", y));
        lastYear = y;
      }
      const row = el("div", "hist");
      const dot = el("div", "hist-dot" + (e.type === "skipped" ? " skip" : ""), e.type === "skipped" ? "–" : "✓");
      row.appendChild(dot);

      const main = el("div", "hist-main");
      main.appendChild(el("div", "hist-title", e.title || e.taskId));
      const meta = el("div", "hist-meta");
      meta.appendChild(el("span", null, fmtDate(e.date)));
      if (e.category) meta.appendChild(el("span", "chip", e.category));
      if (e.by) meta.appendChild(el("span", "chip", e.by === "pro" ? "Pro" : "DIY"));
      if (Number(e.cost) > 0) meta.appendChild(el("span", "chip", money(e.cost)));
      if (e.type === "skipped") meta.appendChild(el("span", "chip", "Skipped"));
      main.appendChild(meta);
      if (e.notes) main.appendChild(el("div", "hist-note", e.notes));
      row.appendChild(main);
      box.appendChild(row);
    });
  }

  // ---------------------------------------------------------------
  // Reports
  // ---------------------------------------------------------------
  function renderReports() {
    const today = todayDay();
    const entries = (state.history.entries || []);
    const completed = entries.filter(e => e.type !== "skipped");
    const active = state.tasks.tasks.filter(t => isActive(t) && !isFinished(t));
    const overdue = active.filter(t => t.nextDue && parseDay(t.nextDue) < today);
    const spend = completed.reduce((s, e) => s + Number(e.cost || 0), 0);
    const spendYr = completed
      .filter(e => String(e.date).slice(0, 4) === String(today.getFullYear()))
      .reduce((s, e) => s + Number(e.cost || 0), 0);

    const onTime = active.length ? Math.round(((active.length - overdue.length) / active.length) * 100) : 100;

    const stats = [
      { n: completed.length, l: "Total done", c: "is-ok" },
      { n: onTime + "%", l: "On schedule", c: onTime >= 85 ? "is-ok" : (onTime >= 60 ? "is-warn" : "is-crit") },
      { n: money(spendYr), l: "Spent " + today.getFullYear(), c: "" },
      { n: money(spend), l: "Spent total", c: "" }
    ];
    const sr = $("#repStats");
    sr.innerHTML = "";
    stats.forEach(s => {
      const d = el("div", "stat " + s.c);
      d.appendChild(el("div", "n", String(s.n)));
      d.appendChild(el("div", "l", s.l));
      sr.appendChild(d);
    });

    // --- completions by month, last 12
    const months = [];
    for (let i = 11; i >= 0; i--) {
      const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
      months.push({
        key: d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0"),
        lab: d.toLocaleDateString(undefined, { month: "short" }) + (d.getMonth() === 0 ? " " + String(d.getFullYear()).slice(2) : ""),
        n: 0
      });
    }
    const mIdx = {};
    months.forEach((m, i) => mIdx[m.key] = i);
    completed.forEach(e => {
      const k = String(e.date).slice(0, 7);
      if (k in mIdx) months[mIdx[k]].n++;
    });
    const maxM = Math.max(1, ...months.map(m => m.n));
    const cm = $("#chartMonths");
    cm.innerHTML = "";
    months.forEach(m => {
      const w = el("div", "cm");
      const bar = el("div", "cm-bar");
      bar.style.height = Math.max(3, Math.round((m.n / maxM) * 100)) + "%";
      if (m.n) bar.appendChild(el("span", null, String(m.n)));
      w.appendChild(bar);
      w.appendChild(el("div", "cm-lab", m.lab));
      cm.appendChild(w);
    });

    // --- by category
    const byCat = {};
    completed.forEach(e => { byCat[e.category || "Other"] = (byCat[e.category || "Other"] || 0) + 1; });
    const cats = Object.keys(byCat).sort((a, b) => byCat[b] - byCat[a]);
    const maxC = Math.max(1, ...cats.map(c => byCat[c]));
    const cb = $("#chartCats");
    cb.innerHTML = "";
    if (!cats.length) {
      cb.innerHTML = '<p class="empty">Nothing completed yet.</p>';
    } else {
      cats.forEach(c => {
        const row = el("div", "cb");
        row.appendChild(el("div", "cb-lab", c));
        const track = el("div", "cb-track");
        const fill = el("div", "cb-fill");
        fill.style.width = Math.round((byCat[c] / maxC) * 100) + "%";
        track.appendChild(fill);
        row.appendChild(track);
        row.appendChild(el("div", "cb-n", String(byCat[c])));
        cb.appendChild(row);
      });
    }

    // --- schedule health by category
    const health = {};
    state.tasks.tasks.forEach(t => {
      if (!isActive(t) || isFinished(t)) return;
      const h = health[t.category] || (health[t.category] = { total: 0, over: 0, soon: 0 });
      h.total++;
      const due = parseDay(t.nextDue);
      if (due) {
        const n = dayDiff(today, due);
        if (n < 0) h.over++;
        else if (n <= 30) h.soon++;
      }
    });
    let html = '<table class="mini"><thead><tr><th>Category</th><th class="num">Active</th><th class="num">Overdue</th><th class="num">Next 30d</th></tr></thead><tbody>';
    Object.keys(health).sort((a, b) => health[b].over - health[a].over || a.localeCompare(b)).forEach(c => {
      const h = health[c];
      html += "<tr><td>" + esc(c) + '</td><td class="num">' + h.total +
        '</td><td class="num"' + (h.over ? ' style="color:var(--crit);font-weight:700"' : "") + ">" + h.over +
        '</td><td class="num">' + h.soon + "</td></tr>";
    });
    html += "</tbody></table>";
    $("#healthTable").innerHTML = html;

    // --- spend
    const spendCat = {};
    completed.forEach(e => {
      if (Number(e.cost) > 0) spendCat[e.category || "Other"] = (spendCat[e.category || "Other"] || 0) + Number(e.cost);
    });
    const sc = Object.keys(spendCat).sort((a, b) => spendCat[b] - spendCat[a]);
    const estAnnual = state.tasks.tasks
      .filter(t => isActive(t) && !isFinished(t) && t.schedule.type !== "once")
      .reduce((s, t) => {
        const per = t.schedule.type === "interval" ? 365 / t.schedule.days : (t.schedule.months || []).length;
        return s + (Number(t.estCost) || 0) * per;
      }, 0);

    let sh = '<p class="muted-sm">Estimated cost to run this whole schedule for a year: <strong>' +
      money(estAnnual) + "</strong> (recurring tasks only, excludes one-time items).</p>";
    if (sc.length) {
      sh += '<table class="mini"><thead><tr><th>Category</th><th class="num">Logged spend</th></tr></thead><tbody>';
      sc.forEach(c => { sh += "<tr><td>" + esc(c) + '</td><td class="num">' + money(spendCat[c]) + "</td></tr>"; });
      sh += "</tbody></table>";
    } else {
      sh += '<p class="empty">No costs logged yet. Add a cost when you tick a task off.</p>';
    }
    $("#costTable").innerHTML = sh;

    // --- never completed
    const never = state.tasks.tasks
      .filter(t => isActive(t) && !isFinished(t) && !t.lastCompleted && t.nextDue && parseDay(t.nextDue) <= today)
      .sort((a, b) => a.nextDue.localeCompare(b.nextDue))
      .slice(0, 25);
    const nd = $("#neverDone");
    nd.innerHTML = "";
    if (!never.length) {
      nd.innerHTML = '<p class="empty">Nothing outstanding. 👏</p>';
    } else {
      const wrap = el("div", "mini-list");
      never.forEach(t => {
        const r = el("div", "mini-row");
        const a = el("span", null, t.title);
        a.style.cursor = "pointer";
        a.addEventListener("click", () => openSheet(t.id));
        r.appendChild(a);
        r.appendChild(el("span", "r", plural(-dayDiff(today, parseDay(t.nextDue)), "day") + " late"));
        wrap.appendChild(r);
      });
      nd.appendChild(wrap);
    }
  }

  // ---------------------------------------------------------------
  // Task detail sheet
  // ---------------------------------------------------------------
  let sheetTaskId = null;

  function openSheet(id) {
    const t = state.tasks.tasks.find(x => x.id === id);
    if (!t) return;
    sheetTaskId = id;
    const today = todayDay();
    const body = $("#sheetBody");

    const chips = [];
    if (isFinished(t)) chips.push(['chip chip-pro', "✓ Completed " + fmtShort(t.lastCompleted)]);
    else {
      const dc = dueChip(t, today);
      chips.push([dc.cls, dc.text]);
    }
    chips.push(["chip", catLabel(t.category)]);
    chips.push(["chip", scheduleLabel(t)]);
    if (t.diy === false) chips.push(["chip chip-pro", "Hire a pro"]);
    if (t.priority === "critical") chips.push(["chip chip-due-over", "Critical"]);
    if (!isActive(t)) chips.push(["chip", "Disabled"]);

    let h = "<h2>" + esc(t.title) + "</h2>";
    h += '<div class="sheet-chips">' +
      chips.map(c => '<span class="' + c[0] + '">' + esc(c[1]) + "</span>").join("") + "</div>";

    h += '<div class="sheet-sec"><h3>Why it matters</h3><div class="why">' + esc(t.why) + "</div></div>";

    h += '<div class="sheet-sec"><h3>How to do it</h3><ol class="steps">' +
      (t.steps || []).map(s => "<li>" + esc(s) + "</li>").join("") + "</ol></div>";

    h += '<div class="sheet-sec"><h3>Details</h3><dl class="kv">';
    h += "<dt>Next due</dt><dd>" + (isFinished(t) ? "—" : esc(fmtDate(t.nextDue))) + "</dd>";
    h += "<dt>Last done</dt><dd>" + (t.lastCompleted ? esc(fmtDate(t.lastCompleted)) : "Never") + "</dd>";
    h += "<dt>Times done</dt><dd>" + (t.timesCompleted || 0) + "</dd>";
    if (t.equipment) h += "<dt>Equipment</dt><dd>" + esc(t.equipment) + "</dd>";
    h += "<dt>Time</dt><dd>~" + (t.estMinutes || 15) + " min</dd>";
    h += "<dt>Typical cost</dt><dd>" + (Number(t.estCost) ? money(t.estCost) : "Free") + "</dd>";
    h += "</dl></div>";

    h += '<div class="sheet-sec"><h3>Your notes</h3>' +
      '<textarea id="sheetNotes" rows="3" placeholder="Filter size, part numbers, who you called…">' +
      esc(t.notes || "") + "</textarea>" +
      '<div class="btn-row"><button class="btn btn-sm" id="sheetSaveNotes">Save notes</button></div></div>';

    h += '<div class="sheet-sec"><h3>Source</h3><p class="src">' + esc(t.source) + "</p></div>";

    h += '<div class="sheet-actions">';
    if (isActive(t) && !isFinished(t)) {
      h += '<button class="btn btn-primary" id="sheetDone">Mark complete</button>';
      h += '<button class="btn" id="sheetSnooze">Snooze 7d</button>';
      if (t.schedule.type !== "once") h += '<button class="btn" id="sheetSkip">Skip this one</button>';
    }
    h += '<button class="btn" id="sheetToggle">' + (t.enabled === false ? "Enable task" : "Disable task") + "</button>";
    h += "</div>";

    body.innerHTML = h;
    $("#sheet").classList.remove("hidden");
    document.body.style.overflow = "hidden";

    const dn = $("#sheetDone");
    if (dn) dn.addEventListener("click", () => { closeSheet(); openDone(id); });
    const sn = $("#sheetSnooze");
    if (sn) sn.addEventListener("click", () => snooze(id, 7));
    const sk = $("#sheetSkip");
    if (sk) sk.addEventListener("click", () => skipTask(id));
    $("#sheetToggle").addEventListener("click", () => toggleTask(id));
    $("#sheetSaveNotes").addEventListener("click", async () => {
      t.notes = $("#sheetNotes").value;
      touch(t);
      await saveAll("Update notes: " + t.title);
      toast("Notes saved");
    });
  }

  function closeSheet() {
    $("#sheet").classList.add("hidden");
    document.body.style.overflow = "";
    sheetTaskId = null;
  }

  // ---------------------------------------------------------------
  // Complete / skip / snooze / toggle
  // ---------------------------------------------------------------
  let doneTaskId = null;

  function openDone(id) {
    const t = state.tasks.tasks.find(x => x.id === id);
    if (!t) return;
    doneTaskId = id;
    $("#doneTitle").textContent = t.title;
    $("#doneDate").value = isoDay(todayDay());
    $("#doneCost").value = "";
    $("#doneNotes").value = "";
    $("#doneBy").value = t.diy === false ? "pro" : "me";
    updateDonePreview();
    $("#doneDlg").classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

  function updateDonePreview() {
    const t = state.tasks.tasks.find(x => x.id === doneTaskId);
    if (!t) return;
    const when = $("#doneDate").value || isoDay(todayDay());
    const nd = nextDueAfter(t, when);
    $("#donePreview").textContent = nd
      ? "Next time: " + fmtDate(nd)
      : "This is a one-time task — it won't be scheduled again.";
  }

  function closeDone() {
    $("#doneDlg").classList.add("hidden");
    document.body.style.overflow = "";
    doneTaskId = null;
  }

  async function confirmDone() {
    const t = state.tasks.tasks.find(x => x.id === doneTaskId);
    if (!t) return;
    const when = $("#doneDate").value || isoDay(todayDay());
    const cost = parseFloat($("#doneCost").value) || 0;
    const by = $("#doneBy").value;
    const notes = $("#doneNotes").value.trim();

    t.lastCompleted = when;
    t.timesCompleted = (t.timesCompleted || 0) + 1;
    t.nextDue = nextDueAfter(t, when);
    touch(t);

    state.history.entries.push({
      id: uid(),
      taskId: t.id,
      title: t.title,
      category: t.category,
      date: when,
      cost: cost,
      by: by,
      notes: notes,
      type: "completed",
      loggedAt: new Date().toISOString()
    });

    closeDone();
    renderAll();
    await saveAll("Complete: " + t.title);
    toast("✓ " + t.title);
  }

  async function skipTask(id) {
    const t = state.tasks.tasks.find(x => x.id === id);
    if (!t) return;
    const when = isoDay(todayDay());
    t.nextDue = nextDueAfter(t, when);
    touch(t);
    state.history.entries.push({
      id: uid(), taskId: t.id, title: t.title, category: t.category,
      date: when, cost: 0, by: "", notes: "Skipped this cycle.",
      type: "skipped", loggedAt: new Date().toISOString()
    });
    closeSheet();
    renderAll();
    await saveAll("Skip: " + t.title);
    toast("Skipped — next " + fmtShort(t.nextDue));
  }

  async function snooze(id, days) {
    const t = state.tasks.tasks.find(x => x.id === id);
    if (!t) return;
    const base = parseDay(t.nextDue) || todayDay();
    const from = base < todayDay() ? todayDay() : base;
    t.nextDue = isoDay(addDays(from, days));
    touch(t);
    closeSheet();
    renderAll();
    await saveAll("Snooze: " + t.title);
    toast("Snoozed to " + fmtShort(t.nextDue));
  }

  async function toggleTask(id) {
    const t = state.tasks.tasks.find(x => x.id === id);
    if (!t) return;
    t.enabled = t.enabled === false;
    touch(t);
    closeSheet();
    renderAll();
    await saveAll((t.enabled ? "Enable: " : "Disable: ") + t.title);
    toast(t.enabled ? "Enabled" : "Disabled");
  }

  // ---------------------------------------------------------------
  // Settings
  // ---------------------------------------------------------------
  const FEATURE_LABELS = {
    pool: ["Pool or spa", "Chemistry, filter and pump tasks"],
    septic: ["Septic system", "Tank inspection and pumping"],
    well: ["Well water", "Water testing, pressure tank, well pump"],
    waterSoftener: ["Water softener / filter", "Salt and cartridge changes"],
    gasAppliances: ["Gas or propane appliances", "Gas line and CO tasks"],
    fireplace: ["Fireplace or chimney", "Annual sweep and inspection"],
    screenedLanai: ["Screened lanai / pool cage", "Screen, frame and anchor tasks"],
    irrigation: ["Irrigation system", "Hunter controller, heads, rain sensor"],
    garage: ["Garage with opener", "Door safety and hardware tasks"],
    dishwasher: ["Dishwasher", "Filter and cleaning cycles"]
  };

  function renderSettings() {
    const c = cfg();
    $("#cfgRepo").value = c.repo || guessRepoFromUrl();
    $("#cfgBranch").value = c.branch;
    $("#cfgToken").value = c.token ? "••••••••••••••••" : "";
    $("#cfgEmail").value = (state.tasks.home && state.tasks.home.reminderEmail) || "";
    $("#cfgNotes").value = (state.tasks.home && state.tasks.home.notes) || "";

    const feats = (state.tasks.home && state.tasks.home.features) || {};
    const box = $("#featureList");
    box.innerHTML = "";
    Object.keys(FEATURE_LABELS).forEach(key => {
      const [name, sub] = FEATURE_LABELS[key];
      const n = state.tasks.tasks.filter(t => t.requires === key).length;
      const row = el("div", "feature");
      const left = el("div", "feature-name");
      left.appendChild(document.createTextNode(name));
      left.appendChild(el("small", null, sub + (n ? " · " + plural(n, "task") : " · no tasks yet")));
      row.appendChild(left);

      const sw = el("label", "switch");
      const inp = document.createElement("input");
      inp.type = "checkbox";
      inp.checked = !!feats[key];
      inp.addEventListener("change", async () => {
        state.tasks.home.features[key] = inp.checked;
        touchHome();
        renderAll();
        await saveAll("Feature " + key + ": " + (inp.checked ? "on" : "off"));
      });
      sw.appendChild(inp);
      sw.appendChild(el("span", "track"));
      row.appendChild(sw);
      box.appendChild(row);
    });

    const total = state.tasks.tasks.length;
    const act = state.tasks.tasks.filter(isActive).length;
    $("#aboutCounts").textContent =
      total + " tasks in the catalog, " + act + " active. Catalog generated " +
      fmtDate(state.tasks.generatedAt) + ".";

    $("#dataInfo").textContent = state.connected
      ? "Connected to " + c.repo + " (" + c.branch + "). Changes commit straight to the repo."
      : "Not connected. Changes are saved in this browser only.";
  }

  function bindSettings() {
    $("#btnSaveCfg").addEventListener("click", async () => {
      const repo = $("#cfgRepo").value.trim();
      const branch = $("#cfgBranch").value.trim() || "main";
      const tokRaw = $("#cfgToken").value.trim();

      if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) {
        setStatus("#cfgStatus", "err", "Repository must look like owner/name.");
        return;
      }
      localStorage.setItem(LS.repo, repo);
      localStorage.setItem(LS.branch, branch);
      if (tokRaw && !/^•+$/.test(tokRaw)) localStorage.setItem(LS.token, tokRaw);

      if (!cfg().token) {
        setStatus("#cfgStatus", "err", "No token saved yet — paste one to enable syncing.");
        return;
      }
      setStatus("#cfgStatus", "busy", "Connecting…");
      try {
        await loadAll();
        renderAll();
        $("#cfgToken").value = "••••••••••••••••";
        setStatus("#cfgStatus", "ok", state.connected ? "Connected. Data loaded from the repo." : "Connected, but load fell back to local.");
      } catch (e) {
        setStatus("#cfgStatus", "err", e.message);
      }
    });

    $("#btnTestCfg").addEventListener("click", async () => {
      const c = cfg();
      if (!c.repo || !c.token) { setStatus("#cfgStatus", "err", "Save a repo and token first."); return; }
      setStatus("#cfgStatus", "busy", "Testing…");
      try {
        const res = await fetch("https://api.github.com/repos/" + c.repo, { headers: ghHeaders(c.token) });
        if (!res.ok) throw new Error("HTTP " + res.status + " — check the repo name and that the token has access to it.");
        const j = await res.json();
        const perms = j.permissions || {};
        setStatus("#cfgStatus", perms.push ? "ok" : "err",
          perms.push
            ? "✓ Connected to " + j.full_name + " with write access."
            : "Reached " + j.full_name + " but the token has no write access. Give it Contents: Read and write.");
      } catch (e) {
        setStatus("#cfgStatus", "err", e.message);
      }
    });

    $("#btnClearCfg").addEventListener("click", () => {
      localStorage.removeItem(LS.token);
      state.connected = false;
      $("#cfgToken").value = "";
      setSync("idle", "Local");
      setStatus("#cfgStatus", "ok", "Token removed from this browser.");
      renderSettings();
    });

    $("#btnSaveEmail").addEventListener("click", async () => {
      const v = $("#cfgEmail").value.trim();
      if (v && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) {
        setStatus("#emailStatus", "err", "That doesn't look like an email address.");
        return;
      }
      state.tasks.home.reminderEmail = v;
      touchHome();
      setStatus("#emailStatus", "busy", "Saving…");
      const ok = await saveAll("Update reminder email");
      setStatus("#emailStatus", ok ? "ok" : "err",
        ok ? "Saved. The daily reminder Action will use this address."
           : "Saved on this device only — connect GitHub to make the Action see it.");
    });

    $("#btnSaveNotes").addEventListener("click", async () => {
      state.tasks.home.notes = $("#cfgNotes").value;
      touchHome();
      setStatus("#notesStatus", "busy", "Saving…");
      const ok = await saveAll("Update home notes");
      setStatus("#notesStatus", ok ? "ok" : "err", ok ? "Saved." : "Saved on this device only.");
    });

    $("#btnExport").addEventListener("click", () => {
      const blob = new Blob([JSON.stringify({
        exportedAt: new Date().toISOString(),
        tasks: state.tasks,
        history: state.history
      }, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "home-maintenance-backup-" + isoDay(todayDay()) + ".json";
      document.body.appendChild(a);
      a.click();
      setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    });

    $("#btnPull").addEventListener("click", async () => {
      await loadAll();
      renderAll();
      toast("Reloaded");
    });
  }

  function setStatus(sel, kind, msg) {
    const n = $(sel);
    n.className = "status " + kind;
    n.textContent = msg;
  }

  // ---------------------------------------------------------------
  // Views
  // ---------------------------------------------------------------
  function switchView(name) {
    state.view = name;
    $$(".tab").forEach(t => t.classList.toggle("is-active", t.dataset.view === name));
    $$(".view").forEach(v => v.classList.toggle("is-active", v.id === "view-" + name));
    window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
    renderCurrent();
  }

  function renderCurrent() {
    if (state.view === "dashboard") renderDashboard();
    else if (state.view === "tasks") renderTasks();
    else if (state.view === "history") renderHistory();
    else if (state.view === "reports") renderReports();
    else if (state.view === "settings") renderSettings();
  }

  function renderAll() {
    const home = state.tasks.home || {};
    $("#homeName").textContent = home.nickname || "Home Maintenance Hub";
    const moved = home.moveInDate ? parseDay(home.moveInDate) : null;
    if (moved) {
      const t = todayDay();
      let months = (t.getFullYear() - moved.getFullYear()) * 12 + (t.getMonth() - moved.getMonth());
      if (t.getDate() < moved.getDate()) months--;
      months = Math.max(0, months);
      $("#homeSub").textContent = "Moved in " + fmtDate(home.moveInDate) + " · " +
        (months < 1 ? "just moved in" : plural(months, "month") + " in");
    } else {
      $("#homeSub").textContent = "";
    }
    /* Null-guarded: during a service-worker update the cached index.html can
       briefly be older than app.js, and a hard crash here would blank the app. */
    const hTitle = $("#heroTitle");
    const hSub = $("#heroSub");
    if (hTitle) hTitle.textContent = home.nickname || "Our home";
    if (hSub) hSub.textContent = $("#homeSub").textContent;
    fillCategoryFilters();
    renderCurrent();
  }

  // ---------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------
  function bindChrome() {
    $$(".tab").forEach(t => t.addEventListener("click", () => switchView(t.dataset.view)));

    $("#btnRefresh").addEventListener("click", async (e) => {
      e.currentTarget.classList.add("spin");
      await loadAll();
      renderAll();
      e.currentTarget.classList.remove("spin");
      toast("Reloaded");
    });

    ["#taskSearch", "#catFilter", "#stateFilter"].forEach(s =>
      $(s).addEventListener("input", renderTasks));
    ["#histSearch", "#histCat", "#histYear"].forEach(s =>
      $(s).addEventListener("input", renderHistory));

    $$("[data-close]").forEach(n => n.addEventListener("click", () => {
      closeSheet(); closeDone();
    }));
    document.addEventListener("keydown", e => {
      if (e.key === "Escape") { closeSheet(); closeDone(); }
    });

    $("#doneConfirm").addEventListener("click", confirmDone);
    $("#doneDate").addEventListener("change", updateDonePreview);

    /* Coming back to the app on one device should show what you did on another.
       Skipped while a dialog is open so a refresh can't wipe a half-filled form. */
    document.addEventListener("visibilitychange", async () => {
      if (document.visibilityState !== "visible") return;
      if (!state.connected) return;
      if (!$("#sheet").classList.contains("hidden")) return;
      if (!$("#doneDlg").classList.contains("hidden")) return;
      if (Date.now() - lastLoad < 30000) return;
      await loadAll();
      renderAll();
    });

    bindSettings();
  }

  async function init() {
    bindChrome();

    if (!localStorage.getItem(LS.repo)) {
      const g = guessRepoFromUrl();
      if (g) localStorage.setItem(LS.repo, g);
    }

    try {
      await loadAll();
    } catch (e) {
      document.getElementById("boot").innerHTML =
        '<div class="boot-inner"><p style="color:var(--crit)">Could not load data.<br>' + esc(e.message) + "</p></div>";
      return;
    }

    renderAll();
    $("#boot").classList.add("hidden");

    if ("serviceWorker" in navigator && location.protocol === "https:") {
      navigator.serviceWorker.register("./sw.js").catch(() => {});
    }
  }

  document.addEventListener("DOMContentLoaded", init);

  // Exposed so the merge rules can be exercised from the console without
  // needing two real devices. Not used by the app itself.
  window.__hmh = { mergeTasks, mergeHistory, state };
})();
