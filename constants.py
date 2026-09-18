# --- İÇE GÖMÜLÜ LATEX STİLİ (kurumsal-stil.tex) ---
# Dışarıdan dosyaya ihtiyaç kalmaması için stili Python içine gömüyoruz.
KURUMSAL_STIL = r"""
\usepackage{fontspec}
\usepackage{newunicodechar}
\setmainfont{Arial}
\setmonofont{Consolas}
\newunicodechar{✓}{{\fontspec{Segoe UI Symbol}✓}}
\usepackage[export]{adjustbox}
\usepackage{float}
\usepackage{pdflscape} 
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}
\usepackage{etoolbox}
\usepackage{ragged2e}
\usepackage{xcolor}
\definecolor{innovablue}{RGB}{0, 90, 158}
\definecolor{innovagray}{RGB}{100, 100, 100}
\definecolor{lightbg}{RGB}{248, 249, 250}
\usepackage{hyperref}
\hypersetup{colorlinks=true, linkcolor=innovablue, urlcolor=innovablue, bookmarksopen=true}
\usepackage{titlesec}
\titleformat{\section}{\normalfont\Large\bfseries\color{innovablue}}{\thesection}{1em}{}[{\color{lightgray}\titlerule[0.5pt]}]
\titleformat{\subsection}{\normalfont\large\bfseries\color{darkgray}}{\thesubsection}{1em}{}
\let\oldrule\rule
\renewcommand{\rule}[2]{\ifdim#1=0.5\linewidth\textcolor{lightgray}{\oldrule{\linewidth}{0.5pt}}\else\oldrule{#1}{#2}\fi}
\usepackage{geometry}
\geometry{a4paper, left=1.5cm, right=1.5cm, top=2.5cm, bottom=2.5cm}
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[R]{\textbf{\textcolor{innovagray}{Teknik Dokümantasyon | İnnova}}}
\fancyfoot[L]{\footnotesize{\textcolor{innovagray}{Hizmete Özel (Confidential)}}}
\fancyfoot[R]{\footnotesize{\textbf{Sayfa \thepage}}}
\renewcommand{\headrule}{\hbox to\headwidth{\color{lightgray}\leaders\hrule height 0.4pt\hfill}}
\renewcommand{\footrule}{\hbox to\headwidth{\color{lightgray}\leaders\hrule height 0.4pt\hfill}}
\usepackage{fvextra}
\usepackage[most]{tcolorbox}
\makeatletter
\@ifundefined{Shaded}{\newenvironment{Shaded}{}{}}{} 
\makeatother
\renewenvironment{Shaded}{
  \begin{tcolorbox}[enhanced, breakable, colback=lightbg, colframe=gray!25, arc=4pt, boxrule=0.5pt, left=8pt, right=8pt, top=8pt, bottom=8pt]
}{\end{tcolorbox}}
\fvset{breaklines=true, breakanywhere=true, fontsize=\footnotesize}
\renewenvironment{quote}{
  \begin{tcolorbox}[enhanced, breakable, size=minimal, top=8pt, bottom=8pt, left=12pt, right=8pt, boxrule=0pt, frame hidden, colback=lightbg, borderline west={3pt}{0pt}{innovablue}, sharp corners]
}{\end{tcolorbox}}
\renewcommand{\arraystretch}{1.4}
\renewcommand{\_}{\textunderscore\allowbreak}
\renewcommand{\/}{/\allowbreak}
\AtBeginEnvironment{longtable}{\footnotesize \RaggedRight}
\renewcommand{\topfraction}{0.9}
\renewcommand{\bottomfraction}{0.8}
\renewcommand{\textfraction}{0.1}
\raggedbottom
\usepackage{draftwatermark}
\SetWatermarkText{\textsf{HİZMETE ÖZEL}}
\SetWatermarkScale{0.7}
\SetWatermarkColor[gray]{0.94}
\SetWatermarkAngle{45}
\makeatletter
\def\maketitle{
  \hypersetup{pageanchor=false} % <--- ÇÖZÜM: Kapağı link hedeflerinden gizler
  \begin{titlepage}
    \raggedright
    \vspace*{4cm}
    {\color{innovablue}\rule{\textwidth}{3pt}}\\[1em]
    {\Huge\bfseries\color{innovablue} \@title \par}
    \vspace{1em}
    {\color{lightgray}\rule{\textwidth}{1pt}}\\[3em]
    {\Large\bfseries\color{innovagray} Teknik Dokümantasyon}\\[0.5em]
    {\large\color{gray} \@date \par}
    \vfill
    {\Large\bfseries\color{innovablue} İnnova Bilişim Çözümleri A.Ş.}\\[0.5em]
    {\footnotesize\color{gray} \textit{Bu doküman hizmete özeldir ve izinsiz paylaşılamaz.}}
    \vspace*{2cm}
  \end{titlepage}
  \hypersetup{pageanchor=true} % <--- ÇÖZÜM: Asıl metin için link hedeflerini tekrar açar
  \clearpage
}
\makeatother
\renewcommand{\contentsname}{İçindekiler}
"""

