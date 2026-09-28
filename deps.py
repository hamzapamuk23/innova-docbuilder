"""
Sistem bağımlılıklarını (pandoc, xelatex, node/npx) bulma ve otomatik kurma.

Her bağımlılık için birden fazla kurulum yolu sırayla denenir; biri başarısız olursa
(winget engelli, GitHub erişimi yok, yönetici izni yok vb.) bir sonrakine geçilir.
Kurulan programların klasörleri çalışan uygulamanın PATH'ine eklendiği için
uygulamayı yeniden başlatmaya gerek kalmaz.
"""
import glob
import json
import os
import platform
import re
import shlex
import shutil
import ssl
import subprocess
import tempfile
import urllib.request
import zipfile

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
IS_ARM = platform.machine().lower() in ("arm64", "aarch64")

HOME = os.path.expanduser("~")
if IS_WINDOWS:
    LOCALAPPDATA = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
    APPDATA = os.environ.get("APPDATA") or os.path.join(HOME, "AppData", "Roaming")
    PROGRAMDATA = os.environ.get("ProgramData") or r"C:\ProgramData"
    PROGRAMFILES = os.environ.get("ProgramFiles") or r"C:\Program Files"
    DATA_DIR = os.path.join(LOCALAPPDATA, "InnovaDocBuilder")
    # TeX kurulum yolu boşluk veya ASCII dışı karakter (ör. Türkçe kullanıcı adı) içeremez;
    # TinyTeX'in resmi kurulum betiğindeki kural aynen uygulanır.
    _TINYTEX_PARENT = APPDATA if re.fullmatch(r"[!-~]+", APPDATA) else PROGRAMDATA
else:
    DATA_DIR = os.path.join(HOME, "Library", "Application Support", "InnovaDocBuilder")
    _TINYTEX_PARENT = os.path.join(HOME, "Library")

# Uygulamanın doğrudan indirdiği taşınabilir araçlar (pandoc, node) buraya açılır
TOOLS_DIR = os.path.join(DATA_DIR, "tools")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
TINYTEX_DIR = os.path.join(_TINYTEX_PARENT, "TinyTeX")

TINYTEX_URL = "https://github.com/rstudio/tinytex-releases/releases/download/daily/" + (
    "TinyTeX-1-windows.exe" if IS_WINDOWS else "TinyTeX-1-darwin.tar.xz"
)
CTAN = "https://mirrors.ctan.org"
PANDOC_FALLBACK_VERSION = "3.11"
USER_AGENT = "InnovaDocBuilder/1.0"

# Kurumsal stil + pandoc şablonunun ihtiyaç duyduğu, TinyTeX / BasicTeX ile gelmeyen LaTeX paketleri.
# (Eksik kalan olursa derleme çıktısından tespit edilip ayrıca kurulur.)
TEX_PACKAGES = [
    "adjustbox", "collectbox", "newunicodechar", "pdflscape", "titlesec", "ragged2e",
    "fancyhdr", "fvextra", "lineno", "upquote", "tcolorbox", "pdfcol", "tikzfill",
    "environ", "trimspaces", "listings", "listingsutf8", "draftwatermark", "float",
    "booktabs", "framed", "soul", "caption", "xurl", "bookmark", "footnotehyper",
    "lm-math", "unicode-math",
]

WINGET_ALREADY_INSTALLED = (0x8A150061, 0x8A15002B)
WINGET_ERRORS = {
    0x8A150014: "paket winget kaynağında bulunamadı",
    0x8A15000F: "winget kaynak verisi eksik (kaynak engellenmiş olabilir)",
    0x8A150010: "bu sisteme uygun kurulum dosyası yok",
    0x8A150011: "indirilen dosyanın doğrulaması (hash) başarısız",
    0x8A150056: "bu kurulum yönetici (admin) olarak açılmış bir uygulamadan yapılamaz",
    0x8A150102: "başka bir kurulum devam ediyor",
    0x8A150105: "diskte yeterli yer yok",
    0x8A150107: "internet bağlantısı yok",
    0x8A150109: "kurulumun tamamlanması için bilgisayarın yeniden başlatılması gerekiyor",
}


