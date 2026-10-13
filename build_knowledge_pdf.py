"""Rebuild the standard-title knowledge PDF and its verified source sidecar.
Input is curated official-source summaries in district_sources.json.
This does not scrape pages or claim every current scheme is represented.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Flowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from config import BASE_DIR, PDF_PATH
from districts import DISTRICTS, normalize_district

class PageMarker(Flowable):
    def __init__(self, record, key):
        super().__init__()
        self.record, self.key = record, key
        self.width = self.height = 0
    def draw(self):
        self.record[self.key] = self.canv.getPageNumber()

def build(input_path=BASE_DIR / 'district_sources.json', output_path=PDF_PATH):
    payload = json.loads(input_path.read_text(encoding='utf-8'))
    records = payload['records']
    represented = {normalize_district(r['district']) for r in records}
    if represented != set(DISTRICTS):
        raise ValueError('Curated dataset must explicitly represent all 38 districts.')
    font = os.getenv('PDF_FONT_PATH', '')
    if not font:
        for candidate in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'C:/Windows/Fonts/arial.ttf']:
            if Path(candidate).exists():
                font = candidate
                break
    regular, bold = 'Helvetica', 'Helvetica-Bold'
    if font:
        pdfmetrics.registerFont(TTFont('PDFBody', font))
        regular = 'PDFBody'
        bold_path = os.getenv('PDF_BOLD_FONT_PATH', '') or str(Path(font).with_name('DejaVuSans-Bold.ttf' if 'DejaVuSans' in font else 'arialbd.ttf'))
        if Path(bold_path).exists():
            pdfmetrics.registerFont(TTFont('PDFBold', bold_path))
            bold = 'PDFBold'
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyTextCustom', fontName=regular, fontSize=10, leading=14, spaceAfter=8))
    styles.add(ParagraphStyle(name='Meta', fontName=regular, fontSize=8, leading=11, spaceAfter=7, textColor=colors.HexColor('#4C6555')))
    styles.add(ParagraphStyle(name='DistrictTitle', fontName=bold, fontSize=17, leading=22, spaceAfter=10, textColor=colors.HexColor('#1B633A')))
    styles.add(ParagraphStyle(name='CoverTitle', fontName=bold, fontSize=27, leading=34, spaceAfter=18, textColor=colors.HexColor('#1B633A')))
    def paragraph(text, style='BodyTextCustom'):
        return Paragraph(html.escape(str(text)), styles[style])
    story = [Spacer(1,38), Paragraph('Tamil Nadu<br/>Agriculture Schemes',styles['CoverTitle']),
             paragraph('District-wise Reference Guide','DistrictTitle'),
             paragraph('Compiled: ' + payload['compiled_at']),
             paragraph('Coverage: all 38 Tamil Nadu districts. Each entry summarises inspected official district-government sources and retains source dates and links.'),
             paragraph('This is a prepared reference guide, not an original Government Order or official government publication. It covers selected schemes, services and document links. It is not an exhaustive or uniformly current district scheme catalogue.'),
             paragraph('Some entries contain only service information or links to documents whose full rules were not extracted. Historical figures remain labelled with their source dates. Missing facts must be reported as not found, rather than inferred.'),
             paragraph('District lists and official websites are checked against the Lok Bhavan district directory. District spellings are normalised for consistent selection.'),
             Paragraph(f'<link href="{payload["district_directory_source"]}" color="#1B633A">Official district directory</link>',styles['Meta']), PageBreak()]
    names = list(DISTRICTS)
    for offset in [0,19]:
        story.append(paragraph('District directory','DistrictTitle'))
        rows = [['District','Official district website']]
        for name in names[offset:offset+19]:
            source = next(r for r in records if normalize_district(r['district']) == name)
            from urllib.parse import urlparse
            hostname = urlparse(source['source_url']).hostname
            rows.append([paragraph(name,'Meta'), Paragraph(f'<link href="https://{hostname}/" color="#1B633A">{hostname}</link>',styles['Meta'])])
        table = Table(rows,colWidths=[150,360],hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1B633A')),
          ('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),bold),
          ('FONTSIZE',(0,0),(-1,0),10),('TOPPADDING',(0,0),(-1,-1),7),
          ('BOTTOMPADDING',(0,0),(-1,-1),7),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#F0F6F0'),colors.white])]))
        story.extend([table, Spacer(1,14), paragraph('Entries include dated sources. A programme listing is not confirmation that a current application window is open.','Meta'), PageBreak()])
    for number, district in enumerate(names):
        if number and number % 2 == 0:
            story.append(PageBreak())
        district_records = [r for r in records if normalize_district(r['district']) == district]
        for position, record in enumerate(district_records):
            block = [paragraph(district,'DistrictTitle')] if position == 0 else []
            block.append(PageMarker(record,'page'))
            block.append(paragraph('Source: ' + record['source'],'Meta'))
            block.append(paragraph('Source date: ' + record.get('source_date','Not supplied'),'Meta'))
            block.append(paragraph('Coverage: ' + record.get('coverage_status','Selected source summary'),'Meta'))
            for text in record['text'].split('\n'):
                block.append(paragraph(text))
            block.append(Paragraph(f'<link href="{html.escape(record["source_url"],quote=True)}" color="#1B633A">Open official source</link>',styles['Meta']))
            block.append(PageMarker(record,'page_end'))
            story.append(KeepTogether(block))
        if number % 2 == 0 and number + 1 < len(names):
            story.append(Spacer(1,22))
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(regular,8)
        canvas.setFillColor(colors.HexColor('#526457'))
        canvas.drawString(42,27,'Tamil Nadu Agriculture Schemes | Compiled ' + payload['compiled_at'])
        canvas.drawRightString(A4[0]-42,27,str(doc.page))
        canvas.restoreState()
    output_path.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(output_path),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=38,bottomMargin=52,
        title='Tamil Nadu Agriculture Schemes', author='Compiled reference guide').build(story,onFirstPage=footer,onLaterPages=footer)
    for record in records:
        record['district'] = normalize_district(record['district'])
        record['knowledge_scope'] = payload['knowledge_scope']
    sidecar = {'pdf_sha256':hashlib.sha256(output_path.read_bytes()).hexdigest(),
               'collected_at':payload['compiled_at'],'knowledge_scope':payload['knowledge_scope'],'records':records}
    output_path.with_suffix('.sources.json').write_text(json.dumps(sidecar,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved PDF and source records:',output_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',default=str(BASE_DIR/'district_sources.json'))
    parser.add_argument('--output',default=str(PDF_PATH))
    args = parser.parse_args()
    build(Path(args.input),Path(args.output))
