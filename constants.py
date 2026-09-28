# --- İÇE GÖMÜLÜ LATEX STİLİ ŞABLONU (kurumsal-stil.tex) ---
# Dışarıdan dosyaya ihtiyaç kalmaması için stili Python içine gömüyoruz.
# <<anahtar>> yer tutucuları style.py'deki tema (PDF Stili sekmesi) ile doldurulur; geri kalanı çekirdektir
# ve kullanıcıya kapalıdır, böylece buraya eklenen düzeltmeler stili özelleştirmiş kullanıcılara da ulaşır.
KURUMSAL_STIL_SABLONU = r"""
\usepackage{fontspec}
\usepackage{newunicodechar}
% Windows yazı tipleri; Mac'te bulunmayanlar için eşdeğerleri kullanılır
\IfFontExistsTF{Arial}{\setmainfont{Arial}}{}
% Menlo varsayılan olarak AAT (CoreText) ile açılır; fontta olmayan bir karakter AAT'de 0xFFFF
% glif numarası üretir ve xdvipdfmx "last_cid < 0xFFFFu" hatasıyla çöker. OpenType'ta atlanıp uyarı verilir.
\IfFontExistsTF{Consolas}{\setmonofont{Consolas}}{\IfFontExistsTF{Menlo}{\setmonofont{Menlo}[Renderer=OpenType]}{}}
\IfFontExistsTF{Segoe UI Symbol}{\newfontfamily\sembolfont{Segoe UI Symbol}}{%
  \IfFontExistsTF{Menlo}{\newfontfamily\sembolfont{Menlo}[Renderer=OpenType]}{\let\sembolfont\relax}}
% AI kurallarının izin verdiği emojiler Arial/Menlo'da yok (boş kutu basılır); sembol fontundaki
% karşılıkları kullanılır. U+FE0F (⚠️ içindeki emoji varyasyon seçicisi) yok sayılır.
\newunicodechar{✓}{{\sembolfont ✓}}
\newunicodechar{✅}{{\sembolfont\color{green!55!black}✔}}
\newunicodechar{❌}{{\sembolfont\color{red!80!black}✘}}
\newunicodechar{⚠}{{\sembolfont\color{orange!90!black}⚠}}
\newunicodechar{^^^^fe0f}{}
\usepackage[export]{adjustbox}
\usepackage{float}
\usepackage{pdflscape} 
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}
\usepackage{etoolbox}
\usepackage{ragged2e}
\usepackage{xcolor}
\definecolor{ttblue}{HTML}{<<primary_color>>}
\definecolor{ttgray}{HTML}{<<secondary_color>>}
\definecolor{lightbg}{RGB}{248, 249, 250}
% titlesec hyperref'ten önce yüklenmeli: hyperref, numarasız başlıklara bağlantı noktası koyan desteği yalnızca
% yüklenirken titlesec'i görürse kurar. Aksi halde İçindekiler bağlantıları kapağa/önceki öğeye gider.
\usepackage{titlesec}
\usepackage{hyperref}
\hypersetup{colorlinks=true, linkcolor=ttblue, urlcolor=ttblue, bookmarksopen=true}
% titlesec bağlantı noktasını başlıktan önce ayrı bir öğe olarak koyar; TeX sayfayı ikisinin arasından
% kırarsa nokta önceki sayfanın dibinde kalır. \nobreak ikisini aynı sayfada tutar. Formatlardaki \color da
% dikey listeye bir öğe ekleyip arkasında yeni bir kırılma noktası açtığı için onların sonuna da \nobreak konur.
\makeatletter
\patchcmd{\ttl@select}{\ttl@Hy@saveanchor}{\ttl@Hy@saveanchor\nobreak}{}{}
\makeatother
\titleformat{\section}{\normalfont\Large\bfseries\color{ttblue}\nobreak}{\thesection}{1em}{}[{\color{lightgray}\titlerule[0.5pt]}]
\titleformat{\subsection}{\normalfont\large\bfseries\color{darkgray}\nobreak}{\thesubsection}{1em}{}
\let\oldrule\rule
\renewcommand{\rule}[2]{\ifdim#1=0.5\linewidth\textcolor{lightgray}{\oldrule{\linewidth}{0.5pt}}\else\oldrule{#1}{#2}\fi}
\usepackage{geometry}
\geometry{a4paper, left=<<margin_x_cm>>, right=<<margin_x_cm>>, top=<<margin_y_cm>>, bottom=<<margin_y_cm>>}
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[R]{\textbf{\textcolor{ttgray}{<<header_text>>}}}
\fancyfoot[L]{\footnotesize{\textcolor{ttgray}{<<footer_text>>}}}
\fancyfoot[C]{\footnotesize{\textcolor{ttgray}{<<footer_center_text>>}}}
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
  \begin{tcolorbox}[enhanced, breakable, size=minimal, top=8pt, bottom=8pt, left=12pt, right=8pt, boxrule=0pt, frame hidden, colback=lightbg, borderline west={3pt}{0pt}{ttblue}, sharp corners]
}{\end{tcolorbox}}
\renewcommand{\arraystretch}{1.4}
\renewcommand{\_}{\textunderscore\allowbreak}
\renewcommand{\/}{/\allowbreak}
\AtBeginEnvironment{longtable}{\footnotesize \RaggedRight}
\renewcommand{\topfraction}{0.9}
\renewcommand{\bottomfraction}{0.8}
\renewcommand{\textfraction}{0.1}
\raggedbottom
<<watermark>>
\makeatletter
\def\maketitle{
  \hypersetup{pageanchor=false} % <--- ÇÖZÜM: Kapağı link hedeflerinden gizler
  \begin{titlepage}
    \raggedright
    \vspace*{4cm}
    {\color{ttblue}\rule{\textwidth}{3pt}}\\[1em]
    {\Huge\bfseries\color{ttblue} \@title \par}
    \vspace{1em}
    {\color{lightgray}\rule{\textwidth}{1pt}}\\[3em]
    {\Large\bfseries\color{ttgray} <<cover_subtitle>>}\\[0.5em]
    {\large\color{gray} \@date \par}
    \vfill
    {\Large\bfseries\color{ttblue} <<cover_org>>}\\[0.5em]
    {\footnotesize\color{gray} \textit{<<cover_notice>>}}
    \vspace*{2cm}
  \end{titlepage}
  \hypersetup{pageanchor=true} % <--- ÇÖZÜM: Asıl metin için link hedeflerini tekrar açar
  \clearpage
}
\makeatother
\renewcommand{\contentsname}{İçindekiler}
<<extra_latex>>
"""