# ───────────────────────────── Yardımcılar ─────────────────────────────

def tail_output(text, lines=4):
    """Uzun komut çıktısının son anlamlı satırlarını döndürür (ilerleme çubukları atılır)."""
    rows = [r.strip() for r in re.split(r"[\r\n]+", text or "") if r.strip()]
    rows = [r for r in rows if not re.fullmatch(r"[\s\-\\|/█▒░.%\dKMGB]+", r)]
    return " | ".join(rows[-lines:])


def _run(cmd, timeout=1800, **kwargs):
    """Komutu konsol penceresi açmadan çalıştırır ve çıktıyı metin olarak yakalar.
    stdin kapalıdır: soru soran bir program görünmez pencerede sonsuza kadar beklemesin."""
    return subprocess.run(
        cmd, capture_output=True, stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
        errors="replace", timeout=timeout, creationflags=NO_WINDOW, **kwargs
    )


def _run_checked(cmd, what, timeout=1800, **kwargs):
    res = _run(cmd, timeout=timeout, **kwargs)
    if res.returncode != 0:
        raise RuntimeError(f"{what} başarısız (kod {res.returncode}): {tail_output(res.stdout + res.stderr)}")
    return res


def _run_as_admin(shell_cmd, prompt):
    """macOS'un kendi şifre penceresiyle komutu yönetici olarak çalıştırır."""
    def q(s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    script = f"do shell script {q(shell_cmd)} with prompt {q(prompt)} with administrator privileges"
    _run_checked(["osascript", "-e", script], "Yönetici yetkisiyle kurulum", timeout=3600)


# ───────────────────────────── PATH yönetimi ─────────────────────────────

def _registry_path():
    """Kurulumların güncellediği kalıcı PATH; çalışan uygulama bunu kendiliğinden görmez."""
    import winreg
    entries = []
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        (winreg.HKEY_CURRENT_USER, "Environment"),
    ]
    for root, key in keys:
        try:
            with winreg.OpenKey(root, key) as k:
                value = winreg.QueryValueEx(k, "Path")[0]
        except OSError:
            continue
        entries += [os.path.expandvars(p) for p in value.split(";") if p.strip()]
    return entries


def _known_bin_dirs():
    """PATH'te olmasa bile programların sıklıkla kurulduğu klasörler."""
    if IS_WINDOWS:
        dirs = [
            os.path.join(LOCALAPPDATA, "Programs", "MiKTeX", "miktex", "bin", "x64"),
            os.path.join(PROGRAMFILES, "MiKTeX", "miktex", "bin", "x64"),
            os.path.join(TINYTEX_DIR, "bin", "windows"),
            os.path.join(LOCALAPPDATA, "Pandoc"),
            os.path.join(PROGRAMFILES, "Pandoc"),
            os.path.join(PROGRAMFILES, "nodejs"),
            os.path.join(LOCALAPPDATA, "Microsoft", "WinGet", "Links"),
            os.path.join(LOCALAPPDATA, "Microsoft", "WindowsApps"),
        ]
        dirs += sorted(glob.glob(r"C:\texlive\*\bin\win*"), reverse=True)
        dirs += glob.glob(os.path.join(TOOLS_DIR, "pandoc-*"))
        dirs += glob.glob(os.path.join(TOOLS_DIR, "node-*"))
    else:
        dirs = ["/opt/homebrew/bin", "/usr/local/bin", "/Library/TeX/texbin"]
        dirs += glob.glob(os.path.join(TINYTEX_DIR, "bin", "*"))
        dirs += sorted(glob.glob("/usr/local/texlive/*/bin/*"), reverse=True)
        dirs += glob.glob(os.path.join(TOOLS_DIR, "pandoc-*", "bin"))
        dirs += glob.glob(os.path.join(TOOLS_DIR, "node-*", "bin"))
        dirs += sorted(glob.glob(os.path.join(HOME, ".nvm", "versions", "node", "*", "bin")), reverse=True)
    return [d for d in dirs if os.path.isdir(d)]


