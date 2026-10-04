import os
import html
import markdown
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def clean_markdown_for_reportlab(text: str) -> str:
    # First escape all special XML characters (&, <, >)
    safe = html.escape(text)
    
    # Process bold first: **text** -> <b>text</b>
    safe = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe)
    
    # Process italic: *text* or _text_ -> <i>text</i> (only when matching pairs on word boundaries)
    safe = re.sub(r'(?<!\w)\*(?!\s)(.*?)(?<!\s)\*(?!\w)', r'<i>\1</i>', safe)
    safe = re.sub(r'(?<!\w)_(?!\s)(.*?)(?<!\s)_(?!\w)', r'<i>\1</i>', safe)
    
    # Process markdown links: [label](url) -> <a href="url" color="blue"><u>label</u></a>
    safe = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" color="blue"><u>\1</u></a>', safe)
    
    # Strip any stray or unmatched HTML/XML-like tags that ReportLab doesn't support
    # Only allow <b>, </b>, <i>, </i>, <u>, </u>, <a>, </a>
    def sanitize_tags(match):
        tag = match.group(0)
        if tag.lower() in ['<b>', '</b>', '<i>', '</i>', '<u>', '</u>'] or tag.lower().startswith('<a ') or tag.lower() == '</a>':
            return tag
        return html.escape(tag)
        
    return safe

def convert_md_to_pdf(md_content: str, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=8
    )
    
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#2b6cb0'),
        spaceBefore=10,
        spaceAfter=4
    )

    h3_style = ParagraphStyle(
        'DocH3',
        parent=styles['Heading3'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#2d3748'),
        spaceBefore=6,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#2d3748'),
        leftIndent=12,
        spaceAfter=2
    )

    story = []
    lines = md_content.split('\n')
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 3))
            continue
            
        formatted_line = clean_markdown_for_reportlab(stripped)
        
        if stripped.startswith('# '):
            clean_text = formatted_line[2:].strip()
            story.append(Paragraph(clean_text, title_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2b6cb0'), spaceBefore=2, spaceAfter=6))
        elif stripped.startswith('## '):
            clean_text = formatted_line[3:].strip()
            story.append(Paragraph(clean_text, h2_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e0'), spaceBefore=1, spaceAfter=4))
        elif stripped.startswith('### '):
            clean_text = formatted_line[4:].strip()
            story.append(Paragraph(clean_text, h3_style))
        elif stripped.startswith('- ') or stripped.startswith('* '):
            clean_text = formatted_line[2:].strip()
            story.append(Paragraph(f"• {clean_text}", bullet_style))
        else:
            story.append(Paragraph(formatted_line, body_style))

    doc.build(story)
    return output_path
