# Historical notes (before the October 2026 redesign)


These notes describe earlier iterations and include superseded behavior. See the [current README](../readme.md) for the current interface, exports, and workflow.

# Land Pattern Overlay Generator: Project History and Handover

## 1. Project objective

The goal was to create a standalone HTML tool that compares a competitor's recommended PCB land pattern with a Panasonic solder terminal.

The generator allows a user to enter:

- Competitor name
- Competitor part number
- Panasonic part number
- Competitor dimensions: `L`, `P1`, `P2`, `W1`, and `W2`
- Panasonic dimensions: `L`, `P1`, `P2`, `W1`, and `W2`

The tool then creates a live, dimensionally scaled overlay with labels, arrows, a comparison table, validation messages, and export options.

## 2. Source example

The initial comparison used the following values.

### Competitor: Bourns recommended land pattern

| Dimension | Value |
|---|---:|
| L | 3.40 |
| P1 | 2.70 |
| P2 | 8.40 |
| W1 | 2.85 |
| W2 | 2.85 |

### Panasonic: ETQP4M4R7KVN solder terminal

| Dimension | Value |
|---|---:|
| L | 3.18 |
| P1 | 4.32 |
| P2 | 6.40 |
| W1 | 1.04 |
| W2 | 1.04 |

All dimensions are in millimetres.

## 3. Dimension interpretation

The generator uses the following geometry:

- `L`: vertical length of each pad or terminal
- `P1`: horizontal inner gap between the left and right pads
- `P2`: total horizontal outside span
- `W1`: width of the left pad or terminal
- `W2`: width of the right pad or terminal

The expected dimensional relationship is:

```text
W1 + P1 + W2 = P2
```

Both the competitor and Panasonic geometries are centred on the same horizontal origin to make the overlay easy to compare.

## 4. Visual conventions

The final color convention is:

- **Competitor land pattern:** red
- **Panasonic solder terminal:** blue
- **General headings and neutral text:** black or dark grey

The central dotted reference line from the early concept was intentionally removed.

The diagram still uses dashed extension lines where needed to connect dimension arrows to the relevant geometry. These are dimension guides, not a centre line.

## 5. Development history

### Stage 1: Initial overlay image

A first engineering-style image was created with:

- Competitor land pattern
- Panasonic terminal overlay
- `L`, `P1`, `P2`, `W1`, and `W2` arrows
- A legend and dimension values

The first color assignment was then corrected so Panasonic became blue and the competitor became red.

### Stage 2: Standalone HTML generator

The static image concept was converted into a standalone HTML generator.

The first generator included:

- Editable text and dimension fields
- Live SVG preview
- Automatic scaling based on entered values
- PNG export
- SVG export
- Print or PDF support
- No external libraries or server requirements

The HTML file can be opened locally in a modern browser such as Microsoft Edge or Google Chrome.

### Stage 3: Compact dimension entry

The entry layout was changed from separate stacked fields to a compact row.

For each product, the headings appear in one line:

```text
L    P1    P2    W1    W2
```

The editable values appear directly beneath the headings.

### Stage 4: Comparison table in the live preview

A two-row comparison table was added to the exported and live SVG.

The table contains:

- A `Part number` column
- `L`, `P1`, `P2`, `W1`, and `W2` columns
- A red competitor row
- A blue Panasonic row

The Panasonic row wording was standardized as:

```text
Panasonic ETQP4M4R7KVN terminal
```

The table heading was simplified from `Title / Part number` to `Part number`.

### Stage 5: Preview overlap correction

The table initially overlapped the drawing. The layout was corrected by:

- Giving the table a dedicated area at the top
- Moving the overlay diagram lower
- Adding a visual divider between the table and diagram
- Increasing the SVG canvas height
- Repositioning the bottom dimension arrows and comment
- Updating the PNG export aspect ratio

### Stage 6: Cleaner unit presentation

The repeated `mm` suffix was removed from individual table cells and diagram labels.

Instead, the preview shows one clear statement:

```text
All dimensions are in mm
```

The input panel also retains the label `Dimensions (mm)`.

### Stage 7: Dimension validation

The generator checks the following relationship independently for both products:

```text
W1 + P1 + W2 = P2
```

A tolerance of `0.03 mm` is used to avoid warnings caused by small rounding differences.

If there is a mismatch, a compact red card appears above the live preview.

For one error, the card displays the relevant product only.

For both errors, the card displays one line in this format:

```text
Dimension Mismatch: Competitor: W1 + P1 + W2 does not equal P2 | Panasonic: W1 + P1 + W2 does not equal P2
```

The card:

- Is approximately half the height of the earlier alert
- Uses compact padding and text
- Remains on one line
- Uses horizontal scrolling on narrow screens rather than wrapping
- Disappears automatically when the dimensions are valid

### Stage 8: Panasonic part-number auto-resolve

The Panasonic side no longer starts with hard-coded numbers. A searchable
part-number list (all 150 catalogue parts from `Inductor all data.xlsx`) feeds
`L`, `P2`, `W1` and `W2` from the datasheet that covers the part's three-letter
suffix (`ETQP4M3R3KFN` → `KFN` → `AGL0000C73-LE.pdf` page 6).

- Grey advice text is shown before anything is entered.
- Selecting a part number from the list (or pressing Enter on a typed one)
  resolves it immediately; `Auto resolve` re-applies the values at any time.
- Typing just the suffix (`KFN`) resolves the shared terminal geometry.
- A provenance chip names the drawing, or an amber note explains that no
  drawing is on file and asks for the dimensions to be typed.

