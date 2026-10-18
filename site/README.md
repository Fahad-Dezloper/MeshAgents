# Marketing site

Static page: no build step, no CDN, no external fonts or scripts. Works from `file://` and on any static host.

## Layout
Hero (headline, subtitle, two buttons, install pill, framed board screenshot), proof marquee, a four-box bento grid, three number cards, the ESTIMATE calculator, a 3-step "Try it in 2 minutes", a 5-question FAQ and the footer. Dark by default; theme toggle in the footer. Screenshots in `assets/` are real captures of the dashboard (WebP, device scale 2).

## Preview
Open `site/index.html` in a browser, or run `python3 -m http.server -d site 8000` and visit http://localhost:8000.
Add `?static` to the URL to show everything at once (no scroll animations, details open), handy for screenshots.

## Deploy (3 lines each)
- **GitHub Pages:** Settings > Pages > deploy from branch, folder `/site` (or copy `site/` to a `gh-pages` branch).
- **Vercel:** `cd site && npx vercel --prod` (framework: Other, no build command).
- **Netlify:** `npx netlify deploy --dir=site --prod`, or drag the `site/` folder into the Netlify dashboard.

## Rename the product
Edit `name` in `site/config.js` (and `cli` / `dir` if the command or folder changes). Name, tagline, repo URL
video and blog links (an empty `video` hides the hero demo button), and the three install steps all render from that file.

## Numbers
Every number lives in `site/facts.js` with a `_src` note. The page renders from it via `data-fact` attributes.
`tests/test_site.py` fails if a number in `index.html` is not in `facts.js`, or a percentage, dollar amount or
decimal appears outside a `data-fact` binding. The calculator output is labelled ESTIMATE with its formulas shown.