def refresh_path(prefer=None):
    """PATH'i kayıt defteri ve bilinen kurulum klasörleriyle günceller.

    Mac'te Finder'dan açılan uygulamalar kısıtlı bir PATH ile başlar (/usr/bin:/bin...),
    Windows'ta ise yeni kurulan programlar kayıt defteri okunmadan görülmez.
    prefer verilirse o klasör PATH'in en başına alınır.
    """
    entries = ([prefer] if prefer else []) + os.environ.get("PATH", "").split(os.pathsep)
    if IS_WINDOWS:
        entries += _registry_path()
    entries += _known_bin_dirs()
    seen, merged = set(), []
    for p in entries:
        key = os.path.normcase(os.path.normpath(p)) if p else None
        if key and key not in seen:
            seen.add(key)
            merged.append(p)
    os.environ["PATH"] = os.pathsep.join(merged)


def find_tool(name):
    refresh_path()
    return shutil.which(name)


def _load_settings():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_setting(key, value):
    data = _load_settings()
    data[key] = value
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def find_xelatex():
    """Test derlemesinden geçmiş LaTeX kurulumunu tercih eder; yoksa PATH'teki xelatex'i döndürür."""
    saved = _load_settings().get("xelatex")
    path = saved if saved and os.path.isfile(saved) else find_tool("xelatex")
    if path:
        # xelatex, PDF sürücüsünü (xdvipdfmx) PATH üzerinden çağırır; kendi klasörü en önde olmalı
        refresh_path(prefer=os.path.dirname(path))
    return path


# ───────────────────────────── İndirme ─────────────────────────────

def _ssl_context():
    ctx = ssl.create_default_context()
    try:
        import certifi  # Paketlenmiş uygulamada sistem sertifikaları bulunamazsa diye
        ctx.load_verify_locations(certifi.where())
    except Exception:
        pass
    return ctx


def _download_urllib(url, dest, log):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, context=_ssl_context(), timeout=60) as resp, open(dest, "wb") as f:
        total = int(resp.headers.get("Content-Length") or 0)
        done, next_pct = 0, 20
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            pct = done * 100 // total if total else 0
            if total > 20 * 1024 * 1024 and pct >= next_pct:
                log(f"      ... %{pct} ({done >> 20}/{total >> 20} MB)")
                next_pct = pct // 20 * 20 + 20
    if total and done < total:
        raise RuntimeError(f"bağlantı yarıda kesildi ({done >> 20}/{total >> 20} MB)")


def _download_curl(url, dest, log):
    curl = shutil.which("curl.exe" if IS_WINDOWS else "curl")
    if not curl:
        raise RuntimeError("curl bulunamadı")
    cmd = [curl, "-fsSL", "--retry", "3", "--retry-delay", "5", "--connect-timeout", "30",
           "-A", USER_AGENT, "-o", dest, url]
    if IS_WINDOWS:
        # Kurumsal proxy'lerde sertifika iptal (revocation) kontrolü takılabiliyor
        cmd.insert(1, "--ssl-no-revoke")
    _run_checked(cmd, "curl", timeout=3600)


def _download_powershell(url, dest, log):
    ps = shutil.which("powershell")
    if not ps:
        raise RuntimeError("PowerShell bulunamadı")
    def q(s):
        return "'" + s.replace("'", "''") + "'"
    script = (
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; "
        # Kimlik doğrulamalı kurumsal proxy'lerde Windows oturum bilgileri kullanılır
        "[Net.WebRequest]::DefaultWebProxy.Credentials = [Net.CredentialCache]::DefaultNetworkCredentials; "
        "$ProgressPreference = 'SilentlyContinue'; "
        f"Invoke-WebRequest -UseBasicParsing -Uri {q(url)} -OutFile {q(dest)}"
    )
    _run_checked([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], "PowerShell", timeout=3600)


