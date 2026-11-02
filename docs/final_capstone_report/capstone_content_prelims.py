# capstone_content_prelims.py
"""
Preliminary pages content definitions for MergeMind Final Capstone Project Report.
Includes Cover, Certificate, Declaration, Acknowledgement, Abstract, Abbreviations.
"""

TITLE_DATA = {
    "project_title": "MERGEMIND: AN AI-POWERED GITHUB REPOSITORY INTELLIGENCE AND AUTOMATED REMEDIATION PLATFORM",
    "subtitle": "A Unified Deterministic Code Governance, Security Posture, and AI-Assisted CI/CD Remediation Architecture",
    "degree": "Bachelor of Technology in Computer Science and Engineering",
    "institution": "School of Technology, Woxsen University",
    "location": "Kamkole, Sadasivpet, Sangareddy, Telangana 502345, India",
    "academic_year": "2025 – 2026",
    "submission_date": "March 2026",
    "student_name": "[Candidate Full Name]",
    "roll_number": "[Student Roll / Registration No.]",
    "supervisor_name": "[Faculty Guide Name, Ph.D.]",
    "supervisor_title": "Assistant Professor, Department of Computer Science and Engineering",
    "hod_name": "[Head of Department Name, Ph.D.]",
    "hod_title": "Professor & Head, Department of Computer Science and Engineering"
}

CERTIFICATE_TEXT = (
    "This is to certify that the project entitled \"MERGEMIND: AN AI-POWERED GITHUB REPOSITORY "
    "INTELLIGENCE AND AUTOMATED REMEDIATION PLATFORM\" submitted by [Candidate Full Name] "
    "([Student Roll / Registration No.]) in partial fulfillment of the requirements for the award of the "
    "degree of Bachelor of Technology in Computer Science and Engineering to the School of Technology, "
    "Woxsen University, Hyderabad, is a record of bona fide work carried out under my supervision and guidance.\n\n"
    "The results embodied in this thesis report have not been submitted to any other University or Institute "
    "for the award of any degree, diploma, fellowship, or other similar title or recognition."
)

DECLARATION_TEXT = (
    "I hereby declare that the capstone project work entitled \"MERGEMIND: AN AI-POWERED GITHUB "
    "REPOSITORY INTELLIGENCE AND AUTOMATED REMEDIATION PLATFORM\" is an authentic record of my own "
    "independent research and engineering work carried out under the supervision of [Faculty Guide Name, Ph.D.], "
    "School of Technology, Woxsen University.\n\n"
    "I further declare that this report has been prepared in accordance with the academic guidelines and ethical "
    "standards prescribed by Woxsen University. To the best of my knowledge and belief, this work contains no "
    "material previously published or written by another person, except where due reference and formal citation "
    "are made in the text. All open-source libraries, frameworks, APIs, and academic literature utilized have "
    "been duly acknowledged and credited in the bibliography."
)

ACKNOWLEDGEMENTS_TEXT = (
    "The completion of this capstone engineering project marks a major milestone in my academic journey. "
    "I express my deepest gratitude to my project supervisor, [Faculty Guide Name, Ph.D.], for invaluable guidance, "
    "insightful architectural critiques, continuous encouragement, and high intellectual standards throughout the "
    "lifecycle of this research.\n\n"
    "I extend my sincere thanks to [Head of Department Name, Ph.D.], Head of the Department of Computer Science "
    "and Engineering, and the faculty review committee at the School of Technology, Woxsen University, for their "
    "constructive feedback and academic mentorship. I also express my heartfelt appreciation to the leadership of "
    "Woxsen University for providing world-class computational infrastructure, laboratory facilities, and an "
    "innovative learning environment.\n\n"
    "Special recognition is extended to the global open-source software engineering community, particularly the teams "
    "behind FastAPI, React, PostgreSQL, Docker, Astral Ruff, Bandit, and Google DeepMind, whose robust foundations "
    "made the design, evaluation, and realization of MergeMind possible.\n\n"
    "Finally, I express my profound debt of gratitude to my family and colleagues whose unwavering moral support, "
    "patience, and belief provided enduring motivation throughout the intensive development and rigorous verification "
    "phases of this capstone deliverable."
)

