// Restyles the Plotly figures the generator embeds so they match the
// Inference Economics brand. Runs after every figure script on the page.
(function () {
  var T = {
    ink: "#1a1b1f", muted: "#64656b", faint: "#8c8d93",
    grid: "rgba(26,27,31,0.07)", axis: "rgba(26,27,31,0.28)",
    brand: "#0066cc", indigo: "#660099", charcoal: "#414042",
    font: '"Avenir LT Std", "Avenir Next", Avenir, Figtree, system-ui, sans-serif'
  };
  var SERIES = { overall: T.brand, "1-bed": T.brand, "2-bed": T.indigo, "3+": T.charcoal };
  var NAMES = { overall: "All units", "1-bed": "1-bed", "2-bed": "2-bed", "3+": "3+ bed" };

  function keyOf(name) {
    name = (name || "").toLowerCase();
    var keys = ["1-bed", "2-bed", "3+", "overall"];
    for (var i = 0; i < keys.length; i++) if (name.indexOf(keys[i]) === 0) return keys[i];
    return null;
  }
  function alpha(hex, a) {
    var n = parseInt(hex.slice(1), 16);
    return "rgba(" + (n >> 16) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
  }
  function plain(gd, i, axis) {
    // Plotly decodes the generator's base64 arrays into fullData; copy them out as plain arrays.
    var v = gd._fullData && gd._fullData[i] && gd._fullData[i][axis];
    return v ? Array.prototype.slice.call(v) : [];
  }

  function baseLayout(l, kind) {
    delete l.template;
    l.paper_bgcolor = "rgba(0,0,0,0)";
    l.plot_bgcolor = "rgba(0,0,0,0)";
    l.font = { family: T.font, size: 12, color: T.muted };
    l.margin = { l: 4, r: kind === "mix" ? 46 : 8, t: kind === "dist" ? 30 : 8, b: 4, pad: 4 };
    l.hoverlabel = { bgcolor: T.ink, bordercolor: T.ink, font: { family: T.font, size: 12, color: "#fff" } };
    l.legend = { orientation: "h", x: 0, xanchor: "left", y: 1.0, yanchor: "bottom", bgcolor: "rgba(0,0,0,0)", font: { size: 12.5, color: T.ink }, title: { text: "" }, itemclick: false, itemdoubleclick: false };
    l.hovermode = kind === "dist" ? "closest" : "x unified";
    l.updatemenus = [];
    // Legends are drawn in HTML above each chart (see buildKey), so spacing is controllable.
    l.showlegend = false;
    if (!l.xaxis) l.xaxis = {};
    if (!l.yaxis) l.yaxis = {};
    Object.keys(l).forEach(function (k) {
      if (!/^[xy]axis\d*$/.test(k)) return;
      var ax = l[k], isX = k.charAt(0) === "x";
      ax.title = { text: "" };
      ax.showgrid = !isX;
      ax.gridcolor = T.grid;
      ax.zeroline = false;
      ax.showline = isX;
      ax.linecolor = T.axis;
      ax.ticks = isX ? "outside" : "";
      ax.ticklen = 4;
      ax.tickcolor = T.axis;
      ax.tickfont = { size: 11.5, color: T.muted };
      ax.automargin = true;
      delete ax.tickprefix;
    });
  }

  function styleTrend(gd, l, d) {
    l.yaxis.tickformat = "$,.0f";
    l.xaxis.hoverformat = "%B %Y";
    d.forEach(function (t) {
      var c = SERIES[keyOf(t.name)] || T.brand;
      if (t.fill === "toself") {
        t.mode = "lines";
        t.fillcolor = alpha(c, 0.14);
        t.line = { width: 0 };
        t.name = "Middle 50% of listings";
        t.hoverinfo = "skip";
      } else {
        t.line = { color: c, width: 2.25, shape: "spline", smoothing: 0.4 };
        t.marker = { size: 5, color: c, line: { color: "#fff", width: 1.5 } };
        t.hovertemplate = "%{y:$,.0f}<extra>Median</extra>";
      }
    });
  }

  function styleMix(gd, l, d) {
    l.yaxis.tickformat = ".0%";
    l.yaxis.range = [0, 1];
    l.yaxis.dtick = 0.25;
    l.xaxis.hoverformat = "%B %Y";
    var fills = { "1-bed": 0.32, "2-bed": 0.26, "3+": 0.22 };
    var last = d.map(function (t, i) { var y = plain(gd, i, "y"); return y.length ? y[y.length - 1] : 0; });
    var total = last.reduce(function (a, b) { return a + b; }, 0) || 1;
    var base = 0, items = [];
    l.annotations = [];
    d.forEach(function (t, i) {
      var k = keyOf(t.name), c = SERIES[k] || T.brand;
      // White seams between bands instead of coloured outlines.
      t.line = { color: "#fff", width: 1.5, shape: "spline", smoothing: 0.4 };
      t.fillcolor = alpha(c, fills[k] || 0.25);
      t.name = NAMES[k] || t.name;
      t.hovertemplate = "%{y:.1%}";
      // Label the latest share at the right edge, centred in its band.
      var share = last[i] / total;
      l.annotations.push({
        xref: "paper", x: 1, xanchor: "left", xshift: 6, yref: "y", y: base + share / 2,
        text: Math.round(share * 100) + "%", showarrow: false,
        font: { family: T.font, size: 12, color: c }
      });
      base += share;
      items.push({ label: t.name, kind: "area", color: alpha(c, (fills[k] || 0.25) + 0.25) });
    });
    return items;
  }

  function styleDist(gd, l, d) {
    var cols = [SERIES["1-bed"], SERIES["2-bed"]];
    d.forEach(function (t, i) {
      t.marker = { color: alpha(cols[i] || T.brand, 0.82), line: { width: 0 } };
      t.hovertemplate = "%{x}<br><b>%{y}</b> listings<extra></extra>";
    });
    l.bargap = 0.08;
    ["xaxis", "xaxis2"].forEach(function (k) { if (l[k]) l[k].tickformat = "$,.0f"; });
    (l.shapes || []).forEach(function (s) {
      var solid = s.line && s.line.dash === "solid";
      s.line = { color: solid ? T.ink : T.faint, width: solid ? 1.5 : 1, dash: solid ? "solid" : "dot" };
    });
    (l.annotations || []).forEach(function (a) {
      a.font = { family: T.font, size: 13, color: T.ink };
      a.text = a.text === "1-bed" ? "1-bed" : a.text === "2-bed" ? "2-bed" : a.text;
    });
  }

  function styleForecast(gd, l, d, flat) {
    l.yaxis.tickformat = "$,.0f";
    l.xaxis.hoverformat = "%B %Y";
    var hi = -1, fi = -1;
    d.forEach(function (t, i) {
      if (t.name === "History") hi = i;
      if (t.name === "Forecast") fi = i;
    });
    d.forEach(function (t, i) {
      if (i === hi) {
        t.name = "Observed median";
        t.line = { color: T.charcoal, width: 2, shape: "spline", smoothing: 0.4 };
        t.hovertemplate = "%{y:$,.0f}";
      } else if (i === fi) {
        t.name = flat ? "Held flat" : "Forecast";
        t.line = { color: flat ? T.faint : T.brand, width: 2, dash: "dash" };
        t.marker = { size: 6, color: flat ? T.faint : T.brand, line: { color: "#fff", width: 1.5 } };
        t.hovertemplate = "%{y:$,.0f}";
        // Join the forecast to the last observed month so the line reads as one series.
        if (hi > -1) {
          var hx = plain(gd, hi, "x"), hy = plain(gd, hi, "y");
          var fx = plain(gd, fi, "x"), fy = plain(gd, fi, "y");
          if (hx.length && fx.length) {
            t.x = [hx[hx.length - 1]].concat(fx);
            t.y = [hy[hy.length - 1]].concat(fy);
          }
        }
      } else if (t.fill === "toself") {
        var wide = /95/.test(t.name);
        t.mode = "lines";
        t.fillcolor = alpha(T.brand, wide ? 0.08 : 0.16);
        t.line = { width: 0 };
        t.name = wide ? "95% range" : "80% range";
        t.visible = flat ? false : true;
        t.hoverinfo = "skip";
      }
    });
    var items = [{ label: "Observed median", kind: "line", color: T.charcoal }];
    items.push({ label: flat ? "Held flat" : "Forecast", kind: "dash", color: flat ? T.faint : T.brand });
    if (!flat) {
      items.push({ label: "80% range", kind: "area", color: alpha(T.brand, 0.3) });
      items.push({ label: "95% range", kind: "area", color: alpha(T.brand, 0.14) });
    }
    return items;
  }

  function buildKey(frame, items) {
    if (!items || !items.length) return;
    var ul = document.createElement("ul");
    ul.className = "key chart-key";
    items.forEach(function (it) {
      var li = document.createElement("li"), i = document.createElement("i");
      i.className = "k-" + it.kind;
      i.style.setProperty("--k", it.color);
      li.appendChild(i);
      li.appendChild(document.createTextNode(it.label));
      ul.appendChild(li);
    });
    frame.parentNode.insertBefore(ul, frame);
  }

  function buildToggle(gd, menu) {
    var host = document.querySelector('[data-toggle-for="' + gd.id + '"]');
    if (!host || !menu || !menu.buttons) return;
    menu.buttons.forEach(function (b, i) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = NAMES[keyOf(b.label)] || b.label;
      btn.setAttribute("aria-pressed", i === 0 ? "true" : "false");
      btn.addEventListener("click", function () {
        window.Plotly.restyle(gd, { visible: b.args[0].visible });
        host.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
        btn.setAttribute("aria-pressed", "true");
      });
      host.appendChild(btn);
    });
    host.hidden = false;
  }

  function theme(frame) {
    var gd = frame.querySelector(".plotly-graph-div");
    if (!gd || !gd.data) throw new Error("figure missing");
    var kind = frame.getAttribute("data-chart");
    var l = gd.layout, d = gd.data;
    var menu = l.updatemenus && l.updatemenus[0];
    baseLayout(l, kind);
    if (kind === "trend") styleTrend(gd, l, d);
    var items = null;
    if (kind === "mix") items = styleMix(gd, l, d);
    if (kind === "dist") styleDist(gd, l, d);
    if (kind === "forecast") items = styleForecast(gd, l, d, frame.getAttribute("data-mode") === "flat");
    buildKey(frame, items);
    return window.Plotly.react(gd, d, l, { displayModeBar: false, responsive: true }).then(function () {
      if (kind === "trend") buildToggle(gd, menu);
      frame.classList.add("is-ready");
    });
  }

  function fail(frame) {
    frame.classList.add("is-error");
  }

  var frames = document.querySelectorAll(".chart-frame");
  if (!window.Plotly) {
    frames.forEach(fail);
    return;
  }
  frames.forEach(function (frame) {
    try {
      theme(frame).catch(function () { fail(frame); });
    } catch (e) {
      fail(frame);
    }
  });
})();
