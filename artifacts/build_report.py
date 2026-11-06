from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "project_report.md"
OUTPUT = ROOT / "artifacts" / "final" / "Team11_Server_Health_Project_Report_EMQX.docx"
ARCHITECTURE = ROOT / "docs" / "team11_architecture.png"
DASHBOARD = ROOT / "docs" / "dashboard_screenshot.png"

FONT = "Liberation Sans"
NAVY = "17365D"
PALE_BLUE = "EAF2F8"
PALE_GRAY = "F5F6F7"
LIGHT_BORDER = "D9D9D9"


def set_cell_shading(cell, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_borders(cell, color: str = LIGHT_BORDER) -> None:
    properties = cell._tc.get_or_add_tcPr()
    borders = properties.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        properties.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), color)


def set_repeat_table_header(row) -> None:
    row_properties = row._tr.get_or_add_trPr()
    marker = OxmlElement("w:tblHeader")
    marker.set(qn("w:val"), "true")
    row_properties.append(marker)


def set_run_font(run, name: str = FONT) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run()
    set_run_font(run)
    field_begin = OxmlElement("w:fldChar")
    field_begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = "PAGE"
    field_end = OxmlElement("w:fldChar")
    field_end.set(qn("w:fldCharType"), "end")
    run._r.extend([field_begin, instruction, field_end])


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.different_first_page_header_footer = True
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.85)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)

    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = FONT
    normal._element.rPr.rFonts.set(qn("w:ascii"), FONT)
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.14

    title = styles["Title"]
    title.font.name = FONT
    title.font.size = Pt(26)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)
    title.paragraph_format.space_after = Pt(10)
    title_properties = title._element.get_or_add_pPr()
    title_border = title_properties.find(qn("w:pBdr"))
    if title_border is not None:
        title_properties.remove(title_border)

    for name, size in (("Heading 1", 17), ("Heading 2", 13), ("Heading 3", 11)):
        style = styles[name]
        style.font.name = FONT
        style._element.rPr.rFonts.set(qn("w:ascii"), FONT)
        style._element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(12 if name == "Heading 1" else 8)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.keep_with_next = True


def add_cover(document: Document) -> None:
    for _ in range(4):
        document.add_paragraph()
    title = document.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("IoT Based Server and IT Infrastructure Health Monitoring")
    title_properties = title._p.get_or_add_pPr()
    title_border = title_properties.find(qn("w:pBdr"))
    if title_border is not None:
        title_properties.remove(title_border)
    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Software Only IoT Mini Project Report")
    set_run_font(run)
    run.font.size = Pt(15)
    run.font.color.rgb = RGBColor(70, 70, 70)

    document.add_paragraph()
    for text, bold in (
        ("Team 11", True),
        ("B.Tech Computer Science and Engineering", False),
        ("Semester 7", False),
        ("Team members and roll numbers: add before submission", False),
    ):
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        set_run_font(run)
        run.bold = bold
        run.font.size = Pt(12)
    document.add_page_break()


def add_contents(document: Document, headings: list[str]) -> None:
    title = document.add_paragraph()
    title.paragraph_format.space_after = Pt(8)
    run = title.add_run("Contents")
    set_run_font(run)
    run.font.size = Pt(17)
    run.bold = True
    for heading in headings:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.18)
        paragraph.paragraph_format.space_after = Pt(3)
        run = paragraph.add_run(heading)
        set_run_font(run)
        run.font.size = Pt(10.5)
    document.add_page_break()


