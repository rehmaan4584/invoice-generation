import io
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
import pymupdf as fitz
from PIL import Image
from config import DATA_DIR


def get_pdf_document(pdf_input: Union[str, Path, bytes]) -> fitz.Document:
    """Loads a PyMuPDF document from file path or bytes."""
    if isinstance(pdf_input, (str, Path)):
        return fitz.open(str(pdf_input))
    if isinstance(pdf_input, bytes):
        return fitz.open(stream=pdf_input, filetype="pdf")
    raise ValueError(f"Unsupported PDF input type: {type(pdf_input)}")


def get_pdf_page_count(pdf_input: Union[str, Path, bytes]) -> int:
    """Returns the total number of pages in the PDF."""
    doc = get_pdf_document(pdf_input)
    count = len(doc)
    doc.close()
    return count


def render_pdf_page_image(
    pdf_input: Union[str, Path, bytes],
    page_number: int = 0,
    dpi: int = 150
) -> Tuple[Image.Image, float, float]:
    """
    Renders a specific page of the PDF into a high-resolution PIL Image.
    Returns: (PIL.Image, page_width_pts, page_height_pts)
    """
    doc = get_pdf_document(pdf_input)
    if page_number < 0 or page_number >= len(doc):
        page_number = 0

    page = doc[page_number]
    rect = page.rect
    width, height = rect.width, rect.height

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()
    return img, width, height


FONTS_DIR = Path(__file__).resolve().parent / "fonts"
CARLITO_REG = FONTS_DIR / "Carlito-Regular.ttf"
CARLITO_BOLD = FONTS_DIR / "Carlito-Bold.ttf"


def map_pdf_font_to_standard(raw_font_name: str, flags: int) -> str:
    """Maps extracted PDF font names to precise fonts (including Carlito/Calibri and standard 14)."""
    name = (raw_font_name or "").lower()
    # PyMuPDF font flags bitmask: bit 4 (16) = bold, bit 5 (32) = italic (bit 1 is subscript)
    is_bold = "bold" in name or "heavy" in name or "black" in name or bool(flags & 16)
    is_italic = "italic" in name or "oblique" in name or "slanted" in name or bool(flags & 32)

    if "carlito" in name or "calibri" in name:
        if is_bold and is_italic:
            return "carlito-bolditalic"
        if is_bold:
            return "carlito-bold"
        if is_italic:
            return "carlito-italic"
        return "carlito"
    elif "times" in name or "serif" in name or "roman" in name:
        if is_bold and is_italic:
            return "tibi"
        if is_bold:
            return "tibo"
        if is_italic:
            return "tiit"
        return "tiro"
    elif "courier" in name or "mono" in name:
        if is_bold and is_italic:
            return "cobi"
        if is_bold:
            return "cobo"
        if is_italic:
            return "coit"
        return "cour"
    else:
        # Helvetica / Arial standard
        if is_bold and is_italic:
            return "hebi"
        if is_bold:
            return "hebo"
        if is_italic:
            return "heit"
        return "helv"


def int_color_to_rgb(color_int: int) -> Tuple[float, float, float]:
    """Converts 24-bit sRGB integer from PDF span to (R, G, B) float tuple."""
    if not color_int or color_int == 0:
        return (0.0, 0.0, 0.0)
    r = ((color_int >> 16) & 255) / 255.0
    g = ((color_int >> 8) & 255) / 255.0
    b = (color_int & 255) / 255.0
    return (round(r, 2), round(g, 2), round(b, 2))