ABSTRACT_TEXT = (
    "Modern software engineering has increasingly shifted toward cloud-native microservice architectures, "
    "accelerated release cadences, and continuous integration/continuous deployment (CI/CD) pipelines. "
    "However, software development teams face severe operational friction arising from fragmented developer "
    "toolchains, invisible code quality debt, unmitigated software supply chain vulnerabilities, high cognitive "
    "fatigue during manual pull request (PR) reviews, and protracted debugging cycles when CI/CD workflows fail. "
    "Conventional static application security testing (SAST) and continuous integration tools operate in operational "
    "silos, generating voluminous diagnostic logs and raw error traces while delegating the burdensome task of root-cause "
    "analysis, context reconstruction, and patch synthesis entirely to human engineers.\n\n"
    "To resolve this fundamental gap, this capstone dissertation presents MergeMind: an AI-powered GitHub repository "
    "intelligence, security governance, and automated code remediation platform. MergeMind is architected as an "
    "integrated, deterministic, and self-hosted engineering platform comprising an asynchronous FastAPI backend, a modern "
    "React 18 single-page application (SPA), an enterprise-grade PostgreSQL relational store, and an isolated Docker "
    "execution sandbox. The platform interfaces seamlessly with GitHub via a privileged GitHub App architecture, "
    "utilizing asymmetric RSA cryptographic key pairs and short-lived JSON Web Tokens (JWT) to secure an authoritative "
    "5,000 requests/hour rate limit pool and listen to repository events via HMAC-SHA256 verified webhooks.\n\n"
    "MergeMind introduces three core technical innovations: (1) A multi-factor deterministic health telemetry engine "
    "that ingests remote repository snapshots via streamed tarball decompression, executing parallel static analysis "
    "harnesses across five weighted dimensions (Ruff code quality: 25%, Bandit AST vulnerability scanning: 25%, pip-audit "
    "known CVE dependency auditing: 20%, Radon cyclomatic complexity and maintainability: 10%, and Pytest execution: 20%) "
    "with dynamic mathematical weight re-normalization and an authoritative qualification gating threshold (≥80% completeness); "
    "(2) An enterprise security posture evaluation suite executing 43 deterministic policy checks across Branch Protection (12 checks), "
    "Security Features (9 checks), Access Control (8 checks), and Repository Settings (14 checks) to compute an objective Security "
    "Posture Index (SPI); and (3) An autonomous AI-driven remediation pipeline powered by Google Gemini 3.6 Flash. When CI/CD "
    "workflows crash, MergeMind ingests and sanitizes raw execution logs (redacting sensitive bearer tokens and secrets via regex filters), "
    "localizes offending stack frames, prompts the LLM to generate precise unified diff patches, syntactically validates modifications "
    "against Python Abstract Syntax Tree (AST) grammar, re-executes tests in an isolated Docker container sandbox, and automatically "
    "authors a verified GitHub Draft Pull Request upon test passage.\n\n"
    "Empirical evaluation conducted across real-world production repositories (including YOLO26n, mergemind-test-sandbox, and AI-Proctoring) "
    "and a comprehensive 185-test verification suite demonstrates that MergeMind successfully discriminates nuanced code health scores "
    "(76/100, 95/100, and 100/100 respectively), completely prevents cross-repository directory contamination, achieves a 100% pass "
    "rate on sandbox-verified syntax repairs, and slashes mean time to triage (MTTT) and mean time to remediation (MTTR) by an "
    "estimated 68% compared to conventional manual workflows."
)

ABBREVIATIONS = [
    ("API", "Application Programming Interface"),
    ("APR", "Automated Program Repair"),
    ("AST", "Abstract Syntax Tree"),
    ("CI/CD", "Continuous Integration / Continuous Deployment"),
    ("CLI", "Command Line Interface"),
    ("CWE", "Common Weakness Enumeration"),
    ("CVE", "Common Vulnerabilities and Exposures"),
    ("CORS", "Cross-Origin Resource Sharing"),
    ("DAST", "Dynamic Application Security Testing"),
    ("DB", "Database"),
    ("ER", "Entity-Relationship"),
    ("HMAC", "Hash-based Message Authentication Code"),
    ("HTTP", "Hypertext Transfer Protocol"),
    ("HTTPS", "Hypertext Transfer Protocol Secure"),
    ("IDE", "Integrated Development Environment"),
    ("IEEE", "Institute of Electrical and Electronics Engineers"),
    ("JSON", "JavaScript Object Notation"),
    ("JWT", "JSON Web Token"),
    ("LLM", "Large Language Model"),
    ("LOC", "Lines of Code"),
    ("MTTR", "Mean Time to Remediation"),
    ("MTTT", "Mean Time to Triage"),
    ("NFR", "Non-Functional Requirement"),
    ("ORM", "Object-Relational Mapping"),
    ("OS", "Operating System"),
    ("PEM", "Privacy Enhanced Mail (Cryptographic Certificate Format)"),
    ("PR", "Pull Request"),
    ("RBAC", "Role-Based Access Control"),
    ("REST", "Representational State Transfer"),
    ("RSA", "Rivest–Shamir–Adleman Cryptographic Algorithm"),
    ("SARIF", "Static Analysis Results Interchange Format"),
    ("SAST", "Static Application Security Testing"),
    ("SCA", "Software Composition Analysis"),
    ("SHA", "Secure Hash Algorithm"),
    ("SPA", "Single Page Application"),
    ("SPI", "Security Posture Index"),
    ("SPDX", "Software Package Data Exchange"),
    ("SQL", "Structured Query Language"),
    ("UI", "User Interface"),
    ("UUID", "Universally Unique Identifier"),
    ("VCS", "Version Control System"),
    ("XSS", "Cross-Site Scripting")
]