def download(url, dest, log):
    """Dosyayı indirir. Kurumsal ağlarda yöntemlerden biri engellenebildiği için sırayla
    Python, curl ve (Windows'ta) PowerShell (sistem proxy ayarlarını kullanır) denenir."""
    methods = [("Python", _download_urllib), ("curl", _download_curl)]
    if IS_WINDOWS:
        methods.append(("PowerShell", _download_powershell))
    errors = []
    for i, (name, method) in enumerate(methods):
        try:
            method(url, dest, log)
            if os.path.getsize(dest) > 0:
                return
            errors.append(f"{name}: boş dosya")
        except Exception as e:
            errors.append(f"{name}: {e}")
            if i < len(methods) - 1:
                log(f"      {name} ile indirilemedi, başka yöntem deneniyor...")
    raise RuntimeError(f"{url} indirilemedi ({'; '.join(errors)})")


def _fetch_text(url, log):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "response")
        download(url, path, log)
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()


def _extract(archive, dest):
    os.makedirs(dest, exist_ok=True)
    if archive.endswith(".zip") and IS_WINDOWS:
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)
    elif archive.endswith(".zip"):
        # zipfile çalıştırma izinlerini korumaz; unzip korur
        _run_checked(["unzip", "-q", "-o", archive, "-d", dest], "unzip")
    else:
        _run_checked(["tar", "-xf", archive, "-C", dest], "tar")
    if IS_MAC:
        _run(["xattr", "-dr", "com.apple.quarantine", dest])


def _install_portable(url, prefix, log):
    """Taşınabilir arşivi indirip uygulamanın araç klasörüne açar (yönetici izni gerekmez)."""
    with tempfile.TemporaryDirectory() as tmp:
        archive = os.path.join(tmp, url.rsplit("/", 1)[-1])
        log(f"      İndiriliyor: {url}")
        download(url, archive, log)
        log("      Arşiv açılıyor...")
        for old in glob.glob(os.path.join(TOOLS_DIR, prefix + "*")):
            shutil.rmtree(old, ignore_errors=True)
        _extract(archive, TOOLS_DIR)


# ───────────────────────────── Paket yöneticileri ─────────────────────────────

def _winget_install(package_id, log, scope=None):
    winget = find_tool("winget")
    if not winget:
        raise RuntimeError("winget bu bilgisayarda yok veya IT tarafından engellenmiş")
    cmd = [winget, "install", "--id", package_id, "--exact", "--source", "winget",
           "--accept-package-agreements", "--accept-source-agreements", "--silent"]
    if scope:
        cmd += ["--scope", scope]
    log(f"      winget install {package_id} çalıştırılıyor (birkaç dakika sürebilir, lütfen bekleyin)...")
    res = _run(cmd, timeout=3600)
    code = res.returncode & 0xFFFFFFFF
    if code == 0 or code in WINGET_ALREADY_INSTALLED:
        return
    reason = WINGET_ERRORS.get(code) or tail_output(res.stdout + res.stderr, 2)
    raise RuntimeError(f"winget hata kodu 0x{code:08X}: {reason}")


def _brew_install(formula, log):
    brew = find_tool("brew")
    if not brew:
        raise RuntimeError("Homebrew kurulu değil")
    env = dict(os.environ, HOMEBREW_NO_AUTO_UPDATE="1", NONINTERACTIVE="1")
    _run_checked([brew, "install", formula], "brew install", timeout=3600, env=env)


# ───────────────────────────── Pandoc & Node ─────────────────────────────