Data pipeline and maintenance: see `docs/data-pipeline.md`. Datasheets live in
`datasheet/`, curated values in `data/terminal_dims.csv` (per suffix) and
`data/pn_overrides.csv` (per part number, used where the terminal depends on the
inductance itself, e.g. the large-current `JFA`/`JFW` family).
Build commands:

```bash
.venv/bin/python tools/extract_pdf_dims.py   # PDF -> candidates + diff report
.venv/bin/python tools/build_catalog.py      # xlsx + CSV -> catalog.json + index.html
```

### Stage 9: Dimension solver

There is no mode switch. The three groups `W1 + W2`, `P1` and `P2` are watched,
and as soon as two of them hold a value the third is calculated and badged
`solved` above its input, with the formula shown underneath:

| Known | Calculated |
|---|---|
| `W1 + W2`, `P2` | `P1 = P2 − W1 − W2` |
| `W1 + W2`, `P1` | `P2 = W1 + P1 + W2` |
| `P1`, `P2` | `W1 = W2 = (P2 − P1) / 2` |

Typing into the solved field hands the calculation over to another field, so the
`solved` badge moves and `W1 + P1 + W2 = P2` can never drift.

Both rows carry this solver. Each has its own `Auto resolve` and `Clear`:

- Panasonic: `Auto resolve` re-applies the datasheet values for the part number.
- Competitor: `Auto resolve` fills the missing value and reports the result
  (`Solved P1 = 2.70 …` or `Consistent — W1 + P1 + W2 = P2 = 8.40 mm.`).
- `Clear` empties that row's `L`, `P1`, `P2`, `W1`, `W2` (and the part number).

The calculated box is read-only, tinted blue, and tagged `CALC`, so the
`W1 + P1 + W2 = P2` relationship can never drift on the Panasonic side.

### Stage 10: Live preview revamp

The preview card became self-contained:

- Header bar with a live indicator, zoom controls (`−` / `Fit` / `+`, 100–300 %)
  and the `PNG`, `SVG` and `Print` actions, which moved out of the form.
- Canvas tightened to 1200 × 860 (the old sheet had a dead band at the bottom);
  exports follow the new box (SVG 1200 × 860, PNG 2400 × 1720).
- Document header as a single title line — *Recommended Land Pattern* **vs.**
  *ETQP4M100KFN Solder Terminal Overlay* — with the unit note on the right and
  automatic font shrinking for long titles.
- Comparison table redrawn as a rounded card with muted uppercase headers,
  colour dots, hairline rows and tabular figures.
- Dimension arrows and labels made thinner and smaller, extension lines at 50 %
  opacity, and a dashed empty state before any values are entered.
- The comment moved to a muted `COMMENT` block at the foot of the sheet.

## 6. Final generator features

The final HTML generator provides:

- Competitor name entry
- Competitor part-number entry
- Panasonic part-number entry
- One-row dimension entry for each product
- Live SVG overlay
- Dimensionally scaled geometry
- Red competitor styling
- Blue Panasonic styling
- Comparison table in the preview
- A single, clear millimetre note
- No dotted centre line
- Automatic dimensional consistency validation
- Compact one-line red mismatch card
- Searchable Panasonic part-number list with datasheet auto-resolve
- Automatic solver that calculates whichever of `P1`, `P2` or `W1 = W2` is missing
- One-word subtitle under every dimension: *height · gap · total · left · right*
- Provenance chip / amber fallback note for every resolved part number
- PNG export
- SVG export
- Print or PDF support
- Responsive browser layout
- Fully local operation

## 7. Current final file

The current generator file is:

```text
land_pattern_overlay_generator_compact_alert.html
```

The supporting project-history file is:

```text
land_pattern_overlay_generator_history.md
```

## 8. How to use the generator

1. Open the HTML file in Microsoft Edge or Google Chrome.
2. Enter the competitor name and optional competitor part number.
3. Enter the Panasonic part number.
4. Enter `L`, `P1`, `P2`, `W1`, and `W2` for both products.
5. Check the live preview and comparison table.
6. If a red mismatch card appears, verify whether `W1 + P1 + W2` equals `P2`.
7. Select one of the output options:
   - **Export PNG** for a high-resolution raster image
   - **Export SVG** for a scalable vector file
   - **Print / PDF** for browser-based printing or PDF creation

## 9. Technical implementation summary

The generator is implemented as one self-contained HTML file using:

- HTML for the input interface
- CSS for layout, colors, responsiveness, and the validation card
- JavaScript for live updates, validation, geometry, and exports
- Inline SVG for the diagram and comparison table
- Browser Canvas for PNG generation

No external JavaScript packages, fonts, APIs, or network connection are required.

## 10. Important maintenance notes

When modifying the generator, preserve these requirements:

1. Panasonic must remain blue.
2. The competitor must remain red.
3. The centre dotted line must not be restored.
4. Units should be stated once rather than repeated after every value.
5. The comparison table must remain separate from the overlay drawing.
6. The Panasonic table label should use the order `Panasonic [part number] terminal`.
7. The validation message should remain a compact one-line red card.
8. PNG and SVG exports should reflect the same content shown in the live preview.
9. The dimensional relationship must continue to be checked with a small rounding tolerance.

## 11. Possible future enhancements

Potential improvements could include:

- Saving and loading product presets
- Importing dimension rows from CSV
- Adding a user-selectable dimensional tolerance
- Adding optional company logos
- Supporting additional pad geometries
- Exporting a structured comparison report
- Allowing custom colors while retaining the Panasonic and competitor defaults
- Adding a reset button and example presets