def extract_page_text_blocks(
    pdf_input: Union[str, Path, bytes],
    page_number: int = 0
) -> List[Dict[str, Any]]:
    """
    Extracts individual text lines from the page with exact coordinates,
    locked font sizes, and locked font families.
    Accurately identifies bold weights from alphanumeric content spans.
    """
    doc = get_pdf_document(pdf_input)
    if page_number < 0 or page_number >= len(doc):
        doc.close()
        return []

    page = doc[page_number]
    page_dict = page.get_text("dict")
    doc.close()

    elements = []
    line_counter = 0

    for b in page_dict.get("blocks", []):
        if "lines" in b:
            for line in b["lines"]:
                # Combine spans in this line
                line_text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                if line_text:
                    bbox = line.get("bbox", [0, 0, 0, 0])
                    spans = line.get("spans", [])
                    
                    # Identify primary content span (prefer span with alphanumeric characters)
                    primary_span = spans[0] if spans else {}
                    for sp in spans:
                        t = sp.get("text", "").strip()
                        if any(c.isalnum() for c in t):
                            primary_span = sp
                            if bool(sp.get("flags", 0) & 16) or "bold" in sp.get("font", "").lower():
                                primary_span = sp
                                break

                    raw_font = primary_span.get("font", "Helvetica") if primary_span else "Helvetica"
                    flags = primary_span.get("flags", 0) if primary_span else 0
                    color_int = primary_span.get("color", 0) if primary_span else 0
                    font_size = primary_span.get("size", 10.0) if primary_span else 10.0
                    font_size = max(6.0, min(48.0, round(font_size, 1)))

                    locked_font_name = map_pdf_font_to_standard(raw_font, flags)
                    locked_color = int_color_to_rgb(color_int)

                    # Exact baseline y from origin if present
                    if primary_span and "origin" in primary_span:
                        origin_y = round(primary_span["origin"][1], 2)
                    elif spans and "origin" in spans[0]:
                        origin_y = round(spans[0]["origin"][1], 2)
                    else:
                        origin_y = round(bbox[1] + font_size * 0.85, 2)

                    # Human-friendly font label for UI display
                    if "bolditalic" in locked_font_name or locked_font_name.endswith("bi"):
                        style_label = "Bold Italic"
                    elif "bold" in locked_font_name or locked_font_name.endswith("bo") or locked_font_name == "hebo":
                        style_label = "Bold"
                    elif "italic" in locked_font_name or locked_font_name.endswith("it") or locked_font_name == "heit":
                        style_label = "Italic"
                    else:
                        style_label = "Regular"

                    if "carlito" in locked_font_name:
                        family_label = "Carlito"
                    elif "ti" in locked_font_name:
                        family_label = "Times"
                    elif "co" in locked_font_name:
                        family_label = "Courier"
                    else:
                        family_label = "Helvetica"

                    elements.append({
                        "id": f"line_{line_counter}",
                        "text": line_text,
                        "x0": round(bbox[0], 1),
                        "y0": round(bbox[1], 1),
                        "x1": round(bbox[2], 1),
                        "y1": round(bbox[3], 1),
                        "font_size": font_size,
                        "font_name": locked_font_name,
                        "font_color": locked_color,
                        "baseline_y": origin_y,
                        "font_display": f"{family_label} {style_label}, {font_size}pt"
                    })
                    line_counter += 1

    return elements