def _install_pandoc_portable(log):
    if IS_WINDOWS:
        suffix = "windows-x86_64.zip"
    else:
        suffix = ("arm64" if IS_ARM else "x86_64") + "-macOS.zip"
    url = None
    try:
        release = json.loads(_fetch_text("https://api.github.com/repos/jgm/pandoc/releases/latest", log))
        url = next((a["browser_download_url"] for a in release.get("assets", []) if a["name"].endswith(suffix)), None)
    except Exception:
        log(f"      GitHub API'ye erişilemedi, bilinen sürüm ({PANDOC_FALLBACK_VERSION}) indirilecek.")
    if not url:
        v = PANDOC_FALLBACK_VERSION
        url = f"https://github.com/jgm/pandoc/releases/download/{v}/pandoc-{v}-{suffix}"
    _install_portable(url, "pandoc-", log)


def _install_node_portable(log):
    releases = json.loads(_fetch_text("https://nodejs.org/dist/index.json", log))
    version = next(r["version"] for r in releases if r.get("lts"))
    arch = "arm64" if IS_ARM else "x64"
    name = f"node-{version}-win-{arch}.zip" if IS_WINDOWS else f"node-{version}-darwin-{arch}.tar.gz"
    _install_portable(f"https://nodejs.org/dist/{version}/{name}", "node-", log)


def _pandoc_strategies():
    if IS_WINDOWS:
        first = ("winget", lambda log: _winget_install("JohnMacFarlane.Pandoc", log, scope="user"))
    else:
        first = ("Homebrew", lambda log: _brew_install("pandoc", log))
    return [first, ("GitHub'dan taşınabilir sürüm (yönetici izni gerekmez)", _install_pandoc_portable)]


def _node_strategies():
    if IS_WINDOWS:
        first = ("winget", lambda log: _winget_install("OpenJS.NodeJS.LTS", log))
    else:
        first = ("Homebrew", lambda log: _brew_install("node", log))
    return [first, ("nodejs.org'dan taşınabilir sürüm (yönetici izni gerekmez)", _install_node_portable)]


def ensure_tool(binary, label, strategies, log):
    """Program yoksa kurulum yöntemlerini sırayla dener. Bulunan/kurulan yolu döndürür."""
    path = find_tool(binary)
    if path:
        log(f"[OK] {label} sistemde zaten kurulu: {path}")
        return path
    log(f"[EKSİK] {label} bulunamadı! Otomatik kurulum başlatılıyor...")
    for i, (name, install) in enumerate(strategies, 1):
        log(f"   -> Yöntem {i}/{len(strategies)}: {name}")
        try:
            install(log)
        except Exception as e:
            log(f"      Başarısız: {e}")
        path = find_tool(binary)
        if path:
            log(f"[BAŞARILI] {label} kuruldu: {path}")
            return path
    log(f"[KRİTİK HATA] {label} hiçbir yöntemle kurulamadı.")
    return None


# ───────────────────────────── LaTeX (xelatex) ─────────────────────────────

def _is_miktex(bin_dir):
    return any(os.path.isfile(os.path.join(bin_dir, n)) for n in ("initexmf.exe", "initexmf"))


def _tlmgr_install(bin_dir, packages, log):
    tlmgr = os.path.join(bin_dir, "tlmgr.bat" if IS_WINDOWS else "tlmgr")
    texlive_root = os.path.dirname(os.path.dirname(bin_dir))
    if IS_MAC and not os.access(texlive_root, os.W_OK):
        # BasicTeX/MacTeX sistem klasörüne kuruludur; paket eklemek yönetici şifresi ister
        cmd = " ".join(shlex.quote(a) for a in [tlmgr, "install", *packages])
        _run_as_admin(cmd, "İnnova DocBuilder eksik LaTeX paketlerini kurmak için yönetici şifrenizi istiyor.")
        return
    res = _run([tlmgr, "install", *packages], timeout=3600)
    if res.returncode != 0:
        log(f"      tlmgr uyarısı: {tail_output(res.stdout + res.stderr, 2)}")


