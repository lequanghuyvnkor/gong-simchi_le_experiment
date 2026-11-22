"""Build editable presenter and stress-plan documents from repository Markdown.

Python 3.10+ and python-docx. PDF export is a separate LibreOffice command.
This builds documents only; it does not run stress experiments.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
GITHUB = 'https://github.com/lequanghuyvnkor/gong-simchi_le_experiment/blob/main/'


def add_hyperlink(paragraph, text, uri):
    part = paragraph.part
    relationship = part.relate_to(uri, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
    hyperlink = OxmlElement('w:hyperlink'); hyperlink.set(qn('r:id'), relationship)
    run = OxmlElement('w:r'); props = OxmlElement('w:rPr')
    color = OxmlElement('w:color'); color.set(qn('w:val'), '0C6A9A'); props.append(color)
    underline = OxmlElement('w:u'); underline.set(qn('w:val'), 'single'); props.append(underline)
    run.append(props); content = OxmlElement('w:t'); content.text = text; run.append(content)
    hyperlink.append(run); paragraph._p.append(hyperlink)


def inline(paragraph, text, source):
    pattern = re.compile(r'(\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|`[^`]+`)')
    for token in pattern.split(text):
        if not token: continue
        if token.startswith('[') and '](' in token:
            label, uri = token[1:].split('](', 1); uri = uri[:-1]
            if not re.match(r'https?://', uri):
                resolved = (source.parent / uri.split('#')[0]).resolve()
                uri = GITHUB + resolved.relative_to(ROOT).as_posix()
            add_hyperlink(paragraph, label, uri)
        elif token.startswith('**'):
            paragraph.add_run(token[2:-2]).bold = True
        elif token.startswith('`'):
            r = paragraph.add_run(token[1:-1]); r.font.name = 'Consolas'; r.font.size = Pt(10)
        else: paragraph.add_run(token)


def cell_shade(cell, fill):
    props = cell._tc.get_or_add_tcPr(); shading = OxmlElement('w:shd'); shading.set(qn('w:fill'), fill); props.append(shading)


def setup(doc, title):
    section = doc.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.top_margin = section.bottom_margin = Mm(18)
    section.left_margin = section.right_margin = Mm(18)
    normal = doc.styles['Normal']; normal.font.name = 'Arial'; normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string('1D2939')
    normal.paragraph_format.space_after = Pt(6); normal.paragraph_format.line_spacing = 1.12
    for name, size in [('Title',23),('Heading 1',17),('Heading 2',13.5),('Heading 3',11.5)]:
        style = doc.styles[name]; style.font.name = 'Arial'; style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string('073B5B')
        style.paragraph_format.space_before = Pt(12); style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.keep_with_next = True
    header = section.header.paragraphs[0]; header.text = 'GONG & SIMCHI-LEVI · EXPERIMENTAL RESEARCH'
    for r in header.runs: r.font.size = Pt(8); r.font.color.rgb = RGBColor.from_string('4B6778')
    footer = section.footer.paragraphs[0]; footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = footer.add_run('Tài liệu dự án · '); r.font.size = Pt(8)
    field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGE'); footer._p.append(field)
    doc.core_properties.title = title
    doc.core_properties.subject = 'Experimental presentation guidance and prospective stress-test design'
    doc.core_properties.author = 'Gong & Simchi-Levi experiment project'
    doc.core_properties.created = doc.core_properties.modified = dt.datetime(2026,11,22,0,0,0)


def render_markdown(source, target):
    doc = Document(); setup(doc, source.stem)
    lines = source.read_text(encoding='utf-8').splitlines(); index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip(): index += 1; continue
        if line.startswith('```'):
            index += 1
            while index < len(lines) and not lines[index].startswith('```'):
                p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(1)
                r = p.add_run(lines[index]); r.font.name = 'Consolas'; r.font.size = Pt(9)
                index += 1
            index += 1; continue
        if line.startswith('|') and index+1 < len(lines) and re.match(r'^\|[\s:|\-]+\|$', lines[index+1]):
            rows=[]
            while index < len(lines) and lines[index].startswith('|'):
                row = [x.strip() for x in lines[index].strip().strip('|').split('|')]
                if not all(re.match(r'^:?-+:?$',x.replace(' ','')) for x in row): rows.append(row)
                index += 1
            table = doc.add_table(rows=1, cols=len(rows[0])); table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.style = 'Table Grid'; table.autofit = False
            width = 6.85/len(rows[0])
            for col in table.columns: col.width = Inches(width)
            for ri, row in enumerate(rows):
                cells = table.rows[0].cells if ri==0 else table.add_row().cells
                for ci, text in enumerate(row):
                    cell=cells[ci]; cell.width=Inches(width);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.TOP
                    p=cell.paragraphs[0];p.paragraph_format.space_after=Pt(3);p.paragraph_format.line_spacing=1.04
                    inline(p,text,source)
                    for r in p.runs:
                        r.font.size=Pt(9.2)
                        if ri==0:r.bold=True;r.font.color.rgb=RGBColor(255,255,255)
                    if ri==0:cell_shade(cell,'073B5B')
                    elif ri%2==0:cell_shade(cell,'EFF6FA')
                if ri==0:
                    repeat=OxmlElement('w:tblHeader');table.rows[0]._tr.get_or_add_trPr().append(repeat)
            doc.add_paragraph();continue
        if line.startswith('# '):
            p=doc.add_paragraph(style='Title');inline(p,line[2:],source)
        elif line.startswith('### '):
            p=doc.add_paragraph(style='Heading 2');inline(p,line[4:],source)
        elif line.startswith('## '):
            p=doc.add_paragraph(style='Heading 1');inline(p,line[3:],source)
        elif line.startswith('- '):
            p=doc.add_paragraph(style='List Bullet');inline(p,line[2:],source)
        elif line.startswith('> '):
            p=doc.add_paragraph();p.paragraph_format.left_indent=Mm(5)
            inline(p,line[2:],source)
            for r in p.runs:r.italic=True
        else:
            p=doc.add_paragraph();inline(p,line,source)
        index += 1
    doc.save(target)
    try:
        output_label = str(target.relative_to(ROOT))
    except ValueError:
        output_label = str(target)
    return {'source':str(source.relative_to(ROOT)),'output':output_label,'paragraphs':len(doc.paragraphs),'tables':len(doc.tables)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=HERE)
    args=parser.parse_args();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    mapping=[(HERE/'playbook_vi.md',out/'experimental_presenter_playbook_vi.docx'),(ROOT/'docs/stress_test_plan.md',out/'stress_test_plan_vi.docx')]
    records=[]
    for source,target in mapping:
        # Link validation prevents stale local references in the exported docs.
        for uri in re.findall(r'\]\(([^)]+)\)',source.read_text(encoding='utf-8')):
            if not re.match(r'https?://',uri):
                assert (source.parent/uri.split('#')[0]).resolve().exists(),(source,uri)
        record=render_markdown(source,target);records.append(record)
    print(json.dumps(records,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
