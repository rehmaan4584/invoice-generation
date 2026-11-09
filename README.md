# PDF Invoice Visual Editor & Document Manager

A fast, lightweight, locally-hosted **Visual PDF Invoice Editor & Document Management System** built with **Python**, **Streamlit**, **PyMuPDF**, and **SQLite**.

Edit PDF invoices directly on their original layout with pixel-perfect in-place text replacement, stamp custom edits, and manage saved documents through a complete CRUD dashboard.

---

## 🌟 Key Features

1. **Pure PDF Workflow:** Dedicated exclusively to `.pdf` invoices (no format conversions or loss of quality).
2. **Exact Original Layout & White Background:** Retains 100% of the original invoice structure, company logos, tables, fonts, and styling.
3. **In-Place Visual Editing:**
   - **Vector PDFs:** Automatically extracts text blocks with coordinates and replaces text directly on the document baseline.
   - **Scanned Photo PDFs:** Whiteout and stamp text at exact coordinates or predefined positions (Invoice #, Date, Items, Totals).
4. **Live Visual Preview:** Render changes on the actual PDF before saving or downloading.
5. **Custom Naming & Storage:** Save modified PDFs with your chosen filename (e.g. `Faire_November_Updated.pdf`).
6. **Full CRUD Document Dashboard:**
   - 👁️ **Preview:** High-res preview of any saved PDF page.
   - 📥 **Download:** 1-click download of the final modified PDF.
   - ✏️ **Edit Again:** Reload any past document directly back into the editor.
   - 🗑️ **Delete:** Remove documents from storage and SQLite database.
7. **Zero Dependencies on AI / LLMs:** 100% local, offline, no API keys, no GPU requirements, and zero costs.

---

## 🚀 Quick Start

### macOS & Linux
```bash
./run.sh
```

### Windows (1-Click)
Double-click `run.bat` or run:
```cmd
run.bat
```

Open your browser at `http://localhost:8501`.

---

## 📂 Project Structure

```
invoice-generation/
├── app.py              # Streamlit Visual Editor & Dashboard
├── config.py           # Directory and path configurations
├── database.py         # SQLite CRUD manager (saved_documents)
├── pdf_engine.py       # PyMuPDF rendering, text extraction, in-place editing
├── requirements.txt    # Minimal dependencies (streamlit, pymupdf, pillow, pandas)
├── run.sh              # Unix/macOS startup script
├── run.bat             # Windows 1-click startup script
└── data/
    ├── uploads/        # Original uploaded PDF files
    ├── edited_pdfs/    # Saved edited PDF invoices
    └── pdf_editor.db   # SQLite database
```
