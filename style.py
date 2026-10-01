"""
Kurumsal PDF stilinin kullanıcının düzenleyebildiği kısmı (tema).

Çekirdek stil (paketler, yükleme sırası, font ve bağlantı düzeltmeleri) constants.py'deki şablonda sabittir;
tema yalnızca şablondaki <<anahtar>> yer tutucularını doldurur. Tema settings.json'da saklanır.
"""
import re

import deps
from constants import KURUMSAL_STIL_SABLONU, FILIGRAN_SABLONU

SETTINGS_KEY = "theme"

DEFAULT_THEME = {
    "primary_color": "#005A9E",
    "secondary_color": "#646464",
    "header_text": "Teknik Dokümantasyon | İnnova Bilişim Çözümleri",
    "footer_text": "Hizmete Özel (Confidential)",
    "footer_center_text": "",
    "watermark_enabled": True,
    "watermark_text": "HİZMETE ÖZEL",
    "cover_subtitle": "Teknik Dokümantasyon",
    "cover_org": "İnnova Bilişim Çözümleri",
    "cover_notice": "Bu doküman hizmete özeldir ve izinsiz paylaşılamaz.",
    "margin_x_cm": 1.5,
    "margin_y_cm": 2.5,
    "extra_latex": "",
}

TEXT_KEYS = ("header_text", "footer_text", "footer_center_text", "watermark_text",
             "cover_subtitle", "cover_org", "cover_notice")
COLOR_KEYS = (("primary_color", "Ana renk"), ("secondary_color", "İkincil renk"))
MARGIN_KEYS = (("margin_x_cm", "Yatay kenar boşluğu"), ("margin_y_cm", "Dikey kenar boşluğu"))

_HEX = re.compile(r"#?([0-9A-Fa-f]{6})")
_PLACEHOLDER = re.compile(r"<<(\w+)>>")
_LATEX_SPECIAL = {
    "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&",
    "#": r"\#", "%": r"\%", "_": r"\_", "^": r"\textasciicircum{}", "~": r"\textasciitilde{}",
}


def _escape(text):
    # Form metni LaTeX komutu olarak yorumlanmasın (ör. "R&D", "%100" derlemeyi bozmasın)
    return "".join(_LATEX_SPECIAL.get(ch, ch) for ch in text)


def _margin(value):
    try:
        cm = float(str(value).strip().replace(",", "."))
    except ValueError:
        return None
    return cm if 0.5 <= cm <= 5 else None


def validate_theme(theme):
    """Temadaki hataları kullanıcıya gösterilecek mesajlar olarak döndürür; liste boşsa tema geçerlidir."""
    errors = []
    for key, label in COLOR_KEYS:
        if not _HEX.fullmatch(str(theme[key]).strip()):
            errors.append(f"{label} #RRGGBB biçiminde olmalı (ör. #005A9E).")
    for key, label in MARGIN_KEYS:
        if _margin(theme[key]) is None:
            errors.append(f"{label} 0,5 ile 5 cm arasında bir sayı olmalı.")
    return errors


def normalize_theme(theme):
    """Geçerli bir temayı kaydedilecek biçime getirir: #RRGGBB renkler, sayı kenar boşlukları, tek satır metinler."""
    result = dict(theme)
    for key, _ in COLOR_KEYS:
        result[key] = "#" + _HEX.fullmatch(str(theme[key]).strip()).group(1).upper()
    for key, _ in MARGIN_KEYS:
        result[key] = _margin(theme[key])
    for key in TEXT_KEYS:
        result[key] = " ".join(str(theme[key]).split())
    result["watermark_enabled"] = bool(theme["watermark_enabled"])
    result["extra_latex"] = str(theme["extra_latex"]).strip()
    return result


def load_theme():
    saved = deps._load_settings().get(SETTINGS_KEY) or {}
    theme = {**DEFAULT_THEME, **{k: v for k, v in saved.items() if k in DEFAULT_THEME}}
    # Ayar dosyası elle bozulmuşsa derleme varsayılan temayla sürer
    return dict(DEFAULT_THEME) if validate_theme(theme) else normalize_theme(theme)


def save_theme(theme):
    deps._save_setting(SETTINGS_KEY, normalize_theme(theme))


def build_style(theme):
    """Temayı çekirdek şablona yerleştirip pandoc'a verilecek LaTeX başlığını üretir."""
    theme = normalize_theme(theme)
    values = {key: _escape(theme[key]) for key in TEXT_KEYS}
    for key, _ in COLOR_KEYS:
        values[key] = theme[key][1:]
    for key, _ in MARGIN_KEYS:
        values[key] = f"{theme[key]:g}cm"
    values["watermark"] = (
        _PLACEHOLDER.sub(lambda m: values[m.group(1)], FILIGRAN_SABLONU) if theme["watermark_enabled"] else ""
    )
    # Gelişmiş LaTeX olduğu gibi, çekirdeğin sonuna eklenir; tek geçişte yerleştiği için içindeki
    # "<<...>>" metinleri yer tutucu sayılmaz
    values["extra_latex"] = theme["extra_latex"]
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], KURUMSAL_STIL_SABLONU)
