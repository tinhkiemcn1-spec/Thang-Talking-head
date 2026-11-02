// Card engine. render_cards.py calls build(card, icons) once, then seek(t) for every frame.
// Animation is a pure function of t, so every frame is reproducible and frames after
// `settle` are identical (the renderer reuses them).
"use strict";

let ICONS = {};
let ANIMS = [];

const clamp = (x) => Math.max(0, Math.min(1, x));
const ease = (p) => 1 - Math.pow(1 - p, 3);

function h(tag, cls, html) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (html != null) el.innerHTML = html;
  return el;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function icon(name, cls) {
  const svg = ICONS[name];
  if (!svg) return h("span", "icon " + (cls || ""), "");
  return h("span", "icon " + (cls || ""), svg);
}

// fx: up | fade | scale | grow-x | grow-y | draw | count
function anim(el, at, fx = "up", dur = 0.5, extra = {}) {
  ANIMS.push({ el, at, fx, dur, ...extra });
  return el;
}

// Path lengths need the element in the document, so measure on the first seek.
function measure(a) {
  a.el.querySelectorAll("path,line,circle,ellipse,polyline").forEach((p) => {
    const len = p.getTotalLength();
    p.style.strokeDasharray = len;
    p.dataset.len = len;
  });
  a.measured = true;
}

function seek(t) {
  for (const a of ANIMS) {
    if (a.fx === "draw" && !a.measured) measure(a);
    const e = ease(clamp((t - a.at) / a.dur));
    const s = a.el.style;
    switch (a.fx) {
      case "up": s.opacity = e; s.transform = `translateY(${(1 - e) * 28}px)`; break;
      case "fade": s.opacity = e; break;
      case "scale": s.opacity = e; s.transform = `scale(${0.86 + 0.14 * e})`; break;
      case "grow-x": s.transform = `scaleX(${e})`; break;
      case "grow-y": s.transform = `scaleY(${e})`; break;
      case "draw":
        s.opacity = e > 0 ? 1 : 0;
        a.el.querySelectorAll("[data-len]").forEach((p) => { p.style.strokeDashoffset = p.dataset.len * (1 - e); });
        break;
      case "count": {
        s.opacity = clamp((t - a.at) / 0.2);
        const v = a.from + (a.to - a.from) * e;
        a.el.textContent = (a.prefix || "") + v.toFixed(a.decimals || 0) + (a.suffix || "");
        break;
      }
    }
  }
}

// "30", "2.5", "1,200" count up; anything else ("2 H 5", "A") just fades in.
function bigNumber(el, value, at) {
  const m = String(value).match(/^([^\d-]*)(-?[\d,]*\.?\d+)(.*)$/);
  if (!m || m[3].match(/\d/)) { el.textContent = value; return anim(el, at, "up"); }
  const num = parseFloat(m[2].replace(/,/g, ""));
  const decimals = (m[2].split(".")[1] || "").length;
  el.textContent = value;
  return anim(el, at, "count", 0.9, { from: 0, to: num, prefix: m[1], suffix: m[3], decimals });
}

function itemBlock(it, cls) {
  const b = h("div", cls);
  if (it.icon) b.appendChild(icon(it.icon, it.gold ? "gold" : ""));
  if (it.label) b.appendChild(h("div", "label" + (it.gold ? " gold" : ""), esc(it.label)));
  if (it.sub) b.appendChild(h("div", "sub", esc(it.sub)));
  return b;
}

function times(card, n) {
  const start = card.start ?? 0.8, step = card.step ?? 0.45;
  return (card.items || []).slice(0, n ?? 99).map((it, i) => it.at ?? start + i * step);
}

