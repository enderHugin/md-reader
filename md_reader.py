# md_reader.py
"""md-reader: lee y edita Markdown. Visor con formato real (titulos, listas, tablas, codigo,
citas, enlaces, imagenes) en modo claro u oscuro, y edicion siempre sobre el texto Markdown,
sola o al lado de la vista, que se actualiza mientras escribes.

Uso:  python md_reader.py [archivo.md]
"""
import json
import os
import re
import subprocess
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import filedialog, messagebox, ttk

APP_NAME = "md-reader"
APP_VERSION = "0.1.0"
HERE = os.path.dirname(os.path.abspath(__file__))

try:
    from markdown_it import MarkdownIt
except ImportError:                    # el instalador lo pone; esto es por si se ejecuta suelto
    MarkdownIt = None

# ---------------------------------------------------------------------------------------------
# Temas (el oscuro es el de cam-ui; el claro, a juego)
# ---------------------------------------------------------------------------------------------
THEMES = {
    "oscuro": dict(bg="#16181c", panel="#20232a", panel2="#2a2e36", fg="#e8e8e8", muted="#8d949e",
                   line="#3a3f48", acc="#3b82f6", acc_active="#2563eb", dis="#666b73",
                   doc_bg="#16181c", doc_fg="#e3e5e8", head="#f3f4f6", link="#6ea8fe",
                   code_bg="#20232a", code_fg="#e6c07b", quote_bg="#1c1f24", quote_bar="#2d4f86",
                   quote_fg="#b4bac3", table_head="#20232a", table_alt="#1a1d22",
                   sel="#2f4f86", find="#6b5a1e", find_cur="#b58a00", caret="#e8e8e8",
                   ed_bg="#1b1e23", ed_fg="#d9dce1", ed_head="#7fb2ff", ed_mark="#8d949e",
                   ed_code="#e6c07b", ed_link="#6ea8fe", ed_quote="#9aa3ad", hr="#3a3f48"),
    "claro": dict(bg="#f4f5f7", panel="#ffffff", panel2="#e8ebf0", fg="#1d2129", muted="#6b7280",
                  line="#d5d9e0", acc="#3b82f6", acc_active="#2563eb", dis="#a0a6b0",
                  doc_bg="#ffffff", doc_fg="#22262e", head="#0f1115", link="#1d4ed8",
                  code_bg="#f0f2f5", code_fg="#9a3412", quote_bg="#f6f8fb", quote_bar="#b9cff5",
                  quote_fg="#4b5563", table_head="#eef1f5", table_alt="#f8f9fb",
                  sel="#bfd6ff", find="#fde68a", find_cur="#f59e0b", caret="#1d2129",
                  ed_bg="#fbfbfc", ed_fg="#22262e", ed_head="#1d4ed8", ed_mark="#8a919c",
                  ed_code="#9a3412", ed_link="#1d4ed8", ed_quote="#6b7280", hr="#d5d9e0"),
}
MODES = [("ver", "Lector"), ("editar", "Editor"), ("dividido", "Dual")]
ZOOM_MIN, ZOOM_MAX = 0.6, 2.4


def _pick_family(root, wanted, fallback):
    have = {f.lower() for f in tkfont.families(root)}
    for f in wanted:
        if f.lower() in have:
            return f
    return fallback


def system_prefers_dark():
    """Lo que tiene elegido el sistema (Windows, macOS, GNOME). Si no se sabe, claro."""
    try:
        if sys.platform == "win32":
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
                return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
        if sys.platform == "darwin":
            r = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"], capture_output=True, text=True, timeout=2)
            return "dark" in r.stdout.lower()
        r = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                           capture_output=True, text=True, timeout=2)
        return "dark" in r.stdout.lower()
    except Exception:
        return False


def config_dir():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, APP_NAME)


def slugify(text, used):
    """Ancla al estilo de GitHub: minusculas, sin puntuacion, espacios a guiones; repetidas, -1, -2..."""
    s = re.sub(r"[^\w\- ]", "", text.strip().lower(), flags=re.UNICODE).replace(" ", "-")
    base, n = s, 1
    while s in used:
        s = "%s-%d" % (base, n)
        n += 1
    used.add(s)
    return s


