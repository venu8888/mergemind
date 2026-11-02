# MergeMind Final Capstone Project Report — LaTeX Dissertation Package

**Institution:** School of Technology, Woxsen University  
**Degree:** Bachelor of Technology in Computer Science and Engineering  
**Academic Year:** 2025 – 2026  
**Document Title:** *MergeMind: An AI-Powered GitHub Repository Intelligence and Automated Remediation Platform*

---

## 1. Package Overview

This repository contains the complete, publication-grade, Overleaf-ready LaTeX capstone project for **MergeMind**. It is structured according to formal IEEE academic dissertation guidelines, targeting approximately **40–45 pages of meaningful technical content** (excluding appendices).

A pre-packaged archive ready for instant Overleaf import is provided as:
`MergeMind_LaTeX_Project.zip`

---

## 2. Directory Structure

```text
final_capstone_report/
│
├── main.tex                             # Controlling LaTeX master document
├── references.bib                       # Complete IEEE BibTeX bibliography (30 entries)
├── README.md                            # Comprehensive Overleaf & compilation guide
├── MergeMind_LaTeX_Project.zip          # Self-contained archive for Overleaf upload
├── MergeMind_Final_Capstone_Report.pdf  # Pre-compiled 78-page dissertation reference
├── MergeMind_Final_Capstone_Report.docx # Editable Microsoft Word dissertation reference
│
├── chapters/                            # Core technical chapters (40-45 pages)
│   ├── chapter1_introduction.tex        # Background, ecosystem, challenges, objectives
│   ├── chapter2_literature_review.tex   # Theory of SAST, DVCS, McCabe, APR, containerization
│   ├── chapter3_system_design.tex       # Multi-tier topology, requirements, scoring methodology
│   ├── chapter4_implementation.tex      # File-by-file audit of all 8 backend subsystems
│   ├── chapter5_testing_results.tex     # 185 passing tests, error injection, empirical results
│   ├── chapter6_discussion_evaluation.tex# Contamination elimination, APR accuracy, benchmarks
│   └── chapter7_conclusion_future_scope.tex # Summary, threat model, limitations, future scope
│
├── preliminary/                         # Front matter (Roman numeral pagination)
│   ├── title_page.tex                   # Formal Woxsen University title page
│   ├── certificate.tex                  # Certificate of authenticity with signature blocks
│   ├── declaration.tex                  # Student authorship declaration
│   ├── acknowledgement.tex              # Formal faculty, university & community acknowledgements
│   ├── abstract.tex                     # Structured academic abstract
│   ├── abbreviations.tex                # 40 standard technical abbreviations table
│   └── lists.tex                        # Table of contents, list of figures, list of tables
│
├── images/                              # Standalone high-resolution report illustrations
│   ├── architecture/                    # Overall, component, auth, deployment, security topologies
│   ├── workflows/                       # Health assessment, PR review, CI failure, remediation loops
│   ├── database/                        # PostgreSQL relational Entity-Relationship diagram
│   ├── diagrams/                        # Use case, sequence, activity diagrams
│   └── screenshots/                     # Real telemetry, diff viewers, ingestion modal UI captures
│
└── appendices/                          # Supplementary technical content
    ├── appendix_a_technology_stack.tex  # Full dependency matrix and production .env configuration
    ├── appendix_b_api_reference.tex     # OpenAPI 3.0 REST endpoint reference and JSON schemas
    ├── appendix_c_database_design.tex   # Complete physical data dictionaries for all tables
    ├── appendix_d_test_cases.tex        # Master test matrix and verbatim 185-test Pytest trace
    └── appendix_e_user_manual.tex       # Deployment instructions, Docker Compose, and web guide
```

---

## 3. How to Upload and Compile in Overleaf

Follow these simple steps to import and compile the project on [Overleaf](https://www.overleaf.com):

1. **Log in to Overleaf:** Navigate to your Overleaf dashboard.
2. **Create New Project:** Click the **`New Project`** button in the top left corner.
3. **Upload ZIP:** Select **`Upload Project`** from the dropdown menu.
4. **Choose File:** Drag and drop `MergeMind_LaTeX_Project.zip` (or browse to `mergemind/docs/final_capstone_report/MergeMind_LaTeX_Project.zip`).
5. **Verify Compiler Settings:**
   - Click the **`Menu`** button in the top left of the Overleaf editor.
   - Under **Settings**, confirm the following:
     - **Compiler:** `pdfLaTeX` (recommended) or `XeLaTeX`
     - **TeX Live Version:** `2023` or `2024`
     - **Main document:** `main.tex`
6. **Compile:** Click **`Recompile`** (or press `Ctrl + Enter`). Overleaf will compile the entire dissertation and display the PDF preview with zero errors.

---

## 4. Customizing Institutional and Candidate Details

Before final submission for your viva examination, open the following files in the `preliminary/` folder and replace the bracketed placeholders with your personal details:

1. **Candidate & Guide Details (`preliminary/title_page.tex` & `preliminary/certificate.tex`):**
   - Replace `[Candidate Full Name]` with your actual legal name.
   - Replace `[Student Roll / Registration No.]` with your Woxsen university registration number.
   - Replace `[Faculty Guide Name, Ph.D.]` with your assigned project supervisor's name.
   - Replace `[Head of Department Name, Ph.D.]` with the name of the Head of the CSE Department.
2. **Student Declaration (`preliminary/declaration.tex`):**
   - Confirm your name and roll number in the declaration signature block.
3. **Hyperref PDF Metadata (`main.tex`):**
   - Update `pdfauthor={[Candidate Full Name]}` in the `\hypersetup` block.

---

## 5. Modifying or Adding New Diagrams

All report figures are stored in the `images/` directory using relative paths:
- **Architecture Diagrams:** Place in `images/architecture/`
- **Workflow Diagrams:** Place in `images/workflows/`
- **Database Diagrams:** Place in `images/database/`
- **Diagrams / Charts:** Place in `images/diagrams/`
- **Application Screenshots:** Place in `images/screenshots/`

To replace any figure, overwrite the corresponding PNG file in the respective folder, or add your new image and update the `\includegraphics` directive in the relevant chapter:

```latex
\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.90\textwidth]{images/architecture/your_new_diagram.png}
    \caption{Your Descriptive Academic Figure Caption}
    \label{fig:your-new-diagram-label}
\end{figure}
```

---

## 6. Pre-Compiled Reference Documents

For immediate offline reading and printing, the following pre-compiled reference documents are included directly in this directory:
- `MergeMind_Final_Capstone_Report.pdf`: 78-page publication-grade PDF compiled with native Word COM automation.
- `MergeMind_Final_Capstone_Report.docx`: 78-page editable Microsoft Word document matching the LaTeX styling.
- `REPORT_CONTENT_AUDIT.md`: Complete implementation audit establishing code provenance for every technical claim in the report.