const LAYOUTS = {
  boxes(card, stage) {
    const row = h("div", "row");
    const ts = times(card);
    card.items.forEach((it, i) => {
      if (i && card.connectors) row.appendChild(anim(h("div", "conn"), ts[i] - 0.15, "grow-x", 0.3));
      const b = itemBlock(it, "box" + (it.hl ? " hl" : "") + (it.dim ? " dim" : ""));
      if (card.numbered) b.prepend(h("div", "num", String(i + 1).padStart(2, "0")));
      row.appendChild(anim(b, ts[i], "up"));
    });
    stage.appendChild(row);
  },

  checklist(card, stage) {
    const split = h("div", "split");
    const list = h("div", "list");
    const ts = times(card);
    card.items.forEach((it, i) => {
      const li = h("div", "li");
      if (it.icon) li.appendChild(icon(it.icon, "muted"));
      li.appendChild(h("div", "label", esc(it.label)));
      if (it.check !== false) li.appendChild(anim(icon("check", "tick"), ts[i] + 0.3, "scale", 0.3));
      list.appendChild(anim(li, ts[i], "up"));
    });
    split.appendChild(list);
    if (card.panel) {
      const p = card.panel, at = p.at ?? ts[ts.length - 1] + 0.6;
      const panel = h("div", "panel");
      if (p.title) panel.appendChild(h("div", "label", esc(p.title)));
      for (let i = 0; i < (p.bars ?? 3); i++) {
        const bar = h("div", "bar");
        bar.style.width = `${90 - i * 18}%`;
        panel.appendChild(bar);
      }
      if (p.badge) panel.appendChild(anim(h("div", "badge label", esc(p.badge)), at + 0.5, "scale", 0.4));
      split.appendChild(anim(panel, at, "up"));
    }
    stage.appendChild(split);
  },

  flow(card, stage) {
    const flow = h("div", "flow");
    const ts = times(card);
    card.items.forEach((it, i) => {
      if (i) {
        const a = h("div", "arrow", '<svg viewBox="0 0 260 40"><line x1="10" y1="20" x2="246" y2="20" stroke="currentColor" stroke-width="2"/><polyline points="232,8 248,20 232,32" fill="none" stroke="currentColor" stroke-width="2"/></svg>');
        flow.appendChild(anim(a, ts[i] - 0.35, "draw", 0.45));
      }
      const n = h("div", "node");
      if (it.icon) {
        if (card.ring) { const r = h("div", "ring" + (it.gold ? " gold" : "")); r.appendChild(icon(it.icon, it.gold ? "gold" : "")); n.appendChild(r); }
        else n.appendChild(icon(it.icon, it.gold ? "gold" : ""));
      }
      n.appendChild(h("div", "label" + (it.gold ? " gold" : ""), esc(it.label)));
      if (it.sub) n.appendChild(h("div", "sub", esc(it.sub)));
      flow.appendChild(anim(n, ts[i], "up"));
    });
    stage.appendChild(flow);
  },

  compare(card, stage) {
    const wrap = h("div", "compare");
    const cols = card.cols || card.items;
    const start = card.start ?? 0.8, step = card.step ?? 0.9;
    cols.forEach((c, i) => {
      if (i) wrap.appendChild(anim(h("div", "vline"), start + 0.2, "grow-y", 0.6));
      const col = h("div", "col");
      if (c.title) col.appendChild(h("div", "label big" + (c.gold ? " gold" : ""), esc(c.title)));
      if (c.icon) col.appendChild(icon(c.icon, c.gold ? "gold" : ""));
      if (c.label) col.appendChild(h("div", "label", esc(c.label)));
      if (c.sub) col.appendChild(h("div", "sub", esc(c.sub)));
      if (c.dim) col.style.filter = "brightness(.55)";
      wrap.appendChild(anim(col, c.at ?? start + i * step, "up"));
    });
    stage.appendChild(wrap);
  },

  equation(card, stage) {
    const eq = h("div", "eq");
    const terms = h("div", "terms");
    let at = card.start ?? 0.7;
    const step = card.step ?? 0.55;
    card.terms.forEach((t) => {
      if (t.op) { terms.appendChild(anim(h("div", "op", esc(t.op)), t.at ?? at, "fade", 0.3)); at += step * 0.6; return; }
      const term = h("div", "term");
      const big = h("div", "big" + (t.gold ? " gold" : ""));
      const num = h("span");
      big.appendChild(num);
      if (t.unit) big.appendChild(h("span", "", " " + esc(t.unit)));
      term.appendChild(big);
      if (t.sub) term.appendChild(h("div", "sub", esc(t.sub)));
      const when = t.at ?? at;
      bigNumber(num, t.value, when);
      terms.appendChild(anim(term, when, "up"));
      at = when + step;
    });
    eq.appendChild(terms);
    if (card.track) {
      const track = anim(h("div", "track"), card.track[0].at ?? at, "fade", 0.3);
      card.track.forEach((s) => {
        const seg = h("div", "seg label", esc(s.label || ""));
        seg.style.flex = s.w ?? 1;
        seg.style.background = { green: "var(--green)", gold: "var(--gold)", dim: "rgba(255,255,255,.12)" }[s.color || "green"];
        if (s.color === "gold") seg.style.color = "#1a1530";
        track.appendChild(anim(seg, s.at ?? at, "grow-x", 0.7));
        at = (s.at ?? at) + 0.6;
      });
      eq.appendChild(track);
    }
    if (card.foot) {
      const foot = h("div", "foot");
      const l = h("div", "label gold", esc(card.foot.left || ""));
      const r = h("div", "term");
      const rb = h("div", "big");
      rb.style.fontSize = "64px";
      r.appendChild(rb);
      foot.appendChild(anim(l, card.foot.at ?? at, "up"));
      if (card.foot.right) bigNumber(rb, card.foot.right, (card.foot.at ?? at) + 0.3);
      foot.appendChild(r);
      eq.appendChild(foot);
    }
    stage.appendChild(eq);
  },

  bars(card, stage) {
    const wrap = h("div", "bars");
    const ts = times(card);
    const max = Math.max(...card.items.map((b) => Number(b.value) || 0)) || 1;
    card.items.forEach((b, i) => {
      const col = h("div", "barcol");
      if (b.top) col.appendChild(anim(h("div", "label", esc(b.top)), ts[i] + 0.4, "fade"));
      const fill = h("div", "barfill " + (b.style || ""));
      fill.style.height = `${(Number(b.value) / max) * (card.maxHeight || 420)}px`;
      col.appendChild(anim(fill, ts[i], "grow-y", 0.7));
      col.appendChild(anim(h("div", "label", esc(b.label ?? "")), ts[i] + 0.2, "fade"));
      if (b.sub) col.appendChild(h("div", "sub", esc(b.sub)));
      wrap.appendChild(col);
    });
    stage.appendChild(wrap);
  },

  stat(card, stage) {
    const wrap = h("div", "stat");
    const at = card.start ?? 0.6;
    if (card.icon) {
      const ic = icon(card.icon, "gold");
      ic.style.width = ic.style.height = "260px";
      wrap.appendChild(anim(ic, at, "scale", 0.6));
    } else if (card.dial !== false) {
      const d = h("div", "dial", '<svg viewBox="0 0 200 200"><circle cx="100" cy="100" r="92" fill="none" stroke="currentColor" stroke-width="2.5"/>' +
        Array.from({ length: 12 }, (_, i) => { const a = i * Math.PI / 6; return `<line x1="${100 + 82 * Math.sin(a)}" y1="${100 - 82 * Math.cos(a)}" x2="${100 + 88 * Math.sin(a)}" y2="${100 - 88 * Math.cos(a)}" stroke="currentColor" stroke-width="2"/>`; }).join("") +
        '<line x1="100" y1="100" x2="100" y2="40" stroke="#fff" stroke-width="3" stroke-linecap="round"/><line x1="100" y1="100" x2="72" y2="152" stroke="#fff" stroke-width="3" stroke-linecap="round"/></svg>');
      wrap.appendChild(anim(d, at, "draw", 1.0));
    }
    const txt = h("div", "txt");
    const big = h("div", "big");
    bigNumber(big, card.value, at + 0.3);
    txt.appendChild(big);
    if (card.unit) txt.appendChild(anim(h("div", "label unit", esc(card.unit)), at + 0.7, "up"));
    if (card.sub) txt.appendChild(anim(h("div", "label sub", esc(card.sub)), at + 1.0, "up"));
    wrap.appendChild(txt);
    stage.appendChild(wrap);
  },

  timeline(card, stage) {
    const tl = h("div", "tl");
    const ts = times(card);
    tl.appendChild(anim(h("div", "base"), (card.start ?? 0.8) - 0.3, "grow-x", Math.max(0.8, ts[ts.length - 1] - ts[0] + 0.6)));
    const n = card.items.length;
    card.items.forEach((it, i) => {
      const st = h("div", "stop");
      st.style.left = `${((i + 0.5) / n) * 100}%`;
      st.appendChild(icon(it.icon || "circle-dot", it.gold ? "gold" : ""));
      st.appendChild(h("div", "dot"));
      st.appendChild(h("div", "label", esc(it.label)));
      if (it.sub) st.appendChild(h("div", "sub", esc(it.sub)));
      tl.appendChild(anim(st, ts[i], "up"));
    });
    stage.appendChild(tl);
  },

  loop(card, stage) {
    const W = 1100, H = 560, rx = 300, ry = 150;
    const loop = h("div", "loop");
    const ring = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    ring.setAttribute("class", "ring");
    ring.setAttribute("viewBox", `0 0 ${W} ${H}`);
    ring.innerHTML = `<ellipse cx="${W / 2}" cy="${H / 2}" rx="${rx}" ry="${ry}" fill="none" stroke="currentColor" stroke-width="2.5"/>`;
    loop.appendChild(ring);
    const ts = times(card);
    anim(ring, (card.start ?? 0.8) - 0.4, "draw", 1.2);
    if (card.center) loop.appendChild(anim(h("div", "center label", esc(card.center)), ts[0] + 0.2, "scale"));
    const n = card.items.length;
    card.items.forEach((it, i) => {
      const a = -Math.PI / 2 + (i / n) * 2 * Math.PI;
      const ex = rx + 170, ey = ry + 90;
      const pt = itemBlock(it, "pt");
      pt.style.left = `${W / 2 + ex * Math.cos(a)}px`;
      pt.style.top = `${H / 2 + ey * Math.sin(a)}px`;
      loop.appendChild(anim(pt, ts[i], "up"));
    });
    stage.appendChild(loop);
  },

  statement(card, stage) {
    const s = h("div", "statement");
    const at = card.start ?? 0.6;
    if (card.icon) s.appendChild(anim(icon(card.icon, "gold"), at, "scale", 0.6));
    if (card.text) s.appendChild(anim(h("div", "label", esc(card.text)), at + 0.5, "up"));
    if (card.sub) s.appendChild(anim(h("div", "sub", esc(card.sub)), at + 0.9, "up"));
    stage.appendChild(s);
  },

  chips(card, stage) {
    const wrap = h("div", "chips");
    let at = card.start ?? 0.7;
    (card.rows || []).forEach((r) => {
      if (r.caption) wrap.appendChild(anim(h("div", "cap", esc(r.caption)), at, "fade"));
      const row = h("div", "chiprow");
      r.chips.forEach((c, j) => row.appendChild(anim(h("div", "chip label", esc(c)), at + 0.15 + j * 0.08, "up", 0.35)));
      wrap.appendChild(row);
      at += 0.4 + r.chips.length * 0.08;
    });
    if (card.highlight) {
      const hl = card.highlight;
      at = hl.at ?? at + 0.3;
      if (hl.caption) wrap.appendChild(anim(h("div", "cap", esc(hl.caption)), at, "fade"));
      const bar = h("div", "hlbar");
      const on = h("div", "on label");
      if (hl.icon) on.appendChild(icon(hl.icon));
      on.appendChild(h("span", "", esc(hl.label)));
      bar.appendChild(anim(on, at + 0.2, "up"));
      if (hl.other) bar.appendChild(anim(h("div", "off label", esc(hl.other)), at + 0.5, "up"));
      wrap.appendChild(bar);
    }
    stage.appendChild(wrap);
  },

  cta(card, stage) {
    const c = h("div", "cta");
    const at = card.start ?? 0.5;
    if (card.image) { const img = h("img"); img.src = card.image; c.appendChild(anim(img, at, "scale", 0.6)); }
    const lines = h("div", "lines");
    ["l1", "l2", "l3", "l4"].forEach((k, i) => {
      if (card[k]) lines.appendChild(anim(h("div", k + " label", esc(card[k])), at + 0.4 + i * 0.45, "up"));
    });
    c.appendChild(lines);
    stage.appendChild(c);
  },
};

