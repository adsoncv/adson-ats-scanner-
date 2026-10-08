import streamlit as st
import os
import re
import io
import pypdf
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# --- Page Configuration ---
st.set_page_config(
    page_title="ADSON — ATS CV Diagnostic Engine",
    page_icon="📄",
    layout="wide"
)

# --- Staff Password Protection ---
if os.path.exists("adson_logo.png"):
    st.sidebar.image("adson_logo.png", width=120)
st.sidebar.title("ADSON Staff Portal")
st.sidebar.write("Official ATS Diagnostic & Review System")
password = st.sidebar.text_input("Enter Staff Password", type="password")

if password != "adson2026":
    st.warning("🔒 Please enter the correct staff password in the sidebar to access the scanner.")
    st.stop()

# --- 1. ATS Evaluation Engine ---
def evaluate_cv_ats(text: str, num_pages: int, target_role: str):
    text_lower = text.lower()
    score = 100
    deductions = []
    breakdown = []
    critical_issues = []
    action_plan = []

    # Pillar 1: Layout & Page Count Check
    p1_score = 25
    if num_pages > 2:
        p1_score -= 15
        deductions.append(f"Excessive document length ({num_pages} pages).")
        critical_issues.append((
            f"Document Length Overkill ({num_pages} Pages)",
            f"The CV spans {num_pages} pages. Corporate ATS parsers penalize extreme document lengths due to diluted keyword ratios. Resumes should strictly be 1 to 2 pages."
        ))
    elif num_pages == 2 and len(text.split()) < 350:
        p1_score -= 8
        deductions.append("Awkward 2-page sprawl with empty second page.")
        critical_issues.append((
            "Page Space Imbalance (Trailing Second Page)",
            "The document spills onto a second page with very few lines, leaving substantial empty space. It should be consolidated into a crisp 1-page layout."
        ))

    if re.search(r'(gender\s*:\s*|marital status\s*:\s*|father name|permanent address)', text_lower):
        p1_score -= 5

    breakdown.append((
        "Layout & Parser Readability",
        f"{int((p1_score/25)*100)}%",
        "Excellent" if p1_score >= 20 else ("Good" if p1_score >= 15 else "Critical"),
        "Single-column flow without tables" if p1_score >= 20 else "Page count or formatting imbalance detected.",
        "#16A34A" if p1_score >= 20 else ("#D97706" if p1_score >= 15 else "#DC2626")
    ))

    # Pillar 2: Timeline & Date Continuity
    p2_score = 20
    relative_dates = re.findall(r'duration\s*:\s*\d+\s*(?:years?|months?)|\b\d+\s*years?\b(?!\s*experience)', text_lower)
    year_only_dates = re.findall(r'\b20\d\d\s*[-–]\s*20\d\d\b', text)
    month_dates = re.findall(r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*20\d\d', text_lower)

    if len(month_dates) == 0 and len(year_only_dates) > 0:
        p2_score -= 8
        critical_issues.append((
            "Vague Year-Only Employment Dates",
            "Job positions list dates only as years without calendar months. ATS parsers require standard month/year ranges (MM/YYYY) to calculate cumulative experience."
        ))
    elif "duration:" in text_lower or len(relative_dates) >= 2:
        p2_score -= 12
        critical_issues.append((
            "Fatal Omission of Calendar Dates",
            "Positions list relative durations (e.g., 'Duration: 1 Year') rather than start and end calendar dates. ATS engines register zero verified experience when calendar dates are absent."
        ))

    breakdown.append((
        "Timeline & Date Continuity",
        f"{int((p2_score/20)*100)}%",
        "Strong" if p2_score >= 16 else ("Needs Work" if p2_score >= 12 else "Critical"),
        "Verified calendar date ranges" if p2_score >= 16 else "Dates lack month specifics or use relative duration strings.",
        "#16A34A" if p2_score >= 16 else ("#D97706" if p2_score >= 12 else "#DC2626")
    ))

    # Pillar 3: Quantified Metrics & Duty Depth
    p3_score = 20
    numbers_count = len(re.findall(r'\b\d+(?:\%|\+|\s*cr|\s*k|\s*m)?\b', text))
    percentages_count = len(re.findall(r'\d+%', text))

    if percentages_count == 0 and numbers_count < 5:
        p3_score -= 12
        critical_issues.append((
            "Complete Absence of Quantified Impact & Metrics",
            "Work duties are listed passively with zero figures: no revenue turnover, transaction counts, team headcounts, or percentage improvements. Hiring managers prioritize measurable outcomes."
        ))
    elif percentages_count < 2:
        p3_score -= 6
        critical_issues.append((
            "Lack of Quantifiable Performance Indicators",
            "Responsibilities describe day-to-day tasks but lack measurable scale (e.g., volume handled, efficiency improvements, or accuracy percentages)."
        ))

    breakdown.append((
        "Work Experience & Metrics",
        f"{int((p3_score/20)*100)}%",
        "Strong" if p3_score >= 16 else ("Needs Work" if p3_score >= 12 else "Critical"),
        "Contains measurable performance metrics" if p3_score >= 16 else "Lacks quantifiable results and operational volume numbers.",
        "#16A34A" if p3_score >= 16 else ("#D97706" if p3_score >= 12 else "#DC2626")
    ))

    # Pillar 4: Domain Keywords & Licensure
    p4_score = 20
    if "accounting software" in text_lower or "erp basics" in text_lower:
        p4_score -= 6
        critical_issues.append((
            "Generic Software Placeholders Used",
            "Lists vague terms like 'Accounting Software' or 'ERP Basics' instead of specific packages (Tally Prime, QuickBooks, SAP, Zoho Books) that ATS keyword bots scan for."
        ))
    
    if "intrastat" in text_lower or "recapitulative statement" in text_lower:
        p4_score -= 10
        critical_issues.append((
            "Unverified Template Tax Terms (EU Intrastat)",
            "Contains European Union tax terms ('Intrastat returns') that do not apply to the GCC/UAE. This indicates unverified template copy-pasting, damaging recruiter trust."
        ))

    breakdown.append((
        "Industry Keywords & Tools",
        f"{int((p4_score/20)*100)}%",
        "Excellent" if p4_score >= 17 else ("Good" if p4_score >= 13 else "Poor"),
        "Saturated with industry-standard terminology" if p4_score >= 17 else "Missing core tools, software, or domain acronyms.",
        "#16A34A" if p4_score >= 17 else ("#D97706" if p4_score >= 13 else "#DC2626")
    ))

    # Pillar 5: Syntax, Grammar & Clutter
    p5_score = 15
    if re.search(r'\b(i am|i have|i successfully|i effectively|my experience)\b', text_lower):
        p5_score -= 4
        critical_issues.append((
            "Amateur First-Person Narrative ('I' Statements)",
            "The summary or experience relies on first-person pronouns ('I', 'my'). Executive resume standards require an authoritative third-person professional tone."
        ))

    common_typos = {
        "resturant": "restaurant", "cirtified": "certified", "orginal": "original",
        "collage": "college", "encured": "ensured", "preperation": "preparation",
        "systerns": "systems", "material status": "marital status"
    }
    found_typos = [f"'{t}'" for t in common_typos if t in text_lower]
    if found_typos:
        p5_score -= 5
        critical_issues.append((
            f"Noticeable Spelling Errors ({', '.join(found_typos[:3])})",
            "Glaring spelling mistakes were detected. Typos contradict claims of 'attention to detail' and trigger automated screening red flags."
        ))

    if "i hereby declare" in text_lower or "hobbies" in text_lower or "sslc" in text_lower:
        p5_score -= 3

    breakdown.append((
        "Content Accuracy & Cleanliness",
        f"{int((p5_score/15)*100)}%",
        "Exceptional" if p5_score >= 13 else ("Fair" if p5_score >= 9 else "Critical"),
        "Clean professional syntax" if p5_score >= 13 else "Contains spelling slips, first-person pronouns, or clutter.",
        "#16A34A" if p5_score >= 13 else ("#D97706" if p5_score >= 9 else "#DC2626")
    ))

    total_score = p1_score + p2_score + p3_score + p4_score + p5_score
    total_score = max(20, min(total_score, 98))

    if total_score >= 80:
        status_text = "INTERVIEW READY (HIGH PARSER COMPATIBILITY)"
    elif total_score >= 50:
        status_text = "MODERATE RISK (NEEDS RECONSTRUCTION)"
    else:
        status_text = "CRITICAL RISK (IMMEDIATE REJECTION HAZARD)"

    action_plan = [
        ("Single-Column ATS Architecture", "Rebuild the layout into an unencumbered single-column format without tables, photos, or graphic sidebars for 100% linear parsing."),
        ("Quantify Commercial Operations", "Incorporate numerical metrics (volume handled, revenue impact, team size, turnaround speed) into bullet points."),
        ("Standardize Date Formats", "Ensure every employment position features standard calendar month/year ranges (MM/YYYY – Present)."),
        ("Keyword & Regulatory Alignment", f"Saturate skills with verified tools, certifications, and licenses required for {target_role}.")
    ]

    return total_score, status_text, breakdown, critical_issues[:4], action_plan

# --- 2. ReportLab PDF Generator ---
def generate_pdf_report(candidate_name, target_role, score, status_text, breakdown, critical_issues, action_plan, logo_path="adson_logo.png"):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        leftMargin=30,
        rightMargin=30,
        topMargin=22,
        bottomMargin=22
    )

    brand_blue = colors.HexColor("#0068FF")
    brand_dark_blue = colors.HexColor("#004ECC")
    brand_light_bg = colors.HexColor("#F0F7FF")
    brand_border = colors.HexColor("#BFDBFE")
    text_dark = colors.HexColor("#0F172A")
    text_muted = colors.HexColor("#475569")

    if score >= 80:
        score_color = colors.HexColor("#16A34A")
        bg_score = colors.HexColor("#F0FDF4")
        border_score = colors.HexColor("#BBF7D0")
    elif score >= 50:
        score_color = colors.HexColor("#D97706")
        bg_score = colors.HexColor("#FFFBEB")
        border_score = colors.HexColor("#FDE68A")
    else:
        score_color = colors.HexColor("#DC2626")
        bg_score = colors.HexColor("#FEF2F2")
        border_score = colors.HexColor("#FECACA")

    brand_title = ParagraphStyle('BrandTitle', fontName='Helvetica-Bold', fontSize=13, leading=15, textColor=brand_blue)
    meta_text = ParagraphStyle('MetaText', fontName='Helvetica', fontSize=8, leading=11.5, textColor=text_dark)
    h2_style = ParagraphStyle('SectionHeader', fontName='Helvetica-Bold', fontSize=9.8, leading=12.5, textColor=brand_dark_blue, spaceBefore=3, spaceAfter=3)
    body_style = ParagraphStyle('BodyDark', fontName='Helvetica', fontSize=8, leading=11, textColor=text_dark)
    body_bold = ParagraphStyle('BodyDarkBold', parent=body_style, fontName='Helvetica-Bold')
    issue_title = ParagraphStyle('IssueTitle', fontName='Helvetica-Bold', fontSize=8.3, leading=11, textColor=brand_dark_blue)
    issue_desc = ParagraphStyle('IssueDesc', fontName='Helvetica', fontSize=7.8, leading=10.5, textColor=text_dark)

    elements = []

    # Header
    if os.path.exists(logo_path):
        logo_img = RLImage(logo_path, width=52, height=52)
    else:
        logo_img = Paragraph("<b>ADSON</b>", brand_title)

    header_left = [[logo_img, Paragraph("<b>ADSON</b><br/><font color='#475569' size='8'>Digital Marketing & Career Solution</font><br/><font color='#0068FF' size='8.5'><b>ATS RESUME DIAGNOSTIC EVALUATION</b></font>", brand_title)]]
    header_left_table = Table(header_left, colWidths=[58, 226])
    header_left_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 0)]))

    header_right_content = Paragraph(f"<para align='right'><b>Candidate:</b> {candidate_name}<br/><b>Target Role:</b> {target_role}<br/><b>WhatsApp:</b> +91 790 740 7290<br/><b>Official Email:</b> hello.adsondigital@gmail.com</para>", meta_text)
    header_table = Table([[header_left_table, header_right_content]], colWidths=[290, 262])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
    elements.append(header_table)
    elements.append(Spacer(1, 3))
    elements.append(HRFlowable(width="100%", thickness=2, color=brand_blue, spaceAfter=5))

    # Scorecard
    score_data = [[
        Paragraph("<b>EXECUTIVE ATS COMPLIANCE RATING</b><br/><font size='7.5' color='#475569'>Benchmarked against standard corporate ATS screening software. Shortlisting threshold is 80%+.</font>", body_style),
        Paragraph(f"<para align='center'><font size='19' color='{score_color.hexval()}'><b>{score} / 100</b></font><br/><font size='7.5' color='{score_color.hexval()}'><b>{status_text}</b></font></para>", body_style)
    ]]
    score_table = Table(score_data, colWidths=[376, 176])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_score),
        ('BOX', (0,0), (-1,-1), 1, border_score),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 4))

    # Metrics Breakdown
    elements.append(Paragraph("<b>ATS Evaluation Metrics Breakdown</b>", h2_style))
    b_data = [[Paragraph("<b>Category</b>", body_bold), Paragraph("<b>Score</b>", body_bold), Paragraph("<b>Status</b>", body_bold), Paragraph("<b>Recruiter & ATS Impact</b>", body_bold)]]
    for cat, sc, st_val, impact, col in breakdown:
        b_data.append([Paragraph(cat, body_style), Paragraph(f"<font color='{col}'><b>{sc}</b></font>", body_style), Paragraph(st_val, body_style), Paragraph(impact, body_style)])
    b_table = Table(b_data, colWidths=[140, 50, 56, 306])
    b_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")), ('TOPPADDING', (0,0), (-1,-1), 2.5), ('BOTTOMPADDING', (0,0), (-1,-1), 2.5)]))
    elements.append(b_table)
    elements.append(Spacer(1, 4))

    # Critical Findings
    elements.append(Paragraph("<b>Detailed Diagnostic Findings & System Errors</b>", h2_style))
    issue_data = []
    for title, desc in critical_issues:
        issue_data.append([Paragraph(f"<b>{title}</b>", issue_title)])
        issue_data.append([Paragraph(desc, issue_desc)])
    issue_table = Table(issue_data, colWidths=[552])
    issue_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")), ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")), ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
    elements.append(issue_table)
    elements.append(Spacer(1, 4))

    # Action Plan
    elements.append(Paragraph("<b>Recommended Reconstruction & Optimization Plan</b>", h2_style))
    recs_text = "<br/>".join([f"<b>• {title}:</b> {desc}" for title, desc in action_plan])
    plan_table = Table([[Paragraph(recs_text, body_style)]], colWidths=[552])
    plan_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), brand_light_bg), ('BOX', (0,0), (-1,-1), 1, brand_border), ('TOPPADDING', (0,0), (-1,-1), 3.5), ('BOTTOMPADDING', (0,0), (-1,-1), 3.5)]))
    elements.append(plan_table)
    elements.append(Spacer(1, 5))

    # Footer
    footer_text = Paragraph("<para align='center'><font color='#FFFFFF' size='7.5'><b>ADSON — Digital Marketing & Career Solution</b> | WhatsApp: <b>+91 790 740 7290</b> | Email: <b>hello.adsondigital@gmail.com</b></font></para>", body_style)
    footer_table = Table([[footer_text]], colWidths=[552])
    footer_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), brand_blue), ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    elements.append(footer_table)

    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer

