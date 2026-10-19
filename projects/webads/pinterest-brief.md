# PINTEREST-GRADE CREATIVES — the 6 templates

Live pin collection needs a Pinterest login (pending item for the owner's
phone). Until then, these six formats are distilled from how web-design
ads actually perform on Pinterest/Instagram — and **each one is already
implemented** by `make_thumb.py` (thumbnail) and the reel structure
(`gen_scripts.py` assigns a template per episode round-robin).

| # | Template | Layout | Used for |
|---|---|---|---|
| 1 | **Mockup Frame** | gradient bg, browser window card (traffic-light dots + URL bar), big headline, price badge | thumb default |
| 2 | **Bold Question** | giant 3-line question, minimal footer strip | hook episodes |
| 3 | **Before/After** | split diagonal: dull left (broken site) vs bright right (new site), "→" arrow | pain episodes |
| 4 | **Price Badge** | solid gradient, circle badge "FROM $1,000", 2-line benefit | offer episodes |
| 5 | **Stat Shock** | one huge number (−7% per second / 75% judge) + one caption line | proof episodes |
| 6 | **Checklist Card** | white card, 5 ✓ items (SEO · Speed · Mobile · Security · Support) | service episodes |

**Palette:** indigo `#1B1F5C` → violet `#5B2BD9` gradient, lime accent
`#C6FF3D`, white cards, near-black text `#0E1020`.
**Type:** Arial Bold / DejaVu Sans Bold, auto-shrink to width (never
height-derived), max 3 lines, price badge always bottom-right of card.
**Grid:** safe margins 80 px; nothing within 220 px of top (Reels UI) or
260 px of bottom.

## Boards to create (owner, 5 minutes)

- "Website Design Ads" — every reel's cover + mockup stills.
- "E-commerce Builds" — store screenshots / before-after.
- "SEO Wins" — stat-shock cards (template 5 as static pins).
- "From $1,000" — price-badge pins linking to the profile.

Post cadence mirrors the reels: 1 pin/day, same artifact pack
(`caption.txt` doubles as pin description).
