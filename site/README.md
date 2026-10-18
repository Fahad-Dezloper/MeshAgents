# Marketing site

Static page: no build step, no CDN, no external fonts or scripts. Works from `file://` and on any static host.

## Layout
Hero with a framed live-board window, a marquee of real proof numbers, four alternating feature sections, charts, a sideways "results wall" of real results, the ESTIMATE calculator, how it works, install steps, FAQ, the fine print, a closer and a footer. Dark by default; the theme toggle is in the footer.

## Preview
Open `site/index.html` in a browser, or run `python3 -m http.server -d site 8000` and visit http://localhost:8000.
Add `?static` to the URL to show everything at once (no scroll animations, details open), handy for screenshots.

## Deploy (3 lines each)
- **GitHub Pages:** Settings > Pages > deploy from branch, folder `/site` (or copy `site/` to a `gh-pages` branch).
- **Vercel:** `cd site && npx vercel --prod` (framework: Other, no build command).
- **Netlify:** `npx netlify deploy --dir=site --prod`, or drag the `site/` folder into the Netlify dashboard.

## Rename the product
Edit `name` in `site/config.js` (and `cli` / `dir` if the command or folder changes). Name, tagline, repo URL
(a placeholder for now), video and blog links, and the install commands all render from that file.

## Numbers
Every number lives in `site/facts.js` with a `_src` note. The page renders from it via `data-fact` attributes.
`tests/test_site.py` fails if a number in `index.html` is not in `facts.js`, or a percentage, dollar amount or
decimal appears outside a `data-fact` binding. The calculator output is labelled ESTIMATE with its formulas shown.