# --- 3. Streamlit Interface ---
st.title("ADSON — ATS CV Diagnostic Engine")
st.caption("Official Applicant Tracking System (ATS) Scanner & Diagnostic Platform")

col1, col2 = st.columns([1, 1])
with col1:
    candidate_name = st.text_input("Candidate Full Name", placeholder="e.g. Muhammed Kasim A H")
with col2:
    target_role = st.text_input("Target Job Title & Industry", placeholder="e.g. Operations Manager (UAE)")

uploaded_file = st.file_uploader("Upload Candidate CV (PDF format)", type=["pdf"])

if uploaded_file and candidate_name and target_role:
    if st.button("🚀 Run Full ATS Diagnostic Audit", use_container_width=True):
        with st.spinner("Analyzing document structure, keywords, metrics, and dates..."):
            pdf_reader = pypdf.PdfReader(uploaded_file)
            num_pages = len(pdf_reader.pages)
            extracted_text = ""
            for page in pdf_reader.pages:
                extracted_text += page.extract_text() or ""

            score, status_text, breakdown, critical_issues, action_plan = evaluate_cv_ats(
                extracted_text, num_pages, target_role
            )

            st.divider()
            res_col1, res_col2 = st.columns([1, 2])
            with res_col1:
                st.metric("ATS Compatibility Score", f"{score} / 100")
                if score >= 80:
                    st.success(f"Status: {status_text}")
                elif score >= 50:
                    st.warning(f"Status: {status_text}")
                else:
                    st.error(f"Status: {status_text}")

            with res_col2:
                st.write("### Evaluation Breakdown")
                for cat, sc, st_val, imp, col in breakdown:
                    st.write(f"- **{cat}**: `{sc}` ({st_val}) — {imp}")

            st.write("### ⚠️ Key Deficiencies Identified")
            for title, desc in critical_issues:
                st.error(f"**{title}**: {desc}")

            pdf_bytes = generate_pdf_report(
                candidate_name, target_role, score, status_text, breakdown, critical_issues, action_plan
            )

            st.download_button(
                label="📥 Download Official ADSON Diagnostic PDF Report",
                data=pdf_bytes,
                file_name=f"ADSON_ATS_Report_{candidate_name.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.write("### 💬 Ready-to-Send Client Message (WhatsApp / Email)")
            whatsapp_msg = f"""Hi {candidate_name.split()[0]},

Thank you for sharing your CV. We conducted a comprehensive diagnostic scan using standard ATS (Applicant Tracking System) software to evaluate how corporate recruitment filters screen your profile.

📊 Current ATS Compatibility Score: {score} / 100 ({status_text})

Key Areas Identified for Improvement:
"""
            for i, (title, desc) in enumerate(critical_issues, 1):
                whatsapp_msg += f"{i}. {title}: {desc}\n"

            whatsapp_msg += f"""
Attached is your full ATS Diagnostic Report. With a professional reconstruction to resolve these issues and optimize your keywords, your profile can easily achieve a 90%+ interview-ready score. Let us know if you would like to proceed with our rewrite service."""

            st.text_area("Copy and Send to Client:", whatsapp_msg, height=220)
