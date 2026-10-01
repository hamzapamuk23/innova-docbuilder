import os
import re
import base64
import subprocess
import platform
import tempfile
from datetime import datetime

IS_WINDOWS = platform.system() == "Windows"

import deps
import style

# Kurulum sonrası doğrulama için derlenen örnek doküman: kurumsal stilin ve pandoc
# şablonunun kullandığı LaTeX paketlerinin hepsini (tablo, kod, alıntı, dipnot, görsel...) tetikler.
TEST_MARKDOWN = r"""
# Sistem Testi

Türkçe karakterler: ğüşıöç ĞÜŞİÖÇ. **Kalın**, *italik*, ~~üstü çizili~~, `satır içi kod`,
[bağlantı](https://example.com) ve dipnot[^1]. ✓ işareti.

[^1]: Dipnot metni.

> **Kritik Uyarı:** Alıntı kutusu testi.

| Alan | Açıklama |
|------|----------|
| INNOVA_USER_PAYMENT_TRANSACTION | ✓ Değer |

- Madde 1
- Madde 2

```python
def merhaba():
    return "dünya"  # yorum
```

## Alt Başlık

### Üçüncü Seviye

#### Dördüncü Seviye

\begin{figure}[htbp]
\centering
\includegraphics[max width=\textwidth, keepaspectratio]{test.png}
\end{figure}
"""
TEST_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _turkish_date():
    aylar = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    now = datetime.now()
    return f"{now.day} {aylar[now.month]} {now.year}"


def _pandoc_version(pandoc):
    try:
        out = subprocess.run([pandoc, "--version"], capture_output=True, text=True,
                             creationflags=deps.NO_WINDOW).stdout
        m = re.search(r"(\d+)\.(\d+)", out)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    except OSError:
        return (0, 0)


def _mermaid_error(stderr):
    """mmdc hata çıktısından Mermaid'in ayrıştırma mesajını (satır no ve ^ işaretiyle) alır, stack trace'i atar."""
    lines = []
    for line in (stderr or "").strip().splitlines():
        if line.lstrip().startswith("at "):
            break
        lines.append(line)
    message = "\n".join(lines).replace("Error: Evaluation failed: Error: ", "").strip()
    return message or deps.tail_output(stderr)


_FENCE_RE = re.compile(r'^[ \t]*(`{3,}|~{3,})')
_TABLE_SEP_CELL_RE = re.compile(r'^:?-{3,}:?$')
# Sütun ağırlığı sınırları: tek bir uzun hücre tabloyu domine etmesin, kısa sütun (ör. "#") okunaksız daralmasın.
_COL_MIN_WEIGHT = 5
_COL_MAX_WEIGHT = 40


def _split_table_row(line):
    """Pipe tablo satırını hücrelere böler; satır içi kod ve kaçışlı (\\|) karakterlerdeki '|' ayraç sayılmaz."""
    cells, current, in_code = [], [], False
    text = line.strip()
    if text.startswith('|'):
        text = text[1:]
    if text.endswith('|') and not text.endswith('\\|'):
        text = text[:-1]
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '\\' and i + 1 < len(text):
            current.append(text[i:i + 2])
            i += 2
            continue
        if ch == '`':
            in_code = not in_code
        if ch == '|' and not in_code:
            cells.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    cells.append(''.join(current).strip())
    return cells


def _visible_length(cell):
    """Hücrenin PDF'te kaplayacağı yaklaşık karakter sayısı (Markdown işaretleri hariç)."""
    return len(re.sub(r'\*\*|__|`', '', cell))