def read_text(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    nl = "\r\n" if b"\r\n" in raw else "\n"
    return text.replace("\r\n", "\n").replace("\r", "\n"), enc, nl


WELCOME = """# md-reader

Lee y edita **Markdown** con su formato de verdad: títulos, listas, tablas, código, citas, enlaces e imágenes.

## Para empezar

- **Abrir** un archivo: `Ctrl+O`. En Windows, *Más ▸ Abrir los .md con md-reader* lo añade al «Abrir con» del explorador.
- **Tres modos**, arriba: *Lector*, *Editor* (el texto Markdown tal cual) y *Dual* (los dos a la vez: lo que escribes se ve al momento). `Ctrl+E` cambia entre lector y editor.
- **Guardar**: `Ctrl+S`. Si el archivo cambia fuera mientras lo ves, se recarga solo.
- **Tema**: claro u oscuro con el botón de arriba; en *Más ▸ Tema*, también «como el sistema».

## Atajos

| Atajo | Qué hace |
|---|---|
| `Ctrl+O` / `Ctrl+N` | abrir / nuevo |
| `Ctrl+S` / `Ctrl+Shift+S` | guardar / guardar como |
| `Ctrl+E` | lector ↔ editor |
| `Ctrl+F` | buscar |
| `Ctrl+=` / `Ctrl+-` / `Ctrl+0` | más grande / más pequeño / tamaño normal |
| `Ctrl+B` / `Ctrl+I` | (editando) **negrita** / *cursiva* |
| `F5` | volver a leer el archivo |

> Las actualizaciones llegan solas; también puedes buscarlas en *Más ▸ Buscar actualizaciones*.

```python
print("hola desde md-reader")
```
"""


# ---------------------------------------------------------------------------------------------
# Del Markdown al widget de texto
# ---------------------------------------------------------------------------------------------
class Renderer:
    """Pinta un documento Markdown (tokens de markdown-it) en un tk.Text con etiquetas."""

    def __init__(self, app, text):
        self.app, self.t = app, text
        self.md = MarkdownIt("commonmark", {"html": True, "linkify": False}).enable(["table", "strikethrough"]) if MarkdownIt else None
        self.images = []
        self.lines = []           # (widget Frame) de las lineas horizontales, para ajustar su ancho
        self.headings = []        # (nivel, texto, indice, ancla)
        self.anchors = {}
        self.links = {}
        self._fonts = {}

    # -- fuentes y etiquetas ----------------------------------------------------------------
    def font_tag(self, mono=False, size=1.0, bold=False, italic=False):
        z = self.app.zoom
        fam = self.app.mono_family if mono else self.app.body_family
        base = self.app.body_size if not mono else self.app.body_size - 1
        px = max(6, int(round(base * size * z)))
        name = "f_%s_%d_%d_%d" % ("m" if mono else "s", px, bold, italic)
        if name not in self._fonts:
            self._fonts[name] = tkfont.Font(family=fam, size=px, weight="bold" if bold else "normal",
                                            slant="italic" if italic else "roman")
            self.t.tag_configure(name, font=self._fonts[name])
        return name

    def setup_tags(self):
        c, z = self.app.c, self.app.zoom
        t = self.t
        pad = int(28 * z)
        t.configure(bg=c["doc_bg"], fg=c["doc_fg"], selectbackground=c["sel"], selectforeground=c["doc_fg"],
                    insertbackground=c["caret"], padx=pad, pady=int(18 * z), spacing1=0, spacing3=0)
        t.tag_configure("p", spacing3=int(10 * z), spacing1=0)
        for lv, (sz, sp1, sp3) in enumerate([(1.9, 6, 10), (1.5, 18, 8), (1.25, 16, 6), (1.1, 14, 4), (1.0, 12, 4), (0.95, 12, 4)], 1):
            t.tag_configure("h%d" % lv, foreground=c["head"], spacing1=int(sp1 * z), spacing3=int(sp3 * z))
        t.tag_configure("link", foreground=c["link"], underline=True)
        t.tag_configure("code", background=c["code_bg"], foreground=c["code_fg"])
        t.tag_configure("pre", background=c["code_bg"], foreground=c["doc_fg"], lmargin1=int(14 * z), lmargin2=int(14 * z),
                        rmargin=int(10 * z), spacing1=0, spacing3=0, wrap="none")
        t.tag_configure("pre_pad", background=c["code_bg"], font=self.font_tag(mono=True, size=0.45))
        t.tag_configure("s", overstrike=True)
        t.tag_configure("muted", foreground=c["muted"])
        t.tag_configure("quote", background=c["quote_bg"], foreground=c["quote_fg"])
        t.tag_configure("th", background=c["table_head"])
        t.tag_configure("tr_alt", background=c["table_alt"])
        t.tag_configure("find", background=c["find"])
        t.tag_configure("find_cur", background=c["find_cur"])
        t.tag_raise("find")
        t.tag_raise("find_cur")
        t.tag_raise("sel")
        t.tag_bind("link", "<Enter>", lambda e: t.configure(cursor="hand2"))
        t.tag_bind("link", "<Leave>", lambda e: t.configure(cursor=""))

    def block_tag(self, kind, depth, z):
        """Etiqueta de margen para listas y citas anidadas (se crea al vuelo)."""
        name = "%s%d" % (kind, depth)
        c = self.app.c
        if kind == "q":
            m = int((10 * depth) * z)
            self.t.tag_configure(name, lmargin1=m, lmargin2=m, lmargincolor=c["quote_bar"] if depth else c["doc_bg"])
        return name

    # -- pintar -------------------------------------------------------------------------------
    def render(self, src, base_dir):
        t = self.t
        self.base_dir = base_dir
        y = t.yview()[0]
        t.configure(state="normal")
        t.delete("1.0", "end")
        for tag in list(t.tag_names()):
            if tag.startswith(("li_", "tbl_", "lnk_", "q")) and tag != "quote":
                t.tag_delete(tag)
        self._fonts.clear()
        for w in self.lines:
            try:
                w.destroy()
            except Exception:
                pass
        self.images, self.lines, self.headings, self.anchors, self.links = [], [], [], {}, {}
        self.setup_tags()
        if self.md is None:
            t.insert("end", "Falta la libreria markdown-it-py (vuelve a ejecutar el instalador).\n\n", ("muted",))
            t.insert("end", src)
        else:
            try:
                self._render_tokens(self.md.parse(src))
            except Exception as e:                       # nunca dejar la vista en blanco
                t.delete("1.0", "end")
                t.insert("end", "No se pudo dar formato a este documento (%s). Se muestra tal cual:\n\n" % e, ("muted",))
                t.insert("end", src)
        # quitar el salto final sobrante
        if t.get("end-2c", "end-1c") == "\n":
            t.delete("end-2c", "end-1c")
        t.configure(state="disabled")
        self.fit_lines()
        t.yview_moveto(y)

    def _ins(self, text, tags):
        self.t.insert("end", text, tuple(tags))

    def _render_tokens(self, toks):
        z = self.app.zoom
        lists = []                  # pila: {"ordered", "n", "tight"}
        quote = 0
        used = set()
        i = 0
        pending_item = None         # prefijo de la vineta pendiente de pintar
        table = None
        heading = None
        while i < len(toks):
            tk_ = toks[i]
            ty = tk_.type
            if ty == "heading_open":
                heading = int(tk_.tag[1])
                start = self.t.index("end-1c")
            elif ty == "heading_close":
                text = self.t.get(start, "end-1c")
                anchor = slugify(text, used)
                mark = "h_" + anchor
                self.t.mark_set(mark, start)
                self.t.mark_gravity(mark, "left")
                self.headings.append((heading, text, start, anchor))
                self.anchors[anchor] = mark
                self._ins("\n", self._block_tags(lists, quote) + ["h%d" % heading])
                if heading <= 2:
                    self._hr(thin=True)
                heading = None
            elif ty == "paragraph_open":
                pass
            elif ty == "paragraph_close":
                tight = lists and lists[-1]["tight"]
                if not tk_.hidden or not tight:
                    self._ins("\n", self._block_tags(lists, quote) + ["p"])
                else:
                    self._ins("\n", self._block_tags(lists, quote))
            elif ty == "inline":
                base = self._block_tags(lists, quote)
                if heading:
                    base = base + ["h%d" % heading]
                if pending_item is not None:
                    self._ins(pending_item, base + [self.font_tag(bold=False)])
                    pending_item = None
                self._inline(tk_.children or [], base, heading=heading, table=table)
            elif ty in ("bullet_list_open", "ordered_list_open"):
                tight = True
                # una lista es "tight" si sus parrafos estan ocultos
                j, depth = i + 1, 0
                while j < len(toks):
                    if toks[j].type in ("bullet_list_open", "ordered_list_open"):
                        depth += 1
                    elif toks[j].type in ("bullet_list_close", "ordered_list_close"):
                        if depth == 0:
                            break
                        depth -= 1
                    elif depth == 0 and toks[j].type == "paragraph_open" and not toks[j].hidden:
                        tight = False
                    j += 1
                start_n = int(tk_.attrGet("start") or 1) if ty == "ordered_list_open" else 1
                if lists and self.t.get("end-2c", "end-1c") != "\n":
                    self._ins("\n", self._block_tags(lists, quote))
                lists.append({"ordered": ty == "ordered_list_open", "n": start_n, "tight": tight})
            elif ty in ("bullet_list_close", "ordered_list_close"):
                lists.pop()
                if not lists:
                    self._spacer(quote)
            elif ty == "list_item_open":
                L = lists[-1]
                if L["ordered"]:
                    pending_item = "%d.\t" % L["n"]
                    L["n"] += 1
                else:
                    pending_item = "•◦▪"[(len(lists) - 1) % 3] + "\t"
                # casillas de tareas: "[ ] " / "[x] "
                if i + 2 < len(toks) and toks[i + 2].type == "inline":
                    m = re.match(r"\[([ xX])\]\s+", toks[i + 2].content)
                    if m and toks[i + 2].children:
                        first = toks[i + 2].children[0]
                        if first.type == "text" and first.content.startswith(m.group(0)):
                            first.content = first.content[len(m.group(0)):]
                            pending_item = ("☑" if m.group(1) in "xX" else "☐") + "\t"
            elif ty == "list_item_close":
                pass
            elif ty == "blockquote_open":
                quote += 1
            elif ty == "blockquote_close":
                quote -= 1
                if quote == 0:
                    self._spacer(0)
            elif ty in ("fence", "code_block"):
                self._code_block(tk_.content, lists, quote, (tk_.info or "").strip())
            elif ty == "hr":
                self._hr()
            elif ty == "html_block":
                self._ins(tk_.content.rstrip("\n") + "\n", self._block_tags(lists, quote) + ["muted", "p", self.font_tag(mono=True, size=0.9)])
            elif ty == "table_open":
                table = self._table_measure(toks, i)
            elif ty == "table_close":
                table = None
                self._spacer(quote)
            elif ty == "tr_open":
                table["col"] = 0
                table["row"] += 1
            elif ty == "tr_close":
                tags = self._block_tags(lists, quote) + [table["tag"]]
                if table["row"] == 1:
                    tags.append("th")
                elif table["row"] % 2 == 1:
                    tags.append("tr_alt")
                self._ins("\n", tags)
            elif ty in ("th_open", "td_open"):
                if table["col"] > 0:
                    self._ins("\t", self._block_tags(lists, quote) + [table["tag"]] + (["th"] if ty == "th_open" else (["tr_alt"] if table["row"] % 2 == 1 and table["row"] > 1 else [])))
                table["col"] += 1
                table["cell_head"] = ty == "th_open"
            i += 1

    def _block_tags(self, lists, quote):
        tags = []
        z = self.app.zoom
        if lists:
            d = len(lists)
            ordered = lists[-1]["ordered"]
            q = int(16 * quote * z)
            m1 = q + int((6 + 22 * (d - 1)) * z)
            m2 = m1 + int((26 if ordered else 18) * z)
            name = "li_%d_%d_%d" % (d, quote, ordered)
            self.t.tag_configure(name, lmargin1=m1, lmargin2=m2, tabs=(m2,))
            if quote:
                self.t.tag_configure(name, lmargincolor=self.app.c["quote_bar"])
            tags.append(name)
        if quote:
            tags.insert(0, "quote")
            if not lists:
                tags.append(self.block_tag("q", quote, z))
        return tags

    def _spacer(self, quote):
        self._ins("\n", (["quote", "q%d" % quote] if quote else []) + [self.font_tag(size=0.4)])

    def _inline(self, children, base, heading=None, table=None):
        strong = em = s = 0
        link = None
        size = {1: 1.9, 2: 1.5, 3: 1.25, 4: 1.1, 5: 1.0, 6: 0.95}.get(heading, 1.0)
        for ch in children:
            ty = ch.type
            if ty in ("text", "code_inline", "softbreak", "hardbreak", "html_inline"):
                bold = bool(strong) or bool(heading) or bool(table and table.get("cell_head"))
                tags = list(base)
                if table:
                    tags.append(table["tag"])
                    if table.get("cell_head"):
                        tags.append("th")
                    elif table["row"] % 2 == 1 and table["row"] > 1:
                        tags.append("tr_alt")
                if ty == "code_inline":
                    tags += ["code", self.font_tag(mono=True, size=size * 0.95, bold=bold, italic=bool(em))]
                    text = ch.content
                elif ty == "html_inline":
                    tags += ["muted", self.font_tag(mono=True, size=size * 0.9)]
                    text = ch.content
                else:
                    tags.append(self.font_tag(size=size, bold=bold, italic=bool(em)))
                    text = ch.content if ty == "text" else ("\n" if ty == "hardbreak" else " ")
                if s:
                    tags.append("s")
                if link:
                    tags += ["link", link]
                self._ins(text, tags)
            elif ty == "strong_open":
                strong += 1
            elif ty == "strong_close":
                strong -= 1
            elif ty == "em_open":
                em += 1
            elif ty == "em_close":
                em -= 1
            elif ty == "s_open":
                s += 1
            elif ty == "s_close":
                s -= 1
            elif ty == "link_open":
                link = "lnk_%d" % len(self.links)
                self.links[link] = ch.attrGet("href") or ""
                self.t.tag_bind(link, "<Button-1>", lambda e, h=self.links[link]: self.app.follow_link(h))
            elif ty == "link_close":
                link = None
            elif ty == "image":
                self._image(ch, base, link)

    def _image(self, tok, base, link):
        src = tok.attrGet("src") or ""
        alt = "".join(c.content for c in (tok.children or [])) or tok.content or src
        path = src if os.path.isabs(src) else os.path.join(self.base_dir or "", src)
        if not re.match(r"^[a-z]+://", src, re.I) and os.path.isfile(path):
            try:
                from PIL import Image, ImageTk
                im = Image.open(path)
                maxw = max(200, self.t.winfo_width() - int(80 * self.app.zoom)) if self.t.winfo_width() > 50 else 800
                if im.width > maxw:
                    im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
                ph = ImageTk.PhotoImage(im)
                self.images.append(ph)
                self.t.image_create("end", image=ph, padx=2, pady=4)
                return
            except Exception:
                pass
        tags = list(base) + ["muted", self.font_tag(italic=True)]
        if re.match(r"^https?://", src, re.I):
            name = "lnk_%d" % len(self.links)
            self.links[name] = src
            self.t.tag_bind(name, "<Button-1>", lambda e, h=src: self.app.follow_link(h))
            tags += ["link", name]
        self._ins("[imagen: %s]" % alt, tags)

    def _code_block(self, content, lists, quote, lang):
        base = self._block_tags(lists, quote)
        f = self.font_tag(mono=True, size=0.95)
        self._ins("\n", base + ["pre", "pre_pad"])
        self._ins(content.rstrip("\n") + "\n", base + ["pre", f])
        self._ins("\n", base + ["pre", "pre_pad"])
        self._spacer(quote)

    def _hr(self, thin=False):
        c = self.app.c
        fr = tk.Frame(self.t, height=1 if thin else 2, bg=c["hr"], bd=0, highlightthickness=0)
        self.t.window_create("end", window=fr, align="center")
        self._ins("\n", [self.font_tag(size=0.5 if thin else 1.0)])
        self.lines.append(fr)

    def fit_lines(self):
        w = self.t.winfo_width() - 2 * int(self.t.cget("padx")) - 6
        for fr in self.lines:
            try:
                fr.configure(width=max(50, w))
            except Exception:
                pass

    def _table_measure(self, toks, i):
        """Anchos de columna para alinear la tabla con tabuladores (el texto de cada celda medido con su fuente)."""
        widths, col, j = [], 0, i
        fn = self._fonts.get(self.font_tag()) or tkfont.Font(font=self.t.cget("font"))
        fb = self._fonts.get(self.font_tag(bold=True))
        while j < len(toks) and toks[j].type != "table_close":
            tkn = toks[j]
            if tkn.type == "tr_open":
                col = 0
            elif tkn.type in ("th_open", "td_open"):
                col += 1
            elif tkn.type == "inline":
                text = "".join(c.content for c in (tkn.children or []) if c.type in ("text", "code_inline"))
                w = (fb if toks[j - 1].type == "th_open" else fn).measure(text)
                while len(widths) < col:
                    widths.append(0)
                widths[col - 1] = max(widths[col - 1], w)
            j += 1
        gap = int(28 * self.app.zoom)
        stops, x = [], 0
        for w in widths[:-1]:
            x += w + gap
            stops.append(x)
        name = "tbl_%d" % i
        self.t.tag_configure(name, tabs=tuple(stops) if stops else (), wrap="none", spacing1=int(3 * self.app.zoom), spacing3=int(3 * self.app.zoom))
        return {"tag": name, "row": 0, "col": 0}


# ---------------------------------------------------------------------------------------------
# Resaltado sencillo del texto Markdown al editar
# ---------------------------------------------------------------------------------------------
ED_RULES = [
    ("ed_head", re.compile(r"^#{1,6} .*$", re.M)),
    ("ed_quote", re.compile(r"^\s*>.*$", re.M)),
    ("ed_mark", re.compile(r"^\s*(?:[-*+]|\d+[.)])\s", re.M)),
    ("ed_bold", re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1")),
    ("ed_ital", re.compile(r"(?<![*_\w])([*_])(?![*_\s])(.+?)(?<![*_\s])\1(?![*_\w])")),
    ("ed_code", re.compile(r"`[^`\n]+`")),
    ("ed_link", re.compile(r"!?\[[^\]\n]*\]\([^)\n]*\)")),
    ("ed_mark", re.compile(r"^(?:---+|\*\*\*+|___+)\s*$", re.M)),
]
FENCE = re.compile(r"^(```|~~~)[^\n]*\n.*?^\1[ \t]*$", re.M | re.S)


# ---------------------------------------------------------------------------------------------
# La aplicacion
# ---------------------------------------------------------------------------------------------
class App:
    def __init__(self, root, path=None):
        self.root = root
        self.cfg_path = os.path.join(config_dir(), "config.json")
        self.cfg = self._load_cfg()
        self.zoom = float(self.cfg.get("zoom", 1.0))
        self.path = None
        self.encoding, self.newline = "utf-8", "\n"
        self.saved_text = ""
        self.mtime = None
        self.mode = self.cfg.get("mode", "ver") if self.cfg.get("mode") in dict(MODES) else "ver"
        self._render_job = self._hl_job = None
        self._find_hits, self._find_pos = [], -1
        self._ext_changed = False
        self.body_family = _pick_family(root, ["Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", "Liberation Sans"], "TkDefaultFont")
        self.mono_family = _pick_family(root, ["Cascadia Mono", "Consolas", "SF Mono", "Menlo", "JetBrains Mono", "DejaVu Sans Mono", "Liberation Mono", "Courier New"], "TkFixedFont")
        self.ui_family = self.body_family
        self.body_size = 11
        self.c = THEMES[self._theme_name()]
        root.title(APP_NAME)
        root.geometry(self.cfg.get("geometry", "1000x720"))
        root.minsize(520, 360)
        self._set_icon()
        self._build()
        self.apply_theme()
        self.set_mode(self.mode, first=True)
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._bind_keys()
        if path:
            self.open_path(path)
        else:
            self.show_text(WELCOME, None)
        root.after(1000, self._watch)
        self._updater_setup()

    # -- configuracion ------------------------------------------------------------------------
    def _load_cfg(self):
        try:
            with open(self.cfg_path, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def save_cfg(self):
        try:
            os.makedirs(os.path.dirname(self.cfg_path), exist_ok=True)
            self.cfg["zoom"] = round(self.zoom, 2)
            self.cfg["mode"] = self.mode
            if self.root.state() == "normal":
                self.cfg["geometry"] = self.root.geometry()
            tmp = self.cfg_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.cfg_path)
        except OSError:
            pass

    def _theme_name(self):
        t = self.cfg.get("theme", "sistema")
        if t == "sistema":
            return "oscuro" if system_prefers_dark() else "claro"
        return t if t in THEMES else "claro"

    def _set_icon(self):
        for p in (os.path.join(HERE, "icon.png"), os.path.join(HERE, "assets", "icon.png")):
            if os.path.exists(p):
                try:
                    self._icon = tk.PhotoImage(file=p)
                    self.root.iconphoto(True, self._icon)
                except Exception:
                    pass
                break

    # -- interfaz -----------------------------------------------------------------------------
    def _build(self):
        r = self.root
        self.bar = ttk.Frame(r, style="Bar.TFrame")
        self.bar.pack(fill="x")
        inner = ttk.Frame(self.bar, style="Bar.TFrame")
        inner.pack(fill="x", padx=10, pady=7)
        ttk.Button(inner, text="Abrir", command=self.ask_open).pack(side="left")
        self.btn_save = ttk.Button(inner, text="Guardar", command=self.save)
        self.btn_save.pack(side="left", padx=(6, 0))
        self.seg = ttk.Frame(inner, style="Bar.TFrame")
        self.seg.pack(side="left", padx=(16, 0))
        self.mode_btns = {}
        for key, label in MODES:
            b = ttk.Button(self.seg, text=label, style="Seg.TButton", command=lambda k=key: self.set_mode(k))
            b.pack(side="left")
            self.mode_btns[key] = b
        self.btn_more = ttk.Menubutton(inner, text="Más", style="TMenubutton")
        self.btn_more.pack(side="right")
        self.menu = tk.Menu(self.btn_more, tearoff=False)
        self.btn_more["menu"] = self.menu
        self.btn_theme = ttk.Button(inner, text="Oscuro", command=self.cycle_theme)
        self.btn_theme.pack(side="right", padx=(0, 6))
        self.btn_toc = ttk.Button(inner, text="Índice", command=self.toggle_toc)
        self.btn_toc.pack(side="right", padx=(0, 6))
        self.lbl_title = ttk.Label(inner, text="", style="BarTitle.TLabel")
        self.lbl_title.pack(side="left", padx=(16, 0))

        # aviso (archivo cambiado fuera)
        self.notice = ttk.Frame(r, style="Notice.TFrame")
        self.notice_lbl = ttk.Label(self.notice, style="Notice.TLabel")
        self.notice_lbl.pack(side="left", padx=10, pady=6)
        ttk.Button(self.notice, text="Ignorar", command=self._hide_notice).pack(side="right", padx=(4, 8), pady=4)
        ttk.Button(self.notice, text="Recargar", style="Accent.TButton", command=lambda: (self._hide_notice(), self.reload(force=True))).pack(side="right", pady=4)

        # barra de busqueda
        self.findbar = ttk.Frame(r, style="Bar.TFrame")
        ttk.Label(self.findbar, text="Buscar:", style="Bar.TLabel").pack(side="left", padx=(10, 6), pady=6)
        self.find_var = tk.StringVar()
        self.find_entry = ttk.Entry(self.findbar, textvariable=self.find_var, width=32)
        self.find_entry.pack(side="left", pady=6)
        self.find_info = ttk.Label(self.findbar, text="", style="BarMuted.TLabel")
        self.find_info.pack(side="left", padx=8)
        ttk.Button(self.findbar, text="✕", width=3, command=self.close_find).pack(side="right", padx=8)
        self.find_var.trace_add("write", lambda *a: self.do_find())
        self.find_entry.bind("<Return>", lambda e: self.find_step(1))
        self.find_entry.bind("<Shift-Return>", lambda e: self.find_step(-1))
        self.find_entry.bind("<Escape>", lambda e: self.close_find())

        # cuerpo: indice | editor | vista
        self.body = ttk.PanedWindow(r, orient="horizontal")
        self.body.pack(fill="both", expand=True)
        self.toc_frame = ttk.Frame(self.body, style="Side.TFrame")
        self.toc = ttk.Treeview(self.toc_frame, show="tree", selectmode="browse", style="Toc.Treeview")
        self.toc.pack(fill="both", expand=True, padx=(6, 0), pady=6)
        self.toc.bind("<<TreeviewSelect>>", self._toc_go)

        self.ed_frame = ttk.Frame(self.body)
        self.editor = tk.Text(self.ed_frame, wrap="word", undo=True, autoseparators=True, maxundo=-1,
                              relief="flat", borderwidth=0, highlightthickness=0, tabs=("4c",))
        ed_sb = ttk.Scrollbar(self.ed_frame, orient="vertical", command=self.editor.yview)
        self.editor.configure(yscrollcommand=lambda a, b: (ed_sb.set(a, b), self._sync_scroll(), self._maybe_rehighlight()))
        ed_sb.pack(side="right", fill="y")
        self.editor.pack(fill="both", expand=True)
        self.editor.bind("<<Modified>>", self._on_edit)

        self.view_frame = ttk.Frame(self.body)
        self.view = tk.Text(self.view_frame, wrap="word", relief="flat", borderwidth=0, highlightthickness=0, cursor="")
        v_sb = ttk.Scrollbar(self.view_frame, orient="vertical", command=self.view.yview)
        self.view.configure(yscrollcommand=v_sb.set)
        v_sb.pack(side="right", fill="y")
        self.view.pack(fill="both", expand=True)
        self.view.bind("<Configure>", lambda e: self.renderer.fit_lines())
        self.renderer = Renderer(self, self.view)

        self.status = ttk.Label(r, text="", style="Status.TLabel", anchor="w")
        self.status.pack(fill="x", side="bottom")
        self._fill_menu()

    def _fill_menu(self):
        m = self.menu
        m.delete(0, "end")
        m.add_command(label="Nuevo                     Ctrl+N", command=self.new)
        m.add_command(label="Abrir…                     Ctrl+O", command=self.ask_open)
        rec = tk.Menu(m, tearoff=False)
        recent = [p for p in self.cfg.get("recent", []) if os.path.exists(p)]
        for p in recent[:10]:
            rec.add_command(label=p, command=lambda p=p: self.open_path(p))
        if not recent:
            rec.add_command(label="(nada todavía)", state="disabled")
        m.add_cascade(label="Recientes", menu=rec)
        m.add_command(label="Guardar                   Ctrl+S", command=self.save)
        m.add_command(label="Guardar como…   Ctrl+Shift+S", command=self.save_as)
        m.add_separator()
        m.add_command(label="Buscar…                    Ctrl+F", command=self.open_find)
        m.add_command(label="Más grande               Ctrl+=", command=lambda: self.set_zoom(self.zoom * 1.1))
        m.add_command(label="Más pequeño             Ctrl+-", command=lambda: self.set_zoom(self.zoom / 1.1))
        m.add_command(label="Tamaño normal          Ctrl+0", command=lambda: self.set_zoom(1.0))
        th = tk.Menu(m, tearoff=False)
        self.theme_var = tk.StringVar(value=self.cfg.get("theme", "sistema"))
        for k, lab in (("sistema", "Como el sistema"), ("claro", "Claro"), ("oscuro", "Oscuro")):
            th.add_radiobutton(label=lab, value=k, variable=self.theme_var, command=lambda k=k: self.set_theme(k))
        m.add_cascade(label="Tema", menu=th)
        m.add_separator()
        if sys.platform == "win32":
            m.add_command(label="Abrir los .md con md-reader", command=self.associate_md)
        m.add_command(label="Buscar actualizaciones…", command=self.show_updates)
        m.add_command(label="Acerca de md-reader", command=self.about)
        for w in (m, rec, th):
            w.configure(bg=self.c["panel"], fg=self.c["fg"], activebackground=self.c["acc"], activeforeground="white",
                        relief="flat", borderwidth=1, font=(self.ui_family, 9))

    def apply_theme(self):
        c = self.c
        r = self.root
        st = ttk.Style(r)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        ui = (self.ui_family, 9)
        st.configure(".", background=c["bg"], foreground=c["fg"], fieldbackground=c["panel"], bordercolor=c["line"],
                     lightcolor=c["bg"], darkcolor=c["bg"], troughcolor=c["panel"], focuscolor=c["bg"], font=ui)
        st.map(".", background=[("disabled", c["bg"]), ("active", c["panel2"])], foreground=[("disabled", c["dis"])])
        st.configure("TFrame", background=c["bg"])
        st.configure("Bar.TFrame", background=c["panel"])
        st.configure("Side.TFrame", background=c["panel"])
        st.configure("Bar.TLabel", background=c["panel"], foreground=c["fg"])
        st.configure("BarMuted.TLabel", background=c["panel"], foreground=c["muted"])
        st.configure("BarTitle.TLabel", background=c["panel"], foreground=c["muted"], font=(self.ui_family, 9))
        st.configure("Status.TLabel", background=c["panel"], foreground=c["muted"], padding=(10, 3), font=(self.ui_family, 8))
        st.configure("Notice.TFrame", background=c["panel2"])
        st.configure("Notice.TLabel", background=c["panel2"], foreground=c["fg"])
        st.configure("TButton", background=c["panel2"], foreground=c["fg"], padding=(10, 5), borderwidth=1, bordercolor=c["line"])
        st.map("TButton", background=[("active", c["line"]), ("disabled", c["panel"])], foreground=[("disabled", c["dis"])])
        st.configure("Seg.TButton", background=c["panel2"], foreground=c["muted"], padding=(12, 5), borderwidth=1, bordercolor=c["line"])
        st.map("Seg.TButton", background=[("active", c["line"])])
        st.configure("SegOn.TButton", background=c["acc"], foreground="white", padding=(12, 5), borderwidth=1, bordercolor=c["acc"])
        st.map("SegOn.TButton", background=[("active", c["acc_active"])])
        st.configure("Accent.TButton", background=c["acc"], foreground="white")
        st.map("Accent.TButton", background=[("active", c["acc_active"])])
        st.configure("TMenubutton", background=c["panel2"], foreground=c["fg"], padding=(10, 5), arrowcolor=c["fg"], borderwidth=1)
        st.map("TMenubutton", background=[("active", c["line"])])
        st.configure("TEntry", fieldbackground=c["bg"], foreground=c["fg"], insertcolor=c["fg"], bordercolor=c["line"], padding=3)
        st.configure("Toc.Treeview", background=c["panel"], fieldbackground=c["panel"], foreground=c["fg"], borderwidth=0, rowheight=int(22 * max(1.0, self.zoom)))
        st.map("Toc.Treeview", background=[("selected", c["panel2"])], foreground=[("selected", c["fg"])])
        st.configure("TPanedwindow", background=c["line"])
        st.configure("Vertical.TScrollbar", background=c["panel2"], troughcolor=c["doc_bg"], bordercolor=c["doc_bg"], arrowcolor=c["muted"], lightcolor=c["panel2"], darkcolor=c["panel2"])
        st.map("Vertical.TScrollbar", background=[("active", c["line"])])
        r.configure(bg=c["bg"])
        # editor
        z = self.zoom
        self.editor.configure(bg=c["ed_bg"], fg=c["ed_fg"], insertbackground=c["caret"], selectbackground=c["sel"],
                              selectforeground=c["ed_fg"], font=(self.mono_family, max(6, int(round((self.body_size - 0.5) * z)))),
                              padx=int(22 * z), pady=int(16 * z), spacing1=2, spacing3=2)
        self.editor.tag_configure("ed_head", foreground=c["ed_head"], font=(self.mono_family, max(6, int(round((self.body_size - 0.5) * z))), "bold"))
        self.editor.tag_configure("ed_bold", font=(self.mono_family, max(6, int(round((self.body_size - 0.5) * z))), "bold"))
        self.editor.tag_configure("ed_ital", font=(self.mono_family, max(6, int(round((self.body_size - 0.5) * z))), "italic"))
        self.editor.tag_configure("ed_code", foreground=c["ed_code"])
        self.editor.tag_configure("ed_fence", foreground=c["ed_code"])
        self.editor.tag_configure("ed_link", foreground=c["ed_link"])
        self.editor.tag_configure("ed_quote", foreground=c["ed_quote"])
        self.editor.tag_configure("ed_mark", foreground=c["ed_mark"])
        self.editor.tag_configure("find", background=c["find"])
        self.editor.tag_configure("find_cur", background=c["find_cur"])
        self.editor.tag_raise("sel")
        self.btn_theme.configure(text="Claro" if self.c is THEMES["oscuro"] else "Oscuro")
        self._title_bar_dark(self.c is THEMES["oscuro"])
        self._fill_menu()
        self._mark_mode_buttons()

    def _title_bar_dark(self, dark):
        if sys.platform != "win32":
            return
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            val = ctypes.c_int(1 if dark else 0)
            for attr in (20, 19):          # DWMWA_USE_IMMERSIVE_DARK_MODE (y su numero antiguo)
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)) == 0:
                    break
        except Exception:
            pass

    def _bind_keys(self):
        r = self.root
        for seq, fn in (("<Control-o>", self.ask_open), ("<Control-n>", self.new), ("<Control-s>", self.save),
                        ("<Control-S>", self.save_as), ("<Control-Shift-s>", self.save_as), ("<Control-f>", self.open_find),
                        ("<Control-e>", self.toggle_edit), ("<F5>", lambda: self.reload(force=True)),
                        ("<Control-equal>", lambda: self.set_zoom(self.zoom * 1.1)), ("<Control-plus>", lambda: self.set_zoom(self.zoom * 1.1)),
                        ("<Control-minus>", lambda: self.set_zoom(self.zoom / 1.1)), ("<Control-0>", lambda: self.set_zoom(1.0))):
            r.bind_all(seq, lambda e, fn=fn: (fn(), "break")[1])
            # en los cuadros de texto, tkinter ya usa Ctrl+O/F/E/N/B... para otras cosas: primero lo nuestro
            for w in (self.editor, self.view):
                w.bind(seq, lambda e, fn=fn: (fn(), "break")[1])
        r.bind_all("<Control-MouseWheel>", lambda e: self.set_zoom(self.zoom * (1.1 if e.delta > 0 else 1 / 1.1)))
        self.editor.bind("<Control-b>", lambda e: (self.wrap_sel("**"), "break")[1])
        self.editor.bind("<Control-i>", lambda e: (self.wrap_sel("*"), "break")[1])
        self.editor.bind("<Control-y>", lambda e: (self._redo(), "break")[1])
        self.editor.bind("<Control-Z>", lambda e: (self._redo(), "break")[1])
        self.editor.bind("<Tab>", self._tab)

    # -- modos ----------------------------------------------------------------------------------
    def set_mode(self, mode, first=False):
        if mode not in dict(MODES):
            return
        self.mode = mode
        for p in list(self.body.panes()):
            self.body.forget(p)
        if self.cfg.get("toc"):
            self.body.add(self.toc_frame, weight=0)
        if mode in ("editar", "dividido"):
            self.body.add(self.ed_frame, weight=1)
        if mode in ("ver", "dividido"):
            self.body.add(self.view_frame, weight=1)
        if mode == "dividido":
            self.root.after(30, self._split_half)
        if self.cfg.get("toc"):
            self.root.after(30, lambda: self.body.sashpos(0, int(200 * max(1, self.zoom))))
        self._mark_mode_buttons()
        if mode in ("editar", "dividido"):
            self.editor.focus_set()
        else:
            self.view.focus_set()
        if not first:
            self.render_now()
            self.save_cfg()

    def _split_half(self):
        try:
            idx = 1 if self.cfg.get("toc") else 0
            w = self.body.winfo_width()
            left = self.body.sashpos(0) if idx else 0
            self.body.sashpos(idx, left + (w - left) // 2)
        except Exception:
            pass

    def _mark_mode_buttons(self):
        for k, b in getattr(self, "mode_btns", {}).items():
            b.configure(style="SegOn.TButton" if k == self.mode else "Seg.TButton")

    def toggle_edit(self):
        """Ctrl+E: lector <-> editor, en la misma ventana (desde Dual, al lector)."""
        self.set_mode("editar" if self.mode == "ver" else "ver")

    def toggle_toc(self):
        self.cfg["toc"] = not self.cfg.get("toc")
        self.set_mode(self.mode)

    # -- tema y tamano --------------------------------------------------------------------------
    def cycle_theme(self):
        self.set_theme("claro" if self.c is THEMES["oscuro"] else "oscuro")

    def set_theme(self, name):
        self.cfg["theme"] = name
        if hasattr(self, "theme_var"):
            self.theme_var.set(name)
        self.c = THEMES[self._theme_name()]
        self.apply_theme()
        self.render_now()
        self.highlight()
        self.save_cfg()

    def set_zoom(self, z):
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, z))
        self.apply_theme()
        self.render_now()
        self.highlight()
        self.save_cfg()
        self.flash("Tamaño %d %%" % round(self.zoom * 100))

    # -- archivo ----------------------------------------------------------------------------------
    def text(self):
        return self.editor.get("1.0", "end-1c")

    def dirty(self):
        return self.text() != self.saved_text

    def show_text(self, text, path):
        if path is None:
            self.encoding, self.newline, self._bom = "utf-8", ("\r\n" if sys.platform == "win32" else "\n"), False
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.saved_text = text if path else (text if text == WELCOME else "")
        self.path = path
        self.render_now(keep_scroll=False)
        self.highlight()
        self._update_title()

    def ask_open(self):
        if not self.confirm_discard():
            return
        d = os.path.dirname(self.path) if self.path else self.cfg.get("last_dir") or os.path.expanduser("~")
        p = filedialog.askopenfilename(parent=self.root, initialdir=d, title="Abrir",
                                       filetypes=[("Markdown", "*.md *.markdown *.mdown *.mkd *.txt"), ("Todos", "*.*")])
        if p:
            self.open_path(p, confirm=False)

    def open_path(self, p, confirm=True):
        if confirm and not self.confirm_discard():
            return
        p = os.path.abspath(p)
        try:
            text, enc, nl = read_text(p)
        except OSError as e:
            messagebox.showerror(APP_NAME, "No se pudo abrir:\n%s\n\n%s" % (p, e), parent=self.root)
            return
        self.encoding, self.newline = ("utf-8" if enc == "utf-8-sig" else enc), nl
        self._bom = enc == "utf-8-sig"
        self.show_text(text, p)
        self.mtime = self._mtime(p)
        self._hide_notice()
        self._remember(p)

    def _remember(self, p):
        rec = [x for x in self.cfg.get("recent", []) if x != p]
        self.cfg["recent"] = [p] + rec[:14]
        self.cfg["last_dir"] = os.path.dirname(p)
        self.save_cfg()
        self._fill_menu()

    @staticmethod
    def _mtime(p):
        try:
            return os.stat(p).st_mtime_ns
        except OSError:
            return None

    def new(self):
        if not self.confirm_discard():
            return
        self.show_text("", None)
        self.saved_text = ""
        if self.mode == "ver":
            self.set_mode("editar")
        self._update_title()

    def save(self):
        if not self.path:
            return self.save_as()
        return self._write(self.path)

    def save_as(self):
        d = os.path.dirname(self.path) if self.path else self.cfg.get("last_dir") or os.path.expanduser("~")
        name = os.path.basename(self.path) if self.path else "sin título.md"
        p = filedialog.asksaveasfilename(parent=self.root, initialdir=d, initialfile=name, defaultextension=".md",
                                         filetypes=[("Markdown", "*.md"), ("Todos", "*.*")], title="Guardar como")
        if not p:
            return False
        if self._write(p):
            self.path = os.path.abspath(p)
            self._remember(self.path)
            self._update_title()
            return True
        return False

    def _write(self, p):
        text = self.text()
        data = text.replace("\n", self.newline)
        try:
            tmp = p + ".guardando"
            with open(tmp, "w", encoding=self.encoding if self.encoding != "latin-1" else "latin-1", newline="") as f:
                if getattr(self, "_bom", False):
                    f.write("﻿")
                f.write(data)
            os.replace(tmp, p)
        except (OSError, UnicodeEncodeError) as e:
            try:
                os.remove(tmp)
            except OSError:
                pass
            messagebox.showerror(APP_NAME, "No se pudo guardar:\n%s\n\n%s" % (p, e), parent=self.root)
            return False
        self.saved_text = text
        self.mtime = self._mtime(p)
        self._update_title()
        self.flash("Guardado")
        return True

    def confirm_discard(self):
        if not self.dirty():
            return True
        name = os.path.basename(self.path) if self.path else "el documento nuevo"
        r = messagebox.askyesnocancel(APP_NAME, "¿Guardar los cambios de %s?" % name, parent=self.root)
        if r is None:
            return False
        if r:
            return bool(self.save())
        return True

    def reload(self, force=False):
        if not self.path:
            return
        if not force and self.dirty():
            return
        y = self.view.yview()[0]
        ins = self.editor.index("insert")
        try:
            text, enc, nl = read_text(self.path)
        except OSError:
            return
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.editor.edit_reset()
        self.saved_text = text
        self.mtime = self._mtime(self.path)
        self.editor.mark_set("insert", ins)
        self.render_now()
        self.view.yview_moveto(y)
        self.highlight()
        self._update_title()

    def _watch(self):
        """Si el archivo cambia fuera: se recarga solo; si ademas hay cambios sin guardar, se avisa."""
        try:
            if self.path:
                m = self._mtime(self.path)
                if m is not None and self.mtime is not None and m != self.mtime:
                    if self.dirty():
                        if not self._ext_changed:
                            self._ext_changed = True
                            self.notice_lbl.configure(text="El archivo ha cambiado fuera de md-reader y aquí tienes cambios sin guardar.")
                            self.notice.pack(fill="x", after=self.bar)
                    else:
                        self.reload()
                        self.flash("Recargado: el archivo cambió fuera")
        finally:
            self.root.after(1000, self._watch)

    def _hide_notice(self):
        self.notice.pack_forget()
        self._ext_changed = False
        if self.path:
            self.mtime = self._mtime(self.path)

    def _update_title(self):
        name = os.path.basename(self.path) if self.path else ("sin título" if self.text() != WELCOME else "Bienvenida")
        mark = " •" if self.dirty() else ""
        self.root.title("%s%s — %s" % (name, mark, APP_NAME))
        self.lbl_title.configure(text=(self.path or name) + mark)
        words = len(re.findall(r"\w+", self.text()))
        self.status.configure(text="%d palabras%s" % (words, "  ·  sin guardar" if self.dirty() else ""))

    def flash(self, msg):
        self.status.configure(text=msg)
        if getattr(self, "_flash_job", None):
            self.root.after_cancel(self._flash_job)
        self._flash_job = self.root.after(2200, self._update_title)

    # -- edicion ----------------------------------------------------------------------------------
    def _on_edit(self, _e=None):
        if not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        self._update_title()
        if self._render_job:
            self.root.after_cancel(self._render_job)
        self._render_job = self.root.after(150, self.render_now)       # en Dual: casi al instante, sin redibujar letra a letra
        if self._hl_job:
            self.root.after_cancel(self._hl_job)
        self._hl_job = self.root.after(150, self.highlight)

    def render_now(self, keep_scroll=True):
        self._render_job = None
        if self.mode == "editar":
            self._fill_toc()
            return
        y = self.view.yview()[0]
        base = os.path.dirname(self.path) if self.path else None
        self.renderer.render(self.text(), base)
        if keep_scroll:
            self.view.yview_moveto(y)
        else:
            self.view.yview_moveto(0)
        self._fill_toc()
        if self.findbar.winfo_ismapped():
            self.do_find(keep=True)

    def highlight(self):
        """Resalta solo lo que se ve (y un margen): asi escribir va igual de fluido en documentos largos."""
        self._hl_job = None
        ed = self.editor
        text = self.text()
        try:
            first = int(ed.index("@0,0").split(".")[0])
            last = int(ed.index("@0,%d" % ed.winfo_height()).split(".")[0])
        except tk.TclError:
            first, last = 1, 200
        a_line, b_line = max(1, first - 150), last + 150
        lines = text.split("\n")
        a_off = sum(len(x) + 1 for x in lines[:a_line - 1])
        b_off = a_off + sum(len(x) + 1 for x in lines[a_line - 1:b_line])
        start, end = "%d.0" % a_line, "%d.0" % (b_line + 1)
        for tag in ("ed_head", "ed_quote", "ed_mark", "ed_bold", "ed_ital", "ed_code", "ed_link", "ed_fence"):
            ed.tag_remove(tag, start, end)
        fences = [(m.start(), m.end()) for m in FENCE.finditer(text)]

        def in_fence(x):
            return any(s <= x < e for s, e in fences)
        for s, e in fences:
            if e > a_off and s < b_off:
                ed.tag_add("ed_fence", "1.0+%dc" % max(s, a_off), "1.0+%dc" % min(e, b_off))
        chunk = text[a_off:b_off]
        for tag, rx in ED_RULES:
            for m in rx.finditer(chunk):
                if not in_fence(a_off + m.start()):
                    ed.tag_add(tag, "1.0+%dc" % (a_off + m.start()), "1.0+%dc" % (a_off + m.end()))
        self._hl_range = (a_line, b_line)

    def _maybe_rehighlight(self):
        r = getattr(self, "_hl_range", None)
        try:
            first = int(self.editor.index("@0,0").split(".")[0])
            last = int(self.editor.index("@0,%d" % self.editor.winfo_height()).split(".")[0])
        except tk.TclError:
            return
        if r is None or first < r[0] or last > r[1]:
            if self._hl_job:
                self.root.after_cancel(self._hl_job)
            self._hl_job = self.root.after(80, self.highlight)

    def wrap_sel(self, mark):
        ed = self.editor
        try:
            a, b = ed.index("sel.first"), ed.index("sel.last")
            ed.edit_separator()
            ed.insert(b, mark)
            ed.insert(a, mark)
            ed.tag_add("sel", a, "%s+%dc" % (b, len(mark) * 2))
        except tk.TclError:
            ed.insert("insert", mark + mark)
            ed.mark_set("insert", "insert-%dc" % len(mark))
        ed.edit_separator()

    def _redo(self):
        try:
            self.editor.edit_redo()
        except tk.TclError:
            pass

    def _tab(self, e):
        # tabulador: dos espacios (en listas, mejor que un \t)
        self.editor.insert("insert", "  ")
        return "break"

    def _sync_scroll(self):
        if self.mode == "dividido" and not getattr(self, "_syncing", False):
            self._syncing = True
            try:
                self.view.yview_moveto(self.editor.yview()[0])
            finally:
                self._syncing = False

    # -- enlaces e indice -------------------------------------------------------------------------
    def follow_link(self, href):
        if not href:
            return
        if href.startswith("#"):
            mark = self.renderer.anchors.get(href[1:].lower())
            if mark:
                self.view.yview(mark)
            return
        if re.match(r"^(https?|mailto):", href, re.I):
            webbrowser.open(href)
            return
        path, _, frag = href.partition("#")
        from urllib.parse import unquote
        base = os.path.dirname(self.path) if self.path else os.getcwd()
        p = os.path.normpath(os.path.join(base, unquote(path)))
        if not os.path.exists(p):
            self.flash("No existe: %s" % p)
            return
        if p.lower().endswith((".md", ".markdown", ".mdown", ".mkd", ".txt")):
            self.open_path(p)
            if frag:
                self.root.after(50, lambda: self.follow_link("#" + frag))
        else:
            self._open_external(p)

    @staticmethod
    def _open_external(p):
        try:
            if sys.platform == "win32":
                os.startfile(p)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", p])
            else:
                subprocess.Popen(["xdg-open", p])
        except Exception:
            pass

    def _fill_toc(self):
        if not self.cfg.get("toc"):
            return
        t = self.toc
        t.delete(*t.get_children())
        heads = self.renderer.headings
        if self.mode == "editar":
            heads, used, src = [], set(), self.text()
            fences = [(x.start(), x.end()) for x in FENCE.finditer(src)]
            for m in re.finditer(r"^(#{1,6}) +(.+?)\s*#*\s*$", src, re.M):
                if not any(s <= m.start() < e for s, e in fences):
                    heads.append((len(m.group(1)), m.group(2), "1.0+%dc" % m.start(), slugify(m.group(2), used)))
        stack = [("", 0)]
        for lv, text, idx, anchor in heads:
            while stack and stack[-1][1] >= lv:
                stack.pop()
            parent = stack[-1][0] if stack else ""
            iid = t.insert(parent, "end", text=text, values=(idx, anchor), open=True)
            stack.append((iid, lv))

    def _toc_go(self, _e=None):
        sel = self.toc.selection()
        if not sel:
            return
        idx, anchor = self.toc.item(sel[0], "values")
        if self.mode == "editar":
            self.editor.see(idx)
            self.editor.yview(idx)
            self.editor.mark_set("insert", idx)
        else:
            mark = self.renderer.anchors.get(anchor)
            if mark:
                self.view.yview(mark)

    # -- buscar -------------------------------------------------------------------------------------
    def _find_target(self):
        return self.editor if self.mode == "editar" or (self.mode == "dividido" and self.root.focus_get() is self.editor) else self.view

    def open_find(self):
        if not self.findbar.winfo_ismapped():
            self.findbar.pack(fill="x", after=self.bar)
        try:
            sel = self._find_target().get("sel.first", "sel.last")
            if sel and "\n" not in sel:
                self.find_var.set(sel)
        except tk.TclError:
            pass
        self.find_entry.focus_set()
        self.find_entry.select_range(0, "end")
        self.do_find()

    def close_find(self):
        self.findbar.pack_forget()
        for w in (self.view, self.editor):
            w.tag_remove("find", "1.0", "end")
            w.tag_remove("find_cur", "1.0", "end")
        self.find_info.configure(text="")

    def do_find(self, keep=False):
        q = self.find_var.get()
        w = self._find_target()
        for x in (self.view, self.editor):
            x.tag_remove("find", "1.0", "end")
            x.tag_remove("find_cur", "1.0", "end")
        self._find_hits = []
        if q:
            idx = "1.0"
            while True:
                idx = w.search(q, idx, "end", nocase=True)
                if not idx:
                    break
                end = "%s+%dc" % (idx, len(q))
                w.tag_add("find", idx, end)
                self._find_hits.append((idx, end))
                idx = end
        if not keep:
            self._find_pos = -1
        self.find_step(1 if not keep else 0)

    def find_step(self, d):
        hits = self._find_hits
        if not hits:
            self.find_info.configure(text="sin resultados" if self.find_var.get() else "")
            return
        self._find_pos = (self._find_pos + d) % len(hits)
        w = self._find_target()
        w.tag_remove("find_cur", "1.0", "end")
        a, b = hits[self._find_pos]
        w.tag_add("find_cur", a, b)
        w.see(a)
        self.find_info.configure(text="%d de %d" % (self._find_pos + 1, len(hits)))

    # -- varios -----------------------------------------------------------------------------------
    def associate_md(self):
        """Windows: md-reader aparece en "Abrir con" para .md y .markdown (solo para este usuario)."""
        try:
            import winreg
            exe = sys.executable.replace("python.exe", "pythonw.exe")
            cmd = '"%s" "%s" "%%1"' % (exe, os.path.abspath(__file__))
            prog = "md-reader.md"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\%s" % prog) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "Documento Markdown")
            ico = os.path.join(HERE, "icon.ico")
            if os.path.exists(ico):
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\%s\DefaultIcon" % prog) as k:
                    winreg.SetValueEx(k, "", 0, winreg.REG_SZ, ico)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\%s\shell\open\command" % prog) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd)
            for ext in (".md", ".markdown"):
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\%s\OpenWithProgids" % ext) as k:
                    winreg.SetValueEx(k, prog, 0, winreg.REG_NONE, b"")
            import ctypes
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
            messagebox.showinfo(APP_NAME, "Listo: md-reader aparece en «Abrir con» para los archivos .md.\n\n"
                                "Para que se abran siempre con él: clic derecho en un .md ▸ Abrir con ▸ Elegir otra aplicación "
                                "▸ md-reader ▸ «Usar siempre esta aplicación».", parent=self.root)
        except Exception as e:
            messagebox.showerror(APP_NAME, "No se pudo: %s" % e, parent=self.root)

    def about(self):
        messagebox.showinfo(APP_NAME, "%s %s\n\nLee y edita Markdown.\nhttps://github.com/enderHugin/md-reader" % (APP_NAME, APP_VERSION), parent=self.root)

    def _updater_setup(self):
        self.updates = None
        try:
            import pyi_update
            self.updates = pyi_update.tk_install(self.root, pyi_update.Updater(__file__, version=APP_VERSION), APP_NAME,
                                                 on_close=self.quit, busy=self.dirty)
        except ImportError:
            pass

    def show_updates(self):
        if self.updates:
            self.updates.show()
        else:
            messagebox.showinfo(APP_NAME, "Esta copia no está instalada con su instalador, así que no se actualiza sola.\n\n"
                                "Descárgalo de https://enderhugin.github.io/md-reader/", parent=self.root)

    def quit(self):
        if not self.confirm_discard():
            return
        self.save_cfg()
        self.root.destroy()


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("enderHugin.md-reader")
        except Exception:
            pass
    root = tk.Tk(className="md-reader")
    path = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    App(root, path)
    root.mainloop()


if __name__ == "__main__":
    main()
