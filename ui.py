import customtkinter as ctk
from tkinter import filedialog
import webbrowser
import subprocess
import threading
import os
import platform
import shutil

# Sadece Windows ise pywinstyles yükle
IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    import pywinstyles

from compiler import compile_pdf
from constants import AI_PROMPT_RULES

# --- RENK PALETİ: (Light, Dark) ---
SIDEBAR_BG = ("#EAEdf1", "#0F1D32")
MAIN_BG = ("#DEE2E8", "#0A1628")
CARD_BG = ("#FFFFFF", "#132035")
CARD_BORDER = ("#C8CED6", "#1C3352")
LOG_BG = ("#F0F2F4", "#0B1221")
LOG_TEXT = ("#24292F", "#8BA0B8")
TEXT_PRIMARY = ("#1F2328", "#E8ECF1")
TEXT_SECONDARY = ("#656D76", "#7B8CA3")
TEXT_MUTED = ("#8B949E", "#3D5069")
NAV_ACTIVE_BG = ("#D0D5DC", "#112845")
NAV_HOVER_BG = ("#D8DDE3", "#1A2D47")
NAV_TEXT = ("#57606A", "#7B8CA3")
NAV_ACTIVE_TEXT = ("#1F2328", "#FFFFFF")
PROGRESS_BG = ("#C8CED6", "#1C3352")
INNOVA_BLUE = "#0078D4"
INNOVA_DARK = "#005A9E"
GREEN = "#28A745"
RED = "#DC3545"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("İnnova DocBuilder")
        
        # Ekranın tam ortasında açılması
        window_width = 800
        window_height = 530
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        self.resizable(False, False)
        self.configure(fg_color=MAIN_BG)

        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")

        self.selected_file = None

        # ===============================================================
        #                           SIDEBAR
        # ===============================================================
        self.sidebar = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color=SIDEBAR_BG)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(25, 30))
        logo_inner = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_inner.pack()
        ctk.CTkLabel(logo_inner, text="İnnova", font=("Segoe UI", 18, "bold"), text_color=INNOVA_BLUE).pack(side="left")
        ctk.CTkLabel(logo_inner, text=" DocBuilder", font=("Segoe UI", 18), text_color=TEXT_SECONDARY).pack(side="left")

        # Navigasyon (Derle Sekmesi Kaldırıldı, Sadeleştirildi)
        self.nav_buttons = {}
        self.nav_dots = {}
        tabs = [
            ("dashboard", "⊞  Dashboard"),
            ("check",     "✔  Sistem Kontrol"),
            ("rules",     "⚙  AI Kuralları"),
        ]

        for tab_id, tab_text in tabs:
            row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=1)

            btn = ctk.CTkButton(
                row, text=tab_text, font=("Segoe UI", 14),
                fg_color="transparent", text_color=NAV_TEXT,
                hover_color=NAV_HOVER_BG, anchor="w",
                height=40, corner_radius=8,
                command=lambda t=tab_id: self.switch_tab(t)
            )
            btn.pack(side="left", fill="both", expand=True)
            dot = ctk.CTkLabel(row, text="", font=("Segoe UI", 10), width=20, text_color=SIDEBAR_BG)
            dot.pack(side="right")
            self.nav_buttons[tab_id] = btn
            self.nav_dots[tab_id] = dot

        self.nav_dots["rules"].configure(text="●", text_color=GREEN)

        # ===============================================================
        #                       SIDEBAR FOOTER
        # ===============================================================
        footer_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", padx=15, pady=(0, 20))

        # Tema Switch
        theme_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
        theme_frame.pack(fill="x", pady=(0, 12))
        self.lbl_theme = ctk.CTkLabel(theme_frame, text="☀️ Açık Tema", font=("Segoe UI", 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_theme.pack(side="left")
        self.theme_switch = ctk.CTkSwitch(theme_frame, text="", width=40, command=self.toggle_theme, progress_color=INNOVA_BLUE)
        self.theme_switch.pack(side="right")

        # Ayırıcı Çizgi (Separator)
        separator = ctk.CTkFrame(footer_frame, height=1, fg_color=CARD_BORDER)
        separator.pack(fill="x", pady=(0, 10))

        # Versiyon & Powered By
        ctk.CTkLabel(footer_frame, text="v1.0.0 • powered by TTPAY", font=("Segoe UI", 10, "bold"), text_color=TEXT_MUTED).pack()

        # ===============================================================
        #                        MAIN CONTENT
        # ===============================================================
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color=MAIN_BG)
        self.main_area.pack(side="right", fill="both", expand=True)

        self.frames = {}
        self._build_dashboard_frame()
        self._build_check_frame()
        self._build_rules_frame()

        self.current_tab = None
        self.switch_tab("dashboard")

        # Uygulama açıldıktan 0.5 saniye sonra AI kural uyarısı
        self.after(500, self.show_rules_modal)

    # ──────────────────────────────────────────────────────────────────
    #  DASHBOARD (Derleme İşlemlerinin Tek Merkezi)
    # ──────────────────────────────────────────────────────────────────
    def _build_dashboard_frame(self):
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["dashboard"] = frame

        # Drop Zone
        self.drop_zone = ctk.CTkFrame(
            frame, height=130, fg_color=CARD_BG,
            border_width=2, border_color=CARD_BORDER, corner_radius=12
        )
        self.drop_zone.pack(fill="x", padx=20, pady=(20, 12))
        self.drop_zone.pack_propagate(False)

        drop_content = ctk.CTkFrame(self.drop_zone, fg_color="transparent")
        drop_content.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_drop_icon = ctk.CTkLabel(drop_content, text="📁", font=("Segoe UI", 26), text_color=TEXT_SECONDARY)
        self.lbl_drop_icon.pack()
        self.lbl_drop_title = ctk.CTkLabel(drop_content, text="Dosya Seçmek İçin Tıklayın", font=("Segoe UI", 14, "bold"), text_color=TEXT_PRIMARY)
        self.lbl_drop_title.pack()
        self.lbl_drop_hint = ctk.CTkLabel(drop_content, text="Markdown dosyalarını (.md) seçin", font=("Segoe UI", 11), text_color=TEXT_SECONDARY)
        self.lbl_drop_hint.pack()

        for w in [self.drop_zone, drop_content] + drop_content.winfo_children():
            w.bind("<Button-1>", lambda e: self._select_file())

        # Compile PDF butonu
        self.btn_compile = ctk.CTkButton(
            frame, text="Compile PDF",
            command=self.start_compile_thread,
            font=("Segoe UI", 14, "bold"),
            fg_color=INNOVA_BLUE, hover_color=INNOVA_DARK,
            height=42, corner_radius=8
        )
        self.btn_compile.pack(fill="x", padx=20, pady=(0, 5))

        # Başarı durumunda gösterilecek butonlar (Başlangıçta gizli)
        self.success_frame = ctk.CTkFrame(frame, fg_color="transparent")
        
        self.btn_open_pdf = ctk.CTkButton(
            self.success_frame, text="📄 PDF'i Aç",
            font=("Segoe UI", 14, "bold"),
            fg_color="#28A745", hover_color="#218838",
            height=42, corner_radius=8
        )
        self.btn_open_pdf.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_open_folder = ctk.CTkButton(
            self.success_frame, text="📂 Klasörü Göster",
            font=("Segoe UI", 14, "bold"),
            fg_color="#17A2B8", hover_color="#138496",
            height=42, corner_radius=8
        )
        self.btn_open_folder.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Progress bar (Determinate mode)
        self.progress_bar = ctk.CTkProgressBar(
            frame, mode="determinate", progress_color=INNOVA_BLUE,
            height=4, corner_radius=2, fg_color=PROGRESS_BG
        )
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 12))
        self.progress_bar.set(0)

        # Log paneli
        log_frame = ctk.CTkFrame(frame, fg_color=LOG_BG, corner_radius=10, border_width=1, border_color=CARD_BORDER)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.log_box = ctk.CTkTextbox(
            log_frame, state="disabled",
            fg_color=LOG_BG, text_color=LOG_TEXT,
            font=("Consolas", 11), corner_radius=8
        )
        self.log_box.pack(fill="both", expand=True, padx=8, pady=8)

        self.log("Sistem hazır. Lütfen bir Markdown dosyası seçin.")

    # ──────────────────────────────────────────────────────────────────
    #  SİSTEM KONTROL: NPX, Winget, Brew Bağımlılık Yöneticisi
    # ──────────────────────────────────────────────────────────────────
    def _build_check_frame(self):
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["check"] = frame

        ctk.CTkLabel(frame, text="Sistem Kontrolü", font=("Segoe UI", 20, "bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=25, pady=(25, 5))
        ctk.CTkLabel(frame, text="PDF derleme için gerekli bağımlılıkları kontrol edin ve otomatik kurun.", font=("Segoe UI", 12), text_color=TEXT_SECONDARY).pack(anchor="w", padx=25, pady=(0, 15))

        card = ctk.CTkFrame(frame, corner_radius=10, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER)
        card.pack(fill="x", padx=25, pady=(0, 15))

        deps_info = [
            ("Pandoc", "Markdown → PDF dönüştürücü"),
            ("XeLaTeX", "LaTeX PDF motoru"),
            ("Mermaid CLI", "Diyagram çizim aracı (NPX)"),
        ]
        for name, desc in deps_info:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=6)
            ctk.CTkLabel(row, text=name, font=("Segoe UI", 13, "bold"), text_color=TEXT_PRIMARY).pack(side="left")
            ctk.CTkLabel(row, text=desc, font=("Segoe UI", 11), text_color=TEXT_SECONDARY).pack(side="left", padx=(10, 0))

        self.btn_check = ctk.CTkButton(
            card, text="Kontrol Et ve Kur",
            command=self.check_system,
            fg_color="#6c757d", hover_color="#5a6268",
            font=("Segoe UI", 13, "bold"), height=38
        )
        self.btn_check.pack(fill="x", padx=15, pady=(10, 15))

        self.check_log = ctk.CTkTextbox(
            frame, state="disabled",
            fg_color=LOG_BG, text_color=LOG_TEXT,
            font=("Consolas", 11), corner_radius=10,
            border_width=1, border_color=CARD_BORDER
        )
        self.check_log.pack(fill="both", expand=True, padx=25, pady=(0, 20))

    # ──────────────────────────────────────────────────────────────────
    #  AI KURALLARI: Kural kopyalama
    # ──────────────────────────────────────────────────────────────────
    def _build_rules_frame(self):
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["rules"] = frame

        ctk.CTkLabel(frame, text="AI Kuralları", font=("Segoe UI", 20, "bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=25, pady=(25, 5))
        ctk.CTkLabel(frame, text="Markdown üretimi için AI asistanınıza verilmesi gereken kurallar.", font=("Segoe UI", 12), text_color=TEXT_SECONDARY).pack(anchor="w", padx=25, pady=(0, 20))

        card = ctk.CTkFrame(frame, corner_radius=10, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER)
        card.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        info_text = (
            "Kusursuz ve kurumsal PDF'ler üretebilmek için, Markdown dosyalarınızı "
            "Yapay Zeka (Antigravity vb.) ile üretirken sisteme Innova standart kurallarını vermeniz gerekmektedir.\n\n"
            "Aksi takdirde üretilen Markdown, derleyici motorumuzu çökertebilir veya sayfa taşmalarına neden olabilir.\n\n"
            "Aşağıdaki butona tıklayarak kural setini kopyalayın ve AI asistanınıza 'Rules' olarak yapıştırın."
        )

        ctk.CTkLabel(card, text=info_text, wraplength=440, justify="left", font=("Segoe UI", 12), text_color=TEXT_PRIMARY).pack(padx=20, pady=(25, 20))

        self.btn_copy_rules = ctk.CTkButton(
            card, text="Kuralları Panoya Kopyala",
            command=self._copy_rules,
            font=("Segoe UI", 13, "bold"), fg_color=INNOVA_BLUE, hover_color=INNOVA_DARK, height=42
        )
        self.btn_copy_rules.pack(padx=20, pady=(0, 25))

    # ===============================================================
    #                      SEKME GEÇİŞİ
    # ===============================================================
    def switch_tab(self, tab_id):
        if self.current_tab == tab_id:
            return
        if self.current_tab and self.current_tab in self.frames:
            self.frames[self.current_tab].pack_forget()
        self.frames[tab_id].pack(fill="both", expand=True)
        for btn_id, btn in self.nav_buttons.items():
            if btn_id == tab_id:
                btn.configure(fg_color=NAV_ACTIVE_BG, text_color=NAV_ACTIVE_TEXT)
            else:
                btn.configure(fg_color="transparent", text_color=NAV_TEXT)
        self.current_tab = tab_id

    # ===============================================================
    #                      TEMA DEĞİŞTİRME
    # ===============================================================
    def toggle_theme(self):
        if self.theme_switch.get():
            ctk.set_appearance_mode("Dark")
            self.lbl_theme.configure(text="🌙 Koyu Tema")
            if IS_WINDOWS:
                pywinstyles.apply_style(self, "acrylic")
        else:
            ctk.set_appearance_mode("Light")
            self.lbl_theme.configure(text="☀️ Açık Tema")
            if IS_WINDOWS:
                pywinstyles.apply_style(self, "normal")

    # ===============================================================
    #                      AI KURAL MODAL
    # ===============================================================
    def show_rules_modal(self):
        """Uygulama açılışında zorunlu olarak gösterilen AI Uyarı Penceresi"""
        modal = ctk.CTkToplevel(self)
        modal.title("Kritik Uyarı - AI Kuralları")
        
        window_width = 500
        window_height = 320
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        modal.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        
        modal.resizable(False, False)
        modal.attributes("-topmost", True)
        modal.grab_set()

        ctk.CTkLabel(modal, text="AI Prompt (Kural) Entegrasyonu Zorunludur!", font=("Segoe UI", 16, "bold"), text_color="#D9534F").pack(pady=(20, 10))

        info_text = (
            "Kusursuz ve kurumsal PDF'ler üretebilmek için, Markdown dosyalarınızı "
            "Yapay Zeka (Antigravity vb.) ile üretirken sisteme Innova standart kurallarını vermeniz gerekmektedir.\n\n"
            "Aksi takdirde üretilen Markdown, derleyici motorumuzu çökertebilir veya sayfa taşmalarına neden olabilir.\n\n"
            "Lütfen aşağıdaki butona tıklayarak kural setini kopyalayın ve AI asistanınıza 'Rules' olarak yapıştırın."
        )

        ctk.CTkLabel(modal, text=info_text, wraplength=440, justify="left", font=("Segoe UI", 12)).pack(pady=(0, 20), padx=20)

        btn_copy = ctk.CTkButton(modal, text="Kuralları Panoya Kopyala", font=("Segoe UI", 12, "bold"),
                                 command=lambda: self.copy_to_clipboard(modal, btn_copy))
        btn_copy.pack(pady=5)

        ctk.CTkButton(modal, text="Anladım, Devam Et", command=modal.destroy,
                      fg_color="#28a745", hover_color="#218838", font=("Segoe UI", 12, "bold")).pack(pady=10)

    def copy_to_clipboard(self, modal, button):
        self.clipboard_clear()
        self.clipboard_append(AI_PROMPT_RULES)
        self.update()
        button.configure(text="Kurallar Kopyalandı!", fg_color=INNOVA_BLUE)
        modal.after(2500, lambda: button.configure(text="Kuralları Panoya Kopyala", fg_color=["#3a7ebf", "#1f538d"]))

    def _copy_rules(self):
        self.clipboard_clear()
        self.clipboard_append(AI_PROMPT_RULES)
        self.update()
        self.btn_copy_rules.configure(text="Kurallar Kopyalandı!", fg_color="#28a745")
        self.after(2500, lambda: self.btn_copy_rules.configure(text="Kuralları Panoya Kopyala", fg_color=INNOVA_BLUE))

    # ===============================================================
    #                    DOSYA SEÇME & DERLEME
    # ===============================================================
    def _select_file(self):
        file_path = filedialog.askopenfilename(
            title="Derlenecek Markdown Dosyasını Seçin",
            filetypes=[("Markdown Dosyaları", "*.md")]
        )
        if file_path:
            self.selected_file = file_path
            self.lbl_drop_title.configure(text=os.path.basename(file_path))
            self.lbl_drop_hint.configure(text="Dosya seçildi — Compile PDF'e tıklayın")
            
            # Görsel Geribildirim
            self.drop_zone.configure(border_color=INNOVA_BLUE)
            self.lbl_drop_icon.configure(text="📄", text_color=INNOVA_BLUE)
            
            # UI Reset
            self.success_frame.pack_forget()
            self.btn_compile.pack(fill="x", padx=20, pady=(0, 5))
            self.progress_bar.set(0)

    def log(self, message):
        def _update():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"> {message}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _update)

    def check_system(self):
        self.check_log.configure(state="normal")
        self.check_log.delete("1.0", "end")
        self.check_log.configure(state="disabled")

        def _log_check(msg):
            def _update():
                self.check_log.configure(state="normal")
                self.check_log.insert("end", f"{msg}\n")
                self.check_log.see("end")
                self.check_log.configure(state="disabled")
            self.after(0, _update)

        _log_check("> Sistem bağımlılıkları kontrol ediliyor...\n")

        def run_checks():
            self.after(0, lambda: self.btn_check.configure(state="disabled"))
            deps = ["pandoc", "xelatex"]
            install_happened = False

            for dep in deps:
                # 1. Kurulu mu kontrol et (shutil.which ile güvenli check)
                cmd_path = shutil.which(dep)
                if cmd_path:
                    _log_check(f"[OK] {dep} sistemde zaten kurulu.")
                    continue
                else:
                    _log_check(f"\n[EKSİK] {dep} bulunamadı! Otomatik kurulum başlatılıyor...")
                    install_happened = True

                # 2. Otomatik Kurulum Senaryoları
                try:
                    if IS_WINDOWS:
                        if dep == "pandoc":
                            _log_check("   -> Pandoc indiriliyor (winget ile)...")
                            subprocess.run('winget install --id JohnMacFarlane.Pandoc --accept-package-agreements --accept-source-agreements --silent', shell=True, check=True)
                        elif dep == "xelatex":
                            _log_check("   -> MiKTeX indiriliyor (Boyutu büyüktür, lütfen bekleyin)...")
                            subprocess.run('winget install --id ChristianSchenk.MiKTeX --accept-package-agreements --accept-source-agreements --silent', shell=True, check=True)
                    else: # Mac Ortamı
                        if dep == "pandoc":
                            _log_check("   -> Pandoc indiriliyor (brew ile)...")
                            subprocess.run("brew install pandoc", shell=True, check=True)
                        elif dep == "xelatex":
                            _log_check("   -> MacTeX indiriliyor (Boyutu büyüktür, lütfen bekleyin)...")
                            subprocess.run("brew install --cask mactex-no-gui", shell=True, check=True)
                    
                    _log_check(f"[BAŞARILI] {dep} başarıyla sisteme entegre edildi!")
                
                except Exception as e:
                    _log_check(f"[KRİTİK HATA] {dep} kurulamadı. IT kısıtlaması olabilir. Hata: {str(e)}")

            # Mermaid (NPX) Kontrolü
            _log_check("\n> Mermaid CLI (NPX) altyapısı kontrol ediliyor...")
            npx_path = shutil.which("npx")
            if npx_path:
                _log_check("[OK] Node.js (npx) bulundu. Mermaid anlık (on-the-fly) çalıştırılacak.")
            else:
                _log_check("[EKSİK] Node.js bulunamadı! Kuruluyor...")
                install_happened = True
                try:
                    if IS_WINDOWS:
                        subprocess.run('winget install --id OpenJS.NodeJS --accept-package-agreements --accept-source-agreements --silent', shell=True, check=True)
                    else:
                        subprocess.run("brew install node", shell=True, check=True)
                    _log_check("[BAŞARILI] Node.js kuruldu.")
                except Exception as e:
                    _log_check(f"[KRİTİK HATA] Node.js kurulamadı. Hata: {str(e)}")

            if install_happened:
                _log_check("\n=======================================================")
                _log_check("⚠️ ÖNEMLİ UYARI: KURULUMLAR TAMAMLANDI ⚠️")
                _log_check("Yeni programların işletim sistemi tarafından algılanıp")
                _log_check("PATH (Ortam Değişkenleri) listesine eklenebilmesi için,")
                _log_check("LÜTFEN UYGULAMAYI KAPATIP YENİDEN AÇINIZ!")
                _log_check("=======================================================\n")
            else:
                _log_check("\n> Tüm sistem gereksinimleri karşılanıyor. PDF derlemeye hazırsınız.")
            
            self.after(0, lambda: self.btn_check.configure(state="normal"))

        threading.Thread(target=run_checks).start()

    def start_compile_thread(self):
        if not self.selected_file:
            file_path = filedialog.askopenfilename(
                title="Derlenecek Markdown Dosyasını Seçin",
                filetypes=[("Markdown Dosyaları", "*.md")]
            )
            if not file_path:
                return
            self.selected_file = file_path

        file_path = self.selected_file
        self.selected_file = None

        self.lbl_drop_title.configure(text="Dosya Seçmek İçin Tıklayın")
        self.lbl_drop_hint.configure(text="Markdown dosyalarını (.md) seçin")
        self.drop_zone.configure(border_color=CARD_BORDER)
        self.lbl_drop_icon.configure(text="📁", text_color=TEXT_SECONDARY)

        self.progress_bar.set(0.1)

        def compile_and_finish():
            compile_pdf(self, file_path)
        
        threading.Thread(target=compile_and_finish).start()

    def on_compile_success(self, pdf_out_path, work_dir):
        def _update():
            self.btn_compile.pack_forget()
            self.success_frame.pack(fill="x", padx=20, pady=(0, 5))
            
            self.btn_open_pdf.configure(command=lambda: webbrowser.open(pdf_out_path))
            
            if IS_WINDOWS:
                self.btn_open_folder.configure(command=lambda: os.startfile(work_dir))
            else:
                self.btn_open_folder.configure(command=lambda: subprocess.run(['open', work_dir]))
                
        self.after(0, _update)