def _prepare_latex(xelatex, log):
    """MiKTeX'te eksik paketlerin soru sormadan otomatik indirilmesini açar."""
    bin_dir = os.path.dirname(os.path.realpath(xelatex))
    if not _is_miktex(bin_dir):
        return
    initexmf = shutil.which("initexmf", path=bin_dir)
    _run([initexmf, "--set-config-value=[MPM]AutoInstall=1"], timeout=120)
    miktex = shutil.which("miktex", path=bin_dir)
    if miktex:
        _run([miktex, "packages", "update-package-database"], timeout=600)


# Uzantısız "I can't find file `Consolas'" satırları \IfFontExistsTF kontrolünün zararsız
# yan ürünüdür; bu yüzden yalnızca uzantılı dosyalar ve gerçek font hataları yakalanır.
_MISSING_FILE_PATTERNS = [
    r"! LaTeX Error: File `([^']+)' not found",
    r"! I can't find file `([^'\s]+\.[A-Za-z]+)'",
    r"! Font [^=\n]+=\[?([^\]\s:;]+)[^\n]*not loadable",
    r'Package fontspec Error:\s*(?:\(fontspec\)\s*)?The font "([^"\s]+)" cannot be found',
]


def fix_missing_latex_packages(output, xelatex, log, attempted):
    """Derleme çıktısındaki eksik dosyaları bulup ilgili LaTeX paketlerini kurar.

    Yeni bir paket kurulmaya çalışıldıysa True döner (derleme tekrar denenmeli).
    attempted: aynı paketin tekrar tekrar denenmesini önleyen küme.
    """
    files = []
    for pattern in _MISSING_FILE_PATTERNS:
        for name in re.findall(pattern, output or ""):
            if name not in files:
                files.append(name)
    if not files or not xelatex:
        return False

    bin_dir = os.path.dirname(os.path.realpath(xelatex))
    log(f"      Eksik LaTeX dosyaları tespit edildi: {', '.join(files)}")
    if _is_miktex(bin_dir):
        # MiKTeX paket adları çoğunlukla dosya adıyla aynıdır
        packages = [p for p in dict.fromkeys(os.path.splitext(f)[0] for f in files) if p not in attempted]
        miktex = shutil.which("miktex", path=bin_dir)
        if not packages or not miktex:
            return False
        attempted.update(packages)
        log(f"      MiKTeX paketleri kuruluyor: {' '.join(packages)}")
        for p in packages:
            _run([miktex, "packages", "install", p], timeout=600)
        return True

    tlmgr = os.path.join(bin_dir, "tlmgr.bat" if IS_WINDOWS else "tlmgr")
    if not os.path.isfile(tlmgr):
        return False
    packages = []
    for f in files:
        candidates = [f] if "." in f else [f + ".otf", f + ".ttf", f + ".tfm"]
        for candidate in candidates:
            res = _run([tlmgr, "search", "--global", "--file", "/" + candidate], timeout=600)
            found = re.findall(r"^([\w.-]+):\s*$", res.stdout, re.M)
            if found:
                packages.append(found[0])
                break
        else:
            if "." in f:
                # Arama sonuçsuzsa paket adı çoğunlukla dosya adıyla aynıdır (titlesec.sty -> titlesec)
                packages.append(os.path.splitext(f)[0])
    packages = [p for p in dict.fromkeys(packages) if p not in attempted]
    if not packages:
        return False
    attempted.update(packages)
    log(f"      LaTeX paketleri kuruluyor: {' '.join(packages)}")
    _tlmgr_install(bin_dir, packages, log)
    return True


def _miktex_xelatex():
    for root in (os.path.join(LOCALAPPDATA, "Programs", "MiKTeX"), os.path.join(PROGRAMFILES, "MiKTeX")):
        path = os.path.join(root, "miktex", "bin", "x64", "xelatex.exe")
        if os.path.isfile(path):
            return path
    return None


def _tinytex_xelatex():
    hits = glob.glob(os.path.join(TINYTEX_DIR, "bin", "*", "xelatex.exe" if IS_WINDOWS else "xelatex"))
    return hits[0] if hits else None


