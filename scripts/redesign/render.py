"""Render the Inference Economics rental report page from extracted report data."""
import datetime as dt
import html
import re
from pathlib import Path

HERE = Path(__file__).parent
ASSETS = "https://raw.githubusercontent.com/Inference-Economics/rental_reports/main/assets"
SITE = "https://www.inference-economics.com"
LABEL = {"overall": "All units", "1-bed": "1-bed", "2-bed": "2-bed", "3+": "3+ bed"}
SWATCH = {"overall": "#1a1b1f", "1-bed": "#0066cc", "2-bed": "#660099", "3+": "#414042"}
CODES = {"Toronto": "TOR", "Vancouver": "VAN"}
# Skyline strip per city (reflection removed, brand tint) and its display height.
SKY = {"Toronto": ("toronto-skyline-strip.png", 190), "Vancouver": ("vancouver-skyline-strip.png", 140)}
PATTERN = "ie-pattern.png"
# Written into every redesigned page so a second run leaves it alone.
MARKER = "inference-economics-report/2"

e = html.escape


def dollars(v):
    return "—" if v is None else f"${v:,.0f}"


def chg(v):
    if v is None:
        return '<span class="chg na">—</span>'
    r = round(v, 1)
    if r == 0:
        return '<span class="chg flat">0.0%</span>'
    cls = "up" if r > 0 else "down"
    sign = "+" if r > 0 else "−"
    return f'<span class="chg {cls}">{sign}{abs(r):.1f}%</span>'


def rangebar(k, lo, hi):
    if None in (k["p25"], k["p75"], k["median"]):
        return '<span class="chg na">—</span>'
    pos = lambda v: (v - lo) / (hi - lo) * 100
    a, b, m = pos(k["p25"]), pos(k["p75"]), pos(k["median"])
    return (
        f'<div class="rangebar" role="img" aria-label="Middle 50% from {dollars(k["p25"])} to {dollars(k["p75"])}, median {dollars(k["median"])}">'
        f'<span class="track"></span><span class="iqr" style="left:{a:.2f}%;width:{b - a:.2f}%"></span>'
        f'<span class="med" style="left:{m:.2f}%"></span></div>'
    )


def month_parts(label):
    d = dt.datetime.strptime(label, "%B %Y").date()
    prev = (d.replace(day=1) - dt.timedelta(days=1)).strftime("%B")
    year_ago = d.replace(year=d.year - 1).strftime("%B %Y")
    return d, prev, year_ago


def lede(city, month, k):
    _, prev, year_ago = month_parts(month)

    def phrase(v, ref, same, above, below):
        if v is None:
            return None
        r = round(v, 1)
        if r == 0:
            return f"{same} {ref}"
        return f"{abs(r):.1f}% {above if r > 0 else below} {ref}"

    mom = phrase(k["mom"], prev, "unchanged from", "higher than", "lower than")
    yoy = phrase(k["yoy"], year_ago, "level with", "above", "below")
    bits = [b for b in (mom, yoy) if b]
    tail = (", " + " and ".join(bits)) if bits else ""
    n = f"{k['n']:,} " if k["n"] else ""
    return (f"The median asking rent across {n}active {city} listings was "
            f"<strong>{dollars(k['median'])}</strong> in {month}{tail}.")


def forecast_meta(title):
    parts = [p.strip() for p in title.split("—")]
    model = parts[1] if len(parts) > 1 else ""
    if "disabled" in model:
        return "flat", "Model off this month. Latest median held flat."
    m = re.match(r"(SARIMA)\(([^)]*)\)×\(([^)]*)\)\s*AIC=(-?[\d.]+)", model)
    if m:
        order = m.group(2).replace(" ", "")
        seas = m.group(3).replace(" ", "")
        aic = m.group(4).replace("-", "−")
        mape = parts[2].split(":", 1)[1].strip() if len(parts) > 2 and ":" in parts[2] else "—"
        txt = f"SARIMA({order})×({seas}) · AIC {aic}"
        if mape and mape != "—":
            txt += f" · backtest MAPE {mape}"
        return "model", txt
    return "model", model


def figure(chart, kind, mode="model"):
    return (
        f'<div class="chart-frame" data-chart="{kind}" data-mode="{mode}">'
        f'<div id="{chart["id"]}" class="plotly-graph-div" style="{chart["style"]}"></div>'
        f'<script type="text/javascript">{chart["script"]}</script>'
        f'<p class="chart-error">This chart could not load. Check your connection and reload the page.</p>'
        f"</div>"
    )


PLOTLY_CDN = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"