def balance_table_widths(content):
    """Pipe tabloların başlık ayırıcı satırını sütun içeriklerine göre yeniden yazar.

    Pandoc, satırlarından biri 72 karakteri aşan tabloyu sayfa genişliğine yayar ve sütun oranlarını
    ayırıcı satırdaki tire sayısından alır. AI'ın ürettiği `| --- | --- |` biçimi eşit genişlik demektir;
    kısa bir ilk sütun ("Kriter", "#") sayfanın yarısını kaplar. Burada tire sayısı, sütundaki en uzun
    hücrenin görünen uzunluğuna (sınırlar içinde) eşitlenir. Hizalama işaretleri (:) korunur, kod
    bloklarına dokunulmaz."""
    lines = content.split('\n')
    out, i, in_fence, fence = [], 0, False, ''
    while i < len(lines):
        line = lines[i]
        m = _FENCE_RE.match(line)
        if m:
            if not in_fence:
                in_fence, fence = True, m.group(1)[0]
            elif m.group(1)[0] == fence:
                in_fence = False
            out.append(line)
            i += 1
            continue
        is_header = (not in_fence and line.lstrip().startswith('|') and i + 1 < len(lines)
                     and lines[i + 1].lstrip().startswith('|'))
        sep_cells = _split_table_row(lines[i + 1]) if is_header else []
        if not sep_cells or not all(_TABLE_SEP_CELL_RE.match(c) for c in sep_cells):
            out.append(line)
            i += 1
            continue
        # Tablo: başlık + ayırıcı + '|' ile başlayan gövde satırları
        end = i + 2
        while end < len(lines) and lines[end].lstrip().startswith('|'):
            end += 1
        rows = [_split_table_row(l) for l in [lines[i]] + lines[i + 2:end]]
        weights = []
        for col in range(len(sep_cells)):
            longest = max((_visible_length(r[col]) for r in rows if col < len(r)), default=0)
            weights.append(min(max(longest, _COL_MIN_WEIGHT), _COL_MAX_WEIGHT))
        new_sep = []
        for cell, weight in zip(sep_cells, weights):
            left, right = cell.startswith(':'), cell.endswith(':')
            dashes = '-' * (weight - left - right)
            new_sep.append((':' if left else '') + dashes + (':' if right else ''))
        out.append(line)
        out.append('| ' + ' | '.join(new_sep) + ' |')
        out.extend(lines[i + 2:end])
        i = end
    return '\n'.join(out)


def build_pandoc_cmd(pandoc, xelatex, md_path, pdf_path, tex_path, title, date):
    # --syntax-highlighting pandoc 3.8 ile geldi; eski sürümler --highlight-style kullanır
    highlight = "--syntax-highlighting=tango" if _pandoc_version(pandoc) >= (3, 8) else "--highlight-style=tango"
    return [
        pandoc, md_path, '-o', pdf_path,
        f'--pdf-engine={xelatex}', f'--include-in-header={tex_path}',
        highlight, '--toc', '--toc-depth=3',
        '--metadata', f'title={title}',
        '--metadata', f'date={date}'
    ]


def run_pandoc(cmd, cwd, xelatex, log, max_fix_rounds=5):
    """Pandoc'u çalıştırır; eksik LaTeX paketi yüzünden hata alırsa paketi kurup tekrar dener."""
    attempted = set()
    for _ in range(max_fix_rounds + 1):
        # UTF-8 encoding ve replace: Windows konsolunun varsayılan charmap (cp1254) ile UTF-8 okumaya çalışıp çökmesini engeller.
        result = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL, text=True, cwd=cwd,
                                encoding="utf-8", errors="replace", creationflags=deps.NO_WINDOW, timeout=1800)
        if result.returncode == 0:
            return result
        if not deps.fix_missing_latex_packages(result.stderr, xelatex, log, attempted):
            return result
        log("      Paketler kuruldu, derleme tekrar deneniyor...")
    return result


