/* =========================================================================
   Median Sobel Bench - logic
   Uses the same integer arithmetic as python/dip.py and the Verilog RTL:
     median  : exact 3x3 median (hardware method: row sort, combine, med3)
     Sobel   : |Gx| + |Gy|
     edges   : magnitude >= threshold
     borders : only interior pixels get an output (valid-window rule)
   ========================================================================= */
(() => {
  "use strict";
  const N = 128;                 // image size
  const NM = N - 2;              // median output size (126)
  const NE = N - 4;              // edge output size   (124)

  const state = {
    imgName: "cameraman",
    clean: null,                 // Uint8Array N*N
    noisy: null,
    median: null,                // Uint8Array NM*NM
    noise: 10,
    thresh: 200,
    seed: 2026,
    sel: { x: 64, y: 40 },       // selected pixel (full-image coords)
  };

  // ---------------------------------------------------------------- helpers
  const $ = (id) => document.getElementById(id);
  const fmt = (n) => n.toLocaleString("en-US");
  const min2 = (a, b) => (a < b ? a : b);
  const max2 = (a, b) => (a > b ? a : b);
  const min3 = (a, b, c) => min2(a, min2(b, c));
  const max3 = (a, b, c) => max2(a, max2(b, c));
  const med3 = (a, b, c) => max2(min2(a, b), min2(max2(a, b), c));

  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  // ---------------------------------------------------------------- image processing
  function addNoise(img, pct, seed) {
    const rnd = mulberry32(seed), d = pct / 100, out = new Uint8Array(img);
    for (let i = 0; i < out.length; i++) {
      const r = rnd();
      if (r < d / 2) out[i] = 0;
      else if (r < d) out[i] = 255;
    }
    return out;
  }

  // window value at (x, y) of a w-wide image
  function medianImage(img, w) {
    const h = img.length / w, ow = w - 2, out = new Uint8Array(ow * (h - 2));
    for (let y = 1; y < h - 1; y++) {
      for (let x = 1; x < w - 1; x++) {
        const r0 = (y - 1) * w + x, r1 = y * w + x, r2 = (y + 1) * w + x;
        const a = [img[r0 - 1], img[r0], img[r0 + 1]];
        const b = [img[r1 - 1], img[r1], img[r1 + 1]];
        const c = [img[r2 - 1], img[r2], img[r2 + 1]];
        const A = max3(min3(...a), min3(...b), min3(...c));
        const B = med3(med3(...a), med3(...b), med3(...c));
        const C = min3(max3(...a), max3(...b), max3(...c));
        out[(y - 1) * ow + (x - 1)] = med3(A, B, C);
      }
    }
    return out;
  }

  function sobelMag(img, w) {
    const h = img.length / w, ow = w - 2, out = new Int32Array(ow * (h - 2));
    for (let y = 1; y < h - 1; y++) {
      for (let x = 1; x < w - 1; x++) {
        const p = (dx, dy) => img[(y + dy) * w + (x + dx)];
        const gx = (p(1, -1) + 2 * p(1, 0) + p(1, 1)) - (p(-1, -1) + 2 * p(-1, 0) + p(-1, 1));
        const gy = (p(-1, 1) + 2 * p(0, 1) + p(1, 1)) - (p(-1, -1) + 2 * p(0, -1) + p(1, -1));
        out[(y - 1) * ow + (x - 1)] = Math.abs(gx) + Math.abs(gy);
      }
    }
    return out;
  }

  const threshold = (mag, t) => Uint8Array.from(mag, (m) => (m >= t ? 1 : 0));

  // crop a w-wide image by k pixels on every side
  function crop(img, w, k) {
    const h = img.length / w, ow = w - 2 * k, out = new img.constructor(ow * (h - 2 * k));
    for (let y = 0; y < h - 2 * k; y++)
      for (let x = 0; x < ow; x++) out[y * ow + x] = img[(y + k) * w + (x + k)];
    return out;
  }

  function psnr(a, b) {
    let s = 0;
    for (let i = 0; i < a.length; i++) { const d = a[i] - b[i]; s += d * d; }
    const mse = s / a.length;
    return mse === 0 ? Infinity : 10 * Math.log10((255 * 255) / mse);
  }

  function edgeScore(pred, gt) {
    let tp = 0, fp = 0, fn = 0;
    for (let i = 0; i < pred.length; i++) {
      if (pred[i] && gt[i]) tp++; else if (pred[i]) fp++; else if (gt[i]) fn++;
    }
    const p = tp + fp ? tp / (tp + fp) : 0, r = tp + fn ? tp / (tp + fn) : 0;
    return { fp, f1: p + r ? (2 * p * r) / (p + r) : 0 };
  }

  // ---------------------------------------------------------------- drawing
  // draw a w-wide gray (or 0/1 binary) image into a 128x128 canvas, centred
  function drawGray(canvas, img, w, binary = false) {
    const ctx = canvas.getContext("2d");
    const id = ctx.createImageData(N, N), off = (N - w) / 2;
    for (let i = 0; i < N * N; i++) id.data[i * 4 + 3] = 255;
    for (let y = 0; y < w; y++) {
      for (let x = 0; x < w; x++) {
        const v = binary ? img[y * w + x] * 255 : img[y * w + x];
        const o = ((y + off) * N + (x + off)) * 4;
        id.data[o] = id.data[o + 1] = id.data[o + 2] = v;
      }
    }
    ctx.putImageData(id, 0, 0);
  }

  function drawProbe(canvas) {
    const ctx = canvas.getContext("2d");
    const { x, y } = state.sel;
    ctx.strokeStyle = "#f2b937";
    ctx.lineWidth = 1;
    ctx.strokeRect(x - 1.5, y - 1.5, 4, 4);
  }

  // ---------------------------------------------------------------- playground
  let views = {};

  function recompute() {
    state.noisy = addNoise(state.clean, state.noise, state.seed);
    state.median = medianImage(state.noisy, N);
    const t = state.thresh;
    const gt = crop(threshold(sobelMag(state.clean, N), t), NM, 1);
    const edgeRaw = crop(threshold(sobelMag(state.noisy, N), t), NM, 1);
    const edgeMed = threshold(sobelMag(state.median, NM), t);

    const denFull = new Uint8Array(state.noisy);       // noisy border, median inside
    for (let y = 0; y < NM; y++) for (let x = 0; x < NM; x++) denFull[(y + 1) * N + x + 1] = state.median[y * NM + x];
    views = { clean: [state.clean, N], noisy: [state.noisy, N], median: [denFull, N],
              edgeRaw: [edgeRaw, NE, true], edgeMed: [edgeMed, NE, true] };
    drawPanels();

    const raw = edgeScore(edgeRaw, gt), med = edgeScore(edgeMed, gt);
    const inner = crop(state.clean, N, 1);
    const pRaw = psnr(inner, crop(state.noisy, N, 1)), pMed = psnr(inner, state.median);
    setMetric("mFpRaw", fmt(raw.fp), "mFpMed", fmt(med.fp), med.fp <= raw.fp);
    setMetric("mF1Raw", raw.f1.toFixed(2), "mF1Med", med.f1.toFixed(2), med.f1 >= raw.f1);
    const db = (v) => (v === Infinity ? "identical" : v.toFixed(1) + " dB");
    setMetric("mPsnrRaw", db(pRaw), "mPsnrMed", db(pMed), pMed >= pRaw);

    renderInspector();
    sim.reset();
  }

  function setMetric(idA, a, idB, b, bBetter) {
    $(idA).textContent = a; $(idB).textContent = b;
    $(idA).classList.toggle("better", !bBetter && a !== b);
    $(idB).classList.toggle("better", bBetter && a !== b);
  }

  function drawPanels() {
    document.querySelectorAll("[data-panel]").forEach((c) => {
      const [img, w, bin] = views[c.dataset.panel];
      drawGray(c, img, w, !!bin);
      drawProbe(c);
    });
  }

  function loadImageFromURL(url) {
    return new Promise((resolve, reject) => {
      const im = new Image();
      im.onload = () => {
        const c = document.createElement("canvas"); c.width = c.height = N;
        const ctx = c.getContext("2d");
        const s = Math.min(im.width, im.height);        // centre square crop
        ctx.drawImage(im, (im.width - s) / 2, (im.height - s) / 2, s, s, 0, 0, N, N);
        const d = ctx.getImageData(0, 0, N, N).data, g = new Uint8Array(N * N);
        for (let i = 0; i < N * N; i++)
          g[i] = Math.round(0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]);
        resolve(g);
      };
      im.onerror = () => reject(new Error("That file could not be read as an image. Try a PNG or JPEG."));
      im.src = url;
    });
  }

  async function selectImage(name) {
    state.imgName = name;
    state.clean = await loadImageFromURL(window.TEST_IMAGES[name]);
    setPressed(name);
    recompute();
  }

  function setPressed(name) {
    document.querySelectorAll("#imagePicker [data-img]").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.img === name)));
    $("uploadLabel").setAttribute("aria-pressed", String(name === "upload"));
  }

  // ---------------------------------------------------------------- pixel inspector
  function cells(vals, centre, klass = "") {
    return vals.map((v, i) => {
      let c = i === centre ? "c" : "";
      if (klass === "noise" && i !== centre) c = v === 255 ? "salt" : v === 0 ? "pepper" : "";
      return `<span class="${c}">${v}</span>`;
    }).join("");
  }

  function renderInspector() {
    const { x, y } = state.sel;
    $("pxPos").textContent = `at column ${x}, row ${y}`;
    const ok = x >= 1 && x <= N - 2 && y >= 1 && y <= N - 2;
    if (!ok) {
      ["winNoisy", "rowSort", "combine", "medResult", "sobel"].forEach((id) => {
        $(id).innerHTML = `<p class="empty">This pixel is on the image border, so it has no full 3×3 window and the hardware gives no output for it. Pick a pixel at least 1 away from the edge.</p>`;
      });
      return;
    }
    const n = state.noisy, w = [];
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) w.push(n[(y + dy) * N + x + dx]);
    $("winNoisy").innerHTML = cells(w, 4, "noise");

    const rows = [w.slice(0, 3), w.slice(3, 6), w.slice(6, 9)].map((r) => [...r].sort((a, b) => a - b));
    $("rowSort").innerHTML =
      `<span class="lbl">low</span><span class="lbl">middle</span><span class="lbl">high</span>` +
      rows.map((r) => r.map((v) => `<span>${v}</span>`).join("")).join("");

    const A = Math.max(rows[0][0], rows[1][0], rows[2][0]);
    const B = med3(rows[0][1], rows[1][1], rows[2][1]);
    const C = Math.min(rows[0][2], rows[1][2], rows[2][2]);
    $("combine").innerHTML =
      `<p>A = largest of the lows = <strong>${A}</strong></p>` +
      `<p>B = median of the middles = <strong>${B}</strong></p>` +
      `<p>C = smallest of the highs = <strong>${C}</strong></p>`;

    const m = med3(A, B, C), sorted = [...w].sort((a, b) => a - b);
    $("medResult").innerHTML =
      `<p class="big">${m}</p>` +
      `<p>Median of A, B and C. Check: the 5th of all 9 values sorted is ${sorted[4]}.</p>` +
      `<div class="nine">${sorted.map((v, i) => `<span class="${i === 4 ? "c" : ""}">${v}</span>`).join("")}</div>` +
      `<p>Noisy value was ${w[4]}, filtered value is ${m}.</p>`;

    // Sobel needs a 3x3 window of the median image around (x, y)
    const mx = x - 1, my = y - 1;
    if (mx < 1 || mx > NM - 2 || my < 1 || my > NM - 2) {
      $("sobel").innerHTML = `<p class="empty">Sobel needs a full window of filtered pixels, so it only runs at least 2 pixels away from the image edge.</p>`;
      return;
    }
    const mw = [];
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) mw.push(state.median[(my + dy) * NM + mx + dx]);
    const [p0, p1, p2, p3, , p5, p6, p7, p8] = mw;
    const right = p2 + 2 * p5 + p8, left = p0 + 2 * p3 + p6;
    const bottom = p6 + 2 * p7 + p8, top = p0 + 2 * p1 + p2;
    const gx = right - left, gy = bottom - top, mag = Math.abs(gx) + Math.abs(gy);
    const isEdge = mag >= state.thresh;
    $("sobel").innerHTML =
      `<div class="grid3">${cells(mw, 4)}</div>` +
      `<div class="calc">` +
      `<p>Gx = (${p2} + 2×${p5} + ${p8}) − (${p0} + 2×${p3} + ${p6}) = ${right} − ${left} = ${gx}</p>` +
      `<p>Gy = (${p6} + 2×${p7} + ${p8}) − (${p0} + 2×${p1} + ${p2}) = ${bottom} − ${top} = ${gy}</p>` +
      `<p>|Gx| + |Gy| = ${Math.abs(gx)} + ${Math.abs(gy)} = ${mag}</p>` +
      `<p class="verdict ${isEdge ? "edge" : ""}">${mag} ${isEdge ? "≥" : "<"} ${state.thresh}, so this pixel is ${isEdge ? "an edge" : "not an edge"}</p>` +
      `</div>`;
  }

  // ---------------------------------------------------------------- clock-by-clock simulation
  // Mirrors rtl/window_buffer.v + rtl/median_filter.v (median_stream.v).
  // Every clock, the "next" register values are computed from the current
  // ones, then all are updated together, like Verilog non-blocking (<=).
  const sim = {
    s: null, hist: [], timer: null, running: false,

    reset() {
      this.stop();
      this.s = {
        cycle: 0, inIdx: 0, col: 0, row: 0,
        lbTop: new Uint8Array(N), lbMid: new Uint8Array(N),
        w: new Array(9).fill(0), wValid: 0,
        lo: [0, 0, 0], mi: [0, 0, 0], hi: [0, 0, 0], v1: 0,
        A: 0, B: 0, C: 0, v2: 0,
        med: 0, mValid: 0,
        out: new Uint8Array(NM * NM), outIdx: 0, firstOut: null,
        lastIn: null,
      };
      this.hist = [];
      this.draw();
    },

    done() { return this.s.outIdx >= NM * NM; },

    tick() {
      const s = this.s;
      if (this.done()) return false;
      const valid = s.inIdx < N * N ? 1 : 0;
      const pix = valid ? state.noisy[s.inIdx] : 0;

      // ---- window_buffer ----
      let nw = s.w, nwValid = 0;
      if (valid) {
        const top = s.lbTop[s.col], mid = s.lbMid[s.col];
        nw = [s.w[1], s.w[2], top, s.w[4], s.w[5], mid, s.w[7], s.w[8], pix];
        nwValid = s.row >= 2 && s.col >= 2 ? 1 : 0;
        s.lbTop[s.col] = mid;           // rows move up by one
        s.lbMid[s.col] = pix;
        s.lastIn = { r: s.row, c: s.col };
        if (s.col === N - 1) { s.col = 0; s.row = s.row === N - 1 ? 0 : s.row + 1; } else s.col++;
        s.inIdx++;
      }
      // ---- median stage 1 (from the old window) ----
      const r = [s.w.slice(0, 3), s.w.slice(3, 6), s.w.slice(6, 9)];
      const nlo = r.map((x) => min3(...x)), nmi = r.map((x) => med3(...x)), nhi = r.map((x) => max3(...x));
      const nv1 = s.wValid;
      // ---- median stage 2 ----
      const nA = max3(...s.lo), nB = med3(...s.mi), nC = min3(...s.hi), nv2 = s.v1;
      // ---- median stage 3 ----
      const nmed = med3(s.A, s.B, s.C), nmValid = s.v2;

      // ---- clock edge: update everything together ----
      s.w = nw; s.wValid = nwValid;
      s.lo = nlo; s.mi = nmi; s.hi = nhi; s.v1 = nv1;
      s.A = nA; s.B = nB; s.C = nC; s.v2 = nv2;
      s.med = nmed; s.mValid = nmValid;
      s.cycle++;
      if (s.mValid) {
        s.out[s.outIdx++] = s.med;
        if (s.firstOut === null) s.firstOut = s.cycle;
      }
      this.hist.push({ valid, pix, wValid: s.wValid, mValid: s.mValid, med: s.med });
      if (this.hist.length > 64) this.hist.shift();
      return true;
    },

    steps(n) { for (let i = 0; i < n && this.tick(); i++); this.draw(); },

    run() {
      if (this.running) { this.stop(); return; }
      if (this.done()) this.reset();
      this.running = true; $("run").textContent = "Pause";
      const slow = $("speed").value === "slow";
      const loop = () => {
        if (!this.running) return;
        this.steps(slow ? 1 : N);
        if (this.done()) { this.stop(); return; }
        this.timer = slow ? setTimeout(loop, 166) : requestAnimationFrame(loop);
      };
      loop();
    },

    stop() {
      this.running = false;
      clearTimeout(this.timer); cancelAnimationFrame(this.timer);
      $("run").textContent = "Run";
    },

    finish() { this.stop(); while (this.tick()); this.draw(); },

    // ------------- drawing the bench
    draw() {
      const s = this.s; if (!s || !state.noisy) return;
      $("cClock").textContent = fmt(s.cycle);
      $("cIn").textContent = s.inIdx < N * N
        ? `row ${Math.floor(s.inIdx / N)}, column ${s.inIdx % N}` : "all 16,384 pixels sent";
      $("cOut").textContent = `${fmt(s.outIdx)} of ${fmt(NM * NM)}`;
      $("cFirst").textContent = s.firstOut === null ? "not yet" : `at clock ${fmt(s.firstOut)}`;
      $("step1").disabled = $("stepRow").disabled = $("finish").disabled = this.done();

      this.drawInput(); this.drawOutput(); this.drawRegs(); this.drawTiming();
    },

    drawInput() {
      const c = $("simIn"), ctx = c.getContext("2d"), k = c.width / N, s = this.s;
      const tmp = document.createElement("canvas"); tmp.width = tmp.height = N;
      drawGray(tmp, state.noisy, N);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(tmp, 0, 0, c.width, c.height);
      // dim the pixels not sent yet
      if (s.inIdx < N * N) {
        const r = Math.floor(s.inIdx / N), col = s.inIdx % N;
        ctx.fillStyle = "rgba(20,35,27,0.72)";
        ctx.fillRect(col * k, r * k, (N - col) * k, k);
        ctx.fillRect(0, (r + 1) * k, c.width, (N - r - 1) * k);
      }
      if (s.lastIn) {
        const { r, c: col } = s.lastIn;
        // rows held in the line buffers
        ctx.fillStyle = "rgba(123,208,162,0.30)";
        for (let rr = r - 2; rr <= r; rr++) if (rr >= 0) ctx.fillRect(0, rr * k, c.width, k);
        // current 3x3 window
        ctx.strokeStyle = "#f2b937"; ctx.lineWidth = 2;
        const x0 = Math.max(0, col - 2), y0 = Math.max(0, r - 2);
        ctx.strokeRect(x0 * k + 1, y0 * k + 1, (col - x0 + 1) * k - 2, (r - y0 + 1) * k - 2);
      }
    },

    drawOutput() {
      const c = $("simOut"), ctx = c.getContext("2d"), s = this.s;
      const tmp = document.createElement("canvas"); tmp.width = tmp.height = N;
      const t = tmp.getContext("2d"), id = t.createImageData(N, N);
      for (let i = 0; i < N * N; i++) { id.data[i * 4 + 3] = 255; }
      for (let i = 0; i < s.outIdx; i++) {
        const y = Math.floor(i / NM) + 1, x = (i % NM) + 1, o = (y * N + x) * 4, v = s.out[i];
        id.data[o] = id.data[o + 1] = id.data[o + 2] = v;
      }
      t.putImageData(id, 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(tmp, 0, 0, c.width, c.height);
    },

    drawRegs() {
      const s = this.s;
      const lb = (id, buf) => {
        const c = $(id), ctx = c.getContext("2d"), k = c.width / N;
        for (let i = 0; i < N; i++) { const v = buf[i]; ctx.fillStyle = `rgb(${v},${v},${v})`; ctx.fillRect(i * k, 0, k + 0.5, c.height); }
        if (s.lastIn) { ctx.fillStyle = "#f2b937"; ctx.fillRect(s.lastIn.c * k, 0, k, c.height); }
      };
      lb("lbTop", s.lbTop); lb("lbMid", s.lbMid);
      $("rWin").innerHTML = s.w.map((v) => `<span>${v}</span>`).join("");
      $("rS1").innerHTML = `<span class="lbl">low</span><span class="lbl">middle</span><span class="lbl">high</span>` +
        [0, 1, 2].map((i) => `<span>${s.lo[i]}</span><span>${s.mi[i]}</span><span>${s.hi[i]}</span>`).join("");
      $("rS2").innerHTML =
        `<p>A <strong>${s.A}</strong></p><p>window valid <strong>${s.wValid}</strong></p>` +
        `<p>B <strong>${s.B}</strong></p><p>stage 1 valid <strong>${s.v1}</strong></p>` +
        `<p>C <strong>${s.C}</strong></p><p>stage 2 valid <strong>${s.v2}</strong></p>` +
        `<p>median_out <strong>${s.med}</strong></p><p>median_valid <strong>${s.mValid}</strong></p>`;
    },

    drawTiming() {
      const c = $("timing"), dpr = window.devicePixelRatio || 1;
      const W = c.clientWidth, H = 236;
      if (c.width !== Math.round(W * dpr)) { c.width = Math.round(W * dpr); c.height = Math.round(H * dpr); }
      const ctx = c.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      const ink = cssVar("--ink"), muted = cssVar("--muted"), mask = cssVar("--mask"), rule = cssVar("--rule"), probe = cssVar("--probe");
      const labelW = W < 520 ? 92 : 124;
      const nCyc = W < 520 ? 10 : W < 900 ? 16 : 24;
      const cw = (W - labelW - 8) / nCyc;
      const hist = this.hist.slice(-nCyc);
      const startCycle = this.s.cycle - hist.length + 1;
      const sig = [
        ["clk", "clk"], ["valid_in", "bit", (h) => h.valid], ["pix_in", "bus", (h) => (h.valid ? h.pix : null)],
        ["window valid", "bit", (h) => h.wValid], ["median_valid", "bit", (h) => h.mValid],
        ["median_out", "bus", (h) => (h.mValid ? h.med : null)],
      ];
      const rowH = 32, top = 24;
      ctx.font = `13px ${cssVar("--sans")}`; ctx.textBaseline = "middle";

      // cycle numbers
      ctx.fillStyle = muted; ctx.textAlign = "center";
      ctx.font = `11px ${cssVar("--mono")}`;
      hist.forEach((_, i) => { if ((startCycle + i) % (nCyc > 16 ? 4 : 2) === 0) ctx.fillText(startCycle + i, labelW + i * cw + cw / 2, 10); });

      sig.forEach(([name, kind, f], si) => {
        const y = top + si * rowH, hi = y + 6, lo = y + rowH - 8, mid = (hi + lo) / 2;
        ctx.fillStyle = ink; ctx.textAlign = "left"; ctx.font = `13px ${cssVar("--sans")}`;
        ctx.fillText(name, 0, mid);
        ctx.strokeStyle = rule; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(labelW, y + rowH - 1); ctx.lineTo(W, y + rowH - 1); ctx.stroke();
        ctx.lineWidth = 1.6;
        if (kind === "clk") {
          ctx.strokeStyle = muted; ctx.beginPath();
          hist.forEach((_, i) => {
            const x = labelW + i * cw;
            ctx.moveTo(x, lo); ctx.lineTo(x, hi); ctx.lineTo(x + cw / 2, hi); ctx.lineTo(x + cw / 2, lo); ctx.lineTo(x + cw, lo);
          });
          ctx.stroke();
        } else if (kind === "bit") {
          ctx.strokeStyle = mask; ctx.beginPath();
          let prev = null;
          hist.forEach((h, i) => {
            const x = labelW + i * cw, yy = f(h) ? hi : lo;
            if (prev === null) ctx.moveTo(x, yy); else ctx.lineTo(x, yy);
            ctx.lineTo(x + cw, yy); prev = yy;
          });
          ctx.stroke();
        } else {
          ctx.font = `11px ${cssVar("--mono")}`; ctx.textAlign = "center";
          hist.forEach((h, i) => {
            const v = f(h), x = labelW + i * cw;
            if (v === null) {
              ctx.strokeStyle = rule; ctx.beginPath(); ctx.moveTo(x, mid); ctx.lineTo(x + cw, mid); ctx.stroke();
            } else {
              const e = Math.min(4, cw / 4);
              ctx.strokeStyle = ink; ctx.beginPath();
              ctx.moveTo(x, mid); ctx.lineTo(x + e, hi); ctx.lineTo(x + cw - e, hi); ctx.lineTo(x + cw, mid);
              ctx.lineTo(x + cw - e, lo); ctx.lineTo(x + e, lo); ctx.closePath(); ctx.stroke();
              if (cw >= 24) { ctx.fillStyle = ink; ctx.fillText(v, x + cw / 2, mid + 1); }
            }
          });
        }
      });
      // cursor on the newest clock
      if (hist.length) {
        const x = labelW + (hist.length - 1) * cw;
        ctx.fillStyle = probe; ctx.globalAlpha = 0.18;
        ctx.fillRect(x, top - 4, cw, sig.length * rowH + 4);
        ctx.globalAlpha = 1;
      } else {
        ctx.fillStyle = muted; ctx.textAlign = "left"; ctx.font = `14px ${cssVar("--sans")}`;
        ctx.fillText("Step the clock to start recording signals.", labelW, top + 2 * rowH);
      }
    },
  };

  // ---------------------------------------------------------------- events
  function bind() {
    document.querySelectorAll("#imagePicker [data-img]").forEach((b) =>
      b.addEventListener("click", () => selectImage(b.dataset.img)));

    $("upload").addEventListener("change", (e) => {
      const f = e.target.files[0]; if (!f) return;
      const url = URL.createObjectURL(f);
      loadImageFromURL(url).then((g) => {
        state.clean = g; state.imgName = "upload"; setPressed("upload"); recompute();
      }).catch((err) => alertInline(err.message)).finally(() => URL.revokeObjectURL(url));
    });

    $("noise").addEventListener("input", (e) => { state.noise = +e.target.value; $("noiseOut").textContent = state.noise + "%"; recompute(); });
    $("thresh").addEventListener("input", (e) => { state.thresh = +e.target.value; $("threshOut").textContent = state.thresh; recomputeEdgesOnly(); });
    $("reseed").addEventListener("click", () => { state.seed = (state.seed * 1103515245 + 12345) >>> 0; recompute(); });

    document.querySelectorAll("[data-panel]").forEach((c) => c.addEventListener("click", (e) => {
      const r = c.getBoundingClientRect();
      state.sel = { x: Math.min(N - 1, Math.floor(((e.clientX - r.left) / r.width) * N)),
                    y: Math.min(N - 1, Math.floor(((e.clientY - r.top) / r.height) * N)) };
      drawPanels(); renderInspector();
    }));

    $("step1").addEventListener("click", () => sim.steps(1));
    $("stepRow").addEventListener("click", () => sim.steps(N));
    $("run").addEventListener("click", () => sim.run());
    $("finish").addEventListener("click", () => sim.finish());
    $("reset").addEventListener("click", () => sim.reset());
    $("speed").addEventListener("change", () => { if (sim.running) { sim.stop(); sim.run(); } });
    window.addEventListener("resize", () => sim.drawTiming());
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => sim.drawTiming());
  }

  // threshold changes do not alter noise, so the clock simulation keeps its place
  function recomputeEdgesOnly() {
    const keep = sim.s, hist = sim.hist;
    recompute();
    sim.s = keep; sim.hist = hist; sim.draw();
  }

  function alertInline(msg) {
    const p = document.querySelector("#try .hint");
    p.textContent = msg;
  }

  // handle for automated checks (used by the project's UI test)
  window.__bench = { state, sim, medianImage, sobelMag };

  bind();
  selectImage("cameraman");
})();