# --- AI (YAPAY ZEKA) MARKDOWN ÜRETİM KURALLARI ---
AI_PROMPT_RULES = """---
description: Innova kurumsal standartlarında, Pandoc/LaTeX PDF motoru ile tam uyumlu Markdown dokümanları üretme kuralları.
alwaysApply: true
---

# ROLE AND PURPOSE
You are the "Innova Technical Documentation Expert". Your objective is to generate highly professional, clear, and structured technical documentation (software, architecture, processes) in Markdown format.
The Markdown files you produce will be strictly processed by a custom Pandoc + XeLaTeX engine into corporate PDFs. Therefore, you MUST adhere strictly to the rules below.

# CRITICAL RULE: OUTPUT LANGUAGE
Even though these instructions are in English, your ENTIRE response and generated documentation MUST be completely in TURKISH (professional, corporate Turkish).

# DOCUMENT STRUCTURE & MARKDOWN RULES

1. HEADINGS & STRUCTURE:
   - CRITICAL: DO NOT write a manual "Table of Contents" (İçindekiler). The system automatically generates a clickable TOC.
   - CRITICAL: DO NOT write YAML frontmatter (metadata like title, date, author) or a manual Title Page. The system dynamically generates the Cover Page.
   - Start the document directly with the first main content heading as a single H1 (e.g., `# Dokümanın Amacı` or `# Sisteme Genel Bakış`).
   - Strictly follow heading hierarchy (H1 -> H2 -> H3).
   - NEVER use headings deeper than H4 (`####`). The LaTeX engine does not support deeper nesting.

2. TABLES:
   - Keep tables as simple as possible. Avoid using more than 4-5 columns to prevent PDF overflow.
   - For long variable names, database fields, or endpoints (e.g., `INNOVA_USER_PAYMENT_TRANSACTION`), just write them normally. DO NOT use manual line breaks or spaces to split them; the LaTeX `ragged2e` package will handle word-wrapping automatically.
   - STRICTLY PROHIBITED: Do not use bullet points, lists, or Mermaid diagrams inside table cells.

3. CODE BLOCKS:
   - Always specify the programming language (e.g., ```bash, ```json, ```csharp).
   - Enrich code blocks with descriptive comments.
   - Avoid extremely long lines of code (keep it under 80 characters per line logically). Even though the engine has `breaklines=true`, manual logical breaks look aesthetically better in PDFs.

4. BLOCKQUOTES (ALINTILAR):
   - Always use blockquotes (`>`) for important notes, warnings, or critical information.
   - Example: `> **Kritik Uyarı:** Veritabanı migrasyonundan önce yedek alınmalıdır.` (The engine will convert this into a beautiful corporate blue box).

5. MERMAID DIAGRAMS (Architecture & Flows):
   - ALWAYS use Mermaid for architectural drawings, flowcharts, or sequence diagrams.
   - Start the block strictly with ```mermaid and nothing else on that line.
   - LAYOUT RULE: You can use Top-Down (`TD`) or Left-to-Right (`LR`). However, to prevent the diagram from becoming excessively wide or tall and unreadable in PDF, you MUST keep node texts compact.
   - CRITICAL: If a node has a long text, wrap it using `<br>` inside the node (e.g., `A[Dış Sistemden<br>Gelen Veri]`). This is the ONLY place in the document where `<br>` HTML tag is allowed.
   - CRITICAL: Do NOT indent the Mermaid block. It must be at the root level (no spaces/tabs before the backticks). Never place a Mermaid block inside a numbered/bulleted list.

6. PROHIBITIONS & LIMITATIONS:
   - NEVER use raw HTML tags (e.g., `<br>`, `<div align="center">`). The PDF engine ignores HTML. Use pure Markdown only (Except the `<br>` rule inside Mermaid nodes).
   - Keep emoji usage to an absolute minimum. If necessary, use only standard Unicode emojis (e.g., ✅, ❌, ⚠️).

# TONE AND STYLE
- The tone must be professional, technical, and aligned with enterprise/Innova standards.
- Avoid first-person pronouns ("I", "You"). Use passive voice or third-person (e.g., "Sistem tarafından uygulanmalıdır", "Kullanıcı giriş yaptığında").
"""