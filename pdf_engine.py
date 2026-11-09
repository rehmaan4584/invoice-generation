import io
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
import pymupdf as fitz
from PIL import Image


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

        for ed in p_edits:
            orig_rect = fitz.Rect(ed["rect"])
            new_text = str(ed.get("new_text", "")).strip()
            font_size = float(ed.get("font_size", 10.0))
            if font_size <= 0:
                font_size = 10.0
            edit_type = ed.get("type", "replace")

            if edit_type == "replace":
                # Digital vector text replacement:
                # 1. Cleanly redact ONLY text glyphs at content stream level.
                # graphics=0 & images=0 ensure table borders, vector lines, underlines and logos stay 100% INTACT.
                # fill=None removes the text characters without painting an opaque white box over borders.
                try:
                    page.add_redact_annot(orig_rect, fill=None)
                    page.apply_redactions(images=0, graphics=0, text=0)
                except Exception:
                    pass
            elif edit_type in ("stamp", "whiteout"):
                # Manual coordinate stamp or whiteout for scanned images:
                page.draw_rect(orig_rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)

            # Direct text insertion at exact baseline
            if new_text and edit_type != "whiteout":
                lines = new_text.splitlines() if "\n" in new_text else [new_text]
                line_spacing = max(font_size * 1.2, 12.0)
                font_name = str(ed.get("font_name", "helv")).lower()
                font_color = ed.get("font_color", (0.0, 0.0, 0.0))
                
                # Check for matching TTF font file
                use_fontfile = None
                insert_fontname = font_name
                if ("carlito" in font_name or "calibri" in font_name or font_name in ("helv", "hebo", "carlito", "carlito-bold")) and CARLITO_REG.exists() and CARLITO_BOLD.exists():
                    is_bold_font = "bold" in font_name or "bo" in font_name
                    use_fontfile = str(CARLITO_BOLD if is_bold_font else CARLITO_REG)
                    insert_fontname = "Carlito-Bold" if is_bold_font else "Carlito-Regular"

                base_y = float(ed.get("baseline_y") or (orig_rect.y0 + (font_size * 0.85)))
                for i, line in enumerate(lines):
                    current_y = base_y + (i * line_spacing)

                    # Subpixel horizontal alignment:
                    # For numeric amounts/values in table cells, center around the original text bounding box center
                    is_numeric_val = any(c.isdigit() for c in line) and not any(c.isalpha() for c in line)
                    if is_numeric_val and orig_rect.width > 0:
                        try:
                            measure_font = fitz.Font(fontfile=use_fontfile) if use_fontfile else fitz.Font(fontname=insert_fontname)
                            line_w = measure_font.text_length(line, fontsize=font_size)
                            orig_center_x = (orig_rect.x0 + orig_rect.x1) / 2.0
                            insert_x = round(orig_center_x - (line_w / 2.0), 2)
                        except Exception:
                            insert_x = orig_rect.x0
                    else:
                        insert_x = orig_rect.x0

                    if use_fontfile:
                        page.insert_text(
                            (insert_x, current_y),
                            line,
                            fontsize=font_size,
                            fontname=insert_fontname,
                            fontfile=use_fontfile,
                            color=font_color
                        )
                    else:
                        page.insert_text(
                            (insert_x, current_y),
                            line,
                            fontsize=font_size,
                            fontname=insert_fontname,
                            color=font_color
                        )

    # Save modified PDF with compression
    doc.save(str(out_path), garbage=4, deflate=True)
    doc.close()
    return out_path