def self_test(pandoc, xelatex, log, style_tex=None):
    """Örnek bir dokümanı kurumsal stille derleyerek araç zincirinin çalıştığını doğrular.

    style_tex verilmezse varsayılan tema kullanılır: kurulum kontrolü kullanıcının stil ayarlarına bağlı olmamalı.
    PDF Stili sekmesi kaydetmeden önce yeni stili buradan geçirir."""
    with tempfile.TemporaryDirectory() as tmp:
        tex_path = os.path.join(tmp, "kurumsal-stil.tex")
        md_path = os.path.join(tmp, "test.md")
        pdf_path = os.path.join(tmp, "test.pdf")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(style_tex or style.build_style(style.DEFAULT_THEME))
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(TEST_MARKDOWN)
        with open(os.path.join(tmp, "test.png"), "wb") as f:
            f.write(TEST_PNG)
        cmd = build_pandoc_cmd(pandoc, xelatex, md_path, pdf_path, tex_path, "Sistem Testi", _turkish_date())
        try:
            result = run_pandoc(cmd, tmp, xelatex, log)
        except (OSError, subprocess.SubprocessError) as e:
            log(f"      Test derlemesi çalıştırılamadı: {e}")
            return False
        if result.returncode == 0 and os.path.isfile(pdf_path):
            return True
        log(f"      Test derlemesi hatası: {deps.tail_output(result.stderr, 6)}")
        return False


