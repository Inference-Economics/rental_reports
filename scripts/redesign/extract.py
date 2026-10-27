"""Pull the figures and Plotly embeds out of a report written by the cloud generator."""
import re
from bs4 import BeautifulSoup


def money(s):
    m = re.search(r"\$([\d,]+(?:\.\d+)?)", s)
    return float(m.group(1).replace(",", "")) if m else None


def pct(s):
    m = re.search(r"([+-]?\d+(?:\.\d+)?)%", s)
    return float(m.group(1)) if m else None


def norm_label(t):
    t = t.lower()
    if t.startswith("overall"):
        return "overall"
    if t.startswith("1"):
        return "1-bed"
    if t.startswith("2"):
        return "2-bed"
    return "3+"


class LayoutChanged(ValueError):
    """The generator's HTML no longer has the structure this script reads."""


def extract(path):
    return extract_html(open(path, encoding="utf-8").read())


def extract_html(text):
    soup = BeautifulSoup(text, "html.parser")
    h1 = soup.find("h1")
    if h1 is None or "Rental Listings" not in h1.get_text():
        raise LayoutChanged("no 'Rental Listings' heading")
    city, month = [p.strip() for p in re.split(r"Rental Listings\s*[—-]\s*", h1.get_text(" ", strip=True))]
    out = {"city": city, "month": month, "kpis": [], "charts": [], "income": None, "notes": []}

    for card in soup.select(".card--kpi"):
        title = card.select_one(".title").get_text(strip=True)
        badges = [b.get_text(strip=True) for b in card.select(".badge")]
        spans = card.select(".deltas span")
        n_txt = next((s.get_text() for s in spans if "n=" in s.get_text()), "")
        iqr_txt = card.select_one(".subtle").get_text(" ", strip=True) if card.select_one(".subtle") else ""
        lo_hi = [float(x.replace(",", "")) for x in re.findall(r"\$([\d,]+)", iqr_txt)]
        out["kpis"].append({
            "key": norm_label(title),
            "median": money(card.select_one(".value").get_text()),
            "mom": pct(badges[0]) if len(badges) > 0 else None,
            "yoy": pct(badges[1]) if len(badges) > 1 else None,
            "m3": pct(badges[2]) if len(badges) > 2 else None,
            "n": int(re.sub(r"\D", "", n_txt)) if n_txt else None,
            "p25": lo_hi[0] if len(lo_hi) > 0 else None,
            "p75": lo_hi[1] if len(lo_hi) > 1 else None,
        })

    for card in soup.select(".card--chart"):
        title = card.select_one(".title").get_text(" ", strip=True)
        body = card.find_all("div", recursive=False)[1]
        div = body.select_one(".plotly-graph-div")
        script = body.find("script")
        out["charts"].append({
            "title": title,
            "id": div["id"],
            "style": div.get("style", ""),
            "script": script.string,
        })

    note = soup.select_one(".card--note")
    if note:
        mult = re.search(r"([\d.]+)×", note.get_text())
        rows = []
        for c in note.find_parent(class_="grid").select(".card.sm-4"):
            rows.append({
                "key": norm_label(c.select_one(".title").get_text(strip=True)),
                "hourly": money(c.select_one(".value").get_text()),
                "annual": money(c.select_one(".subtle").get_text()),
            })
        out["income"] = {"multiple": float(mult.group(1)) if mult else 3.0, "rows": rows}

    out["notes"] = [li.get_text(" ", strip=True) for li in soup.select(".footer li")]

    keys = {k["key"] for k in out["kpis"]}
    if "overall" not in keys or len(keys) < 2:
        raise LayoutChanged(f"expected overall and per-bedroom indicators, found {sorted(keys)}")
    if len(out["charts"]) != 5 or not all(c["script"] for c in out["charts"]):
        raise LayoutChanged(f"expected 5 charts, found {len(out['charts'])}")
    if not out["income"] or not out["income"]["rows"]:
        raise LayoutChanged("income benchmarks missing")
    return out
