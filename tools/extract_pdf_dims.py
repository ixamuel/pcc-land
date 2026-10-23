#!/usr/bin/env python3
"""Extract candidate terminal dimensions from the Panasonic datasheet PDFs.

This is the *assistive* half of the pipeline. The drawings are vector artwork
with rotated labels, so a fully automatic read is not trustworthy enough to be
the single source of truth. The script therefore:

  1. finds every "Dimensions in mm (not to scale)" page,
  2. splits each page into the per-type drawing tiles,
  3. classifies the dimension labels of a tile into P2 / W1 / W2 / L / H,
  4. cross-checks P2 against the body length in the workbook,
  5. writes data/pdf_dim_candidates.csv and diffs it against the curated
     data/terminal_dims.csv, so a human reviews only the differences.

Accepted values are copied into data/terminal_dims.csv by hand (or with
--apply --only-suffix, for high confidence rows).

Usage
  .venv/bin/python tools/extract_pdf_dims.py
  .venv/bin/python tools/extract_pdf_dims.py --diff-only
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASHEET_DIRS = [ROOT / "datasheet", ROOT]
OUT_CSV = ROOT / "data" / "pdf_dim_candidates.csv"
CURATED_CSV = ROOT / "data" / "terminal_dims.csv"
OVERRIDES_CSV = ROOT / "data" / "pn_overrides.csv"

sys.path.insert(0, str(ROOT / "tools"))
from build_catalog import load_parts  # noqa: E402

TOL_RE = re.compile(r"^\(?(\d+(?:[.,]\d+)?)\)?\s*(?:±|\+-)\s*(\d+(?:[.,]\d+)?)$")
MAX_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*max\.?$", re.I)
MIN_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*min\.?$", re.I)
SUFFIX_RE = re.compile(r"□□□\s*([A-Z]{3})((?:\s*/\s*[A-Z]{3}(?![A-Z0-9]))*)")
CAPTION_RE = re.compile(r"^PCC-[A-Z0-9]+(?:-[A-Z]{1,3})?\s*type$", re.I)
ALIAS_RE = re.compile(r"[A-Z]{3}")
DIM_PAGE_MARKER = "Dimensions in mm"
PLAIN_RE = re.compile(r"^\(?(\d+(?:[.,]\d+)?)\)?$")

# Estimated horizontal offset from a caption to the centre of its drawing.
TILE_CENTRE_OFFSET = 76

# A drawing tile starts about this far left of its caption, is roughly this
# wide, and the next tile starts a little before the next caption.
TILE_LEFT_PAD = 130
TILE_WIDTH = 210
# Captions that belong to the same drawing row are at most this far apart in y.
ROW_BAND = 25
# Captions closer than this to the previous caption sit on the same row.
NEXT_ROW_GAP = 60
# Labels may sit slightly above their caption line.
CAPTION_TOP_MARGIN = 30


def num(text):
    return float(text.replace(",", "."))


def suffixes_in(text):
    """'...□□□YFC/YGC)' -> ['YFC', 'YGC'], order preserved, duplicates removed."""
    found = []
    for match in SUFFIX_RE.finditer(text):
        for suffix in [match.group(1)] + ALIAS_RE.findall(match.group(2)):
            if suffix not in found:
                found.append(suffix)
    return found


def page_lines(page):
    """Every text line with its own bounding box (spans merged)."""
    lines = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                lines.append({"bbox": tuple(line["bbox"]), "text": text})
    return lines


def line_tokens(lines):
    """Return (value, tolerance, bbox, raw, kind) for every dimension label."""
    tokens = []
    for line in lines:
        raw = line["text"]
        match = TOL_RE.match(raw.replace(" ", ""))
        if match:
            tokens.append({"value": num(match.group(1)), "tol": num(match.group(2)),
                           "bbox": line["bbox"], "raw": raw, "kind": "tol"})
            continue
        match = MAX_RE.match(raw)
        if match:
            tokens.append({"value": num(match.group(1)), "tol": None,
                           "bbox": line["bbox"], "raw": raw, "kind": "max"})
            continue
        match = MIN_RE.match(raw)
        if match:
            tokens.append({"value": num(match.group(1)), "tol": None,
                           "bbox": line["bbox"], "raw": raw, "kind": "min"})
            continue
        match = PLAIN_RE.match(raw.replace(" ", ""))
        if match:
            tokens.append({"value": num(match.group(1)), "tol": None,
                           "bbox": line["bbox"], "raw": raw, "kind": "plain"})
    return tokens


def page_tiles(page):
    """Split a dimensions page into drawing tiles.

    Each "PCC-... type" caption owns the dimension labels that sit between the
    caption and the next drawing row, inside the caption's column.
    """
    lines = page_lines(page)
    tokens = line_tokens(lines)
    captions = [line for line in lines if CAPTION_RE.match(line["text"])]
    suffix_lines = [line for line in lines if SUFFIX_RE.search(line["text"])]
    if not captions:
        return []

    caption_ys = sorted({line["bbox"][1] for line in captions})
    tiles = []
    for caption in captions:
        cx, cy = caption["bbox"][0], caption["bbox"][1]

        row_xs = sorted({round(line["bbox"][0])
                         for line in captions if abs(line["bbox"][1] - cy) <= ROW_BAND})
        column = min(range(len(row_xs)), key=lambda index: abs(row_xs[index] - cx))
        x_start = row_xs[column - 1] + TILE_WIDTH if column > 0 else row_xs[0] - TILE_LEFT_PAD
        x_end = row_xs[column] + TILE_WIDTH if column + 1 < len(row_xs) else page.rect.width
        y_end = min((y for y in caption_ys if y > cy + NEXT_ROW_GAP), default=page.rect.height)

        tile_tokens = [token for token in tokens
                       if x_start <= token["bbox"][0] < x_end and cy - CAPTION_TOP_MARGIN <= token["bbox"][1] < y_end]
        if not tile_tokens:
            continue

        suffixes = []
        for line in suffix_lines:
            if -5 <= line["bbox"][1] - cy <= NEXT_ROW_GAP and abs(line["bbox"][0] - cx) <= 45:
                suffixes = suffixes_in(line["text"])
                break
        if not suffixes:
            for line in suffix_lines:
                if -5 <= line["bbox"][1] - cy <= NEXT_ROW_GAP:
                    suffixes = suffixes_in(line["text"])
                    break
        if not suffixes:
            continue

        tiles.append({"suffixes": suffixes, "type": caption["text"].replace(" type", ""),
                      "centre": cx + TILE_CENTRE_OFFSET, "tokens": tile_tokens})
    return tiles


def classify(tile, body_l):
    """Turn one tile's tokens into P2 / W1 / W2 / L / H with a confidence score.

    Where several labels could be the same dimension, the one nearest the
    drawing centre wins; a value matching the workbook body length wins for P2.
    """
    def distance(token):
        return abs((token["bbox"][0] + token["bbox"][2]) / 2 - tile["centre"])

    tol_values = [token for token in tile["tokens"] if token["kind"] == "tol"]
    plain_values = [token for token in tile["tokens"] if token["kind"] == "plain"]
    spans = [token for token in tol_values if token["tol"] in (0.4, 0.5, 0.6) and token["value"] > 2]

    p2 = None
    if spans:
        if body_l:
            p2 = min(spans, key=lambda token: (abs(token["value"] - body_l) > 0.15, token["bbox"][1]))
        else:
            # The outside span is always dimensioned above the body length.
            p2 = min(spans, key=lambda token: token["bbox"][1])

    half = p2["value"] / 2 - 0.05 if p2 else 99
    widths = [token for token in tol_values
              if token is not p2 and token["tol"] in (0.4, 0.5) and token["value"] <= half]
    if not widths:
        widths = [token for token in plain_values if 0.3 < token["value"] <= half]
    w1 = w2 = min(widths, key=distance)["value"] if widths else None

    lengths = [token for token in tol_values
               if token not in widths and token is not p2 and token["tol"] in (0.15, 0.16, 0.2, 0.3)]
    length = min(lengths, key=distance)["value"] if lengths else None

    heights = [token["value"] for token in tile["tokens"] if token["kind"] == "max"]

    if p2 and body_l and abs(p2["value"] - body_l) <= 0.15 and w1 and length:
        confidence = "high"
    elif p2 and (w1 or length):
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "suffix": tile["suffixes"],
        "p2": p2["value"] if p2 else None,
        "w1": w1,
        "w2": w2,
        "l": length,
        "h_max": max(heights) if heights else None,
        "confidence": confidence,
        "pcb_type": tile["type"],
        "tokens": " ; ".join(token["raw"] for token in tile["tokens"]),
    }


def datasheets():
    """All datasheets, folder first, identical copies skipped."""
    hashes, found = set(), []
    for folder in DATASHEET_DIRS:
        if not folder.is_dir():
            continue
        for pdf in sorted(folder.glob("*.pdf")):
            digest = hashlib.sha1(pdf.read_bytes()).hexdigest()
            if digest in hashes:
                print(f"  skip duplicate {pdf.relative_to(ROOT)}")
                continue
            hashes.add(digest)
            found.append(pdf)
    return found


def mf_table_rows(page, body_l):
    """Large-current series: terminal given as A (width) / B / C (storage) table.

    Rows start with a bare part number; A sits ~55-120 px and C ~155-240 px to
    its right. The terminal width changes with the inductance, so these rows are
    reported per part number, not per suffix. P2 is the span that matches the
    body length of the family drawing above the table.
    """
    lines = page_lines(page)
    tokens = line_tokens(lines)
    part_lines = [line for line in lines if re.fullmatch(r"ETQP[A-Z0-9]+", line["text"])]
    if not part_lines:
        return []

    table_top = min(line["bbox"][1] for line in part_lines)
    spans = [token for token in tokens
             if token["kind"] == "tol" and token["tol"] in (0.4, 0.5, 0.6)
             and token["value"] > 2 and token["bbox"][1] < table_top]

    def pick(part_line, low, high):
        for line in lines:
            if abs(line["bbox"][1] - part_line["bbox"][1]) > 4:
                continue
            offset = line["bbox"][0] - part_line["bbox"][0]
            if low <= offset <= high:
                match = TOL_RE.match(line["text"].replace(" ", ""))
                if match:
                    return num(match.group(1))
        return None

    rows = []
    for part in part_lines:
        width = pick(part, 55, 120)
        storage = pick(part, 155, 240)
        if width is None or storage is None:
            continue
        pn = part["text"]
        suffix = pn[-3:]
        wanted = body_l.get(suffix)
        if wanted:
            p2 = min(spans, key=lambda token: abs(token["value"] - wanted)) if spans else None
        else:
            column = [span for span in spans
                      if part["bbox"][0] - 120 <= span["bbox"][0] <= part["bbox"][0] + 220]
            p2 = min(column, key=lambda token: token["bbox"][1]) if column else None
        rows.append({
            "pn": pn,
            "suffix": suffix,
            "p2": p2["value"] if p2 else None,
            "w1": width,
            "w2": width,
            "l": storage,
            "h_max": None,
            "confidence": "medium",
            "pcb_type": "",
            "tokens": f"A {width} ; C {storage} ; P2 {p2['raw'] if p2 else '-'}",
            "aliases": suffix,
        })
    return rows


def extract():
    try:
        import fitz
    except ImportError:  # pragma: no cover - guided failure
        sys.exit("PyMuPDF is required:  .venv/bin/pip install pymupdf")

    body_l = {}
    for part in load_parts():
        body_l.setdefault(part["suffix"], part["body_l"])

    rows = {}
    pn_rows = {}
    for pdf in datasheets():
        document = fitz.open(pdf)
        for page_number, page in enumerate(document, start=1):
            if DIM_PAGE_MARKER not in page.get_text():
                continue
            for tile in page_tiles(page):
                primary = tile["suffixes"][0]
                row = classify(tile, body_l.get(primary))
                row["source"] = f"{pdf.name} p{page_number}"
                row["suffix"] = primary
                row["aliases"] = "/".join(tile["suffixes"])
                # Keep the highest confidence hit per suffix; drawings shared by
                # several suffixes are recorded once under each of them.
                rank = {"high": 3, "medium": 2, "low": 1}
                for suffix in tile["suffixes"]:
                    if suffix not in rows or rank[row["confidence"]] > rank[rows[suffix]["confidence"]]:
                        rows[suffix] = dict(row, suffix=suffix)

            for row in mf_table_rows(page, body_l):
                row["source"] = f"{pdf.name} p{page_number}"
                rank = {"high": 3, "medium": 2, "low": 1}
                key = row["pn"]
                if key not in pn_rows or rank[row["confidence"]] > rank[pn_rows[key]["confidence"]]:
                    pn_rows[key] = row
    return rows, pn_rows


def load_curated(path=CURATED_CSV, key="suffix"):
    curated = {}
    if not path.exists():
        return curated
    with path.open(newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(row for row in handle if not row.lstrip().startswith("#")):
            key_value = (record.get(key) or "").strip().upper()
            if key_value:
                curated[key_value] = record
    return curated


def write_csv(rows, pn_rows):
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = ["pn", "suffix", "p2", "w1", "w2", "l", "h_max", "confidence",
              "pcb_type", "source", "aliases", "tokens"]
    combined = [dict(row, pn="") for row in rows.values()] + list(pn_rows.values())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in combined:
            writer.writerow(row)
    print(f"Wrote {OUT_CSV.relative_to(ROOT)} ({len(rows)} suffixes, {len(pn_rows)} part numbers)")


def diff(rows, curated, pn_rows, overrides):
    print("\nsuffix  extracted                          curated                              verdict")
    print("-" * 108)
    for key in sorted(set(rows) | set(curated)):
        found = rows.get(key)
        known = curated.get(key)
        got = "-" if not found else f"P2 {fmt(found['p2'])} W {fmt(found['w1'])} L {fmt(found['l'])}"
        want = "-" if not known else (f"P2 {known['p2']} W {known['w1']} L {known['l']}"
                                      if known.get("p2") else f"manual ({known.get('status')})")
        if not found:
            verdict = "PDF-only" if not known else "curated only"
        elif not known:
            verdict = "NEW - needs review"
        elif same(found, known):
            verdict = "match"
        else:
            verdict = "DIFF - review"
        print(f"{key:<7} {got:<34} {want:<36} {verdict}")

    if not pn_rows:
        return
    print("\npart number        extracted                          overrides                            verdict")
    print("-" * 108)
    for key in sorted(set(pn_rows) | set(overrides)):
        found = pn_rows.get(key)
        known = overrides.get(key)
        got = "-" if not found else f"P2 {fmt(found['p2'])} W {fmt(found['w1'])} L {fmt(found['l'])}"
        want = "-" if not known else f"P2 {known.get('p2')} W {known.get('w1')} L {known.get('l')}"
        if not found:
            verdict = "override only"
        elif not known:
            verdict = "NEW - needs review"
        elif same(found, known):
            verdict = "match"
        else:
            verdict = "DIFF - review"
        print(f"{key:<18} {got:<34} {want:<36} {verdict}")


def fmt(value):
    return "-" if value is None else f"{value:g}"


def same(found, known):
    for source, target in (("p2", "p2"), ("w1", "w1"), ("w2", "w2"), ("l", "l")):
        if found[source] is None or not known.get(target):
            return False
        if abs(found[source] - float(known[target])) > 0.02:
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--diff-only", action="store_true", help="compare without rewriting the candidate CSV")
    args = parser.parse_args()

    rows, pn_rows = extract()
    if not args.diff_only:
        write_csv(rows, pn_rows)
    diff(rows, load_curated(), pn_rows, load_curated(OVERRIDES_CSV, "pn"))


if __name__ == "__main__":
    main()
