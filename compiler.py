import os
import re
import subprocess
import platform
import shutil
from datetime import datetime

IS_WINDOWS = platform.system() == "Windows"

from constants import KURUMSAL_STIL


def compile_pdf(app, md_path):
    app.after(0, lambda: app.btn_compile.configure(state="disabled"))
    work_dir = os.path.dirname(md_path)
    filename = os.path.basename(md_path)
    base_name = os.path.splitext(filename)[0]
    
    app.log(f"İşleniyor: {filename}")
    temp_files = []

    try:
        # 1. Stili geçici olarak oluştur
        tex_path = os.path.join(work_dir, "kurumsal-stil.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(KURUMSAL_STIL)
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
            npx_path = shutil.which('npx')
            if not npx_path:
                raise Exception("Node.js (npx) sistemde bulunamadı! Lütfen 'Sistem Kontrol' menüsünden kurun.")

            # npx ile işletim sisteminden bağımsız anlık (on-the-fly) çalıştırma
            # DİKKAT: mmdc komutu açıkça belirtilmelidir, aksi takdirde npx '-p' parametresini kendine ait (--package) zanneder.
            creation_flags = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
            subprocess.run(
                [npx_path, '--yes', '@mermaid-js/mermaid-cli@9.1.7', 'mmdc', '-i', mmd_path, '-o', png_path, '-b', 'transparent', '-s', '3', '-p', puppeteer_config_path, '--quiet'],
                check=True, cwd=work_dir, creationflags=creation_flags
            )
            
            replace_str = f"\n\\vspace{{0.5cm}}\n\\begin{{figure}}[htbp]\n\\centering\n\\includegraphics[max width=\\textwidth, keepaspectratio]{{temp-diagram-{i}.png}}\n\\end{{figure}}\n\\vspace{{0.5cm}}\n"
            content = content.replace(match.group(0), replace_str)
            temp_files.extend([mmd_path, png_path])

        # 4. Tablo Taşma Kalkanı (Word-wrap Hack)
        app.log("Uzun kelimeler için tablo taşma kalkanı (ZWSP) uygulanıyor...")
        def insert_zwsp(match_obj):
            word = match_obj.group(0)
            return '\u200B'.join([word[i:i+10] for i in range(0, len(word), 10)])
        content = re.sub(r'\b\w{20,}\b', insert_zwsp, content)

        # 5. Geçici MD oluştur
        temp_md_path = os.path.join(work_dir, "temp.md")
        with open(temp_md_path, "w", encoding="utf-8") as f:
            f.write(content)
        temp_files.append(temp_md_path)

        # 6. Başlık ve Tarih Üretimi
        clean_title = base_name.replace("-", " ").replace("_", " ").title()
        # Tarih formatı (Türkçe ay isimleri için manuel mapping)
        aylar = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        now = datetime.now()
        current_date = f"{now.day} {aylar[now.month]} {now.year}"

        # 7. Pandoc Derlemesi
        app.after(0, lambda: app.progress_bar.set(0.7))
        app.log("Pandoc ile kurumsal PDF derleniyor (Bu işlem birkaç saniye sürebilir)...")
        pdf_out_path = os.path.join(work_dir, f"{base_name}.pdf")
        pandoc_cmd = [
            'pandoc', temp_md_path, '-o', pdf_out_path,
            '--pdf-engine=xelatex', f'--include-in-header={tex_path}',
            '--syntax-highlighting=tango', '--toc', '--toc-depth=3',
            '--metadata', f'title={clean_title}',
            '--metadata', f'date={current_date}'
        ]
        
        # cwd=work_dir eklendi! Bu sayede Pandoc, PNG resimlerini seçilen dosyanın klasöründe bulabilecek.
        # UTF-8 encoding ve replace eklendi: Windows konsolunun varsayılan charmap (cp1254) ile UTF-8 okumaya çalışıp çökmesini engeller.
        creation_flags = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
        result = subprocess.run(pandoc_cmd, capture_output=True, text=True, cwd=work_dir, encoding="utf-8", errors="replace", creationflags=creation_flags)
        
        if result.returncode != 0:
            app.log("[KRİTİK HATA] Pandoc PDF'i derlerken çöktü!")
            app.log(result.stderr)
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
