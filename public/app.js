/* MalariaScope page logic. Screens: start, counting, result, evaluation.
 * The slide session lives only in this page's memory (no storage, no patient data).
 * See devpost/spec.md > Counting page (public/app.js).
 */
(function () {
  "use strict";

  var WORK_SIZE = 1600;           // must match malariascope/analysis.py
  var COLORS = { wbc: "#2563EB", par: "#DC2626" };
  var $ = function (id) { return document.getElementById(id); };
  var t = I18n.t;

  var state = {
    session: null,      // Protocol session
    current: null,      // field being reviewed: {image, width, height, wbc[], parasites[], quality, flagged, accepted}
    tool: "remove",     // remove | add-par | add-wbc
    samples: null,      // sample manifest
    sampleIndex: 0,
  };

  // ---------- screens ----------
  function show(name) {
    document.querySelectorAll(".screen").forEach(function (s) {
      s.hidden = s.dataset.screen !== name;
    });
    $("topbar-ref").textContent = state.session && name !== "start" && name !== "evaluation" ? state.session.reference : "";
    window.scrollTo(0, 0);
  }

  // ---------- start ----------
  $("slide-ref").addEventListener("input", function () {
    $("start-btn").disabled = !this.value.trim();
  });
  $("start-form").addEventListener("submit", function (e) {
    e.preventDefault();
    startSession($("slide-ref").value.trim(), false);
  });

  function startSession(reference, sample) {
    state.session = Protocol.newSession(reference, sample);
    state.current = null;
    state.sampleIndex = 0;
    $("thumbs").innerHTML = "";
    $("pick-btn").hidden = sample;
    $("next-sample-btn").hidden = !sample;
    renderField();
    renderTotals();
    show("counting");
  }

  // ---------- upload ----------
  $("pick-btn").addEventListener("click", function () { $("file-input").click(); });
  $("file-input").addEventListener("change", function () {
    if (this.files[0]) handleFile(this.files[0]);
    this.value = "";
  });
  var dz = $("dropzone");
  ["dragenter", "dragover"].forEach(function (ev) {
    dz.addEventListener(ev, function (e) { e.preventDefault(); dz.classList.add("dragging"); });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    dz.addEventListener(ev, function (e) { e.preventDefault(); dz.classList.remove("dragging"); });
  });
  dz.addEventListener("drop", function (e) {
    var f = e.dataTransfer.files[0];
    if (f && state.session && !state.current) handleFile(f);
  });

  function showError(msg) {
    $("field-error").textContent = msg;
    $("field-error").hidden = !msg;
  }

  // Shrink to <= WORK_SIZE on the long side (keeps uploads small for Vercel's 4.5 MB limit).
  // Parasites are only a few pixels wide and JPEG re-compression erases some of them,
  // so a photo that is already small enough is sent untouched, and resizing uses high quality.
  var MAX_UPLOAD_BYTES = 3500000;
  function loadAndResize(blob) {
    return createImageBitmap(blob).then(function (bmp) {
      var scale = Math.min(1, WORK_SIZE / Math.max(bmp.width, bmp.height));
      var c = document.createElement("canvas");
      c.width = Math.round(bmp.width * scale);
      c.height = Math.round(bmp.height * scale);
      c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
      if (scale === 1 && blob.size <= MAX_UPLOAD_BYTES && /^image\/(jpeg|png)$/.test(blob.type)) {
        return { canvas: c, blob: blob };
      }
      return new Promise(function (resolve) {
        c.toBlob(function (out) { resolve({ canvas: c, blob: out }); }, "image/jpeg", 0.95);
      });
    });
  }

  function handleFile(file) {
    showError("");
    if (!file.type || file.type.indexOf("image/") !== 0) {
      showError(t("err.notImage"));
      return;
    }
    setBusy(true);
    loadAndResize(file)
      .catch(function () { throw new Error("not_an_image"); })
      .then(analyse)
      .catch(function (err) {
        showError(err.message === "not_an_image" ? t("err.notImage") : t("err.network"));
      })
      .then(function () { setBusy(false); });
  }

  function analyse(resized) {
    var form = new FormData();
    form.append("image", resized.blob, "field.jpg");
    return fetch("/api/analyze", { method: "POST", body: form }).then(function (r) {
      return r.json().then(function (body) {
        if (!r.ok) throw new Error(body.error || "server_error");
        var img = new Image();
        img.src = resized.canvas.toDataURL("image/jpeg", 0.85);
        return new Promise(function (resolve) { img.onload = resolve; }).then(function () {
          var flagged = !body.quality.ok;
          state.current = {
            image: img, width: body.width, height: body.height,
            wbc: body.wbc, parasites: body.parasites, quality: body.quality,
            flagged: flagged, accepted: !flagged,
          };
          state.tool = "add-par";
          setTool("add-par"); // toggles back to the default "remove" tool
          renderField();
        });
      });
    });
  }

  // ---------- sample slide (real NLM fields, real analyser) ----------
  function loadManifest() {
    if (state.samples) return Promise.resolve(state.samples);
    return fetch("samples/manifest.json").then(function (r) {
      if (!r.ok) throw new Error("no_samples");
      return r.json();
    }).then(function (m) { state.samples = m; return m; });
  }

  function nextSample() {
    showError("");
    setBusy(true);
    loadManifest()
      .then(function (m) {
        if (state.sampleIndex >= m.fields.length) throw new Error("samples_done");
        var file = m.fields[state.sampleIndex++];
        return fetch("samples/" + file).then(function (r) { return r.blob(); });
      })
      .then(loadAndResize)
      .then(analyse)
      .catch(function (err) {
        showError(err.message === "samples_done" ? t("err.samplesDone") : t("err.sampleLoad"));
      })
      .then(function () { setBusy(false); });
  }

  $("next-sample-btn").addEventListener("click", nextSample);
  $("sample-btn").addEventListener("click", function () {
    loadManifest().then(function (m) {
      startSession(m.reference, true);
    }).catch(function () { alert(t("err.sampleUnavailable")); });
  });

  function setBusy(on) {
    $("busy").hidden = !on;
    document.querySelectorAll("#screen-counting button").forEach(function (b) { b.disabled = on; });
  }

  // ---------- drawing ----------
  var canvas = $("field-canvas");
  var ctx = canvas.getContext("2d");

  function draw() {
    var f = state.current;
    if (!f) return;
    canvas.width = f.width;
    canvas.height = f.height;
    ctx.drawImage(f.image, 0, 0, f.width, f.height);
    if (f.flagged && !f.accepted) return;
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = COLORS.wbc;
    f.wbc.forEach(function (m) { ring(m); });
    ctx.strokeStyle = COLORS.par;
    f.parasites.forEach(function (m) { ring(m); });
  }
  function ring(m) {
    ctx.beginPath();
    ctx.arc(m.x, m.y, Math.max(m.r, 7), 0, Math.PI * 2);
    ctx.stroke();
  }

  // ---------- render ----------
  function renderField() {
    var f = state.current;
    var has = !!f;
    canvas.hidden = !has;
    $("drop-empty").hidden = has;
    $("field-box").hidden = !has;
    if (!has) {
      $("drop-title").textContent = state.session && state.session.fields.length
        ? t("count.dropNext") : t("count.dropFirst");
      return;
    }
    draw();
    var counted = !f.flagged || f.accepted;
    $("field-wbc").textContent = counted ? f.wbc.length : 0;
    $("field-par").textContent = counted ? f.parasites.length : 0;
    var badge = $("quality-badge");
    if (f.quality.reason === "blur") {
      badge.textContent = t("quality.blur"); badge.className = "badge warn";
    } else if (f.quality.reason === "no_cells") {
      badge.textContent = t("quality.noCells"); badge.className = "badge warn";
    } else {
      badge.textContent = t("quality.good"); badge.className = "badge";
    }
    var blocked = f.flagged && !f.accepted;
    $("flag").hidden = !blocked;
    $("flag-text").textContent = f.quality.reason === "blur" ? t("flag.blur") : t("flag.noCells");
    $("tools").hidden = blocked;
    canvas.style.cursor = blocked ? "default" : state.tool === "remove" ? "pointer" : "crosshair";
  }

  function renderTotals() {
    var s = state.session;
    var g = Protocol.guidance(s);
    $("wbc-progress").textContent = s.totals.wbc + " / " + g.target;
    $("wbc-bar").style.width = Math.min(100, (100 * s.totals.wbc) / g.target) + "%";
    $("par-total").textContent = s.totals.parasites;
    $("fields-total").textContent = s.fields.length;
    $("guidance").textContent = guidanceText(s, g);
    $("guidance").classList.toggle("done", g.canFinish);
    $("result-btn").hidden = !g.canFinish;
  }

  // Protocol decides; the page words it in the current language.
  function guidanceText(s, g) {
    if (!s.fields.length) return t("guide.first");
    if (g.canFinish) return t("guide.enough");
    return g.extended ? t("guide.extend", { n: g.remainingWbc }) : t("guide.more", { n: g.remainingWbc });
  }

  // ---------- correcting marks ----------
  function setTool(tool) {
    state.tool = state.tool === tool ? "remove" : tool;
    $("tool-par").setAttribute("aria-pressed", state.tool === "add-par");
    $("tool-wbc").setAttribute("aria-pressed", state.tool === "add-wbc");
  }
  $("tool-par").addEventListener("click", function () { setTool("add-par"); });
  $("tool-wbc").addEventListener("click", function () { setTool("add-wbc"); });

  canvas.addEventListener("click", function (e) {
    var f = state.current;
    if (!f || (f.flagged && !f.accepted)) return;
    // Screen pixels -> image pixels (the canvas is scaled by CSS).
    var rect = canvas.getBoundingClientRect();
    var x = (e.clientX - rect.left) * (f.width / rect.width);
    var y = (e.clientY - rect.top) * (f.height / rect.height);
    if (state.tool === "add-par") {
      f.parasites.push({ x: x, y: y, r: 9, manual: true });
    } else if (state.tool === "add-wbc") {
      f.wbc.push({ x: x, y: y, r: 20, manual: true });
    } else {
      removeNearest(f, x, y, 12 * (f.width / rect.width));
    }
    renderField();
  });

  function removeNearest(f, x, y, tolerance) {
    var best = null;
    [["parasites", f.parasites], ["wbc", f.wbc]].forEach(function (pair) {
      pair[1].forEach(function (m, i) {
        var d = Math.hypot(m.x - x, m.y - y);
        if (d <= Math.max(m.r, tolerance) && (!best || d < best.d)) best = { list: pair[0], i: i, d: d };
      });
    });
    if (best) f[best.list].splice(best.i, 1);
  }

  // ---------- flagged photos ----------
  $("retake-btn").addEventListener("click", function () {
    state.current = null;
    renderField();
    if (state.session.sample) nextSample(); else $("file-input").click();
  });
  $("use-anyway-btn").addEventListener("click", function () {
    if (state.current) { state.current.accepted = true; renderField(); }
  });

  // ---------- confirm / discard (WHO running count) ----------
  function fieldCounts(f) {
    var counted = !f.flagged || f.accepted;
    return { wbc: counted ? f.wbc.length : 0, parasites: counted ? f.parasites.length : 0, counted: counted };
  }

  $("confirm-btn").addEventListener("click", function () {
    var f = state.current;
    if (!f) return;
    var c = fieldCounts(f);
    var thumb = document.createElement("canvas");
    thumb.width = 208; thumb.height = Math.round(208 * f.height / f.width);
    thumb.getContext("2d").drawImage(canvas, 0, 0, thumb.width, thumb.height);
    var field = {
      id: state.session.fields.length + 1,
      thumbnailUrl: thumb.toDataURL("image/jpeg", 0.7),
      wbcCount: c.wbc,
      parasiteCount: c.parasites,
      flagged: f.flagged,
      note: f.flagged ? (c.counted ? "note.usedAnyway" : "note.notCounted") : "",
    };
    state.session = Protocol.addField(state.session, field);
    addThumb(field);
    state.current = null;
    renderField();
    renderTotals();
  });

  $("discard-btn").addEventListener("click", function () {
    state.current = null;
    showError("");
    renderField();
  });

  function addThumb(field) {
    var el = document.createElement("div");
    el.className = "thumb";
    el.innerHTML = '<img alt=""><span></span>';
    el.querySelector("img").src = field.thumbnailUrl;
    el.querySelector("img").alt = t("thumb.alt", { n: field.id });
    el.querySelector("span").textContent = t("thumb.label", { n: field.id, wbc: field.wbcCount, par: field.parasiteCount });
    $("thumbs").appendChild(el);
  }

  // ---------- navigation ----------
  function askConfirm(text) {
    var dlg = $("confirm-dialog");
    $("confirm-text").textContent = text;
    return new Promise(function (resolve) {
      dlg.addEventListener("close", function onClose() {
        dlg.removeEventListener("close", onClose);
        resolve(dlg.returnValue === "ok");
      });
      dlg.showModal();
    });
  }

  function unfinished() {
    var s = state.session;
    return !!(s && (s.fields.length || state.current));
  }

  function newSlide() {
    var go = unfinished() && !state.reviewed
      ? askConfirm(t("dialog.newSlide", { n: state.session.fields.length }))
      : Promise.resolve(true);
    go.then(function (ok) {
      if (!ok) return;
      state.session = null;
      state.current = null;
      $("slide-ref").value = "";
      $("start-btn").disabled = true;
      show("start");
    });
  }

  $("brand").addEventListener("click", function () { show(state.session ? "counting" : "start"); });
  $("new-slide-btn").addEventListener("click", newSlide);
  $("result-new-btn").addEventListener("click", newSlide);

  // ---------- result and report ----------
  function fmt(n) { return I18n.number(n); }

  $("result-btn").addEventListener("click", function () {
    state.reviewed = false;
    state.resultAt = Date.now();
    $("review-check").checked = false;
    renderResult();
    show("result");
  });
  $("back-btn").addEventListener("click", function () { show("counting"); });
  $("print-btn").addEventListener("click", function () { window.print(); });
  $("review-check").addEventListener("change", function () {
    state.reviewed = this.checked;
    renderStatus();
  });

  function renderStatus() {
    var st = $("r-status");
    st.textContent = state.reviewed ? t("report.reviewed") : t("report.preliminary");
    st.className = "status " + (state.reviewed ? "reviewed" : "preliminary");
  }

  function renderResult() {
    var s = state.session;
    var d = Protocol.density(s);
    $("r-ref").textContent = s.reference + (s.sample ? t("report.sample") : "");
    $("r-date").textContent = new Date(state.resultAt || Date.now()).toLocaleString(I18n.locale(), { dateStyle: "medium", timeStyle: "short" });
    $("r-density").textContent = s.totals.parasites === 0 ? t("report.none") : t("report.unit", { n: fmt(d) });
    $("r-formula").textContent = t("report.formula", {
      par: s.totals.parasites, k: fmt(Protocol.WBC_PER_UL), wbc: s.totals.wbc, d: d === null ? "—" : fmt(d) });
    $("r-fields").textContent = s.fields.length;
    $("r-wbc").textContent = s.totals.wbc;
    $("r-par").textContent = s.totals.parasites;
    var body = $("r-table").querySelector("tbody");
    body.innerHTML = "";
    s.fields.forEach(function (f) {
      var tr = document.createElement("tr");
      [f.id, f.wbcCount, f.parasiteCount, f.note ? t(f.note) : ""].forEach(function (v) {
        var td = document.createElement("td");
        td.textContent = v;
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    renderStatus();
  }

  // ---------- evaluation ("How accurate is it?") ----------
  $("nav-accuracy").addEventListener("click", function () {
    show("evaluation");
    loadEvaluation();
  });

  function pct(x) { return x === null || x === undefined ? "—" : Math.round(x * 100) + " %".slice(I18n.lang === "fr" ? 0 : 1); }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function metric(label, value, sub) {
    var m = el("div", "metric");
    m.appendChild(el("span", "label", label));
    m.appendChild(el("span", "big", value));
    if (sub) m.appendChild(el("span", "hint", sub));
    return m;
  }

  function table(headers, rows) {
    var wrap = el("div", "table-wrap");
    var t = el("table", "table");
    var tr = el("tr");
    headers.forEach(function (h) { tr.appendChild(el("th", "", h)); });
    var thead = el("thead"); thead.appendChild(tr); t.appendChild(thead);
    var tb = el("tbody");
    rows.forEach(function (r) {
      var row = el("tr");
      r.forEach(function (v) { row.appendChild(el("td", "", String(v))); });
      tb.appendChild(row);
    });
    t.appendChild(tb); wrap.appendChild(t);
    return wrap;
  }

  var evaluation = null;
  function loadEvaluation() {
    if (evaluation) { renderEvaluation(); return; }
    $("eval-intro").textContent = t("eval.loading");
    fetch("evaluation/evaluation.json").then(function (r) { return r.json(); }).then(function (ev) {
      evaluation = ev;
      renderEvaluation();
    }).catch(function () {
      $("eval-intro").textContent = t("eval.error");
    });
  }

  function renderEvaluation() {
    var ev = evaluation;
    if (!ev) return;
    var s = ev.summary;
    $("eval-intro").textContent = t("eval.intro",
      { tune: ev.tuningPatients.length, held: ev.heldOutPatients.length, fields: ev.images.length });
    var body = $("eval-body");
    body.innerHTML = "";

    body.appendChild(el("h2", "", t("eval.wbc")));
    var g1 = el("div", "metric-grid");
    g1.appendChild(metric(t("eval.found"), fmt(s.wbc.expertTotal)));
    g1.appendChild(metric(t("eval.recall"), pct(s.wbc.recall), t("eval.recallWbc")));
    g1.appendChild(metric(t("eval.precision"), pct(s.wbc.precision), t("eval.precisionWbc")));
    g1.appendChild(metric(t("eval.err"), "±" + fmt(s.wbc.meanAbsCountError), t("panel.wbcUnit")));
    body.appendChild(g1);

    body.appendChild(el("h2", "", t("eval.par")));
    var g2 = el("div", "metric-grid");
    g2.appendChild(metric(t("eval.found"), fmt(s.parasites.expertTotal)));
    g2.appendChild(metric(t("eval.recall"), pct(s.parasites.recall), t("eval.recallPar")));
    g2.appendChild(metric(t("eval.precision"), pct(s.parasites.precision), t("eval.precisionPar")));
    g2.appendChild(metric(t("eval.err"), "±" + fmt(s.parasites.meanAbsCountError), t("panel.parUnit")));
    body.appendChild(g2);

    body.appendChild(el("h2", "", t("eval.densityTitle")));
    body.appendChild(table([t("eval.thPatient"), t("eval.thFields"), t("eval.thExpert"), t("eval.thOurs"), t("eval.thDiff")],
      ev.patients.map(function (p) {
        var diff = p.expert.density ? Math.round(100 * (p.ours.density - p.expert.density) / p.expert.density) : null;
        return [p.patient, p.fields, fmt(p.expert.density), fmt(p.ours.density), diff === null ? "—" : (diff > 0 ? "+" : "") + diff + "%"];
      })));
    body.appendChild(el("p", "muted", t("eval.caution")));

    body.appendChild(el("h2", "", t("eval.failTitle")));
    body.appendChild(el("p", "muted", t("eval.failIntro")));
    var fl = el("div", "failures");
    ev.failures.forEach(function (f) {
      var card = el("figure", "failure");
      card.style.margin = "0";
      var img = el("img"); img.src = f.image; img.alt = t("eval.failAlt", { id: f.id }); img.loading = "lazy";
      card.appendChild(img);
      var cap = el("p");
      cap.appendChild(el("strong", "", t("eval.failCaption", { e: f.expert.parasites, o: f.ours.parasites })));
      var note = typeof f.note === "string" ? f.note : (f.note && (f.note[I18n.lang] || f.note.en)) || "";
      cap.appendChild(document.createTextNode(note));
      card.appendChild(cap);
      fl.appendChild(card);
    });
    body.appendChild(fl);

    body.appendChild(el("h2", "", t("eval.allTitle")));
    body.appendChild(table([t("eval.thField"), t("eval.thExpertWbc"), t("eval.thOurWbc"), t("eval.thExpertPar"),
      t("eval.thOurPar"), t("eval.thRecall"), t("eval.thPrecision")],
      ev.images.map(function (r) {
        return [r.id, r.expert.wbc, r.ours.wbc, r.expert.parasites, r.ours.parasites, pct(r.recall.parasites), pct(r.precision.parasites)];
      })));

    var src = el("p", "hint", t("eval.source", {
      dataset: ev.dataset, citation: ev.citation, rw: ev.matchRadiusPx.wbc,
      rp: ev.matchRadiusPx.parasites, size: ev.matchRadiusPx.imageLongSide }));
    src.style.marginTop = "1.5rem";
    body.appendChild(src);
  }

  // ---------- language ----------
  function renderLanguage() {
    I18n.apply(document);
    if (state.session) {
      renderTotals();
      renderField();
      $("thumbs").innerHTML = "";
      state.session.fields.forEach(addThumb);
      if (!$("screen-result").hidden) renderResult();
    } else {
      renderField();
    }
    renderEvaluation();
  }
  $("lang-btn").addEventListener("click", function () {
    I18n.setLang(I18n.lang === "fr" ? "en" : "fr");
    renderLanguage();
  });

  window.MalariaScope = { state: state, show: show };
  renderLanguage();
  show("start");
})();
