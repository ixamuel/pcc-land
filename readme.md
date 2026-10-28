# Land Pattern Overlay

A single offline HTML file for comparing competitor land patterns with Panasonic solder terminals. Open `index.html` directly in a modern browser; no server or build is required.

## Quick start

1. Open `index.html`, or serve this folder locally with `python3 -m http.server 8765` and visit `http://127.0.0.1:8765/`.
2. Enter the competitor manufacturer / part number and dimensions.
3. Select a Panasonic part or enter its full part number and press Enter to load available datasheet dimensions.
4. Choose Manual or Auto resolve and adjust dimensions as needed. Use **Same width** when W1 and W2 should stay linked.
5. Use **Dimensions** to show component annotations or optional P1–P1 distances, then **Export** to download PDF/PNG or print.

Inputs are held only for the current page session; refreshing resets them. Export a report before closing if you need to keep a record.

## Current interface

- A full-height 440 px light sidebar, with a hamburger button opening the Settings drawer at 960 px and below.
- One combined competitor manufacturer / part-number field.
- Five dimension inputs on one row: **L, P1, P2, W1, W2**, with **Height, Inner gap, Total span, Left width, Right width** subtitles.
- Independent **Manual / Auto resolve** controls for each component. Manual mode never runs the solver. Auto mode calculates a dependent value; editing that value moves the calculation to another field.
- **Same width** explicitly links W1 and W2 in either mode. Enabling it uses the last edited width (or the other populated width). Unlinked widths can differ; the solver never assumes they are equal.
- Selecting a catalog part, or entering a recognized part or suffix and pressing Enter, loads its datasheet dimensions once. For example, `ETQP3M4R7KVN` or `KFN`. No load button is needed. Unequal catalog widths automatically disable the width link.
- A selected full Panasonic part adds a blue **↗ Datasheet** link beside its source text, opening its Panasonic product page in a new tab. The PDF component table links the blue, underlined part number to the same page. Suffix-only selections and cleared selections have no link.
- A copy icon sits inside the selected Panasonic part-number field, immediately left of the chevron. It copies only the committed full part number, shows a checkmark for 1.5 seconds after success, and announces success to screen readers. It is hidden while the picker is open, for suffix-only selections, and when empty. If clipboard access fails, a message explains how to copy manually.
- Matching SVG chevrons on the part picker, Document settings, Dimension guide, and Dimensions rotate in 160 ms. Reduced-motion preferences disable the transitions. Export keeps its plain down arrow and opens immediately.
- Missing datasheet dimensions remain blank and are identified in the source message; body length is not substituted for terminal span.
- Title and comment appear in the main header and remain editable under Document settings. The default title is **Recommended Land Pattern**. Comments automatically name the selected Panasonic part and competitor using “Panasonic [PN] solder terminals on [competitor] recommended land pattern.”; a manually edited comment is preserved.
- Red Clear actions sit beside Dimensions (mm). The drawing automatically fits its space; there are no zoom controls.

## Drawing and downloads

The geometry uses **one shared scale on both axes**. X increases rightwards and Y upwards. Both components share the midpoint of their outer span; asymmetric pads are positioned from their actual widths. Zero inner gap is valid. Inconsistent or incomplete patterns are omitted from the drawing rather than shown with misleading geometry.

The view includes an adaptive mm grid, labeled axes, and all five dimension annotations for each component. Perpendicular extension lines are 0.55 px, lighter than the 0.9 px dimension arrows and 1.6 px pad outlines. L labels run parallel to their arrows, with the bottom of each label facing its terminal. The Dimensions dropdown controls component dimensions in the preview; exported reports retain those annotations.

The same dropdown offers **P1–P1 distances**, off by default. It measures from each competitor inner edge to the corresponding Panasonic inner edge using actual pad coordinates. Equal displayed values use **D** on both sides; unequal values use **Dₗ** and **Dᵣ**. Negative values retain their sign, and zero uses an alignment tick. Overlapping distance intervals use separate annotation rows. When enabled, distances appear only in the drawing in the preview, PDF, PNG, and Print; they do not add table rows.

For centered, equal-width pads, each side is `D = (P1_Panasonic − P1_competitor) / 2`. For example, P1 values of 3.50 and 2.70 mm give **D = 0.40 mm per side**. With unequal widths, each distance comes from its actual inner-edge coordinates:

- Left: `competitor.innerLeft − Panasonic.innerLeft`.
- Right: `Panasonic.innerRight − competitor.innerRight`.

Positive values mean the Panasonic inner edge lies to the left of the competitor inner edge on the left terminal, or to its right on the right terminal. Negative values reverse that relationship. These are geometric offsets, not a pass/fail assessment of soldering suitability.

**Export** offers PDF, PNG, and Print. Reports show the title and wrapped comment first, followed by the colored component table and annotated overlay. There is no separate COMMENT footer or repeated legend sentence. Grid and axes are optional and on by default. PDF is vector A4 landscape, labeled “Not to physical scale”; PNG is 2400 × 1696. Download filenames use `[Panasonic PN]_[competitor]_overlay.pdf` or `.png`, with spaces and unsafe filename characters replaced by underscores. Empty names are omitted; if both are empty, the name is `land-pattern_overlay`. An export-ready link allows retrying a download. Incomplete patterns are identified in the report footer.

PDF libraries and the part catalog are bundled into the HTML so exports work offline. The Datasheet links open the selected part’s Panasonic product page and require an internet connection. PNG is a static image and has no clickable links. See [PDF dependency notes](docs/pdf-dependencies.md) for versions, licenses, and update instructions.

## Checks and maintenance

```sh
node tests/dimensions.test.cjs
.venv/bin/python tools/build_catalog.py --check
```

The regression checks cover manual preservation, calculation handoff, linked/independent widths, missing or invalid inputs, asymmetric geometry, common-axis scaling, annotation retention, P1–P1 offsets (equal, asymmetric, negative, zero, and overlapping intervals), inward-facing L labels, and escaped export text. The catalog `--check` command is not fully read-only: it writes `data/catalog.json` and uses today's generation date; regenerate with `.venv/bin/python tools/build_catalog.py` when needed. This updates both the embedded catalog and `data/catalog.json`.

Application code is between `BEGIN APPLICATION` / `END APPLICATION`. Pure solver and rendering functions precede `DOM APPLICATION`; tests execute those functions directly from the HTML. Generated catalog markers are unchanged.

Browser verification: desktop and narrow-screen layouts; full part-number and suffix selection; mode changes and independent widths; all five annotations per component; generated PDF/PNG reports; PDF link destination and position; mouse/keyboard part-number copying and selection resets. The PDF was rendered and visually checked as a single A4 landscape page.

## Project history

Earlier implementation notes are preserved in [Project history](docs/project-history.md). They describe superseded behavior, including older export formats and solver controls.
