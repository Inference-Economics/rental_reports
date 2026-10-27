# Report design

The cloud pipeline still writes the original report HTML. During the monthly
publish run, `restyle.py` reads the figures and Plotly charts out of that file
and replaces it with the Inference Economics page design before the reports are
committed and deployed.

## Files

- `extract.py` reads headline figures, the five charts, income benchmarks and
  notes from a generator report. It raises `LayoutChanged` if the generator's
  HTML stops matching, which fails the workflow before anything is published.
- `render.py` builds the page.
- `report.css` and `report.js` are inlined into every page. `report.js` restyles
  the Plotly figures after they load.
- Images come from `assets/`: `logo-symbol`, `logo-wordmark`, `ie-pattern.png`,
  `toronto-skyline-strip.png` and `vancouver-skyline-strip.png`.

## Use

```sh
pip install -r scripts/redesign/requirements.txt

# Redesign both cities for a month, in place
python scripts/redesign/restyle.py --month 2026-10

# Self-contained previews (Plotly and images embedded) for checking a change
python scripts/redesign/restyle.py reports/*/2026-09/index.html \
  --preview previews/ --plotly path/to/plotly.min.js
```

A page that has already been redesigned is skipped, so running the script twice
does nothing. To redesign an older month, run it with that month and commit the
result.

## Adding a city

Add the city's skyline strip to `assets/`, then add an entry to `SKY` (file name
and display height) and `CODES` in `render.py`.
