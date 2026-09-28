import customtkinter as ctk
from tkinter import filedialog, colorchooser, messagebox
import webbrowser
import subprocess
import threading
import os
import platform

# Sadece Windows ise pywinstyles yükle
IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    import pywinstyles

import deps
import style
from compiler import compile_pdf, self_test as compile_self_test
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
TT_BLUE = "#0078D4"
TT_DARK = "#005A9E"
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
        ctk.CTkLabel(logo_frame, text="İnnova", font=("Segoe UI", 18, "bold"), text_color=TT_BLUE, height=24).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(logo_frame, text="DocBuilder", font=("Segoe UI", 18), text_color=TEXT_SECONDARY, height=24).pack(side="left")

        # Navigasyon (Derle Sekmesi Kaldırıldı, Sadeleştirildi)
        self.nav_buttons = {}
        self.nav_dots = {}
        tabs = [
            ("dashboard", "⊞  Dashboard"),
            ("check",     "✔  Sistem Kontrol"),
            ("rules",     "⚙  AI Kuralları"),
            ("style",     "✎  PDF Stili"),
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
        self.theme_switch = ctk.CTkSwitch(theme_frame, text="", width=40, command=self.toggle_theme, progress_color=TT_BLUE)
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
        self._build_style_frame()

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
            fg_color=TT_BLUE, hover_color=TT_DARK,
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
            frame, mode="determinate", progress_color=TT_BLUE,
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
            "Yapay Zeka (Antigravity vb.) ile üretirken sisteme İnnova standart kurallarını vermeniz gerekmektedir.\n\n"
            "Aksi takdirde üretilen Markdown, derleyici motorumuzu çökertebilir veya sayfa taşmalarına neden olabilir.\n\n"
            "Aşağıdaki butona tıklayarak kural setini kopyalayın ve AI asistanınıza 'Rules' olarak yapıştırın."
        )

        ctk.CTkLabel(card, text=info_text, wraplength=440, justify="left", font=("Segoe UI", 12), text_color=TEXT_PRIMARY).pack(padx=20, pady=(25, 20))

        self.btn_copy_rules = ctk.CTkButton(
            card, text="Kuralları Panoya Kopyala",
            command=self._copy_rules,
            font=("Segoe UI", 13, "bold"), fg_color=TT_BLUE, hover_color=TT_DARK, height=42
        )
        self.btn_copy_rules.pack(padx=20, pady=(0, 25))

    # ──────────────────────────────────────────────────────────────────
    #  PDF STİLİ: Kurumsal stilin düzenlenebilir kısmı (tema, bkz. style.py)
    # ──────────────────────────────────────────────────────────────────
    def _build_style_frame(self):
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["style"] = frame

        ctk.CTkLabel(frame, text="PDF Stili", font=("Segoe UI", 20, "bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=25, pady=(25, 5))
        ctk.CTkLabel(frame, text="Kurumsal PDF'in renk, metin ve sayfa ayarları. Kaydetmeden önce test derlemesi yapılır.", font=("Segoe UI", 12), text_color=TEXT_SECONDARY).pack(anchor="w", padx=25, pady=(0, 10))

        # Butonlar önce alta yerleşir ki kaydırılabilir form kalan yüksekliği doldursun
        bottom = ctk.CTkFrame(frame, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=25, pady=(0, 15))
        self.lbl_style_status = ctk.CTkLabel(bottom, text="", font=("Segoe UI", 11), text_color=TEXT_SECONDARY,
                                             wraplength=540, justify="left", anchor="w")
        self.lbl_style_status.pack(fill="x", pady=(0, 6))
        buttons = ctk.CTkFrame(bottom, fg_color="transparent")
        buttons.pack(fill="x")
        self.btn_style_save = ctk.CTkButton(
            buttons, text="Kaydet ve Test Et", command=self._save_style,
            font=("Segoe UI", 13, "bold"), fg_color=TT_BLUE, hover_color=TT_DARK, height=38
        )
        self.btn_style_save.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.btn_style_reset = ctk.CTkButton(
            buttons, text="Varsayılana Dön", command=self._reset_style,
            font=("Segoe UI", 13, "bold"), fg_color="#6c757d", hover_color="#5a6268", height=38
        )
        self.btn_style_reset.pack(side="left", fill="x", expand=True, padx=(5, 0))

        form = ctk.CTkScrollableFrame(frame, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=CARD_BORDER)
        form.pack(fill="both", expand=True, padx=25, pady=(0, 10))
        form.grid_columnconfigure(1, weight=1)

        self.style_vars = {}
        row = 0

        def section(title, hint=None):
            nonlocal row
            ctk.CTkLabel(form, text=title, font=("Segoe UI", 13, "bold"), text_color=TT_BLUE).grid(
                row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(14 if row else 6, 2))
            row += 1
            if hint:
                ctk.CTkLabel(form, text=hint, font=("Segoe UI", 11), text_color=TEXT_SECONDARY,
                             wraplength=480, justify="left").grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))
                row += 1

        def label(text):
            ctk.CTkLabel(form, text=text, font=("Segoe UI", 12), text_color=TEXT_PRIMARY).grid(
                row=row, column=0, sticky="w", padx=(10, 10), pady=3)

        def text_field(key, text, width=None):
            nonlocal row
            label(text)
            var = ctk.StringVar()
            ctk.CTkEntry(form, textvariable=var, font=("Segoe UI", 12), height=30, width=width or 140).grid(
                row=row, column=1, sticky="w" if width else "ew", padx=(0, 10), pady=3)
            self.style_vars[key] = var
            row += 1

        def color_field(key, text):
            nonlocal row
            label(text)
            holder = ctk.CTkFrame(form, fg_color="transparent")
            holder.grid(row=row, column=1, sticky="w", pady=3)
            var = ctk.StringVar()
            ctk.CTkEntry(holder, textvariable=var, font=("Consolas", 12), height=30, width=100).pack(side="left")
            swatch = ctk.CTkFrame(holder, width=30, height=30, corner_radius=6, border_width=1, border_color=CARD_BORDER)
            swatch.pack(side="left", padx=8)

            def update_swatch(*_):
                value = var.get().strip()
                value = value if value.startswith("#") else "#" + value
                if not style.validate_theme({**style.DEFAULT_THEME, key: value}):
                    swatch.configure(fg_color=value)
            var.trace_add("write", update_swatch)

            def pick():
                current = var.get().strip()
                valid = not style.validate_theme({**style.DEFAULT_THEME, key: current})
                chosen = colorchooser.askcolor(color=("#" + current.lstrip("#")) if valid else None, parent=self, title=text)[1]
                if chosen:
                    var.set(chosen.upper())
            ctk.CTkButton(holder, text="Seç", width=60, height=30, command=pick,
                          fg_color="#6c757d", hover_color="#5a6268").pack(side="left")
            self.style_vars[key] = var
            row += 1

        section("Renkler", "Ana renk başlıklarda, bağlantılarda ve kapakta; ikincil renk üst/alt bilgide kullanılır.")
        color_field("primary_color", "Ana renk")
        color_field("secondary_color", "İkincil renk")

        section("Üst ve Alt Bilgi", "Orta alt bilgi her sayfanın altında ortalanır (ör. takım adı); boş bırakılırsa gösterilmez.")
        text_field("header_text", "Üst bilgi (sağ üst)")
        text_field("footer_text", "Alt bilgi (sol alt)")
        text_field("footer_center_text", "Alt bilgi (orta)")

        section("Filigran")
        label("Filigranı göster")
        self.style_vars["watermark_enabled"] = ctk.BooleanVar()
        ctk.CTkSwitch(form, text="", variable=self.style_vars["watermark_enabled"], progress_color=TT_BLUE).grid(
            row=row, column=1, sticky="w", pady=3)
        row += 1
        text_field("watermark_text", "Filigran metni")

        section("Kapak Sayfası")
        text_field("cover_subtitle", "Alt başlık")
        text_field("cover_org", "Kurum adı")
        text_field("cover_notice", "Uyarı metni")

        section("Sayfa Kenar Boşlukları (cm)")
        text_field("margin_x_cm", "Sağ ve sol", width=80)
        text_field("margin_y_cm", "Üst ve alt", width=80)

        # Serbest LaTeX alanı, LaTeX bilmeyenlerin kafasını karıştırmasın diye bir düğmenin arkasında gizli durur
        self.style_form = form
        self.btn_style_advanced = ctk.CTkButton(
            form, text="", command=lambda: self._show_style_advanced(not self.style_advanced_visible),
            font=("Segoe UI", 13, "bold"), fg_color="transparent", text_color=TT_BLUE,
            hover_color=NAV_HOVER_BG, anchor="w", height=28, width=10
        )
        self.btn_style_advanced.grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=(14, 2))
        row += 1
        self.style_advanced_hint = ctk.CTkLabel(
            form, text="Çekirdek stilin sonuna eklenen serbest LaTeX; yalnızca LaTeX bilenler içindir. "
                       "Hatalı kod test derlemesinde yakalanır ve kaydedilmez.",
            font=("Segoe UI", 11), text_color=TEXT_SECONDARY, wraplength=480, justify="left")
        self.style_advanced_hint.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))
        row += 1
        self.style_extra = ctk.CTkTextbox(form, height=110, font=("Consolas", 11), fg_color=LOG_BG, text_color=LOG_TEXT,
                                          border_width=1, border_color=CARD_BORDER)
        self.style_extra.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=(3, 10))

        theme = style.load_theme()
        self._fill_style_form(theme)
        # Kayıtlı özel LaTeX varsa alan açık başlar; etkin olan kod gözden gizli kalmasın
        self._show_style_advanced(bool(theme["extra_latex"]), scroll=False)

    def _show_style_advanced(self, show, scroll=True):
        self.style_advanced_visible = show
        for widget in (self.style_advanced_hint, self.style_extra):
            if show:
                widget.grid()
            else:
                widget.grid_remove()
        self.btn_style_advanced.configure(text="▾  Gelişmiş ayarları gizle" if show else "▸  Gelişmiş ayarları göster")
        if show and scroll:
            # Alan formun en altında açılır; kullanıcının ayrıca kaydırması gerekmesin
            self.after(50, lambda: self.style_form._parent_canvas.yview_moveto(1.0))

    def _fill_style_form(self, theme):
        for key, var in self.style_vars.items():
            if key == "watermark_enabled":
                var.set(bool(theme[key]))
            elif key in ("margin_x_cm", "margin_y_cm"):
                var.set(f"{theme[key]:g}".replace(".", ","))
            else:
                var.set(theme[key])
        self.style_extra.delete("1.0", "end")
        self.style_extra.insert("1.0", theme["extra_latex"])

    def _read_style_form(self):
        theme = {key: var.get() for key, var in self.style_vars.items()}
        theme["extra_latex"] = self.style_extra.get("1.0", "end")
        return theme

    def _set_style_status(self, text, color=TEXT_SECONDARY, busy=False):
        def _update():
            self.lbl_style_status.configure(text=text, text_color=color)
            state = "disabled" if busy else "normal"
            self.btn_style_save.configure(state=state)
            self.btn_style_reset.configure(state=state)
        self.after(0, _update)

    def _save_style(self):
        theme = self._read_style_form()
        errors = style.validate_theme(theme)
        if errors:
            self._set_style_status("\n".join(errors), RED)
            return
        theme = style.normalize_theme(theme)
        self._set_style_status("Test derlemesi yapılıyor, lütfen bekleyin...", busy=True)

        def run():
            pandoc, xelatex = deps.find_tool("pandoc"), deps.find_xelatex()
            if not pandoc or not xelatex:
                self._set_style_status("Pandoc veya XeLaTeX bulunamadı. Önce 'Sistem Kontrol' sekmesinden kurun.", RED)
                return
            messages = []
            try:
                ok = compile_self_test(pandoc, xelatex, messages.append, style.build_style(theme))
            except Exception as e:
                ok = False
                messages.append(str(e))
            if ok:
                style.save_theme(theme)
                self._set_style_status("Kaydedildi. Sonraki derlemelerde bu stil kullanılacak.", GREEN)
            else:
                detail = messages[-1].strip() if messages else ""
                # LaTeX hatası "!" ile başlar; öncesindeki font uyarıları kullanıcı için gürültüdür
                detail = detail[detail.find("! "):] if "! " in detail else detail[-400:]
                self._set_style_status(f"Test derlemesi başarısız oldu, stil kaydedilmedi.\n{detail}", RED)

        threading.Thread(target=run, daemon=True).start()

    def _reset_style(self):
        if not messagebox.askyesno("Varsayılana Dön", "Tüm PDF stili ayarları varsayılan değerlere dönecek. Devam edilsin mi?", parent=self):
            return
        style.save_theme(style.DEFAULT_THEME)
        self._fill_style_form(style.DEFAULT_THEME)
        self._set_style_status("Varsayılan stil geri yüklendi.", GREEN)

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
            "Yapay Zeka (Antigravity vb.) ile üretirken sisteme İnnova standart kurallarını vermeniz gerekmektedir.\n\n"
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
        button.configure(text="Kurallar Kopyalandı!", fg_color=TT_BLUE)
        modal.after(2500, lambda: button.configure(text="Kuralları Panoya Kopyala", fg_color=["#3a7ebf", "#1f538d"]))

    def _copy_rules(self):
        self.clipboard_clear()
        self.clipboard_append(AI_PROMPT_RULES)
        self.update()
        self.btn_copy_rules.configure(text="Kurallar Kopyalandı!", fg_color="#28a745")
        self.after(2500, lambda: self.btn_copy_rules.configure(text="Kuralları Panoya Kopyala", fg_color=TT_BLUE))

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
            self.drop_zone.configure(border_color=TT_BLUE)
            self.lbl_drop_icon.configure(text="📄", text_color=TT_BLUE)
            
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
            try:
                # Her bağımlılık için birden fazla kurulum yolu sırayla denenir (bkz. deps.py)
                failed = deps.check_and_install(compile_self_test, _log_check)
            except Exception as e:
                failed = ["?"]
                _log_check(f"\n[SİSTEM HATASI] {e}")

            if failed:
                _log_check("\n=======================================================")
                _log_check(f"⚠️ KURULAMAYAN BİLEŞENLER: {', '.join(failed)}")
                _log_check("Tüm otomatik yöntemler denendi. İnternet/proxy erişimi veya")
                _log_check("IT kısıtlaması olabilir. Yukarıdaki hata mesajlarını IT")
                _log_check("ekibinizle paylaşabilirsiniz.")
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
            
            if IS_WINDOWS:
                self.btn_open_pdf.configure(command=lambda: webbrowser.open(pdf_out_path))
                self.btn_open_folder.configure(command=lambda: os.startfile(work_dir))
            else:
                # Mac'te webbrowser düz dosya yolunu AppleScript "open location" ile açmaya çalışır ve sessizce başarısız olur
                self.btn_open_pdf.configure(command=lambda: subprocess.run(['open', pdf_out_path]))
                self.btn_open_folder.configure(command=lambda: subprocess.run(['open', work_dir]))
                
        self.after(0, _update)