def compile_pdf(app, md_path):
    app.after(0, lambda: app.btn_compile.configure(state="disabled"))
    work_dir = os.path.dirname(md_path)
    filename = os.path.basename(md_path)
    base_name = os.path.splitext(filename)[0]
    
    app.log(f"İşleniyor: {filename}")
    temp_files = []

    try:
        # 1. Stili (PDF Stili sekmesindeki temayla) geçici olarak oluştur
        theme = style.load_theme()
        tex_path = os.path.join(work_dir, "kurumsal-stil.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(style.build_style(theme))
        temp_files.append(tex_path)

        # 2. MD Dosyasını Oku
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 3. Mermaid Şemalarını Çıkart ve Çiz
        app.after(0, lambda: app.progress_bar.set(0.4))
        app.log("Markdown analiz ediliyor, Mermaid şemaları çıkartılıyor...")
        pattern = r'(?s)```mermaid\s*(.*?)\s*```'
        matches = list(re.finditer(pattern, content))
        
        for i, match in enumerate(matches, 1):
            mermaid_code = match.group(1)
            mmd_path = os.path.join(work_dir, f"temp-diagram-{i}.mmd")
            png_path = os.path.join(work_dir, f"temp-diagram-{i}.png")
            puppeteer_config_path = os.path.join(work_dir, "puppeteer-config.json")
            
            with open(puppeteer_config_path, "w", encoding="utf-8") as f:
                f.write('{"args": ["--no-sandbox"]}')
            
            with open(mmd_path, "w", encoding="utf-8") as f:
                f.write(mermaid_code)
            
            
            app.log(f"-> Şema {i} yüksek çözünürlüklü PNG olarak npx (izole ortam) ile çiziliyor...")
            # İşletim sistemindeki npx.cmd (veya Mac için npx) dosyasının tam yolunu güvenlice bul
            npx_path = deps.find_tool('npx')
            if not npx_path:
                raise Exception("Node.js (npx) sistemde bulunamadı! Lütfen 'Sistem Kontrol' menüsünden kurun.")

            # Çizim hata verse de geçici dosyalar kullanıcının klasöründe kalmasın
            temp_files.extend([mmd_path, png_path])

            # npx ile işletim sisteminden bağımsız anlık (on-the-fly) çalıştırma
            # DİKKAT: mmdc komutu açıkça belirtilmelidir, aksi takdirde npx '-p' parametresini kendine ait (--package) zanneder.
            # 9.1.7'de kalınmalı: sonraki sürümler Node 18+ ister. AI kurallarındaki UML sözdizimi kısıtları bu sürüme göredir.
            creation_flags = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
            result = subprocess.run(
                [npx_path, '--yes', '@mermaid-js/mermaid-cli@9.1.7', 'mmdc', '-i', mmd_path, '-o', png_path, '-b', 'transparent', '-s', '3', '-p', puppeteer_config_path, '--quiet'],
                capture_output=True, stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                cwd=work_dir, creationflags=creation_flags
            )
            if result.returncode != 0:
                raise Exception(f"Şema {i} çizilemedi:\n{_mermaid_error(result.stderr)}")

            # max height: Uzun (dikey) şemaların sayfanın alt kenarından taşmasını engeller.
            replace_str = f"\n\\vspace{{0.5cm}}\n\\begin{{figure}}[htbp]\n\\centering\n\\includegraphics[max width=\\textwidth, max height=0.85\\textheight, keepaspectratio]{{temp-diagram-{i}.png}}\n\\end{{figure}}\n\\vspace{{0.5cm}}\n"
            content = content.replace(match.group(0), replace_str)

        # 4a. Tablo Sütun Oranları
        # ZWSP'den önce çalışmalı: görünmez karakterler hücre uzunluğu ölçümünü şişirmesin.
        app.log("Tablo sütun genişlikleri içeriğe göre dengeleniyor...")
        content = balance_table_widths(content)

        # 4b. Tablo Taşma Kalkanı (Word-wrap Hack)
        # Pandoc ZWSP'yi \hspace{0pt}'e çevirir, yani o noktada tiresiz satır kırılabilir. Bu yüzden yalnızca
        # tanımlayıcılara (CamelCase, SNAKE_CASE, rakamlı) uygulanır; düz Türkçe kelimeleri TeX tireleyerek böler.
        # Kod bloklarına (ZWSP orada karakter olarak kalır, renklendirmeyi bozar) ve bağlantı adreslerine
        # (ZWSP linki bozar) dokunulmaz.
        app.log("Uzun kelimeler için tablo taşma kalkanı (ZWSP) uygulanıyor...")
        def insert_zwsp(match_obj):
            if match_obj.group(1):
                return match_obj.group(1)
            word = match_obj.group(0)
            if not re.search(r'[_\d]', word) and word[1:].islower():
                return word
            return '\u200B'.join([word[i:i+10] for i in range(0, len(word), 10)])
        content = re.sub(r'(?ms)(^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\2[ \t]*$|<[^>\s]+>|\]\([^)\s]*\)|https?://[^\s|)>]+)|\b\w{20,}\b',
                         insert_zwsp, content)

        # 5. Geçici MD oluştur
        temp_md_path = os.path.join(work_dir, "temp.md")
        with open(temp_md_path, "w", encoding="utf-8") as f:
            f.write(content)
        temp_files.append(temp_md_path)

        # 6. Başlık ve Tarih Üretimi
        clean_title = base_name.replace("-", " ").replace("_", " ").title()
        current_date = _turkish_date()

        # 7. Pandoc Derlemesi
        pandoc_path = deps.find_tool('pandoc')
        xelatex_path = deps.find_xelatex()
        if not pandoc_path or not xelatex_path:
            raise Exception("Pandoc veya XeLaTeX bulunamadı! Lütfen 'Sistem Kontrol' menüsünden kurun.")

        app.after(0, lambda: app.progress_bar.set(0.7))
        app.log("Pandoc ile kurumsal PDF derleniyor (Bu işlem birkaç saniye sürebilir)...")
        pdf_out_path = os.path.join(work_dir, f"{base_name}.pdf")
        pandoc_cmd = build_pandoc_cmd(pandoc_path, xelatex_path, temp_md_path, pdf_out_path, tex_path, clean_title, current_date)

        # cwd=work_dir eklendi! Bu sayede Pandoc, PNG resimlerini seçilen dosyanın klasöründe bulabilecek.
        result = run_pandoc(pandoc_cmd, work_dir, xelatex_path, app.log)

        if result.returncode != 0:
            app.log("[KRİTİK HATA] Pandoc PDF'i derlerken çöktü!")
            app.log(result.stderr)
            if theme != style.DEFAULT_THEME:
                app.log("Özel PDF stili etkin. Sorun stilden kaynaklanıyor olabilir; "
                        "'PDF Stili' sekmesinden 'Varsayılana Dön' ile tekrar deneyebilirsiniz.")
        else:
            app.log(f"[BAŞARILI] PDF hazır: {base_name}.pdf")
            app.after(0, lambda: [
                app.progress_bar.set(1.0),
                app.on_compile_success(pdf_out_path, work_dir)
            ])

    except Exception as e:
        app.log(f"[SİSTEM HATASI]: {str(e)}")
    
    finally:
        # Temizlik
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
        app.after(0, lambda: app.btn_compile.configure(state="normal"))
