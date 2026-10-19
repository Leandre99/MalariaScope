/* MalariaScope page logic. Screens: start, counting, result, evaluation.
 * The slide session lives only in this page's memory (no storage, no patient data).
 * See devpost/spec.md > Counting page (public/app.js).
 */
(function () {
  "use strict";

  var WORK_SIZE = 1600;           // must match malariascope/analysis.py
  var COLORS = { wbc: "#2563EB", par: "#DC2626" };
  var $ = function (id) { return document.getElementById(id); };

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
  function loadAndResize(blob) {
    return createImageBitmap(blob).then(function (bmp) {
      var scale = Math.min(1, WORK_SIZE / Math.max(bmp.width, bmp.height));
      var c = document.createElement("canvas");
      c.width = Math.round(bmp.width * scale);
      c.height = Math.round(bmp.height * scale);
      c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
      return new Promise(function (resolve) {
        c.toBlob(function (out) { resolve({ canvas: c, blob: out }); }, "image/jpeg", 0.9);
      });
    });
  }

  function handleFile(file) {
    showError("");
    if (!file.type || file.type.indexOf("image/") !== 0) {
      showError("This file isn't an image we can read.");
      return;
    }
    setBusy(true);
    loadAndResize(file)
      .catch(function () { throw new Error("not_an_image"); })
      .then(analyse)
      .catch(function (err) {
        showError(err.message === "not_an_image"
          ? "This file isn't an image we can read."
          : "Couldn't reach the analyser — check the connection and try again.");
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
        showError(err.message === "samples_done"
          ? "That was the last sample field."
          : "Couldn't load the sample field — try again.");
      })
      .then(function () { setBusy(false); });
  }

  $("next-sample-btn").addEventListener("click", nextSample);
  $("sample-btn").addEventListener("click", function () {
    loadManifest().then(function (m) {
      startSession(m.reference, true);
    }).catch(function () { alert("Sample slide unavailable."); });
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
        ? "Upload the next field" : "Upload your first field";
      return;
    }
    draw();
    var counted = !f.flagged || f.accepted;
    $("field-wbc").textContent = counted ? f.wbc.length : 0;
    $("field-par").textContent = counted ? f.parasites.length : 0;
    var badge = $("quality-badge");
    if (f.quality.reason === "blur") {
      badge.textContent = "Out of focus"; badge.className = "badge warn";
    } else if (f.quality.reason === "no_cells") {
      badge.textContent = "No cells found"; badge.className = "badge warn";
    } else {
      badge.textContent = "Good photo"; badge.className = "badge";
    }
    var blocked = f.flagged && !f.accepted;
    $("flag").hidden = !blocked;
    $("flag-text").textContent = f.quality.reason === "blur"
      ? "Out of focus — please refocus and retake. Nothing from this photo is counted."
      : "No cells found — is this a thick smear field? Nothing from this photo is counted.";
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
    $("guidance").textContent = g.message;
    $("guidance").classList.toggle("done", g.canFinish);
    $("result-btn").hidden = !g.canFinish;
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
      note: f.flagged ? (c.counted ? "Flagged, used anyway" : "Flagged, not counted") : "",
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
    el.querySelector("img").alt = "Field " + field.id;
    el.querySelector("span").textContent = "#" + field.id + " · " + field.wbcCount + " WBC · " + field.parasiteCount + " P";
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
      ? askConfirm("Start a new slide? The current count (" + state.session.fields.length + " fields) will be cleared.")
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

  window.MalariaScope = { state: state, show: show };
  show("start");
})();