def _basictex_xelatex():
    path = "/Library/TeX/texbin/xelatex"
    return path if os.path.isfile(path) else None


def _install_miktex_winget(log):
    _winget_install("MiKTeX.MiKTeX", log, scope="user")


def _install_miktex_ctan(log):
    """MiKTeX'in resmi kurulum dosyasını CTAN'dan indirip yalnızca bu kullanıcıya kurar."""
    base = f"{CTAN}/systems/win32/miktex/setup/windows-x64/"
    versions = re.findall(r"basic-miktex-([\d.]+)-x64\.exe", _fetch_text(base, log))
    if not versions:
        raise RuntimeError("CTAN'da MiKTeX kurulum dosyası bulunamadı")
    latest = max(versions, key=lambda v: [int(x) for x in v.split(".") if x])
    with tempfile.TemporaryDirectory() as tmp:
        exe = os.path.join(tmp, f"basic-miktex-{latest}-x64.exe")
        log(f"      İndiriliyor: MiKTeX {latest}")
        download(base + os.path.basename(exe), exe, log)
        log("      MiKTeX kuruluyor (birkaç dakika sürebilir)...")
        _run_checked([exe, "--unattended", "--private"], "MiKTeX kurulumu", timeout=3600)


def _install_tinytex(log):
    """TinyTeX: taşınabilir TeX Live dağıtımı. Kullanıcı klasörüne kurulur, yönetici izni gerekmez."""
    with tempfile.TemporaryDirectory() as tmp:
        archive = os.path.join(tmp, TINYTEX_URL.rsplit("/", 1)[-1])
        log(f"      İndiriliyor: {TINYTEX_URL}")
        download(TINYTEX_URL, archive, log)
        log("      Arşiv açılıyor...")
        if IS_WINDOWS:
            # Kendiliğinden açılan 7-Zip arşivi; bulunduğu klasöre "TinyTeX" dizinini çıkarır
            _run_checked([archive, "-y"], "TinyTeX arşivi", cwd=tmp)
        else:
            _run_checked(["tar", "-xf", archive, "-C", tmp], "TinyTeX arşivi")
        extracted = os.path.join(tmp, "TinyTeX")
        if not os.path.isdir(extracted):
            raise RuntimeError("TinyTeX arşivi beklenen içeriği çıkarmadı")
        shutil.rmtree(TINYTEX_DIR, ignore_errors=True)
        shutil.move(extracted, TINYTEX_DIR)
    if IS_MAC:
        _run(["xattr", "-dr", "com.apple.quarantine", TINYTEX_DIR])

    xelatex = _tinytex_xelatex()
    if not xelatex:
        raise RuntimeError("TinyTeX açıldı ancak xelatex bulunamadı")
    bin_dir = os.path.dirname(xelatex)
    tlmgr = os.path.join(bin_dir, "tlmgr.bat" if IS_WINDOWS else "tlmgr")
    log("      XeTeX yazı tipi yapılandırması yapılıyor...")
    _run([tlmgr, "postaction", "install", "script", "xetex"], timeout=600)
    log("      Kurumsal şablonun ihtiyaç duyduğu LaTeX paketleri kuruluyor...")
    _tlmgr_install(bin_dir, TEX_PACKAGES, log)