def render(d, inline_plotly=None):
    plotly_tag = (f"<script>{inline_plotly}</script>" if inline_plotly
                  else f'<script src="{PLOTLY_CDN}"></script>')
    css = (HERE / "report.css").read_text()
    js = (HERE / "report.js").read_text()
    city, month = d["city"], d["month"]
    when, prev, _ = month_parts(month)
    code = f"{CODES.get(city, city[:3].upper())} · {when:%Y-%m}"
    kp = {k["key"]: k for k in d["kpis"]}
    overall = kp["overall"]
    sizes = [kp[k] for k in ("1-bed", "2-bed", "3+") if k in kp]

    lows = [k["p25"] for k in d["kpis"] if k["p25"]]
    highs = [k["p75"] for k in d["kpis"] if k["p75"]]
    pad = (max(highs) - min(lows)) * 0.08
    lo, hi = min(lows) - pad, max(highs) + pad

    rows = "".join(
        f"""
        <tr>
          <td><span class="unit"><i class="swatch" style="background:{SWATCH[k['key']]}"></i>{LABEL[k['key']]}</span></td>
          <td class="median">{dollars(k['median'])}</td>
          <td class="rangecell">{rangebar(k, lo, hi)}<div class="range-legend"><span>{dollars(k['p25'])}</span><span>{dollars(k['p75'])}</span></div></td>
          <td class="col-chg" data-label="1 mo">{chg(k['mom'])}</td>
          <td class="col-chg" data-label="12 mo">{chg(k['yoy'])}</td>
          <td class="col-chg" data-label="3 mo">{chg(k['m3'])}</td>
          <td class="n">{f"{k['n']:,}" if k['n'] else '—'}</td>
        </tr>""" for k in sizes)

    ch = d["charts"]
    f1_mode, f1_meta = forecast_meta(ch[3]["title"])
    f2_mode, f2_meta = forecast_meta(ch[4]["title"])
    outlook_note = (
        "Seasonal ARIMA projection of the median asking rent. Shaded bands show the 80% and 95% ranges."
        if "model" in (f1_mode, f2_mode)
        else f"The forecast model is switched off for {city} this month, so the latest median is carried forward without ranges."
    )

    inc = d["income"]
    mult = inc["multiple"]
    rule = "rent at no more than a third of gross income" if mult == 3 else f"gross income of {mult:g}× the rent"
    inc_rows = "".join(
        f"""
        <tr>
          <td><span class="unit"><i class="swatch" style="background:{SWATCH[r['key']]}"></i>{LABEL[r['key']]}</span></td>
          <td class="sub">{dollars(kp[r['key']]['median'])}/mo</td>
          <td><span class="big-num">${r['hourly']:,.2f}</span><span class="sub"> /hr</span></td>
          <td><span class="big-num">{dollars(r['annual'])}</span><span class="sub"> /yr</span></td>
        </tr>""" for r in inc["rows"])

    notes = "".join(f"<li>{e(n)}</li>" for n in d["notes"])
    sky = SKY.get(city)
    sky_img = (f'<div class="horizon"><div class="wrap"><img class="skyline" src="{ASSETS}/{sky[0]}" '
               f'alt="" aria-hidden="true" style="--sky-h:{sky[1]}px" /></div></div>') if sky else ""
    title = f"{city} rental report, {month}"
    desc = f"Median asking rents for {city} rental listings in {month}, by number of bedrooms, with trends, a three-month outlook and income benchmarks."

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{e(title)} | Inference Economics</title>
  <meta name="description" content="{e(desc)}" />
  <meta property="og:title" content="{e(title)}" />
  <meta property="og:description" content="{e(desc)}" />
  <meta property="og:site_name" content="Inference Economics" />
  <meta property="og:type" content="article" />
  <meta name="theme-color" content="#0066cc" />
  <meta name="generator" content="{MARKER}" />
  <link rel="icon" type="image/png" href="{ASSETS}/logo-symbol?raw=1" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600&family=Geist+Mono:wght@400;500&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet" />
  {plotly_tag}
  <style>
{css}
  </style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to report</a>

  <header class="topbar">
    <div class="wrap">
      <a href="{SITE}" aria-label="Inference Economics home">
        <img src="{ASSETS}/logo-wordmark?raw=1" alt="Inference Economics" width="115" height="34" />
      </a>
      <nav aria-label="Report">
        <span class="issue hide-sm">{e(code)}</span>
        <a class="hide-sm" href="#methods">Methods</a>
        <a href="{SITE}/rental-reports">All reports</a>
      </nav>
    </div>
  </header>

  <main id="main">
    <section class="hero" aria-labelledby="report-title">
      <div class="wrap">
        <div>
          <p class="eyebrow rise" style="--i:0">{e(city)} rental market</p>
          <h1 id="report-title" class="rise" style="--i:1">{e(when.strftime('%B'))}<span>{when.year}</span></h1>
          <p class="lede rise" style="--i:2">{lede(city, month, overall)}</p>
        </div>
        <aside class="headline-figure rise" style="--i:3" aria-label="Headline figure">
          <p class="label">Median asking rent, all units</p>
          <p class="big">{dollars(overall['median'])}<small>/mo</small></p>
          <dl class="changes">
            <dt>vs {e(prev)}</dt><dt>vs a year ago</dt><dt>vs 3 months</dt>
            <dd>{chg(overall['mom'])}</dd><dd>{chg(overall['yoy'])}</dd><dd>{chg(overall['m3'])}</dd>
          </dl>
          <div class="range">
            <p class="label" style="margin-bottom:8px">Middle 50% of listings</p>
            {rangebar(overall, overall['p25'] - (overall['p75'] - overall['p25']) * 0.35, overall['p75'] + (overall['p75'] - overall['p25']) * 0.35)}
            <div class="range-legend"><span>{dollars(overall['p25'])}</span><span>median {dollars(overall['median'])}</span><span>{dollars(overall['p75'])}</span></div>
          </div>
        </aside>
      </div>
      {sky_img}
    </section>

    <section class="section" aria-labelledby="s1">
      <div class="wrap">
        <div class="section-head">
          <h2 id="s1"><span class="num">01</span>By number of bedrooms</h2>
          <p>Median asking rent by number of bedrooms. The bar shows where the middle half of listings sit, with the median marked, on a scale shared across rows.</p>
        </div>
        <table class="ledger sizes">
          <thead>
            <tr><th scope="col">Bedrooms</th><th scope="col">Median</th><th scope="col">Middle 50% of listings</th><th scope="col">1 mo</th><th scope="col">12 mo</th><th scope="col">3 mo</th><th scope="col">Listings</th></tr>
          </thead>
          <tbody>{rows}
          </tbody>
        </table>
      </div>
    </section>

    <section class="section" aria-labelledby="s2">
      <div class="wrap">
        <div class="section-head">
          <h2 id="s2"><span class="num">02</span>Rents over time</h2>
          <p>Monthly median asking rent, with the middle 50% of listings shaded. Use the toggle to filter by number of bedrooms.</p>
        </div>
        <div class="chart-grid">
          <figure class="chart" style="margin:0">
            <div class="chart-head">
              <div><h3>Median asking rent</h3></div>
              <div class="segmented" role="group" aria-label="Number of bedrooms" data-toggle-for="{ch[0]['id']}" hidden></div>
            </div>
            {figure(ch[0], "trend")}
          </figure>
          <figure class="chart span-5" style="margin:0">
            <div class="chart-head"><div><h3>Listing mix</h3><p>Share of active listings by number of bedrooms.</p></div></div>
            {figure(ch[1], "mix")}
          </figure>
          <figure class="chart span-7" style="margin:0">
            <div class="chart-head"><div><h3>Where {e(when.strftime('%B'))} listings are priced</h3><p>Count of 1- and 2-bed listings by asking rent.</p></div></div>
            {figure(ch[2], "dist")}
            <ul class="key"><li><i></i>Median</li><li><i class="dot"></i>25th and 75th percentile</li></ul>
          </figure>
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="s3">
      <div class="wrap">
        <div class="section-head">
          <h2 id="s3"><span class="num">03</span>Three-month outlook</h2>
          <p>{e(outlook_note)}</p>
        </div>
        <div class="chart-grid">
          <figure class="chart span-6" style="margin:0">
            <div class="chart-head"><div><h3>1-bed</h3></div><p class="model{' off' if f1_mode == 'flat' else ''}">{e(f1_meta)}</p></div>
            {figure(ch[3], "forecast", f1_mode)}
          </figure>
          <figure class="chart span-6" style="margin:0">
            <div class="chart-head"><div><h3>2-bed</h3></div><p class="model{' off' if f2_mode == 'flat' else ''}">{e(f2_meta)}</p></div>
            {figure(ch[4], "forecast", f2_mode)}
          </figure>
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="s4">
      <div class="wrap">
        <div class="section-head">
          <h2 id="s4"><span class="num">04</span>Income needed</h2>
          <p>Pre-tax income needed to rent at the median, using the common rule of keeping {rule}.</p>
        </div>
        <div class="afford">
          <div class="formula">
            <h3>How it is calculated</h3>
            <p>A full-time year is 40 hours a week for 52 weeks.</p>
            <code>hourly = median rent × {mult:g} ÷ (40 × 52 ÷ 12)<br />annual = hourly × 40 × 52</code>
          </div>
          <table class="ledger compact">
            <thead><tr><th scope="col">Bedrooms</th><th scope="col">Median rent</th><th scope="col">Hourly wage</th><th scope="col">Annual income</th></tr></thead>
            <tbody>{inc_rows}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </main>

  <footer>
    <section class="methods" id="methods" aria-labelledby="m-title" style="--pattern:url('{ASSETS}/{PATTERN}')">
      <div class="wrap">
        <h2 id="m-title">Notes and methods</h2>
        <ul>{notes}<li>1 mo, 12 mo and 3 mo columns are percentage changes in the median against earlier periods.</li></ul>
      </div>
    </section>
    <div class="colophon">
      <div class="wrap">
        <div class="brandline">
          <img src="{ASSETS}/logo-symbol?raw=1" alt="" />
          <span>Inference Economics. {e(city)} rental report, {e(month)}.</span>
        </div>
        <nav aria-label="Footer">
          <a href="{SITE}/rental-reports">All rental reports</a>
          <a href="{SITE}">inference-economics.com</a>
        </nav>
      </div>
    </div>
  </footer>

  <script>
{js}
  </script>
</body>
</html>
"""