def add_caption(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(3)
    paragraph.paragraph_format.space_after = Pt(8)
    run = paragraph.add_run(text)
    set_run_font(run)
    run.italic = True
    run.font.size = Pt(9)


def add_image(document: Document, path: Path, caption: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    width = 6.0 if path == DASHBOARD else 6.3
    run.add_picture(str(path), width=Inches(width))
    add_caption(document, caption)


def add_table(document: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    columns = max(len(row) for row in rows)
    table = document.add_table(rows=1, cols=columns)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    header = table.rows[0]
    set_repeat_table_header(header)
    for index in range(columns):
        text = rows[0][index] if index < len(rows[0]) else ""
        cell = header.cells[index]
        cell.text = text
        set_cell_shading(cell, NAVY)
        set_cell_borders(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for run in cell.paragraphs[0].runs:
            set_run_font(run)
            run.bold = True
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(255, 255, 255)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row_number, values in enumerate(rows[1:], start=1):
        cells = table.add_row().cells
        for index in range(columns):
            cell = cells[index]
            cell.text = values[index] if index < len(values) else ""
            set_cell_borders(cell)
            set_cell_shading(cell, PALE_BLUE if row_number % 2 == 0 else "FFFFFF")
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for run in cell.paragraphs[0].runs:
                set_run_font(run)
                run.font.size = Pt(8.7)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT if index == 0 else WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph().paragraph_format.space_after = Pt(1)


def add_rich_paragraph(document: Document, text: str, style: str | None = None) -> None:
    paragraph = document.add_paragraph(style=style)
    parts = re.split(r"(`[^`]+`|\*\*[^*]+\*\*)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            set_run_font(run, "Liberation Mono")
            run.font.size = Pt(9.2)
        elif part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            set_run_font(run)
            run.bold = True
        else:
            run = paragraph.add_run(part)
            set_run_font(run)


def add_numbered_paragraph(document: Document, number: str, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(0.25)
    paragraph.paragraph_format.first_line_indent = Inches(-0.25)
    paragraph.paragraph_format.space_after = Pt(2.5)
    prefix = paragraph.add_run(f"{number}. ")
    set_run_font(prefix)
    prefix.bold = True
    parts = re.split(r"(`[^`]+`|\*\*[^*]+\*\*)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            set_run_font(run, "Liberation Mono")
            run.font.size = Pt(9.2)
        elif part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            set_run_font(run)
            run.bold = True
        else:
            run = paragraph.add_run(part)
            set_run_font(run)


def markdown_body(document: Document, markdown: str) -> None:
    lines = markdown.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith("## Abstract"))
    lines = lines[start:]
    index = 0
    inserted_architecture = False
    inserted_dashboard = False
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading in {"6 Model development", "11 Verification", "References"}:
                document.add_page_break()
            paragraph = document.add_heading(heading, level=1)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.left_indent = Inches(0)
            paragraph.paragraph_format.first_line_indent = Inches(0)
            if heading == "3 System architecture" and not inserted_architecture:
                add_image(document, ARCHITECTURE, "Figure 1  Two-laptop closed-loop IoT architecture")
                inserted_architecture = True
            if heading == "7 Advanced operational analytics" and not inserted_dashboard:
                add_image(document, DASHBOARD, "Figure 2  Enhanced operational dashboard with mixed fleet state")
                inserted_dashboard = True
            index += 1
            continue
        if line.startswith("### "):
            document.add_heading(line[4:].strip(), level=2)
            index += 1
            continue
        if line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            parsed = [[cell.strip() for cell in row.strip("|").split("|")] for row in table_lines]
            if len(parsed) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in parsed[1]):
                parsed.pop(1)
            add_table(document, parsed)
            continue
        number_match = re.match(r"^(\d+)\.\s+(.*)", line)
        if number_match:
            add_numbered_paragraph(document, number_match.group(1), number_match.group(2))
            index += 1
            continue
        if line.startswith("- "):
            add_rich_paragraph(document, line[2:], "List Bullet")
            index += 1
            continue
        paragraph_lines = [line]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate or candidate.startswith(("## ", "### ", "|", "- ")) or re.match(r"^\d+\. ", candidate):
                break
            paragraph_lines.append(candidate)
            index += 1
        add_rich_paragraph(document, " ".join(paragraph_lines))


def add_header_footer(document: Document) -> None:
    for section in document.sections:
        header = section.header.paragraphs[0]
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = header.add_run("Team 11  Server Health Monitoring")
        set_run_font(run)
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(100, 100, 100)
        footer = section.footer.paragraphs[0]
        add_page_number(footer)
        for run in footer.runs:
            run.font.size = Pt(8.5)
            run.font.color.rgb = RGBColor(100, 100, 100)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    markdown = SOURCE.read_text(encoding="utf-8")
    headings = [line[3:].strip() for line in markdown.splitlines() if line.startswith("## ")]
    document = Document()
    configure_document(document)
    add_cover(document)
    add_contents(document, headings)
    markdown_body(document, markdown)
    add_header_footer(document)
    document.core_properties.title = "IoT Based Server and IT Infrastructure Health Monitoring"
    document.core_properties.subject = "Team 11 B.Tech CSE Semester 7 IoT Mini Project"
    document.core_properties.author = "Team 11"
    document.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
