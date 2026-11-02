# build_capstone_report.py
"""
Master compiler script for MergeMind Final Capstone Project Report.
Generates:
- MergeMind_Final_Capstone_Report.docx (LaTeX/IEEE-styled docx)
- MergeMind_Final_Capstone_Report.pdf (typeset via Word COM automation)
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Import content modules
import capstone_content_prelims as prelims
import capstone_content_ch1_ch3 as ch1_3
import capstone_content_ch4_ch6 as ch4_6
import capstone_content_ch7_ch9 as ch7_9
import capstone_content_ch10_ch14 as ch10_14
import capstone_content_appendices as appx
from docx_helpers import add_page_number, set_cell_margins, set_cell_background, set_table_borders

DOCS_DIR = r"C:\Users\lucky\Downloads\mergemind\docs\final_capstone_report"
DIAGRAMS_DIR = os.path.join(DOCS_DIR, "MergeMind_Diagrams")
ASSETS_DIR = os.path.join(DOCS_DIR, "MergeMind_Report_Assets")
DOCX_PATH = os.path.join(DOCS_DIR, "MergeMind_Final_Capstone_Report.docx")
PDF_PATH = os.path.join(DOCS_DIR, "MergeMind_Final_Capstone_Report.pdf")

def create_report():
    print("Initializing MergeMind Final Capstone Report Document...")
    doc = docx.Document()

    # Configure Document Margins (A4, 1-inch margins)
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

    # Base Normal Style
    normal_style = doc.styles['Normal']
    normal_font = normal_style.font
    normal_font.name = 'Times New Roman'
    normal_font.size = Pt(12)
    normal_font.color.rgb = RGBColor(30, 41, 59) # Slate 800
    normal_style.paragraph_format.line_spacing = 1.5
    normal_style.paragraph_format.space_after = Pt(6)
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Configure Header / Footer
    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hrun = hp.add_run("MergeMind: Final Capstone Project Report | Woxsen University")
    hrun.font.name = 'Times New Roman'
    hrun.font.size = Pt(8.5)
    hrun.font.color.rgb = RGBColor(100, 116, 139)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    frun = fp.add_run("Page ")
    frun.font.name = 'Times New Roman'
    frun.font.size = Pt(10)
    frun.font.color.rgb = RGBColor(100, 116, 139)
    add_page_number(frun)

    # ---------------------------------------------------------
    # Helper functions for structured elements
    # ---------------------------------------------------------
    def add_p(text, bold_prefix="", italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(space_after)
        if bold_prefix:
            r_b = p.add_run(bold_prefix)
            r_b.bold = True
            r_b.font.name = 'Times New Roman'
            r_b.font.size = Pt(12)
            r_b.font.color.rgb = RGBColor(15, 23, 42)
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12)
        r.italic = italic
        r.font.color.rgb = RGBColor(30, 41, 59)
        return p

    def add_heading_1(text):
        doc.add_page_break()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(12)
        r = p.add_run(text)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(18)
        r.font.color.rgb = RGBColor(15, 23, 42)
        return p

    def add_heading_2(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(text)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(14)
        r.font.color.rgb = RGBColor(30, 41, 59)
        return p

    def add_heading_3(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(text)
        r.bold = True
        r.italic = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12)
        r.font.color.rgb = RGBColor(51, 65, 85)
        return p

    def add_table_element(caption, headers, rows):
        # Table Caption
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_cap.paragraph_format.space_before = Pt(10)
        p_cap.paragraph_format.space_after = Pt(4)
        rc = p_cap.add_run(caption)
        rc.bold = True
        rc.font.name = 'Times New Roman'
        rc.font.size = Pt(10.5)
        rc.font.color.rgb = RGBColor(15, 23, 42)

        # Table
        num_cols = len(headers)
        table = doc.add_table(rows=len(rows) + 1, cols=num_cols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(table)

        # Header Row
        hdr_cells = table.rows[0].cells
        for i, h in enumerate(headers):
            hdr_cells[i].text = h
            set_cell_background(hdr_cells[i], "F1F5F9") # slate-100
            set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
            p = hdr_cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(0)
            r = p.runs[0]
            r.bold = True
            r.font.name = 'Times New Roman'
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(15, 23, 42)

        # Data Rows
        for r_idx, row_data in enumerate(rows):
            row_cells = table.rows[r_idx + 1].cells
            bg_color = "FFFFFF" if r_idx % 2 == 0 else "F8FAFC"
            for c_idx, cell_value in enumerate(row_data):
                row_cells[c_idx].text = str(cell_value)
                set_cell_background(row_cells[c_idx], bg_color)
                set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
                p = row_cells[c_idx].paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_after = Pt(0)
                if p.runs:
                    r = p.runs[0]
                    r.font.name = 'Times New Roman'
                    r.font.size = Pt(9)
                    r.font.color.rgb = RGBColor(51, 65, 85)

        # Space after table
        p_space = doc.add_paragraph()
        p_space.paragraph_format.space_before = Pt(4)
        p_space.paragraph_format.space_after = Pt(8)

    def add_figure_element(img_filename, caption, width=Inches(6.0)):
        # Auto-convert .jpg to .png if png exists
        base, _ = os.path.splitext(img_filename)
        candidates = [
            os.path.join(DIAGRAMS_DIR, f"{base}.png"),
            os.path.join(ASSETS_DIR, f"{base}.png"),
            os.path.join(DIAGRAMS_DIR, img_filename),
            os.path.join(ASSETS_DIR, img_filename)
        ]
        img_path = None
        for c in candidates:
            if os.path.exists(c):
                img_path = c
                break

        if img_path and os.path.exists(img_path):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(8)
            p_img.paragraph_format.space_after = Pt(4)
            p_img.add_run().add_picture(img_path, width=width)

            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_before = Pt(2)
            p_cap.paragraph_format.space_after = Pt(10)
            rc = p_cap.add_run(caption)
            rc.bold = True
            rc.font.name = 'Times New Roman'
            rc.font.size = Pt(10)
            rc.font.color.rgb = RGBColor(51, 65, 85)
        else:
            print(f"Warning: Image file not found: {img_filename}")

    # =========================================================
    # PRELIMINARY PAGES
    # =========================================================
    print("Writing Preliminary Pages...")
    # Cover Page
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(36)
    p_title.paragraph_format.space_after = Pt(12)
    rt = p_title.add_run(prelims.TITLE_DATA["project_title"])
    rt.bold = True
    rt.font.name = 'Times New Roman'
    rt.font.size = Pt(19)
    rt.font.color.rgb = RGBColor(15, 23, 42)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(32)
    rs = p_sub.add_run(prelims.TITLE_DATA["subtitle"])
    rs.italic = True
    rs.font.name = 'Times New Roman'
    rs.font.size = Pt(12.5)
    rs.font.color.rgb = RGBColor(71, 85, 105)

    p_rep = doc.add_paragraph()
    p_rep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_rep.paragraph_format.space_after = Pt(24)
    r_rep = p_rep.add_run("A FINAL CAPSTONE PROJECT REPORT\nsubmitted in partial fulfillment of the requirements for the award of the degree of\n")
    r_rep.font.name = 'Times New Roman'
    r_rep.font.size = Pt(11)
    r_deg = p_rep.add_run(prelims.TITLE_DATA["degree"])
    r_deg.bold = True
    r_deg.font.name = 'Times New Roman'
    r_deg.font.size = Pt(12.5)

    # Author and Supervisor Table
    auth_table = doc.add_table(rows=1, cols=2)
    auth_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(auth_table, top_sz=0, bottom_sz=0)
    c1, c2 = auth_table.rows[0].cells
    c1.text = f"Submitted by:\n{prelims.TITLE_DATA['student_name']}\nRoll No: {prelims.TITLE_DATA['roll_number']}"
    c2.text = f"Under the Guidance of:\n{prelims.TITLE_DATA['supervisor_name']}\n{prelims.TITLE_DATA['supervisor_title']}"
    for cell in [c1, c2]:
        p = cell.paragraphs[0]
        p.paragraph_format.line_spacing = 1.3
        for r in p.runs:
            r.font.name = 'Times New Roman'
            r.font.size = Pt(11)

    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_before = Pt(40)
    p_inst.paragraph_format.space_after = Pt(4)
    r_inst = p_inst.add_run(f"{prelims.TITLE_DATA['institution']}\n{prelims.TITLE_DATA['location']}\n{prelims.TITLE_DATA['academic_year']}")
    r_inst.bold = True
    r_inst.font.name = 'Times New Roman'
    r_inst.font.size = Pt(12)

    # Certificate Page
    add_heading_1("CERTIFICATE OF AUTHENTICITY")
    for para in prelims.CERTIFICATE_TEXT.split("\n\n"):
        add_p(para)

    # Signatures Table
    doc.add_paragraph().paragraph_format.space_before = Pt(40)
    sig_table = doc.add_table(rows=1, cols=3)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(sig_table, top_sz=0, bottom_sz=0)
    s1, s2, s3 = sig_table.rows[0].cells
    s1.text = f"_____________________\n{prelims.TITLE_DATA['supervisor_name']}\nProject Supervisor"
    s2.text = f"_____________________\n{prelims.TITLE_DATA['hod_name']}\nHead of Department"
    s3.text = "_____________________\nExternal Examiner\nViva Voce Committee"
    for cell in [s1, s2, s3]:
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.2
        for r in p.runs:
            r.font.name = 'Times New Roman'
            r.font.size = Pt(9.5)

    # Student Declaration
    add_heading_1("STUDENT DECLARATION")
    for para in prelims.DECLARATION_TEXT.split("\n\n"):
        add_p(para)
    doc.add_paragraph().paragraph_format.space_before = Pt(30)
    p_dec_sig = doc.add_paragraph()
    p_dec_sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_ds = p_dec_sig.add_run(f"_____________________________\n{prelims.TITLE_DATA['student_name']}\n{prelims.TITLE_DATA['roll_number']}\nDate: {prelims.TITLE_DATA['submission_date']}")
    r_ds.font.name = 'Times New Roman'
    r_ds.font.size = Pt(11)

    # Acknowledgements
    add_heading_1("ACKNOWLEDGEMENTS")
    for para in prelims.ACKNOWLEDGEMENTS_TEXT.split("\n\n"):
        add_p(para)

    # Abstract
    add_heading_1("ABSTRACT")
    for para in prelims.ABSTRACT_TEXT.split("\n\n"):
        add_p(para)

    # Abbreviations
    add_heading_1("LIST OF ABBREVIATIONS")
    add_table_element("Table P.1: Standard Abbreviations and Acronyms Used in this Dissertation",
                      ["Acronym", "Full Expanded Definition"],
                      prelims.ABBREVIATIONS)

    # Table of Contents Outline
    add_heading_1("TABLE OF CONTENTS")
    toc_entries = [
        ("Preliminary Pages", "i – viii"),
        ("Chapter 1: Introduction", "1"),
        ("Chapter 2: Problem Definition and Requirements Analysis", "6"),
        ("Chapter 3: Literature Review and Technical Foundations", "12"),
        ("Chapter 4: Proposed System and Architecture", "18"),
        ("Chapter 5: Multi-Factor Health Telemetry and Scoring Methodology", "25"),
        ("Chapter 6: Enterprise Security Posture and Governance Engine", "30"),
        ("Chapter 7: System Implementation and Module Breakdown", "35"),
        ("Chapter 8: Database Design and Data Dictionary", "42"),
        ("Chapter 9: API Design and Interface Specifications", "47"),
        ("Chapter 10: AI Integration and Prompt Engineering", "52"),
        ("Chapter 11: Testing, Verification and Quality Assurance", "57"),
        ("Chapter 12: Results, Discussion and Comparative Evaluation", "63"),
        ("Chapter 13: Security, Reliability, Limitations and Future Scope", "69"),
        ("Chapter 14: Conclusion", "73"),
        ("References (IEEE Format)", "75"),
        ("Appendix A: Deployment Configuration and Environment Variables", "78"),
        ("Appendix B: Complete 43 Security Checks Master Reference Table", "80"),
        ("Appendix C: Complete OpenAPI 3.0 Endpoints Specification", "83"),
        ("Appendix D: Sample AI Remediation Prompt and Generated Diff", "85"),
        ("Appendix E: Pytest 185 Automated Test Suite Execution Log Trace", "87")
    ]
    add_table_element("Table P.2: Summary Table of Contents and Page Mappings",
                      ["Chapter / Section Title", "Starting Page"],
                      toc_entries)

    # =========================================================
    # CHAPTERS 1 TO 3
    # =========================================================
    print("Writing Chapters 1 to 3...")
    # Chapter 1
    add_heading_1(f"Chapter 1: {ch1_3.CHAPTER_1_CONTENT['title']}")
    for sec in ch1_3.CHAPTER_1_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)

    # Chapter 2
    add_heading_1(f"Chapter 2: {ch1_3.CHAPTER_2_CONTENT['title']}")
    for sec in ch1_3.CHAPTER_2_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)
        if sec.get('table_id') == "FR_TABLE":
            add_table_element("Table 2.1: Comprehensive Functional Requirements Specification (FR-01 to FR-16)",
                              ["Requirement ID", "Functional Module", "Operational Specification"],
                              ch1_3.FR_TABLE_ROWS)
        elif sec.get('table_id') == "NFR_TABLE":
            add_table_element("Table 2.2: Non-Functional Requirements Specification (NFR-01 to NFR-08)",
                              ["Requirement ID", "Quality Dimension", "Guaranteed Quality Standard & Target Metric"],
                              ch1_3.NFR_TABLE_ROWS)

    # Chapter 3
    add_heading_1(f"Chapter 3: {ch1_3.CHAPTER_3_CONTENT['title']}")
    for sec in ch1_3.CHAPTER_3_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)
        if sec.get('table_id') == "COMPARE_TABLE":
            add_table_element("Table 3.1: Comparative Analysis: Conventional DevOps Tools vs MergeMind",
                              ch1_3.COMPARE_TABLE_ROWS[0],
                              ch1_3.COMPARE_TABLE_ROWS[1:])

    # =========================================================
    # CHAPTERS 4 TO 6
    # =========================================================
    print("Writing Chapters 4 to 6...")
    # Chapter 4
    add_heading_1(f"Chapter 4: {ch4_6.CHAPTER_4_CONTENT['title']}")
    for sec in ch4_6.CHAPTER_4_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)
        if 'figure_id' in sec:
            add_figure_element(sec['figure_id'], sec['figure_caption'])

    # Chapter 5
    add_heading_1(f"Chapter 5: {ch4_6.CHAPTER_5_CONTENT['title']}")
    for sec in ch4_6.CHAPTER_5_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)
        if sec.get('table_id') == "HEALTH_VARIANCE_TABLE":
            add_table_element("Table 5.1: Multi-Factor Health Telemetry Evaluation across Disparate Repositories",
                              ch4_6.HEALTH_VARIANCE_TABLE_ROWS[0],
                              ch4_6.HEALTH_VARIANCE_TABLE_ROWS[1:])
        if 'figure_id' in sec:
            add_figure_element(sec['figure_id'], sec['figure_caption'])

    # Chapter 6
    add_heading_1(f"Chapter 6: {ch4_6.CHAPTER_6_CONTENT['title']}")
    for sec in ch4_6.CHAPTER_6_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)
        if 'figure_id' in sec:
            add_figure_element(sec['figure_id'], sec['figure_caption'])

    # =========================================================
    # CHAPTERS 7 TO 9
    # =========================================================
    print("Writing Chapters 7 to 9...")
    # Chapter 7
    add_heading_1(f"Chapter 7: {ch7_9.CHAPTER_7_CONTENT['title']}")
    for sec in ch7_9.CHAPTER_7_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)
        if 'figure_id' in sec:
            add_figure_element(sec['figure_id'], sec['figure_caption'])

    # Chapter 8
    add_heading_1(f"Chapter 8: {ch7_9.CHAPTER_8_CONTENT['title']}")
    for sec in ch7_9.CHAPTER_8_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)
        if 'figure_id' in sec:
            add_figure_element(sec['figure_id'], sec['figure_caption'])
        if sec.get('table_id') == "DATA_DICT_REPOS":
            add_table_element("Table 8.1: Data Dictionary for 'repositories' Entity",
                              ch7_9.DATA_DICT_REPOS_ROWS[0],
                              ch7_9.DATA_DICT_REPOS_ROWS[1:])
        elif sec.get('table_id') == "DATA_DICT_HEALTH":
            add_table_element("Table 8.2: Data Dictionary for 'health_assessments' Entity",
                              ch7_9.DATA_DICT_HEALTH_ROWS[0],
                              ch7_9.DATA_DICT_HEALTH_ROWS[1:])
        elif sec.get('table_id') == "DATA_DICT_CI_REMED":
            add_table_element("Table 8.3: Data Dictionary for 'ci_failures' and 'remediation_proposals' Entities",
                              ch7_9.DATA_DICT_CI_REMED_ROWS[0],
                              ch7_9.DATA_DICT_CI_REMED_ROWS[1:])

    # Chapter 9
    add_heading_1(f"Chapter 9: {ch7_9.CHAPTER_9_CONTENT['title']}")
    for sec in ch7_9.CHAPTER_9_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)
        if sec.get('table_id') == "API_ENDPOINT_TABLE":
            add_table_element("Table 9.1: Comprehensive REST API Endpoint Reference Specification",
                              ch7_9.API_ENDPOINT_TABLE_ROWS[0],
                              ch7_9.API_ENDPOINT_TABLE_ROWS[1:])

    # =========================================================
    # CHAPTERS 10 TO 14
    # =========================================================
    print("Writing Chapters 10 to 14...")
    # Chapter 10
    add_heading_1(f"Chapter 10: {ch10_14.CHAPTER_10_CONTENT['title']}")
    for sec in ch10_14.CHAPTER_10_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)
        if 'figure_id' in sec:
            add_figure_element(sec['figure_id'], sec['figure_caption'])

    # Chapter 11
    add_heading_1(f"Chapter 11: {ch10_14.CHAPTER_11_CONTENT['title']}")
    for sec in ch10_14.CHAPTER_11_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)
        if sec.get('table_id') == "TEST_BREAKDOWN_TABLE":
            add_table_element("Table 11.1: Automated Verification Test Suite Breakdown across All 8 Modules (185 Passing Tests)",
                              ch10_14.TEST_BREAKDOWN_TABLE_ROWS[0],
                              ch10_14.TEST_BREAKDOWN_TABLE_ROWS[1:])
        elif sec.get('table_id') == "TEST_CASES_TABLE":
            add_table_element("Table 11.2: Representative Automated Test Case Specifications and Verification Results",
                              ch10_14.TEST_CASES_TABLE_ROWS[0],
                              ch10_14.TEST_CASES_TABLE_ROWS[1:])

    # Chapter 12
    add_heading_1(f"Chapter 12: {ch10_14.CHAPTER_12_CONTENT['title']}")
    for sec in ch10_14.CHAPTER_12_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)
        if sec.get('table_id') == "BENCHMARK_TABLE":
            add_table_element("Table 12.1: Operational Benchmark: Conventional Manual Workflow vs MergeMind Platform",
                              ch10_14.BENCHMARK_TABLE_ROWS[0],
                              ch10_14.BENCHMARK_TABLE_ROWS[1:])

    # Chapter 13
    add_heading_1(f"Chapter 13: {ch10_14.CHAPTER_13_CONTENT['title']}")
    for sec in ch10_14.CHAPTER_13_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)

    # Chapter 14
    add_heading_1(f"Chapter 14: {ch10_14.CHAPTER_14_CONTENT['title']}")
    for sec in ch10_14.CHAPTER_14_CONTENT['sections']:
        add_heading_2(f"{sec['num']} {sec['title']}")
        for para in sec['body'].split("\n\n"):
            add_p(para)

    # =========================================================
    # REFERENCES & APPENDICES
    # =========================================================
    print("Writing References and Appendices...")
    add_heading_1("REFERENCES")
    for ref in appx.REFERENCES:
        p_ref = doc.add_paragraph()
        p_ref.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_ref.paragraph_format.line_spacing = 1.15
        p_ref.paragraph_format.space_after = Pt(4)
        r = p_ref.add_run(ref)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(10)

    # Appendix A
    add_heading_1(appx.APPENDIX_A_CONTENT['title'])
    for para in appx.APPENDIX_A_CONTENT['text'].split("\n\n"):
        add_p(para)

    # Appendix B
    add_heading_1("Appendix B: Complete 43 Security Checks Master Reference Table")
    add_table_element("Table B.1: Enterprise Security Posture 43-Check Master Specification",
                      appx.APPENDIX_B_ROWS[0],
                      appx.APPENDIX_B_ROWS[1:])

    # Appendix C
    add_heading_1(appx.APPENDIX_C_CONTENT['title'])
    for para in appx.APPENDIX_C_CONTENT['text'].split("\n\n"):
        add_p(para)

    # Appendix D
    add_heading_1(appx.APPENDIX_D_CONTENT['title'])
    for para in appx.APPENDIX_D_CONTENT['text'].split("\n\n"):
        add_p(para)

    # Appendix E
    add_heading_1(appx.APPENDIX_E_CONTENT['title'])
    for para in appx.APPENDIX_E_CONTENT['text'].split("\n\n"):
        add_p(para)

    # Save DOCX
    print(f"Saving compiled DOCX to {DOCX_PATH}...")
    doc.save(DOCX_PATH)
    print("DOCX successfully generated and saved!")

if __name__ == "__main__":
    create_report()