# Filigran açıksa şablondaki <<watermark>> yerine konur
FILIGRAN_SABLONU = r"""\usepackage{draftwatermark}
\SetWatermarkText{\textsf{<<watermark_text>>}}
\SetWatermarkScale{0.7}
\SetWatermarkColor[gray]{0.94}
\SetWatermarkAngle{45}"""

# --- AI (YAPAY ZEKA) MARKDOWN ÜRETİM KURALLARI ---
AI_PROMPT_RULES = """---
description: İnnova kurumsal standartlarında, Pandoc/LaTeX PDF motoru ile tam uyumlu Markdown dokümanları üretme kuralları.
alwaysApply: true
---

# ROLE AND PURPOSE
You are the "İnnova Technical Documentation Expert". Your objective is to generate highly professional, clear, and structured technical documentation (software, architecture, processes) in Markdown format.
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

5. MERMAID DIAGRAMS (Architecture, Flows & UML):
   - ALWAYS use Mermaid for architectural drawings, flows, and UML diagrams. Choose the diagram type by what is being explained:
     - `flowchart`: processes, activity flows, and architecture overviews.
     - `sequenceDiagram`: the order of messages between users, services, and systems.
     - `classDiagram`: classes, interfaces, and their relationships (inheritance, composition, dependency).
     - `stateDiagram-v2`: the lifecycle and state transitions of a single entity (e.g., an order or a request).
     - `erDiagram`: database tables and their relationships.
   - Start the block strictly with ```mermaid and nothing else on that line. The next line is the diagram type keyword (e.g., `classDiagram`).
   - LAYOUT RULE: You can use Top-Down (`TD`) or Left-to-Right (`LR`); in class and state diagrams write `direction LR` on the second line. However, to prevent the diagram from becoming excessively wide or tall and unreadable in PDF, you MUST keep node texts compact.
   - SIZE RULE: The engine shrinks every diagram to fit within one page. An oversized diagram will fit, but its text becomes too small to read. Therefore:
     - Flowcharts: at most 6 levels along the main direction and at most 4 nodes side by side on any level.
     - Sequence diagrams: at most 6 participants and about 12 messages.
     - Class diagrams: at most 8 classes and at most 5 members (attributes + methods) per class. Show only the members that matter for the explanation.
     - State diagrams: at most 10 states.
     - ER diagrams: at most 6 entities and at most 6 attributes per entity (keys and the most important columns).
     - For longer flows or larger models, prefer `LR` or split into several smaller diagrams (e.g., the main path in one diagram and the error paths in another, or one class diagram per module).
     - Avoid routing many edges from different levels into a single distant node (e.g., one shared "Error" node at the bottom); this adds extra height.
   - UML SYNTAX RULES: The engine uses Mermaid 9.1. Newer syntax breaks the build, so use only the forms below:
     - Class and ER diagrams: class, entity, attribute, and method names MUST use ASCII letters only, as in source code (e.g., `Siparis`, `SIPARIS_KALEMI`, `odemeYap()`). Turkish characters in these names break the build or corrupt the output. Turkish text is allowed in relationship labels (e.g., `Siparis --> Musteri : ait olduğu`); in ER diagrams quote the label (e.g., `MUSTERI ||--o{ SIPARIS : "verir"`).
     - Class diagrams: write generics with tildes (`List~Siparis~`), never with `<>`. Mark interfaces and abstract classes with `<<interface>>` or `<<abstract>>` inside the class body. Do NOT use `namespace` blocks or `note` lines; they break the build.
     - State diagrams: give Turkish display names through an alias (e.g., `state "Ödeme Bekleniyor" as Bekliyor`) and use the alias in transitions. Use `[*]` for the start and end states.
   - CRITICAL: If a flowchart node has a long text, wrap it using `<br>` inside the node (e.g., `A[Dış Sistemden<br>Gelen Veri]`). This is the ONLY place in the document where `<br>` HTML tag is allowed. In class, state, and ER diagrams keep names short instead of using `<br>`.
   - CRITICAL: Do NOT indent the Mermaid block. It must be at the root level (no spaces/tabs before the backticks). Never place a Mermaid block inside a numbered/bulleted list.

6. PROHIBITIONS & LIMITATIONS:
   - NEVER use raw HTML tags (e.g., `<br>`, `<div align="center">`). The PDF engine ignores HTML. Use pure Markdown only (Except the `<br>` rule inside Mermaid flowchart nodes).
   - Keep emoji usage to an absolute minimum. If necessary, use only standard Unicode emojis (e.g., ✅, ❌, ⚠️).

# TONE AND STYLE
- The tone must be professional, technical, and aligned with enterprise/İnnova standards.
- Avoid first-person pronouns ("I", "You"). Use passive voice or third-person (e.g., "Sistem tarafından uygulanmalıdır", "Kullanıcı giriş yaptığında").
"""