function build(card, icons, opts = {}) {
  ICONS = icons || {};
  ANIMS = [];
  document.body.className = "font-" + (opts.font || "inter");
  const root = document.getElementById("root");
  root.innerHTML = "";

  if (card.layout === "caption") {
    document.body.classList.add("transparent");
    root.appendChild(h("div", "caption " + (card.pos || "bottom"), esc(card.text).replace(/\n/g, "<br>")));
    return 0;
  }

  const el = h("div", "card" + (card.title ? "" : " nohead"));
  if (card.title) {
    const head = h("div", "head");
    if (card.eyebrow) head.appendChild(anim(h("div", "eyebrow", esc(card.eyebrow)), 0.1, "fade", 0.4));
    head.appendChild(anim(h("div", "title", esc(card.title)), 0.2, "up", 0.5));
    head.appendChild(anim(h("div", "rule"), 0.35, "grow-x", 0.8));
    el.appendChild(head);
  }
  const stage = h("div", "stage");
  el.appendChild(stage);
  if (card.note) el.appendChild(anim(h("div", "note" + (card.noteLeft ? " left" : ""), esc(card.note)), card.noteAt ?? 1.2, "fade", 0.5));
  root.appendChild(el);

  const fn = LAYOUTS[card.layout];
  if (!fn) throw new Error("unknown layout " + card.layout);
  fn(card, stage);
  seek(0);
  return Math.max(0, ...ANIMS.map((a) => a.at + a.dur));
}

window.build = build;
window.seek = seek;
window.LAYOUT_NAMES = Object.keys(LAYOUTS);
