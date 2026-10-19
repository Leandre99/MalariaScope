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
          renderField();
        });
      });
    });
  }

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
  }

  // ---------- navigation ----------
  $("brand").addEventListener("click", function () { show(state.session ? "counting" : "start"); });
  $("new-slide-btn").addEventListener("click", function () { show("start"); });

  window.MalariaScope = { state: state, show: show };
  show("start");
})();