def apply_edits_and_export(
    source_pdf: Union[str, Path, bytes],
    edits: List[Dict[str, Any]],
    output_path: Union[str, Path]
) -> Path:
    """
    Applies in-place edits cleanly:
    - For digital text replacements: clean redaction with graphics=0, fill=None to preserve
      100% of vector lines, table borders, and underlines without any white box artifacts.
    - For manual stamps/whiteouts: paints opaque background box for scanned images.
    - Inserts text at exact subpixel baseline.
    """
    doc = get_pdf_document(source_pdf)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Group edits by page
    edits_by_page: Dict[int, List[Dict[str, Any]]] = {}
    for edit in edits:
        p = edit.get("page", 0)
        edits_by_page.setdefault(p, []).append(edit)

    for p_idx, p_edits in edits_by_page.items():
        if p_idx < 0 or p_idx >= len(doc):
            continue
        page = doc[p_idx]

        # Step 1: Cleanly wipe and redact old text from all edit rectangles on this page
        for ed in p_edits:
            orig_rect = fitz.Rect(ed["rect"])
            edit_type = ed.get("type", "replace")
            # Mask the original text area cleanly
            page.draw_rect(orig_rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
            try:
                page.add_redact_annot(orig_rect, fill=(1, 1, 1))
            except Exception:
                pass

        try:
            page.apply_redactions(images=0, graphics=0)
        except Exception:
            pass

        # Step 2: Register unique embedded fonts AFTER apply_redactions to guarantee clean CMap encoding
        fn_reg = f"F_edit_reg_{p_idx}_{int(time.time() * 1000) % 100000}"
        fn_bold = f"F_edit_bold_{p_idx}_{int(time.time() * 1000) % 100000}"
        has_carlito = CARLITO_REG.exists() and CARLITO_BOLD.exists()
        if has_carlito:
            page.insert_font(fontname=fn_reg, fontfile=str(CARLITO_REG))
            page.insert_font(fontname=fn_bold, fontfile=str(CARLITO_BOLD))

        # Step 3: Insert newly edited text cleanly at exact subpixel baseline
        for ed in p_edits:
            orig_rect = fitz.Rect(ed["rect"])
            new_text = str(ed.get("new_text", "")).strip()
            font_size = float(ed.get("font_size", 10.0))
            if font_size <= 0:
                font_size = 10.0
            edit_type = ed.get("type", "replace")

            if new_text and edit_type != "whiteout":
                lines = new_text.splitlines() if "\n" in new_text else [new_text]
                line_spacing = max(font_size * 1.2, 12.0)
                font_name = str(ed.get("font_name", "helv")).lower()
                font_color = ed.get("font_color", (0.05, 0.05, 0.05))
                is_bold_font = "bold" in font_name or "bo" in font_name or "hebo" in font_name

                base_y = float(ed.get("baseline_y") or (orig_rect.y0 + (font_size * 0.85)))
                for i, line in enumerate(lines):
                    current_y = base_y + (i * line_spacing)

                    # Subpixel horizontal alignment:
                    # For numeric amounts/values in table cells, center around the original text bounding box center
                    is_numeric_val = any(c.isdigit() for c in line) and not any(c.isalpha() for c in line)
                    if is_numeric_val and orig_rect.width > 0:
                        try:
                            measure_font = fitz.Font(fontfile=str(CARLITO_BOLD if is_bold_font else CARLITO_REG)) if has_carlito else fitz.Font(fontname="helv")
                            line_w = measure_font.text_length(line, fontsize=font_size)
                            orig_center_x = (orig_rect.x0 + orig_rect.x1) / 2.0
                            insert_x = round(orig_center_x - (line_w / 2.0), 2)
                        except Exception:
                            insert_x = orig_rect.x0
                    else:
                        insert_x = orig_rect.x0

                    if has_carlito:
                        use_fn = fn_bold if is_bold_font else fn_reg
                        page.insert_text(
                            (insert_x, current_y),
                            line,
                            fontsize=font_size,
                            fontname=use_fn,
                            color=font_color
                        )
                    else:
                        use_fn = "helv-bold" if is_bold_font else "helv"
                        page.insert_text(
                            (insert_x, current_y),
                            line,
                            fontsize=font_size,
                            fontname=use_fn,
                            color=font_color
                        )

    # Save modified PDF with compression
    doc.save(str(out_path), garbage=4, deflate=True)
    doc.close()
    return out_path


def detect_end_table_rows(
    pdf_input: Union[str, Path, bytes],
    page_number: int = 0
) -> List[Dict[str, Any]]:
    """
    Detects table item rows and identifies the exact last row and right border of tables.
    Returns robust metadata (including table right edge and all vertical gridlines) so that:
    1. The '+' button is always placed OUTSIDE the table on the right (never inside columns).
    2. Only ONE '+' button appears per table.
    3. All table columns and borders are fully extended without missing borders.
    """
    doc = get_pdf_document(pdf_input)
    if page_number < 0 or page_number >= len(doc):
        doc.close()
        return []

    page = doc[page_number]
    blocks = extract_page_text_blocks(pdf_input, page_number)
    drawings = page.get_drawings()
    doc.close()

    if not blocks:
        return []

    # Method 1: Detect tables with drawn gridlines (Borders & Column Lines)
    v_segs = []
    h_segs = []
    default_color = (0.74, 0.76, 0.78)
    default_lw = 0.5

    for d in drawings:
        r = d['rect']
        col = d.get('color') or (0.0, 0.0, 0.0)
        lw = d.get('width') or 0.5
        if r.width <= 2.5 and r.height >= 12:
            v_segs.append((r.x0, r.y0, r.y1, col, lw))
        elif r.height <= 2.5 and r.width >= 30:
            h_segs.append((r.y0, r.x0, r.x1, col, lw))

    v_xs = sorted(list(set(round(x, 1) for x, y0, y1, c, lw in v_segs)))
    end_rows: List[Dict[str, Any]] = []

    if len(v_xs) >= 3:
        min_x = min(v_xs)
        max_x = max(v_xs)
        y0_candidates = [y0 for x, y0, y1, c, lw in v_segs if min_x <= x <= max_x]
        y1_candidates = [y1 for x, y0, y1, c, lw in v_segs if min_x <= x <= max_x]

        if y0_candidates and y1_candidates:
            table_y0 = min(y0_candidates)
            table_y1 = max(y1_candidates)

            # Deduplicate and cluster horizontal lines (merging twin divider lines within 12.0 pt)
            raw_h_ys = sorted(list(set(round(y0, 1) for y0, x0, x1, c, lw in h_segs if table_y0 - 5 <= y0 <= table_y1 + 5)))
            table_h_lines = []
            for y in raw_h_ys:
                if not table_h_lines:
                    table_h_lines.append(y)
                elif y - table_h_lines[-1] >= 12.0:
                    table_h_lines.append(y)
                else:
                    # Merge twin border lines
                    table_h_lines[-1] = y

            if len(table_h_lines) >= 2:
                row_diffs = [round(table_h_lines[i] - table_h_lines[i - 1], 1) for i in range(1, len(table_h_lines))]
                valid_diffs = [d for d in row_diffs if d >= 18.0]
                if valid_diffs:
                    delta_y = row_diffs[-1] if row_diffs[-1] >= 18.0 else valid_diffs[-1]
                else:
                    delta_y = 28.0
            else:
                delta_y = 28.0
            delta_y = max(22.0, min(delta_y, 45.0))

            y_cut = table_y1
            last_row_blocks = [
                b for b in blocks
                if (table_y1 - delta_y - 10 <= b['y0'] <= table_y1 + 4) and (min_x - 10 <= b['x0'] <= max_x + 10)
            ]

            # If no blocks in immediate last row slot, grab blocks from row above table bottom
            if not last_row_blocks:
                last_row_blocks = [
                    b for b in blocks
                    if (table_y1 - 50 <= b['y0'] <= table_y1 + 4) and (min_x - 10 <= b['x0'] <= max_x + 10)
                ]

            # Get drawing color and line width
            table_color = default_color
            line_width = default_lw
            for x, y0, y1, col, lw in v_segs:
                if min_x <= x <= max_x:
                    table_color = col
                    line_width = lw
                    break

            end_rows.append({
                'x0': min_x,
                'x1': max_x,
                'y0': table_y0,
                'y1': table_y1,
                'btn_y': round(table_y1 - delta_y / 2, 1),
                'btn_y0': round(table_y1 - delta_y, 1),
                'y_cut': round(y_cut, 1),
                'delta_y': delta_y,
                'v_lines': [x for x in v_xs if min_x <= x <= max_x],
                'table_color': table_color,
                'line_width': line_width,
                'blocks': last_row_blocks
            })

    # Method 2: Fallback for borderless tables (using text clusters)
    if not end_rows:
        rows: List[Dict[str, Any]] = []
        for b in sorted(blocks, key=lambda x: (x['y0'], x['x0'])):
            placed = False
            for r in rows:
                if abs(r['y0'] - b['y0']) <= 6.0:
                    r['blocks'].append(b)
                    r['x0'] = min(r['x0'], b['x0'])
                    r['x1'] = max(r['x1'], b['x1'])
                    r['y1'] = max(r['y1'], b['y1'])
                    placed = True
                    break
            if not placed:
                rows.append({
                    'y0': b['y0'],
                    'y1': b['y1'],
                    'x0': b['x0'],
                    'x1': b['x1'],
                    'blocks': [b]
                })

        multi_col_rows = [r for r in rows if len(r['blocks']) >= 2]
        if multi_col_rows:
            clusters: List[List[Dict[str, Any]]] = []
            curr_c: List[Dict[str, Any]] = [multi_col_rows[0]]
            for r in multi_col_rows[1:]:
                gap = r['y0'] - curr_c[-1]['y0']
                if 5.0 <= gap <= 60.0:
                    curr_c.append(r)
                else:
                    if len(curr_c) >= 2:
                        clusters.append(curr_c)
                    curr_c = [r]
            if len(curr_c) >= 2:
                clusters.append(curr_c)

            if clusters:
                cluster = max(clusters, key=lambda c: len(c))
                last_r = cluster[-1]
                prev_r = cluster[-2]
                delta_y = round(max(last_r['y0'] - prev_r['y0'], 20.0), 1)
                tbl_x1 = max(b['x1'] for r in cluster for b in r['blocks'])
                tbl_x0 = min(b['x0'] for r in cluster for b in r['blocks'])

                end_rows.append({
                    'x0': round(tbl_x0, 1),
                    'x1': round(tbl_x1, 1),
                    'y0': round(cluster[0]['y0'], 1),
                    'y1': round(last_r['y1'], 1),
                    'btn_y': round((last_r['y0'] + last_r['y1']) / 2, 1),
                    'btn_y0': round(last_r['y0'], 1),
                    'y_cut': round(last_r['y1'] + 4.0, 1),
                    'delta_y': delta_y,
                    'v_lines': [],
                    'table_color': default_color,
                    'line_width': default_lw,
                    'blocks': last_r['blocks']
                })

    return end_rows


def duplicate_table_row_and_shift(
    source_pdf: Union[str, Path, bytes],
    page_number: int = 0,
    row_data: Optional[Dict[str, Any]] = None,
    output_path: Optional[Union[str, Path]] = None,
    *args,
    **kwargs
) -> Path:
    """
    Clones the target row directly below the table:
    - Shifts all content below y_cut downward by delta_y via lossless vector slicing.
    - Inserts cloned row cells in the gap [y_cut, y_cut + delta_y] matching original fonts & text.
    - Extends all vertical column dividers and draws horizontal line across full table width.
    - Resilient signature accepting row_data dictionary or unpacked kwargs.
    """
    if row_data is None:
        if args and isinstance(args[0], dict):
            row_data = args[0]
            if len(args) > 1 and output_path is None:
                output_path = args[1]
        elif 'row_data' in kwargs:
            row_data = kwargs.pop('row_data')
        else:
            row_data = kwargs

    if output_path is None:
        if args and len(args) >= 2 and not isinstance(args[0], dict):
            output_path = args[1]
        elif 'output_path' in kwargs:
            output_path = kwargs['output_path']
        else:
            output_path = DATA_DIR / f"temp_shifted_{int(time.time() * 1000)}.pdf"

    doc = get_pdf_document(source_pdf)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    new_doc = fitz.open()

    y_cut = float(row_data.get('y_cut', 300.0))
    delta_y = float(row_data.get('delta_y', 22.0))
    v_lines = row_data.get('v_lines', [])
    table_color = row_data.get('table_color', (0.74, 0.76, 0.78))
    line_width = float(row_data.get('line_width', 0.5))
    row_blocks = row_data.get('blocks', [])

    for pno in range(len(doc)):
        if pno != page_number:
            new_doc.insert_pdf(doc, from_page=pno, to_page=pno)
            continue

        page = doc[pno]
        w, h = page.rect.width, page.rect.height
        new_page = new_doc.new_page(width=w, height=h)

        # 1. Top Slice (0 to y_cut) unchanged
        new_page.show_pdf_page(fitz.Rect(0, 0, w, y_cut), doc, pno, clip=fitz.Rect(0, 0, w, y_cut))

        # 2. Bottom Slice (y_cut to h) shifted down by delta_y
        new_page.show_pdf_page(fitz.Rect(0, y_cut + delta_y, w, h), doc, pno, clip=fitz.Rect(0, y_cut, w, h - delta_y))

        # 3. Draw Table Gridlines across the gap [y_cut, y_cut + delta_y]
        if v_lines and len(v_lines) >= 2:
            # Extend all vertical column lines
            for vx in v_lines:
                new_page.draw_line(fitz.Point(vx, y_cut), fitz.Point(vx, y_cut + delta_y), color=table_color, width=line_width)

            # Draw horizontal divider at y_cut and at y_cut + delta_y across full table width
            new_page.draw_line(fitz.Point(v_lines[0], y_cut), fitz.Point(v_lines[-1], y_cut), color=table_color, width=line_width)
            new_page.draw_line(fitz.Point(v_lines[0], y_cut + delta_y), fitz.Point(v_lines[-1], y_cut + delta_y), color=table_color, width=line_width)

        # 4. Register fonts with unique names to prevent CMap/encoding collisions
        fn_reg = f"F_carlito_reg_{pno}_{int(time.time() * 1000) % 100000}"
        fn_bold = f"F_carlito_bold_{pno}_{int(time.time() * 1000) % 100000}"
        has_carlito = CARLITO_REG.exists() and CARLITO_BOLD.exists()
        if has_carlito:
            new_page.insert_font(fontname=fn_reg, fontfile=str(CARLITO_REG))
            new_page.insert_font(fontname=fn_bold, fontfile=str(CARLITO_BOLD))

        # 5. Collect blocks for all columns (last row + templates for any empty columns)
        page_blocks = extract_page_text_blocks(source_pdf, pno)
        table_blocks = [
            b for b in page_blocks
            if row_data.get('y0', 0) <= b['y0'] <= (y_cut + 2)
        ]

        cloned_blocks = []
        last_row_top = float(row_data.get('btn_y0', y_cut - delta_y))

        if v_lines and len(v_lines) >= 2:
            for i in range(len(v_lines) - 1):
                c_x0, c_x1 = v_lines[i], v_lines[i + 1]
                in_last = [b for b in row_blocks if c_x0 - 5 <= b['x0'] < c_x1 + 5]
                if in_last:
                    for b in in_last:
                        base_y = float(b.get('baseline_y') or (b['y0'] + b.get('font_size', 10.0) * 0.85))
                        cloned_blocks.append((b, b['x0'], base_y + delta_y))
                else:
                    # Column is empty in last row: grab template from row above in the same column
                    above = [
                        b for b in table_blocks
                        if c_x0 - 5 <= b['x0'] < c_x1 + 5 and b['y0'] < last_row_top
                    ]
                    if above:
                        lowest_y0 = max(b['y0'] for b in above)
                        for b in above:
                            if abs(b['y0'] - lowest_y0) <= 6:
                                f_size = float(b.get('font_size', 10.0))
                                new_y = last_row_top + delta_y + (delta_y / 2) + f_size * 0.35
                                cloned_blocks.append((b, b['x0'], new_y))
        else:
            for b in row_blocks:
                f_size = float(b.get('font_size', 10.0))
                base_y = float(b.get('baseline_y') or (b['y0'] + f_size * 0.85))
                cloned_blocks.append((b, b['x0'], base_y + delta_y))

        # 6. Insert cloned text blocks into the new gap
        for b, insert_x, insert_y in cloned_blocks:
            font_size = float(b.get('font_size', 10.0))
            is_bold = 'bold' in str(b.get('font_name', '')).lower() or 'bo' in str(b.get('font_name', '')).lower()
            font_color = b.get('font_color', (0.05, 0.05, 0.05))

            if has_carlito:
                use_fn = fn_bold if is_bold else fn_reg
                new_page.insert_text(
                    (insert_x, insert_y),
                    b['text'],
                    fontsize=font_size,
                    fontname=use_fn,
                    color=font_color
                )
            else:
                use_fn = "helv-bold" if is_bold else "helv"
                new_page.insert_text(
                    (insert_x, insert_y),
                    b['text'],
                    fontsize=font_size,
                    fontname=use_fn,
                    color=font_color
                )

    new_doc.save(str(out_path), garbage=4, deflate=True)
    new_doc.close()
    doc.close()
    return out_path
