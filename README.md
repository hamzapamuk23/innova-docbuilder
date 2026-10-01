# innova-docbuilder

Markdown dokümanlarını İnnova kurumsal stilinde PDF'e dönüştüren masaüstü uygulaması.

## Geliştirme ortamında çalıştırma (`python app.py`)

Aşağıdaki adımları sırasıyla uygulayın.

1. **Python 3.10+ kurun** ([python.org](https://www.python.org/downloads/)). Windows'ta kurulum sırasında
   *"Add python.exe to PATH"* ve *"tcl/tk and IDLE"* seçeneklerinin işaretli olduğundan emin olun
   (arayüz Tkinter kullanır).

2. **(İsteğe bağlı) Sanal ortam oluşturun ve etkinleştirin:**

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS
   source .venv/bin/activate
   ```

3. **pip'i güncelleyin:**

   ```bash
   python -m pip install --upgrade pip
   ```

4. **Arayüz kütüphanesini kurun:**

   ```bash
   python -m pip install customtkinter
   ```

5. **(Yalnızca Windows) Pencere stili kütüphanesini kurun:**

   ```bash
   python -m pip install pywinstyles
   ```

6. **(Önerilen) SSL sertifika paketini kurun** — kurumsal ağlarda bağımlılık indirmelerinin
   sertifika hatası vermemesi için:

   ```bash
   python -m pip install certifi
   ```

7. **Uygulamayı başlatın:**

   ```bash
   python app.py
   ```

> **Not:** Pandoc, LaTeX (MiKTeX / TinyTeX / BasicTeX) ve Node.js (Mermaid/UML diyagramları için)
> Python paketi değildir; bunları elle kurmanıza gerek yoktur. Uygulama ilk çalıştırmada eksik olanları
> tespit eder ve otomatik olarak kurar (winget/Homebrew veya yönetici izni gerektirmeyen taşınabilir sürümler).

## Exe dosyası üretme

Yukarıdaki paketler kuruluyken:

```bash
python -m pip install pyinstaller
pyinstaller --noconsole --onefile --collect-all customtkinter --name "InnovaDocBuilder" app.py
```

Çıktı `dist/InnovaDocBuilder.exe` konumunda oluşur.