def _install_basictex(log):
    """BasicTeX (MacTeX'in küçük sürümü) resmi paketini CTAN'dan indirip kurar; yönetici şifresi ister."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = os.path.join(tmp, "BasicTeX.pkg")
        log("      İndiriliyor: BasicTeX.pkg (~140 MB)")
        download(f"{CTAN}/systems/mac/mactex/BasicTeX.pkg", pkg, log)
        log("      Yönetici şifresi isteniyor (kurulum ve LaTeX paketleri tek seferde yüklenecek)...")
        tlmgr = "/Library/TeX/texbin/tlmgr"
        script = (
            f"installer -pkg {shlex.quote(pkg)} -target / && "
            f"({tlmgr} update --self; {tlmgr} install {' '.join(TEX_PACKAGES)}; true)"
        )
        _run_as_admin(script, "İnnova DocBuilder, BasicTeX (LaTeX) kurmak için yönetici şifrenizi istiyor.")


def _latex_strategies():
    """(açıklama, kurulum fonksiyonu, kurulu xelatex'i bulan fonksiyon)"""
    if IS_WINDOWS:
        return [
            ("winget ile MiKTeX", _install_miktex_winget, _miktex_xelatex),
            ("TinyTeX - GitHub'dan (yönetici izni gerekmez)", _install_tinytex, _tinytex_xelatex),
            ("MiKTeX resmi kurulum dosyası - CTAN'dan (yönetici izni gerekmez)", _install_miktex_ctan, _miktex_xelatex),
        ]
    return [
        ("TinyTeX - GitHub'dan (yönetici izni gerekmez)", _install_tinytex, _tinytex_xelatex),
        ("BasicTeX resmi paketi - CTAN'dan (yönetici şifresi istenir)", _install_basictex, _basictex_xelatex),
    ]


def ensure_latex(pandoc, verify, log):
    """xelatex'i bulur/kurar ve örnek bir PDF derleyerek gerçekten çalıştığını doğrular.

    Mevcut kurulum testi geçemezse (eksik paket, bozuk kurulum vb.) sıradaki kurulum
    yöntemine geçilir. verify(pandoc, xelatex, log) -> bool
    """
    tested = set()

    def works(xelatex):
        tested.add(os.path.normcase(os.path.realpath(xelatex)))
        refresh_path(prefer=os.path.dirname(xelatex))
        _prepare_latex(xelatex, log)
        if not pandoc:
            log("      Pandoc olmadığı için test PDF'i derlenemedi; yalnızca kurulum doğrulandı.")
            return True
        log("   -> Test PDF'i derleniyor (ilk seferde eksik LaTeX paketleri indirileceği için birkaç dakika sürebilir)...")
        if verify(pandoc, xelatex, log):
            _save_setting("xelatex", xelatex)
            log("[OK] Test PDF'i başarıyla derlendi.")
            return True
        return False

    current = find_xelatex()
    if current:
        log(f"[OK] xelatex bulundu: {current}")
        if works(current):
            return current
        log("[UYARI] Mevcut LaTeX kurulumu test PDF'ini derleyemedi. Alternatif kurulum deneniyor...")
    else:
        log("[EKSİK] xelatex bulunamadı! Otomatik kurulum başlatılıyor...")

    strategies = _latex_strategies()
    for i, (name, install, locate) in enumerate(strategies, 1):
        existing = locate()
        if existing and os.path.normcase(os.path.realpath(existing)) in tested:
            continue
        log(f"   -> Yöntem {i}/{len(strategies)}: {name}")
        if not existing:
            try:
                install(log)
            except Exception as e:
                log(f"      Başarısız: {e}")
        path = locate()
        if not path:
            continue
        log(f"      xelatex kuruldu: {path}")
        if works(path):
            log("[BAŞARILI] xelatex kuruldu ve doğrulandı.")
            return path
        log("      Kurulum tamamlandı ancak test PDF'i derlenemedi, sıradaki yöntem deneniyor...")
    log("[KRİTİK HATA] xelatex hiçbir yöntemle kurulamadı.")
    return None


def check_and_install(verify, log):
    """Tüm bağımlılıkları kontrol eder, eksikleri kurar. Kurulamayanların adlarını döndürür."""
    pandoc = ensure_tool("pandoc", "Pandoc", _pandoc_strategies(), log)
    log("")
    xelatex = ensure_latex(pandoc, verify, log)
    log("\n> Mermaid CLI (NPX) altyapısı kontrol ediliyor...")
    npx = ensure_tool("npx", "Node.js (npx)", _node_strategies(), log)
    return [name for name, ok in (("Pandoc", pandoc), ("XeLaTeX", xelatex), ("Node.js", npx)) if not ok]
