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
APP_VERSION = "0.1.6"
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
SITE_URL = "https://enderhugin.github.io/md-reader/"
REPO_URL = "https://github.com/enderHugin/md-reader"
KOFI_URL = "https://ko-fi.com/jaimeluisolguinmesina"
ABOUT_TAGLINE = "Lee y edita Markdown, en claro u oscuro."
ABOUT_CHIPS = ("Lector", "Editor", "Dual", "Claro · Oscuro", "Índice", "Se actualiza solo")
ABOUT_ASK = "Si md-reader te resulta útil, invítame a un café y ayúdame a seguir mejorándolo."
ABOUT_BTN = "☕  Invítame a un café en Ko-fi"
ABOUT_CREDIT = "Hecho con cariño por Jaime Luis Olguín Mesina"
ABOUT_DEMO = "# Hola\n\nEsto es **md-reader**:\n\n- escribes *Markdown*\n- lo ves al momento\n\n> claro u oscuro\n"
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

- **Abrir** un archivo: `Ctrl+O`, o con doble clic en un `.md` (el instalador añade md-reader al «Abrir con»).
- **Tres modos**, arriba: *Lector*, *Editor* (el texto Markdown tal cual) y *Dual* (los dos a la vez: lo que escribes se ve al momento). `Ctrl+E` cambia entre lector y editor.
- **En el lector**: clic en una casilla ☐ para marcarla, y **doble clic** en cualquier sitio para editar justo ahí.
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
| `Ctrl+V` | pegar: lo copiado de Word, Writer o una web entra como Markdown |
| `Ctrl+Shift+V` | pegar sin formato |
| `F5` | volver a leer el archivo |

> Las actualizaciones llegan solas; también puedes buscarlas en *Más ▸ Buscar actualizaciones*.

```python
print("hola desde md-reader")
```
"""


GUIDE = """# Guía de formatos

Cada formato, con **cómo se escribe** (el recuadro) y **cómo se ve** (debajo). Puedes ponerlos a mano o seleccionar un trozo y usar el **botón derecho** del ratón, en el editor o en el lector.

## Texto

```
**negrita**   *cursiva*   ***las dos***   ~~tachado~~   `código`
```

**negrita**   *cursiva*   ***las dos***   ~~tachado~~   `código`

Atajos en el editor: `Ctrl+B` negrita, `Ctrl+I` cursiva.

## Títulos

```
# Título grande
## Título mediano
### Título pequeño
```

Un `#` al principio de la línea, seguido de un espacio. Hasta seis niveles (`######`). Salen en el *Índice*.

## Párrafos y saltos de línea

```
Un párrafo.
Esta línea sale debajo.

Una línea en blanco empieza otro párrafo.
```

Un párrafo.
Esta línea sale debajo.

Una línea en blanco empieza otro párrafo.

(En *Más ▸ Respetar los saltos de línea* puedes pasar al Markdown estricto, donde un salto simple se convierte en espacio.)

## Listas

```
- un punto
- otro punto
  - uno dentro (dos espacios delante)

1. primero
2. segundo
```

- un punto
- otro punto
  - uno dentro (dos espacios delante)

1. primero
2. segundo

## Casillas de tareas

```
- [ ] pendiente
- [x] hecha
```

- [ ] pendiente
- [x] hecha

En el lector, un clic en la casilla la marca o la desmarca.

## Enlaces e imágenes

```
[texto del enlace](https://ejemplo.com)
[a otra sección](#tablas)
![descripción](foto.png)
```

[texto del enlace](https://ejemplo.com) · [a otra sección](#tablas)

Las imágenes se buscan junto al archivo `.md` (por ejemplo, `foto.png` en la misma carpeta).

## Citas

```
> Esto es una cita.
> Puede tener **formato**.
```

> Esto es una cita.
> Puede tener **formato**.

## Código

````
```
un bloque de código
  respeta los espacios
```
````

```
un bloque de código
  respeta los espacios
```

## Tablas

```
| Columna | Otra |
|---|---|
| a | b |
| c | d |
```

| Columna | Otra |
|---|---|
| a | b |
| c | d |

## Línea horizontal

```
---
```

---

## HTML

También vale un poco de HTML para lo que Markdown no tiene. Se ve el resultado, no las etiquetas, y nada se ejecuta.

```
<span style="color:red">en rojo</span>
<del style="color:red">tachado en rojo</del>
<u>subrayado</u>, <mark>resaltado</mark>, H<sub>2</sub>O, x<sup>2</sup>
<div align="center">centrado</div>
<!-- un comentario: no se ve -->
```

<span style="color:red">en rojo</span>, <del style="color:red">tachado en rojo</del>, <u>subrayado</u>, <mark>resaltado</mark>, H<sub>2</sub>O, x<sup>2</sup>

<div align="center">centrado</div>

## Copiar y pegar con Word, Writer…

- **Copiar**: en el lector, `Ctrl+C` copia con formato, listo para pegar en Word, Writer o un correo.
- **Pegar**: `Ctrl+V` convierte lo copiado de Word, Writer, Google Docs o una web en Markdown: títulos, negrita, cursiva, listas, tablas, enlaces y colores.
- `Ctrl+Shift+V` pega solo el texto, sin convertir nada.

## En el lector

- **Clic** en una casilla: la marca o la desmarca.
- **Doble clic** en cualquier sitio: al editor, justo en esa línea.
- **Botón derecho** sobre un trozo seleccionado: darle formato sin pasar al editor.
- `Ctrl+Z` deshace también desde el lector.
"""


# ---------------------------------------------------------------------------------------------
# Copiar con formato (para pegar en Word, Writer, correo...): HTML en el portapapeles
# ---------------------------------------------------------------------------------------------
import html as _html

CSS_CODE = "font-family:Consolas,'Courier New',monospace;background:#f0f2f5"
CSS_PRE = "font-family:Consolas,'Courier New',monospace;background:#f0f2f5;padding:8px;white-space:pre"
CSS_QUOTE = "border-left:3px solid #3b82f6;margin:0 0 0 4px;padding:2px 10px;color:#4b5563"
CSS_TABLE = "border-collapse:collapse"
CSS_CELL = "border:1px solid #c8ced8;padding:4px 8px;vertical-align:top"
ITEM_PREFIX = re.compile(r"^(?:[•◦▪]|\d+\.)\t")
TASK_PREFIX = re.compile(r"^([☐☑])\t")


def _inline_html(segs, heading=False, head_cell=False):
    """Trozos (texto, etiquetas) -> HTML con negrita, cursiva, tachado, codigo y enlaces."""
    out = []
    for text, tags, href in segs:
        if not text:
            continue
        if text.startswith("\x00IMG"):
            out.append('<img src="%s">' % _html.escape(text[4:], quote=True))
            continue
        t = _html.escape(text).replace("\n", "<br>")
        f = next((x for x in tags if x.startswith("f_")), None)
        bold = italic = False
        if f:
            parts = f.split("_")            # f_s_14_1_0 -> familia, px, negrita, cursiva
            bold, italic = parts[3] == "1", parts[4] == "1"
        if "code" in tags:
            t = '<code style="%s">%s</code>' % (CSS_CODE, t)
        if italic:
            t = "<i>" + t + "</i>"
        if bold and not heading and not head_cell:
            t = "<b>" + t + "</b>"
        if "s" in tags:
            t = "<s>" + t + "</s>"
        if "u" in tags:
            t = "<u>" + t + "</u>"
        if "sup" in tags:
            t = "<sup>" + t + "</sup>"
        if "sub" in tags:
            t = "<sub>" + t + "</sub>"
        css = ";".join(("color:#" + x[3:]) if x.startswith("hc_") else ("background-color:#" + x[3:])
                       for x in sorted(tags) if x.startswith(("hc_", "hb_")))
        if css:
            t = '<span style="%s">%s</span>' % (css, t)
        if href:
            t = '<a href="%s">%s</a>' % (_html.escape(href, quote=True), t)
        out.append(t)
    return "".join(out)


def html_from_view(t, a, b, links, decor=(), images=None):
    """Convierte lo que se ve en el lector entre a y b (con sus etiquetas) en HTML; asi se copia exactamente lo
    seleccionado, aunque sea medio parrafo. Devuelve (html, texto plano)."""
    active = set(t.tag_names(a))
    lines, cur = [], []          # cada linea: lista de (texto, etiquetas, enlace) o "HR"
    images = images or {}
    for key, val, idx in t.dump(a, b, text=True, tag=True, window=True, image=True):
        if key == "tagon":
            active.add(val)
        elif key == "tagoff":
            active.discard(val)
        elif key == "image":
            if val in images:
                from pathlib import Path
                cur.append(("\x00IMG" + Path(images[val]).resolve().as_uri(), frozenset(active), None))
        elif key == "window":
            if val not in decor:            # la linea fina bajo los titulos es decoracion, no una <hr>
                lines.append("HR")
        elif key == "text":
            tags = frozenset(active)
            href = next((links.get(x) for x in tags if x.startswith("lnk_")), None)
            parts = val.split("\n")
            for i, part in enumerate(parts):
                if part:
                    cur.append((part, tags, href))
                if i < len(parts) - 1:
                    # la etiqueta de bloque la da el propio salto de linea (y lo que haya en la linea)
                    lines.append((cur, tags | frozenset(x for _, tg, _ in cur for x in tg)))
                    cur = []
    if cur:
        lines.append((cur, frozenset(x for _, tg, _ in cur for x in tg)))

    out, para, pre, quote, lists = [], [], [], [], []   # lists: pila de [profundidad, numerada, li_abierto]

    centered = [False]

    def flush_para():
        if para:
            out.append(('<p style="text-align:center">%s</p>' if centered[0] else "<p>%s</p>") % "<br>".join(para))
            para.clear()
        centered[0] = False

    def flush_pre():
        if pre:
            out.append('<pre style="%s">%s</pre>' % (CSS_PRE, "\n".join(pre)))
            pre.clear()

    def flush_quote():
        if quote:
            out.append('<blockquote style="%s"><p>%s</p></blockquote>' % (CSS_QUOTE, "<br>".join(quote)))
            quote.clear()

    def close_lists(depth=0):
        while lists and lists[-1][0] > depth:
            d, ordered, li_open = lists.pop()
            out.append(("</li>" if li_open else "") + ("</ol>" if ordered else "</ul>"))

    def flush_all():
        flush_para()
        flush_pre()
        flush_quote()

    table = []
    def flush_table():
        if table:
            rows = []
            for cells, head in table:
                tag = "th" if head else "td"
                bg = ";background:#eef1f5" if head else ""
                rows.append("<tr>%s</tr>" % "".join('<%s style="%s%s">%s</%s>' % (tag, CSS_CELL, bg, c, tag) for c in cells))
            out.append('<table style="%s">%s</table>' % (CSS_TABLE, "".join(rows)))
            table.clear()

    plain = t.get(a, b)
    for line in lines:
        if line == "HR":
            flush_all(); flush_table(); close_lists()
            out.append("<hr>")
            continue
        segs, tags = line
        text = "".join(x[0] for x in segs)
        if "pre_pad" in tags and not text.strip():
            continue
        if "pre" in tags:
            flush_para(); flush_quote(); flush_table(); close_lists()
            pre.append(_html.escape(text))
            continue
        flush_pre()
        if not text.strip():                       # separacion entre parrafos / bloques
            flush_para(); flush_quote(); flush_table()
            continue
        tbl = any(x.startswith("tbl_") for x in tags)
        if tbl:
            flush_para(); flush_quote(); close_lists()
            cells, cell = [], []
            for txt, tg, hr in segs:
                pieces = txt.split("\t")
                for k, piece in enumerate(pieces):
                    if k:
                        cells.append(cell)
                        cell = []
                    cell.append((piece, tg, hr))
            cells.append(cell)
            table.append(([_inline_html(c, head_cell="th" in tags) for c in cells], "th" in tags))
            continue
        flush_table()
        h = next((int(x[1]) for x in tags if re.fullmatch(r"h[1-6]", x)), None)
        if h:
            flush_para(); flush_quote(); close_lists()
            out.append("<h%d>%s</h%d>" % (h, _inline_html(segs, heading=True), h))
            continue
        li = next((x for x in tags if x.startswith("li_")), None)
        if li:
            flush_para(); flush_quote()
            _, d, _q, ordered = li.split("_")
            d, ordered = int(d), ordered == "1"
            m = ITEM_PREFIX.match(text) or TASK_PREFIX.match(text)
            # quitar la vineta / numero pintados (Word pone los suyos); las casillas se quedan como simbolo
            body = segs
            if m:
                cut = len(m.group(0))
                keep = (m.group(1) + " ") if TASK_PREFIX.match(text) else ""
                body, n = [], 0
                for txt, tg, hr in segs:
                    if n >= cut:
                        body.append((txt, tg, hr))
                    elif n + len(txt) > cut:
                        body.append((txt[cut - n:], tg, hr))
                    n += len(txt)
                if keep:
                    body.insert(0, (keep, frozenset(), None))
                close_lists(d)
                if lists and lists[-1][0] == d and lists[-1][1] != ordered:
                    close_lists(d - 1)
                while not lists or lists[-1][0] < d:
                    out.append("<ol>" if ordered else "<ul>")
                    lists.append([lists[-1][0] + 1 if lists else 1, ordered, False])
                if lists[-1][2]:
                    out.append("</li>")
                out.append("<li>" + _inline_html(body))
                lists[-1][2] = True
            else:                                   # segunda linea del mismo punto
                body = [(x[0].lstrip("\t") if i == 0 else x[0], x[1], x[2]) for i, x in enumerate(segs)]
                if lists and lists[-1][2]:
                    out.append("<br>" + _inline_html(body))
                else:
                    para.append(_inline_html(body))
            continue
        close_lists()
        if "quote" in tags:
            flush_para()
            quote.append(_inline_html(segs))
            continue
        if "center" in tags:
            centered[0] = True
        para.append(_inline_html(segs))
    flush_all(); flush_table(); close_lists()
    return "\n".join(out), plain


def md_to_html(src, breaks=True):
    """Markdown -> HTML (para "copiar con formato" desde el editor o el documento entero)."""
    if MarkdownIt is None:
        return "<pre>%s</pre>" % _html.escape(src)
    md = MarkdownIt("commonmark", {"html": True, "breaks": breaks}).enable(["table", "strikethrough"])
    src = re.sub(r"<!--.*?-->", "", src, flags=re.S)       # los comentarios no se copian
    h = md.render(src)
    h = h.replace("<code>", '<code style="%s">' % CSS_CODE).replace("<pre>", '<pre style="%s">' % CSS_PRE)
    h = h.replace("<blockquote>", '<blockquote style="%s">' % CSS_QUOTE).replace("<table>", '<table style="%s">' % CSS_TABLE)
    h = re.sub(r"<(t[hd])(\s[^>]*)?>", lambda m: '<%s style="%s"%s>' % (m.group(1), CSS_CELL + (";background:#eef1f5" if m.group(1) == "th" else ""), m.group(2) or ""), h)
    h = h.replace('<li>[ ] ', '<li>☐ ').replace('<li>[x] ', '<li>☑ ').replace('<li>[X] ', '<li>☑ ')
    return h


def cf_html(fragment):
    """El formato "HTML Format" del portapapeles de Windows (el que leen Word y Writer): una cabecera con las
    posiciones, en bytes, del documento y del fragmento."""
    head = "Version:0.9\r\nStartHTML:%010d\r\nEndHTML:%010d\r\nStartFragment:%010d\r\nEndFragment:%010d\r\n"
    pre = '<html><head><meta charset="utf-8"></head><body style="font-family:Calibri,Arial,sans-serif">\r\n<!--StartFragment-->'
    post = "<!--EndFragment-->\r\n</body></html>"
    dummy = head % (0, 0, 0, 0)
    start_html = len(dummy.encode("utf-8"))
    start_frag = start_html + len(pre.encode("utf-8"))
    end_frag = start_frag + len(fragment.encode("utf-8"))
    end_html = end_frag + len(post.encode("utf-8"))
    return (head % (start_html, end_html, start_frag, end_frag) + pre + fragment + post).encode("utf-8")


def _win_clipboard(html_fragment, plain):
    import ctypes
    from ctypes import wintypes
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    u32.OpenClipboard.argtypes = [wintypes.HWND]
    u32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    u32.SetClipboardData.restype = wintypes.HANDLE
    u32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
    u32.RegisterClipboardFormatW.restype = wintypes.UINT
    k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    k32.GlobalAlloc.restype = wintypes.HGLOBAL
    k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]

    def put(fmt, data):
        h = k32.GlobalAlloc(0x0002, len(data))          # GMEM_MOVEABLE
        p = k32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        k32.GlobalUnlock(h)
        if not u32.SetClipboardData(fmt, h):
            raise OSError("SetClipboardData")
    for _ in range(10):                                 # otro programa puede tenerlo abierto un instante
        if u32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        raise OSError("el portapapeles está ocupado")
    try:
        u32.EmptyClipboard()
        put(13, (plain + "\0").encode("utf-16-le"))           # CF_UNICODETEXT
        put(u32.RegisterClipboardFormatW("HTML Format"), cf_html(html_fragment) + b"\0")
    finally:
        u32.CloseClipboard()


def set_rich_clipboard(root, html_fragment, plain):
    """Pone en el portapapeles el texto con formato (y el texto normal, para donde no se admite formato).
    Devuelve True si fue con formato."""
    try:
        if sys.platform == "win32":
            _win_clipboard(html_fragment, plain)
            return True
        doc = '<html><head><meta charset="utf-8"></head><body>%s</body></html>' % html_fragment
        if sys.platform == "darwin":
            rtf = subprocess.run(["textutil", "-stdin", "-stdout", "-format", "html", "-convert", "rtf",
                                  "-inputencoding", "UTF-8"], input=doc.encode("utf-8"), capture_output=True, timeout=10).stdout
            if rtf:
                subprocess.run(["pbcopy"], input=rtf, timeout=10, check=True)
                return True
        else:
            import shutil
            if shutil.which("wl-copy") and os.environ.get("WAYLAND_DISPLAY"):
                subprocess.run(["wl-copy", "--type", "text/html"], input=doc.encode("utf-8"), timeout=10, check=True)
                return True
            if shutil.which("xclip"):
                subprocess.Popen(["xclip", "-selection", "clipboard", "-t", "text/html"], stdin=subprocess.PIPE).communicate(doc.encode("utf-8"), timeout=10)
                return True
    except Exception:
        pass
    root.clipboard_clear()
    root.clipboard_append(plain)
    return False


# ---------------------------------------------------------------------------------------------
# Pegar: del texto con formato (Word, Writer, navegador...) a Markdown
# ---------------------------------------------------------------------------------------------
def _win_clipboard_html():
    import ctypes
    from ctypes import wintypes
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    u32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
    u32.RegisterClipboardFormatW.restype = wintypes.UINT
    u32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    u32.OpenClipboard.argtypes = [wintypes.HWND]
    u32.GetClipboardData.argtypes = [wintypes.UINT]
    u32.GetClipboardData.restype = wintypes.HANDLE
    k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalSize.argtypes = [wintypes.HGLOBAL]
    k32.GlobalSize.restype = ctypes.c_size_t
    fmt = u32.RegisterClipboardFormatW("HTML Format")
    if not u32.IsClipboardFormatAvailable(fmt):
        return None
    for _ in range(10):
        if u32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        return None
    try:
        h = u32.GetClipboardData(fmt)
        if not h:
            return None
        p = k32.GlobalLock(h)
        try:
            data = ctypes.string_at(p, k32.GlobalSize(h))
        finally:
            k32.GlobalUnlock(h)
    finally:
        u32.CloseClipboard()
    return cf_html_fragment(data)


def cf_html_fragment(data):
    """Del formato "HTML Format" de Windows, el fragmento copiado (posiciones en bytes)."""
    data = data.split(b"\0", 1)[0]
    try:
        sf = int(re.search(rb"StartFragment:\s*(-?\d+)", data).group(1))
        ef = int(re.search(rb"EndFragment:\s*(-?\d+)", data).group(1))
        if 0 <= sf <= ef <= len(data):
            return data[sf:ef].decode("utf-8", "replace")
    except Exception:
        pass
    s = data.decode("utf-8", "replace")
    m = re.search(r"<!--StartFragment-->(.*)<!--EndFragment-->", s, re.S)
    return m.group(1) if m else s[s.find("<"):]


def get_clipboard_html(root):
    """El HTML del portapapeles, si lo que se copio tenia formato (Word, Writer, una web...). Si no, None."""
    try:
        if sys.platform == "win32":
            return _win_clipboard_html()
        if sys.platform == "darwin":
            for cls in ("HTML", "RTF "):
                r = subprocess.run(["osascript", "-e", "the clipboard as «class %s»" % cls], capture_output=True, timeout=10)
                m = re.search(rb"\xc2\xabdata \w+ ?([0-9A-Fa-f]+)\xc2\xbb", r.stdout)
                if not m:
                    continue
                raw = bytes.fromhex(m.group(1).decode())
                if cls == "HTML":
                    return raw.decode("utf-8", "replace")
                out = subprocess.run(["textutil", "-stdin", "-stdout", "-format", "rtf", "-convert", "html"],
                                     input=raw, capture_output=True, timeout=10).stdout
                return out.decode("utf-8", "replace") or None
            return None
        try:
            return root.clipboard_get(type="text/html") or None
        except tk.TclError:
            import shutil
            if shutil.which("wl-paste") and os.environ.get("WAYLAND_DISPLAY"):
                r = subprocess.run(["wl-paste", "--no-newline", "--type", "text/html"], capture_output=True, timeout=10)
                return r.stdout.decode("utf-8", "replace") if r.returncode == 0 and r.stdout else None
    except Exception:
        pass
    return None


_VOID = {"br", "hr", "img", "input", "meta", "link", "col", "wbr", "area", "base", "source"}
_SKIP = {"script", "style", "head", "title", "xml", "template", "noscript", "o:p", "w:sdt"}
_BLOCKS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "tr", "td", "th", "thead",
           "tbody", "tfoot", "blockquote", "pre", "hr", "section", "article", "header", "footer", "main", "nav",
           "aside", "figure", "figcaption", "dl", "dt", "dd", "center", "address", "details", "summary", "caption"}
_PLAIN_COLORS = {"black", "windowtext", "auto", "inherit", "initial", "currentcolor", "#000", "#000000",
                 "rgb(0,0,0)", "text", "canvastext", "white", "#fff", "#ffffff", "transparent", "rgb(255,255,255)",
                 "window", "none"}


class _Node:
    __slots__ = ("tag", "attrs", "kids", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.kids, self.parent = tag, attrs or {}, [], parent


def _parse_html(src):
    from html.parser import HTMLParser
    root = _Node("#root")
    cur = [root]
    skip = [0]

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if skip[0]:
                if tag in _SKIP:
                    skip[0] += 1
                return
            if tag in _SKIP:
                skip[0] += 1
                return
            n = _Node(tag, {k: (v or "") for k, v in attrs}, cur[-1])
            # un <p>/<li> abierto se cierra al empezar otro bloque del mismo tipo
            if tag in ("p", "li", "tr", "td", "th") and cur[-1].tag == tag:
                cur.pop()
                n.parent = cur[-1]
            cur[-1].kids.append(n)
            if tag not in _VOID:
                cur.append(n)

        def handle_startendtag(self, tag, attrs):
            if skip[0] or tag in _SKIP:
                return
            cur[-1].kids.append(_Node(tag, {k: (v or "") for k, v in attrs}, cur[-1]))

        def handle_endtag(self, tag):
            if tag in _SKIP:
                skip[0] = max(0, skip[0] - 1)
                return
            if skip[0]:
                return
            for i in range(len(cur) - 1, 0, -1):
                if cur[i].tag == tag:
                    del cur[i:]
                    break

        def handle_data(self, data):
            if not skip[0]:
                cur[-1].kids.append(data)

    P(convert_charrefs=True).feed(re.sub(r"<!\[if [^\]]*\]>|<!\[endif\]>", "", src))
    return root


def _style(n):
    out = {}
    for decl in (n.attrs.get("style") or "").split(";"):
        if ":" in decl:
            k, v = decl.split(":", 1)
            out[k.strip().lower()] = v.strip().lower().replace("'", "").replace('"', "")
    return out


def _run_style(n, st):
    """Estilo de texto que aporta un elemento, encima del que ya trae (st)."""
    st = dict(st)
    t, css = n.tag, _style(n)
    if t in ("b", "strong"):
        st["bold"] = True
    if t in ("i", "em", "cite", "dfn", "var"):
        st["italic"] = True
    if t in ("u", "ins"):
        st["under"] = True
    if t in ("s", "del", "strike"):
        st["strike"] = True
    if t in ("code", "kbd", "samp", "tt"):
        st["code"] = True
    if t == "mark":
        st["mark"] = True
    if t in ("sup", "sub"):
        st[t] = True
    if t == "a" and n.attrs.get("href") and not n.attrs["href"].startswith(("javascript:", "#_")):
        st["href"] = n.attrs["href"]
    if t == "font" and n.attrs.get("color"):
        st["color"] = n.attrs["color"].lower()
    fw = css.get("font-weight")
    if fw:
        st["bold"] = fw in ("bold", "bolder") or (fw.isdigit() and int(fw) >= 600)
    fs = css.get("font-style")
    if fs:
        st["italic"] = fs in ("italic", "oblique")
    td = css.get("text-decoration") or css.get("text-decoration-line")
    if td:
        if "underline" in td:
            st["under"] = True
        elif td.startswith("none"):
            st["under"] = False
        if "line-through" in td:
            st["strike"] = True
    if css.get("vertical-align") in ("super", "sub"):
        st[css["vertical-align"].replace("super", "sup")] = True
    if "color" in css:
        st["color"] = css["color"]
    bg = css.get("background-color") or css.get("background") or css.get("mso-highlight")
    if bg:
        st["bg"] = bg.split()[0]
    ff = css.get("font-family", "")
    if any(x in ff for x in ("courier", "consolas", "monospace", "menlo", "monaco", "mono")):
        st["code"] = True
    return st


def _md_escape(s):
    s = s.replace("\\", "\\\\").replace("`", "\\`").replace("*", "\\*")
    s = re.sub(r"(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])", r"\\_", s)
    s = re.sub(r"([\[\]])", r"\\\1", s)
    s = re.sub(r"<(?=[A-Za-z/!])", "&lt;", s)
    return s


class _Md:
    def __init__(self):
        self.in_heading = False

    # ---- en linea ----
    def runs(self, n, st, out):
        for k in n.kids:
            if isinstance(k, str):
                out.append((k, st))
                continue
            if k.tag == "br":
                out.append(("\n", {}))
                continue
            if k.tag == "img":
                src, alt = k.attrs.get("src", ""), k.attrs.get("alt", "")
                if src.startswith(("http://", "https://")):
                    out.append(("\0IMG![%s](%s)" % (alt.replace("]", ""), src), {}))
                elif alt:
                    out.append((alt, st))
                continue
            if k.tag == "input" and k.attrs.get("type") == "checkbox":
                out.append(("\0BOX" + ("[x] " if "checked" in k.attrs else "[ ] "), {}))
                continue
            css = _style(k)
            if "mso-list" in css and "ignore" in css.get("mso-list", ""):
                continue                                         # la vineta que pinta Word
            if css.get("display") == "none" or css.get("mso-hide") == "all":
                continue
            self.runs(k, _run_style(k, st), out)
        return out

    def inline(self, n, st=None, pre=False):
        runs = self.runs(n, st or {}, [])
        return self.render_runs(runs, pre)

    def render_runs(self, runs, pre=False):
        # espacios: como en HTML, salvo en <pre>
        norm = []
        for text, st in runs:
            if text.startswith("\0") or text == "\n" or pre:
                norm.append((text, st))
                continue
            text = re.sub(r"[ \t\r\n\f]+", " ", text.replace("\xa0", " "))
            if text:
                norm.append((text, st))
        # fusiona trozos seguidos con el mismo estilo
        merged = []
        for text, st in norm:
            if merged and merged[-1][1] == st and not text.startswith("\0") and not merged[-1][0].startswith("\0") and text != "\n" and merged[-1][0] != "\n":
                merged[-1] = (merged[-1][0] + text, st)
            else:
                merged.append((text, st))
        # agrupa por enlace
        out = []
        i = 0
        while i < len(merged):
            href = merged[i][1].get("href")
            j = i
            while j < len(merged) and merged[j][1].get("href") == href and merged[j][0] != "\n":
                j += 1
            if j == i:
                j = i + 1
            inner = "".join(self.wrap(t, s, link=bool(href)) for t, s in merged[i:j])
            if href and inner.strip():
                lead = inner[:len(inner) - len(inner.lstrip())]
                trail = inner[len(inner.rstrip()):]
                inner = "%s[%s](%s)%s" % (lead, inner.strip(), href.replace(" ", "%20").replace(")", "%29"), trail)
            out.append(inner)
            i = j
        s = "".join(out)
        s = re.sub(r" *\n *", "\n", s) if not pre else s
        return s

    def wrap(self, text, st, link=False):
        if text == "\n":
            return "\n"
        if text.startswith("\0"):
            return text[4:]
        if not text.strip():
            return text
        lead = text[:len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()):]
        core = text.strip()
        if st.get("code"):
            tick = "``" if "`" in core else "`"
            core = tick + core + tick
            st = {k: v for k, v in st.items() if k not in ("bg", "color")}
        else:
            core = _md_escape(core)
            if st.get("bold") and not self.in_heading:
                core = "**" + core + "**"
            if st.get("italic"):
                core = "*" + core + "*"
            if st.get("strike"):
                core = "~~" + core + "~~"
        if st.get("under") and not link:
            core = "<u>" + core + "</u>"
        for t in ("sup", "sub"):
            if st.get(t):
                core = "<%s>%s</%s>" % (t, core, t)
        bg = (st.get("bg") or "").replace(" ", "")
        if st.get("mark") or bg == "yellow":
            core = "<mark>" + core + "</mark>"
        elif bg and bg not in _PLAIN_COLORS:
            core = '<span style="background-color:%s">%s</span>' % (bg, core)
        col = (st.get("color") or "").replace(" ", "")
        if col and col not in _PLAIN_COLORS and not link and not self.in_heading:
            core = '<span style="color:%s">%s</span>' % (col, core)
        return lead + core + trail

    # ---- bloques ----
    def blocks(self, n, st=None):
        """Lista de bloques: (tipo, texto). Los de tipo 'li' van seguidos, sin linea en blanco entre ellos."""
        st = st or {}
        out, buf = [], []

        def flush():
            if buf:
                tmp = _Node("#p")
                tmp.kids = list(buf)
                txt = self.inline(tmp, st).strip("\n ")
                if txt.strip():
                    out.append(("p", self.guard(txt)))
                buf.clear()

        for k in n.kids:
            if isinstance(k, str) or (k.tag not in _BLOCKS and not self.has_block(k)):
                buf.append(k)
                continue
            if k.tag not in _BLOCKS:                     # <span> con bloques dentro (Google Docs: <b id=docs-internal...>)
                flush()
                out += self.blocks(k, _run_style(k, st))
                continue
            flush()
            out += self.block(k, st)
        flush()
        return out

    def has_block(self, n):
        return any(not isinstance(k, str) and (k.tag in _BLOCKS or self.has_block(k)) for k in n.kids)

    def guard(self, txt):
        """Que un parrafo no se lea como titulo, lista o cita sin querer."""
        lines = []
        for ln in txt.split("\n"):
            ln = re.sub(r"^(\s*)([#>+-])(?=\s|$)", r"\1\\\2", ln)
            ln = re.sub(r"^(\s*\d+)([.)])(?=\s)", r"\1\\\2", ln)
            lines.append(ln)
        return "\n".join(lines)

    def block(self, k, st):
        t = k.tag
        css = _style(k)
        cls = (k.attrs.get("class") or "").lower()
        if t in ("p", "div") and "mso-list" in css:
            m = re.search(r"level(\d+)", css["mso-list"])
            level = int(m.group(1)) if m else 1
            marker = ""
            for d in self._descend(k):
                if not isinstance(d, str) and "ignore" in _style(d).get("mso-list", ""):
                    marker = re.sub(r"\s+", "", "".join(x for x in self._texts(d))).replace("\xa0", "")
                    break
            mm = re.match(r"^(\d+)[.)]", marker)
            ordered = bool(mm) or bool(re.match(r"^[a-zA-Z]{1,3}[.)]$", marker))
            mark = (mm.group(1) + "." if mm else "1.") if ordered else "-"
            txt = self.inline(k, _run_style(k, st)).strip()
            box = ""
            if txt[:1] in "☐☑☒":
                box, txt = ("[ ] " if txt[0] == "☐" else "[x] "), txt[1:].lstrip()
            lid = re.match(r"\s*(l\d+)", css["mso-list"])
            return [("li:" + (lid.group(1) if lid else "w") + ("o" if ordered else "u"), "    " * (level - 1) + mark + " " + box + txt.replace("\n", "\n" + "    " * level))]
        if re.fullmatch(r"h[1-6]", t) or "msotitle" in cls or "msosubtitle" in cls:
            lv = int(t[1]) if t[0] == "h" and t[1:].isdigit() else (1 if "msotitle" in cls else 2)
            self.in_heading = True
            txt = self.inline(k, st).replace("\n", " ").strip()
            self.in_heading = False
            return [("p", "#" * lv + " " + txt)] if txt else []
        if t in ("ul", "ol"):
            return self.list_(k, st, 0)
        if t == "li":
            return self.list_(_wrap_node("ul", k), st, 0)
        if t == "blockquote" or "msoquote" in cls or "msointensequote" in cls:
            inner = self.join(self.blocks(k, st)) if t == "blockquote" else self.inline(k, st).strip()
            return [("p", "\n".join(("> " + ln) if ln else ">" for ln in inner.split("\n")))] if inner.strip() else []
        if t == "pre":
            code = "".join(self._texts(k, br="\n")).strip("\n")
            fence = "````" if "```" in code else "```"
            return [("p", fence + "\n" + code + "\n" + fence)]
        if t == "hr":
            return [("p", "---")]
        if t == "table":
            return self.table(k, st)
        if t in ("tr", "td", "th", "thead", "tbody", "tfoot"):
            return self.table(_wrap_node("table", k), st)
        if t in ("p", "div", "center", "dt", "dd", "figcaption", "summary", "caption", "address") and not self.has_block(k):
            txt = self.inline(k, _run_style(k, st)).strip("\n ")
            if txt.strip():
                return [("p", self.guard(txt))]
            return []
        if self._is_code_box(k):                        # un editor de codigo (VS Code...): texto tal cual
            code = "".join(self._texts(k, br="\n")).strip("\n")
            return [("p", "```\n" + code + "\n```")] if code.strip() else []
        return self.blocks(k, _run_style(k, st))

    def _is_code_box(self, k):
        css = _style(k)
        return "pre" in css.get("white-space", "") and any(x in css.get("font-family", "") for x in ("consolas", "monospace", "courier", "menlo", "mono"))

    def _descend(self, n):
        for k in n.kids:
            yield k
            if not isinstance(k, str):
                yield from self._descend(k)

    def _texts(self, n, br=""):
        for k in n.kids:
            if isinstance(k, str):
                yield k
            elif k.tag == "br":
                yield br
            elif k.tag in ("div", "p", "tr", "li") and br:
                yield from self._texts(k, br)
                yield br
            else:
                yield from self._texts(k, br)

    def list_(self, k, st, depth, key=None):
        ordered = k.tag == "ol"
        key = key or "li:%d" % id(k)
        try:
            num = int(k.attrs.get("start", "1"))
        except ValueError:
            num = 1
        out = []
        for li in k.kids:
            if isinstance(li, str):
                continue
            if li.tag in ("ul", "ol"):                   # lista dentro de lista sin <li> (algunos editores)
                out += self.list_(li, st, depth + 1, key)
                continue
            if li.tag != "li":
                continue
            mark = ("%d." % num) if ordered else "-"
            num += 1
            pad = "    " * depth
            head = _Node("#p")
            rest = []
            for c in li.kids:
                if not isinstance(c, str) and c.tag in ("ul", "ol"):
                    rest.append(c)
                elif rest:
                    rest.append(c)
                else:
                    head.kids.append(c)
            first = self.join(self.blocks(head, st)) if self.has_block(head) else self.inline(head, st).strip()
            box = ""
            if first[:1] in "☐☑☒":
                box, first = ("[ ] " if first[0] == "☐" else "[x] "), first[1:].lstrip()
            if first.startswith(("[ ] ", "[x] ")):
                box, first = first[:4], first[4:]
            first = first.replace("\n\n", "\n").replace("\n", "\n" + pad + "    ")
            out.append((key, pad + mark + " " + box + first))
            for c in rest:
                if not isinstance(c, str) and c.tag in ("ul", "ol"):
                    out += self.list_(c, st, depth + 1, key)
                else:
                    tmp = _Node("#p")
                    tmp.kids = [c]
                    txt = self.join(self.blocks(tmp, st))
                    if txt.strip():
                        out.append((key, "\n".join(pad + "    " + ln for ln in txt.split("\n"))))
        return out

    def table(self, k, st):
        rows = []

        def walk(n):
            for c in n.kids:
                if isinstance(c, str):
                    continue
                if c.tag == "tr":
                    rows.append([x for x in c.kids if not isinstance(x, str) and x.tag in ("td", "th")])
                elif c.tag in ("thead", "tbody", "tfoot"):
                    walk(c)
                elif c.tag in ("td", "th"):
                    rows.append([x for x in n.kids if not isinstance(x, str) and x.tag in ("td", "th")])
                    return
        walk(k)
        if not rows:
            return self.blocks(k, st)
        cells = []
        for r in rows:
            line = []
            for c in r:
                txt = self.join(self.blocks(c, st)) if self.has_block(c) else self.inline(c, st).strip()
                txt = re.sub(r"\n+", "<br>", txt.strip()).replace("|", "\\|")
                line.append(txt)
            cells.append(line)
        width = max(len(r) for r in cells)
        if width == 1 and len(cells) == 1:
            return [("p", cells[0][0].replace("<br>", "\n"))] if cells[0][0] else []
        cells = [r + [""] * (width - len(r)) for r in cells]
        md = ["| " + " | ".join(cells[0]) + " |", "|" + "|".join(["---"] * width) + "|"]
        md += ["| " + " | ".join(r) + " |" for r in cells[1:]]
        return [("p", "\n".join(md))]

    @staticmethod
    def join(blocks):
        out = ""
        prev = None
        for kind, txt in blocks:
            if out:
                out += "\n" if (kind.startswith("li") and kind == prev) else "\n\n"
            out += txt
            prev = kind
        return out


def _wrap_node(tag, child):
    n = _Node(tag)
    n.kids = [child]
    return n


def html_to_md(src):
    """HTML (lo que dejan en el portapapeles Word, Writer, Google Docs, un navegador...) -> Markdown."""
    root = _parse_html(src)
    conv = _Md()
    md = conv.join(conv.blocks(root))
    md = re.sub(r"\n{3,}", "\n\n", md).strip("\n")
    return md


# ---------------------------------------------------------------------------------------------
# Un poco de HTML dentro del Markdown (colores, subrayado, centrado...), sin ejecutar nada
# ---------------------------------------------------------------------------------------------
ATTR_RX = re.compile(r"""([a-zA-Z_:-]+)\s*(?:=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?""")
TAG_RX = re.compile(r"^<\s*(/)?\s*([a-zA-Z][a-zA-Z0-9]*)([^>]*?)(/)?\s*>$", re.S)
HTML_INLINE_TAGS = {"b": {"bold": True}, "strong": {"bold": True}, "i": {"italic": True}, "em": {"italic": True},
                    "u": {"under": True}, "ins": {"under": True}, "s": {"strike": True}, "del": {"strike": True},
                    "strike": {"strike": True}, "mark": {"mark": True}, "code": {"mono": True}, "kbd": {"mono": True},
                    "tt": {"mono": True}, "samp": {"mono": True}, "sup": {"sup": True}, "sub": {"sub": True},
                    "small": {"size": 0.85}, "big": {"size": 1.2}, "span": {}, "font": {}, "a": {}, "abbr": {}, "q": {}}


def html_attrs(s):
    return {m.group(1).lower(): (m.group(2) or m.group(3) or m.group(4) or "") for m in ATTR_RX.finditer(s or "")}


def html_style(tag, attrs):
    """Estilo de una etiqueta HTML: lo de la propia etiqueta + su atributo style (+ color= de <font>, align=)."""
    st = dict(HTML_INLINE_TAGS.get(tag, {}))
    if tag == "font" and attrs.get("color"):
        st["color"] = attrs["color"]
    if attrs.get("align", "").lower() == "center" or tag == "center":
        st["center"] = True
    for decl in (attrs.get("style") or "").split(";"):
        if ":" not in decl:
            continue
        k, v = [x.strip().lower() for x in decl.split(":", 1)]
        if k == "color":
            st["color"] = v
        elif k in ("background-color", "background"):
            st["bg"] = v.split()[0] if v else v
        elif k == "font-weight":
            st["bold"] = v in ("bold", "bolder") or (v.isdigit() and int(v) >= 600)
        elif k == "font-style":
            st["italic"] = v in ("italic", "oblique")
        elif k in ("text-decoration", "text-decoration-line"):
            st["under"] = "underline" in v
            st["strike"] = "line-through" in v
        elif k == "text-align":
            st["center"] = v == "center"
        elif k == "font-size":
            m = re.match(r"([\d.]+)\s*(em|rem|%|px|pt)?", v)
            kw = {"small": 0.85, "x-small": 0.75, "smaller": 0.85, "large": 1.2, "x-large": 1.45, "larger": 1.2}
            if v in kw:
                st["size"] = kw[v]
            elif m:
                n, u = float(m.group(1)), m.group(2) or "px"
                st["size"] = n / 100 if u == "%" else n if u in ("em", "rem") else n / 15.0 if u == "px" else n / 11.0
                st["size"] = max(0.5, min(3.0, st["size"]))
        elif k == "font-family" and "mono" in v:
            st["mono"] = True
    if tag == "a" and attrs.get("href"):
        st["href"] = attrs["href"]
    return st


def css_color(widget, v):
    """Color CSS (nombre, #rgb, #rrggbb, rgb()) -> #rrggbb, o None si no se entiende."""
    v = (v or "").strip()
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", v)
    if m:
        return "#%02x%02x%02x" % tuple(min(255, int(x)) for x in m.groups())
    if re.fullmatch(r"#[0-9a-fA-F]{3}", v):
        return "#" + "".join(c * 2 for c in v[1:]).lower()
    try:
        r, g, b = widget.winfo_rgb(v)
        return "#%02x%02x%02x" % (r // 257, g // 257, b // 257)
    except Exception:
        return None


def merge_styles(stack):
    out = {}
    for st in stack:
        out.update({k: v for k, v in st.items() if v not in (None, False) or k in ("bold", "italic", "under", "strike")})
    return out


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
        t.tag_configure("task", foreground=c["acc"])
        t.tag_bind("task", "<Enter>", lambda e: t.configure(cursor="hand2"))
        t.tag_bind("task", "<Leave>", lambda e: t.configure(cursor=""))

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
            if tag.startswith(("li_", "tbl_", "lnk_", "task_", "q")) and tag != "quote":
                t.tag_delete(tag)
        self._fonts.clear()
        for w in self.lines:
            try:
                w.destroy()
            except Exception:
                pass
        self.images, self.lines, self.headings, self.anchors, self.links = [], [], [], {}, {}
        self.blocks = []          # (indice en la vista, linea del Markdown) de cada bloque: para "doble clic = editar aqui"
        self.decor = set()        # lineas decorativas (bajo los titulos): no se copian
        self.image_paths = {}     # imagen del lector -> archivo (para copiarla con formato)
        self.setup_tags()
        if self.md is None:
            t.insert("end", "Falta la libreria markdown-it-py (vuelve a ejecutar el instalador).\n\n", ("muted",))
            t.insert("end", src)
        else:
            try:
                src2, self.line_map = self._lenient(src) if self.app.cfg.get("breaks", True) else (src, None)
                self._render_tokens(self.md.parse(src2))
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

    def html_tags(self, st, size):
        """Etiquetas de Tk para un estilo HTML ya combinado. Devuelve (etiquetas, negrita, cursiva, mono, tamano)."""
        tags = []
        c = css_color(self.t, st.get("color")) if st.get("color") else None
        if c:
            name = "hc_" + c[1:]
            self.t.tag_configure(name, foreground=c)
            tags.append(name)
        bg = css_color(self.t, st.get("bg")) if st.get("bg") else None
        if st.get("mark") and not bg:
            bg = self.app.c["find"]
        if bg:
            name = "hb_" + bg[1:]
            self.t.tag_configure(name, background=bg)
            tags.append(name)
        if st.get("under"):
            self.t.tag_configure("u", underline=True)
            tags.append("u")
        if st.get("strike"):
            tags.append("s")
        z = self.app.zoom
        if st.get("sup"):
            self.t.tag_configure("sup", offset=int(5 * z))
            tags.append("sup")
            size *= 0.75
        if st.get("sub"):
            self.t.tag_configure("sub", offset=-int(3 * z))
            tags.append("sub")
            size *= 0.75
        if st.get("center"):
            self.t.tag_configure("center", justify="center")
            tags.append("center")
        return tags, bool(st.get("bold")), bool(st.get("italic")), bool(st.get("mono")), size * st.get("size", 1.0)

    def _html_block(self, content, base):
        """Un bloque HTML (<div>, <p align=center>, comentarios...): su texto con su estilo; nada se ejecuta."""
        from html.parser import HTMLParser
        r = self
        runs = []            # (texto, estilo) ; "\n" separa lineas ; ("HR", None)
        state = {"stack": [], "skip": 0}

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                a = {k: (v or "") for k, v in attrs}
                if tag in ("script", "style", "head", "title"):
                    state["skip"] += 1
                    return
                if tag == "br":
                    runs.append(("\n", {}))
                    return
                if tag == "hr":
                    runs.append(("HR", None))
                    return
                if tag == "img":
                    runs.append(("[imagen: %s]" % (a.get("alt") or a.get("src") or ""), {"italic": True}))
                    return
                st = html_style(tag, a)
                if re.fullmatch(r"h[1-6]", tag):
                    st.update(bold=True, size={"h1": 1.9, "h2": 1.5, "h3": 1.25}.get(tag, 1.1))
                if tag in ("p", "div", "center", "li", "tr", "ul", "ol", "table", "blockquote", "details", "summary") or re.fullmatch(r"h[1-6]", tag):
                    if runs and runs[-1][0] != "\n":
                        runs.append(("\n", {}))
                    if tag == "li":
                        runs.append(("•  ", merge_styles(state["stack"] + [st])))
                state["stack"].append((tag, st))

            def handle_endtag(self, tag):
                if tag in ("script", "style", "head", "title"):
                    state["skip"] = max(0, state["skip"] - 1)
                    return
                for i in range(len(state["stack"]) - 1, -1, -1):
                    if state["stack"][i][0] == tag:
                        del state["stack"][i:]
                        break
                if tag in ("p", "div", "center", "li", "tr", "ul", "ol", "table", "blockquote") or re.fullmatch(r"h[1-6]", tag):
                    if runs and runs[-1][0] != "\n":
                        runs.append(("\n", {}))

            def handle_data(self, data):
                if state["skip"]:
                    return
                data = re.sub(r"\s+", " ", data)
                if data.strip() or (runs and runs[-1][0] not in ("\n", "HR")):
                    runs.append((data, merge_styles([x[1] for x in state["stack"]])))

        P(convert_charrefs=True).feed(content)
        any_text = False
        for text, st in runs:
            if text == "HR":
                self._hr()
                continue
            if text == "\n":
                if any_text and self.t.get("end-2c", "end-1c") != "\n":
                    self._ins("\n", base)
                continue
            tags, bold, italic, mono, size = self.html_tags(st, 1.0)
            if st.get("href"):
                name = "lnk_%d" % len(self.links)
                self.links[name] = st["href"]
                self.t.tag_bind(name, "<Button-1>", lambda e, h=st["href"]: self.app.follow_link(h))
                tags += ["link", name]
            self._ins(text, base + tags + [self.font_tag(mono=mono, size=size, bold=bold, italic=italic)])
            any_text = True
        if any_text:
            if self.t.get("end-2c", "end-1c") != "\n":
                self._ins("\n", base)
            self._ins("\n", base + ["p", self.font_tag(size=0.5)])

    FENCE_LINE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
    OL_LINE = re.compile(r"^\s{0,3}\d{1,9}[.)]\s")
    ITEM_LINE = re.compile(r"^\s*(?:[-*+]|\d{1,9}[.)])\s")

    def _lenient(self, src):
        """Markdown "como se escribe": una lista numerada se reconoce aunque vaya pegada a una linea de texto
        o empiece por un numero distinto de 1 (en Markdown estricto se juntaria con el parrafo de arriba).
        Devuelve el texto para pintar y, para cada linea suya, la linea original (para clics y doble clic)."""
        out, lmap = [], []
        fence = None
        prev = ""
        for n, line in enumerate(src.split("\n")):
            m = self.FENCE_LINE.match(line)
            if fence:
                if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not line.strip().strip(fence[0]):
                    fence = None
            elif m:
                fence = m.group(1)
            elif self.OL_LINE.match(line) and prev.strip() and not self.ITEM_LINE.match(prev) \
                    and not prev.startswith((" ", "\t")) and not prev.lstrip().startswith(("|", ">")):
                out.append("")
                lmap.append(n)
            out.append(line)
            lmap.append(n)
            prev = line
        return "\n".join(out), lmap

    def src_line(self, ln):
        m = getattr(self, "line_map", None)
        return m[ln] if m and 0 <= ln < len(m) else ln

    def line_at(self, index):
        """Linea del Markdown (desde 0) del bloque que se ve en ese punto de la vista."""
        line = 0
        for idx, ln in self.blocks:
            if self.t.compare(idx, "<=", index):
                line = ln
            else:
                break
        return line

    def _render_tokens(self, toks):
        z = self.app.zoom
        lists = []                  # pila: {"ordered", "n", "tight"}
        quote = 0
        used = set()
        i = 0
        pending_item = None         # prefijo de la vineta pendiente de pintar
        table = None
        heading = None
        pending_task = None         # linea del Markdown de la casilla pendiente de pintar
        while i < len(toks):
            tk_ = toks[i]
            ty = tk_.type
            if tk_.map and (ty.endswith("_open") or ty in ("fence", "code_block", "hr", "html_block")):
                self.blocks.append((self.t.index("end-1c"), self.src_line(tk_.map[0])))
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
                    # separacion entre parrafos: una linea vacia baja (con "spacing" Tk estiraria tambien el fondo
                    # del codigo en linea de la ultima linea del parrafo)
                    self._ins("\n", self._block_tags(lists, quote))
                    self._ins("\n", self._block_tags(lists, quote) + ["p", self.font_tag(size=0.5)])
                else:
                    self._ins("\n", self._block_tags(lists, quote))
            elif ty == "inline":
                base = self._block_tags(lists, quote)
                if heading:
                    base = base + ["h%d" % heading]
                if pending_item is not None:
                    tags = base + [self.font_tag(bold=False)]
                    if pending_task is not None:
                        glyph, rest = pending_item[0], pending_item[1:]
                        name = "task_%d" % pending_task
                        self.t.tag_bind(name, "<Button-1>", lambda e, ln=pending_task: self.app.toggle_task(ln))
                        self._ins(glyph, tags + ["task", name, self.font_tag(size=1.15)])
                        self._ins(rest, tags)
                    else:
                        self._ins(pending_item, tags)
                    pending_item = pending_task = None
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
                            if tk_.map:
                                pending_task = self.src_line(tk_.map[0])
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
                self._html_block(tk_.content, self._block_tags(lists, quote))
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
        hstack = []                    # etiquetas HTML abiertas en esta linea: (nombre, estilo)
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
                if ty == "html_inline":
                    m = TAG_RX.match(ch.content.strip())
                    if ch.content.lstrip().startswith("<!--") or not m:
                        continue                              # comentarios: no se ven
                    closing, name, attrs, selfclose = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
                    if name == "br":
                        text = "\n\t" if any(str(t).startswith("li_") for t in base) else "\n"
                        self._ins(text, tags + [self.font_tag(size=size)])
                        continue
                    if closing:
                        for k in range(len(hstack) - 1, -1, -1):
                            if hstack[k][0] == name:
                                del hstack[k:]
                                break
                    elif not selfclose and name not in ("img", "hr", "wbr", "input"):
                        hstack.append((name, html_style(name, html_attrs(attrs))))
                    continue
                hs = merge_styles([x[1] for x in hstack]) if hstack else {}
                htags, hb, hi, hm, hsize = self.html_tags(hs, size) if hs else ([], False, False, False, size)
                tags += htags
                if hs.get("href") and not link:
                    name = "lnk_%d" % len(self.links)
                    self.links[name] = hs["href"]
                    self.t.tag_bind(name, "<Button-1>", lambda e, h=hs["href"]: self.app.follow_link(h))
                    tags += ["link", name]
                if ty == "code_inline" or hm:
                    tags += (["code"] if ty == "code_inline" else []) + [self.font_tag(mono=True, size=hsize * 0.95, bold=bold or hb, italic=bool(em) or hi)]
                    text = ch.content
                else:
                    tags.append(self.font_tag(size=hsize, bold=bold or hb, italic=bool(em) or hi))
                    brk = ty == "hardbreak" or (ty == "softbreak" and self.app.cfg.get("breaks", True))
                    text = ch.content if ty == "text" else ("\n" if brk else " ")
                    if text == "\n" and any(str(t).startswith("li_") for t in base):
                        text = "\n\t"          # dentro de una lista, la linea siguiente sigue alineada con el texto
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
                name = self.t.image_create("end", image=ph, padx=2, pady=4)
                self.image_paths[name] = path
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
        if thin:
            self.decor.add(str(fr))
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
    ("ed_mark", re.compile(r"</?[a-zA-Z][^>\n]*>|<!--.*?-->")),
]
FENCE = re.compile(r"^(```|~~~)[^\n]*\n.*?^\1[ \t]*$", re.M | re.S)


# ---------------------------------------------------------------------------------------------
# Acerca de: tarjeta con una mini demo del modo Dual (se escribe Markdown y se ve al momento)
# ---------------------------------------------------------------------------------------------
class AboutDialog:
    def __init__(self, app):
        self.app = app
        c = app.c
        z = 1.0
        top = self.top = tk.Toplevel(app.root)
        top.title("Acerca de md-reader")
        top.configure(bg=c["panel"])
        top.resizable(False, False)
        top.transient(app.root)
        ui = app.ui_family
        pad = dict(padx=22)
        head = tk.Frame(top, bg=c["panel"])
        head.pack(fill="x", pady=(20, 6), **pad)
        if getattr(app, "_icon", None) is not None:
            try:
                self._ico = app._icon.subsample(max(1, app._icon.width() // 56))
                tk.Label(head, image=self._ico, bg=c["panel"]).pack(side="left", padx=(0, 14))
            except Exception:
                pass
        tt = tk.Frame(head, bg=c["panel"])
        tt.pack(side="left", fill="x")
        tk.Label(tt, text="md-reader", bg=c["panel"], fg=c["fg"], font=(ui, 20, "bold")).pack(anchor="w")
        tk.Label(tt, text="versión %s" % APP_VERSION, bg=c["panel"], fg=c["muted"], font=(ui, 9)).pack(anchor="w")
        tk.Label(top, text=ABOUT_TAGLINE, bg=c["panel"], fg=c["fg"], font=(ui, 11)).pack(anchor="w", pady=(6, 10), **pad)

        # mini demo: editor | lector
        demo = tk.Frame(top, bg=c["line"], bd=0)
        demo.pack(fill="x", **pad)
        self.ed = tk.Text(demo, width=24, height=9, wrap="word", relief="flat", bd=0, highlightthickness=0,
                          bg=c["ed_bg"], fg=c["ed_fg"], font=(app.mono_family, 9), padx=10, pady=8, cursor="")
        self.ed.pack(side="left", fill="both", padx=(1, 0), pady=1)
        self.vw = tk.Text(demo, width=26, height=9, wrap="word", relief="flat", bd=0, highlightthickness=0, cursor="")
        self.vw.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        self.mini = Renderer(_MiniApp(app), self.vw)
        self.vw.configure(padx=10, pady=6)

        chips = tk.Frame(top, bg=c["panel"])
        chips.pack(fill="x", pady=(12, 4), **pad)
        for r in range(0, len(ABOUT_CHIPS), 3):
            row = tk.Frame(chips, bg=c["panel"])
            row.pack(anchor="w", pady=3)
            for ch in ABOUT_CHIPS[r:r + 3]:
                tk.Label(row, text=ch, bg=c["panel2"], fg=c["fg"], font=(ui, 8), padx=8, pady=3).pack(side="left", padx=(0, 6))

        tk.Label(top, text=ABOUT_ASK, bg=c["panel"], fg=c["fg"], font=(ui, 10), wraplength=430, justify="left").pack(
            anchor="w", pady=(10, 10), **pad)
        btn = tk.Button(top, text=ABOUT_BTN, command=lambda: webbrowser.open(KOFI_URL), bg="#ff5e5b", fg="white",
                        activebackground="#e94b48", activeforeground="white", relief="flat", bd=0, cursor="hand2",
                        font=(ui, 11, "bold"), padx=18, pady=9)
        btn.pack(fill="x", **pad)
        links = tk.Frame(top, bg=c["panel"])
        links.pack(pady=(12, 2))
        for i, (txt, url) in enumerate((("Página del programa", SITE_URL), ("Código", REPO_URL),
                                         ("Opinar o avisar de un fallo", REPO_URL + "/issues/new/choose"))):
            if i:
                tk.Label(links, text="·", bg=c["panel"], fg=c["muted"]).pack(side="left", padx=4)
            lb = tk.Label(links, text=txt, bg=c["panel"], fg=c["link"], font=(ui, 9, "underline"), cursor="hand2")
            lb.pack(side="left")
            lb.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
        tk.Label(top, text=ABOUT_CREDIT, bg=c["panel"], fg=c["muted"], font=(ui, 8)).pack(pady=(4, 2))
        tk.Label(top, text="Software libre, licencia MIT", bg=c["panel"], fg=c["muted"], font=(ui, 8)).pack(pady=(0, 16))
        top.bind("<Escape>", lambda e: top.destroy())
        self.i = 0
        self._tick()
        top.update_idletasks()
        x = app.root.winfo_rootx() + (app.root.winfo_width() - top.winfo_reqwidth()) // 2
        y = app.root.winfo_rooty() + max(0, (app.root.winfo_height() - top.winfo_reqheight()) // 3)
        top.geometry("+%d+%d" % (max(0, x), max(0, y)))
        top.focus_set()

    def _tick(self):
        """Escribe la demo letra a letra (como si tecleara alguien) y la pinta al momento; al acabar, vuelve a empezar."""
        try:
            if not self.top.winfo_exists():
                return
        except tk.TclError:
            return
        n = len(ABOUT_DEMO)
        self.i = self.i + 1 if self.i < n + 40 else 0
        txt = ABOUT_DEMO[:min(self.i, n)]
        self.ed.configure(state="normal")
        self.ed.delete("1.0", "end")
        self.ed.insert("1.0", txt + ("▏" if self.i <= n and self.i % 2 else ""))
        self.ed.configure(state="disabled")
        self.mini.render(txt, None)
        self.top.after(55 if self.i <= n else 90, self._tick)


class GuideWindow:
    """F1: la guia de formatos, pintada con el mismo lector (asi se ve exactamente como quedara)."""
    def __init__(self, app):
        self.app = app
        c = app.c
        top = self.top = tk.Toplevel(app.root)
        top.title("Guía de formatos — md-reader")
        top.configure(bg=c["bg"])
        w, h = int(720 * max(1, app.zoom)), int(760 * max(1, app.zoom))
        top.geometry("%dx%d+%d+%d" % (w, h, app.root.winfo_rootx() + 60, app.root.winfo_rooty() + 40))
        fr = ttk.Frame(top)
        fr.pack(fill="both", expand=True)
        self.t = tk.Text(fr, wrap="word", relief="flat", borderwidth=0, highlightthickness=0, cursor="")
        sb = ttk.Scrollbar(fr, orient="vertical", command=self.t.yview)
        self.t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.t.pack(fill="both", expand=True)
        self.r = Renderer(_GuideApp(app, self), self.t)
        self.r.render(GUIDE, None)
        self.t.bind("<Configure>", lambda e: self.r.fit_lines())
        top.bind("<Escape>", lambda e: top.destroy())
        top.bind("<F1>", lambda e: top.destroy())
        top.focus_set()


class _GuideApp:
    """Lo que el Renderer necesita para pintar la guia (los enlaces #... saltan dentro de la guia)."""
    def __init__(self, app, win):
        self.app, self.win = app, win
        self.c, self.zoom, self.cfg = app.c, app.zoom, {"breaks": True}
        self.body_family, self.mono_family, self.body_size = app.body_family, app.mono_family, app.body_size

    def follow_link(self, href):
        if href.startswith("#"):
            mark = self.win.r.anchors.get(href[1:].lower())
            if mark:
                self.win.t.yview(mark)
        elif re.match(r"^https?:", href):
            webbrowser.open(href)

    def toggle_task(self, line):
        pass


class _MiniApp:
    """Lo que el Renderer necesita de la aplicacion, a tamano pequeno (para la demo del Acerca de)."""
    def __init__(self, app):
        self.c, self.zoom, self.cfg = app.c, 0.75, {"breaks": True}
        self.body_family, self.mono_family, self.body_size = app.body_family, app.mono_family, app.body_size

    def follow_link(self, href):
        pass

    def toggle_task(self, line):
        pass


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
        self.view.bind("<Double-Button-1>", self._edit_here)
        for seq in ("<Control-c>", "<Control-C>", "<<Copy>>"):        # copiar desde el lector: con formato
            self.view.bind(seq, lambda e: self.copy_rich_view())
        if sys.platform == "darwin":
            self.view.bind("<Command-c>", lambda e: self.copy_rich_view())
        self.editor.bind("<<Paste>>", lambda e: self.paste_rich())                 # pegar de Word/Writer/web: a Markdown
        self.view.bind("<<Paste>>", lambda e: self.paste_rich(from_view=True))
        for w in (self.editor, self.view):
            w.bind("<Control-V>", lambda e, v=w is self.view: self.paste_plain(from_view=v))   # Ctrl+Mayus+V: sin formato
            if sys.platform == "darwin":
                w.bind("<Command-V>", lambda e, v=w is self.view: self.paste_plain(from_view=v))
        self.view.bind("<Control-v>", lambda e: self.paste_rich(from_view=True))
        for seq in ("<Control-z>", "<Control-Z>", "<Control-y>"):      # deshacer tambien desde el lector (p.ej. una casilla)
            self.view.bind(seq, lambda e, s=seq: (self._undo_from_view(redo=s != "<Control-z>"), "break")[1])
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
        self.breaks_var = tk.BooleanVar(value=self.cfg.get("breaks", True))
        m.add_checkbutton(label="Respetar los saltos de línea", variable=self.breaks_var, command=self.toggle_breaks)
        m.add_command(label="Guía de formatos              F1", command=self.show_guide)
        m.add_command(label="Copiar todo con formato (para Word…)", command=self.copy_rich_all)
        m.add_separator()
        if sys.platform == "win32":
            m.add_command(label="Abrir los .md con md-reader", command=self.associate_md)
        m.add_command(label="Buscar actualizaciones…", command=self.show_updates)
        m.add_separator()
        m.add_command(label="☕  Acerca de md-reader y apoyarlo", command=self.about)
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
        self.editor.bind("<Control-b>", lambda e: (self.fmt_inline("**"), "break")[1])
        self.editor.bind("<Control-i>", lambda e: (self.fmt_inline("*"), "break")[1])
        self.editor.bind("<Control-k>", lambda e: (self.fmt_link(), "break")[1])
        r.bind_all("<F1>", lambda e: (self.show_guide(), "break")[1])
        btns = ("<Button-2>", "<Control-Button-1>") if sys.platform == "darwin" else ("<Button-3>",)
        for b_ in btns:
            self.editor.bind(b_, lambda e: self._context_menu(e, "editor"))
            self.view.bind(b_, lambda e: self._context_menu(e, "view"))
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
        ed.configure(autoseparators=False)
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
        ed.configure(autoseparators=True)

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

    # -- dar formato (menu del boton derecho, atajos) --------------------------------------------
    LINE_PREFIX = re.compile(r"^(\s*)(?:#{1,6}\s+|>\s?|(?:[-*+]|\d{1,9}[.)])\s+(?:\[[ xX]\]\s+)?)?")
    INLINE = [("Negrita", "**", "Ctrl+B"), ("Cursiva", "*", "Ctrl+I"), ("Tachado", "~~", ""), ("Código", "`", "")]
    LINES = [("Título 1", "h1"), ("Título 2", "h2"), ("Título 3", "h3"), (None, None), ("Lista con puntos", "ul"),
             ("Lista numerada", "ol"), ("Casilla de tarea", "task"), ("Cita", "quote"), (None, None), ("Texto normal", "plain")]

    def _ed_batch(self, fn):
        """Ejecuta un cambio en el editor como un solo paso de Ctrl+Z, y repinta."""
        ed = self.editor
        ed.configure(autoseparators=False)
        try:
            ed.edit_separator()
            fn(ed)
            ed.edit_separator()
        finally:
            ed.configure(autoseparators=True)
        self.render_now()
        self.highlight()
        self._update_title()

    def fmt_inline(self, mark):
        """Pone (o quita, si ya lo tiene) negrita, cursiva, tachado o codigo a lo seleccionado."""
        def go(ed):
            try:
                a, b = ed.index("sel.first"), ed.index("sel.last")
            except tk.TclError:
                ed.insert("insert", mark + mark)
                ed.mark_set("insert", "insert-%dc" % len(mark))
                return
            txt = ed.get(a, b)
            n = len(mark)
            before = ed.get("%s-%dc" % (a, n), a)
            after = ed.get(b, "%s+%dc" % (b, n))
            if len(txt) >= 2 * n and txt.startswith(mark) and txt.endswith(mark):
                ed.delete("%s-%dc" % (b, n), b)
                ed.delete(a, "%s+%dc" % (a, n))
                ed.tag_add("sel", a, "%s-%dc" % (b, 2 * n))
            elif before == mark and after == mark and not (mark == "*" and (ed.get("%s-2c" % a, a) == "**" and ed.get(b, "%s+2c" % b) == "**" and ed.get("%s-3c" % a, a) != "***")):
                ed.delete(b, "%s+%dc" % (b, n))
                ed.delete("%s-%dc" % (a, n), a)
                ed.tag_add("sel", "%s-%dc" % (a, n), "%s-%dc" % (b, n))
            else:
                # los espacios de los bordes, fuera (Markdown no admite "** texto **")
                lead = len(txt) - len(txt.lstrip())
                trail = len(txt) - len(txt.rstrip())
                a2, b2 = "%s+%dc" % (a, lead), "%s-%dc" % (b, trail)
                ed.insert(b2, mark)
                ed.insert(a2, mark)
                ed.tag_remove("sel", "1.0", "end")
                ed.tag_add("sel", a2, "%s+%dc" % (a2, len(txt) - lead - trail + 2 * n))
        self._ed_batch(go)

    def fmt_link(self):
        def go(ed):
            try:
                a, b = ed.index("sel.first"), ed.index("sel.last")
                txt = ed.get(a, b)
                ed.delete(a, b)
            except tk.TclError:
                a, txt = ed.index("insert"), "texto"
            url = txt if re.match(r"^https?://\S+$", txt) else "https://"
            ed.insert(a, "[%s](%s)" % (txt, url))
            ua = "%s+%dc" % (a, len(txt) + 3)
            ed.tag_remove("sel", "1.0", "end")
            ed.tag_add("sel", ua, "%s+%dc" % (ua, len(url)))      # la direccion, seleccionada para escribirla
            ed.mark_set("insert", "%s+%dc" % (ua, len(url)))
        self._ed_batch(go)
        self.editor.focus_set()

    def _sel_lines(self):
        ed = self.editor
        try:
            a, b = ed.index("sel.first"), ed.index("sel.last")
            l1, l2 = int(a.split(".")[0]), int(b.split(".")[0])
            if b.endswith(".0") and l2 > l1:
                l2 -= 1
        except tk.TclError:
            l1 = l2 = int(ed.index("insert").split(".")[0])
        return l1, l2

    def fmt_lines(self, kind, l1=None, l2=None):
        """Titulo, lista, casilla, cita o texto normal para las lineas seleccionadas (o la del cursor).
        Si ya lo tienen todas, se quita."""
        if l1 is None:
            l1, l2 = self._sel_lines()

        def kind_of(line):
            t = line.lstrip()
            if re.match(r"#{1,6}\s", t):
                return "h%d" % min(3, len(t) - len(t.lstrip("#")))
            if re.match(r"(?:[-*+]|\d+[.)])\s+\[[ xX]\]\s", t):
                return "task"
            if re.match(r"[-*+]\s", t):
                return "ul"
            if re.match(r"\d+[.)]\s", t):
                return "ol"
            if t.startswith(">"):
                return "quote"
            return "plain"

        def go(ed):
            lines = [ed.get("%d.0" % n, "%d.end" % n) for n in range(l1, l2 + 1)]
            textual = [x for x in lines if x.strip()]
            undo = textual and all(kind_of(x) == kind for x in textual)
            k = "plain" if undo else kind
            num = 0
            for i, line in enumerate(lines):
                n = l1 + i
                if not line.strip():
                    continue
                m = self.LINE_PREFIX.match(line)
                indent, body = m.group(1), line[m.end():]
                num += 1
                pre = {"h1": "# ", "h2": "## ", "h3": "### ", "ul": "- ", "ol": "%d. " % num, "task": "- [ ] ",
                       "quote": "> ", "plain": ""}[k]
                if k.startswith("h"):
                    indent = ""
                ed.delete("%d.0" % n, "%d.end" % n)
                ed.insert("%d.0" % n, indent + pre + body)
            ed.tag_remove("sel", "1.0", "end")
            ed.tag_add("sel", "%d.0" % l1, "%d.end" % l2)
        self._ed_batch(go)

    def fmt_code_block(self, l1=None, l2=None):
        if l1 is None:
            l1, l2 = self._sel_lines()

        def go(ed):
            ed.insert("%d.end" % l2, "\n```")
            ed.insert("%d.0" % l1, "```\n")
        self._ed_batch(go)

    def _theme_menu(self, m):
        m.configure(bg=self.c["panel"], fg=self.c["fg"], activebackground=self.c["acc"], activeforeground="white",
                    relief="flat", borderwidth=1, font=(self.ui_family, 9))
        return m

    def _context_menu(self, e, where):
        """Boton derecho: formatos para lo seleccionado (en el editor, o en el lector sobre el Markdown de ese trozo)."""
        m = self._theme_menu(tk.Menu(self.root, tearoff=False))
        if where == "view":
            ok_inline, l1, l2 = self._map_view_selection(e)
        else:
            ok_inline, l1, l2 = True, None, None
            self.editor.focus_set()
        st = "normal" if ok_inline else "disabled"
        for label, mark, key in self.INLINE:
            m.add_command(label=label, accelerator=key, state=st, command=lambda k=mark: self.fmt_inline(k))
        m.add_command(label="Enlace…", state=st, command=self.fmt_link)
        m.add_separator()
        for label, kind in self.LINES:
            if label is None:
                m.add_separator()
            else:
                m.add_command(label=label, command=lambda k=kind: self.fmt_lines(k, l1, l2) if l1 is not None else self.fmt_lines(k))
        m.add_command(label="Bloque de código", command=lambda: self.fmt_code_block(l1, l2) if l1 is not None else self.fmt_code_block())
        m.add_separator()
        w = self.view if where == "view" else self.editor
        if where == "editor":
            m.add_command(label="Cortar", accelerator="Ctrl+X", command=lambda: w.event_generate("<<Cut>>"))
            m.add_command(label="Copiar (Markdown)", accelerator="Ctrl+C", command=lambda: w.event_generate("<<Copy>>"))
            m.add_command(label="Copiar con formato (para Word…)", command=self.copy_rich_editor)
            m.add_command(label="Pegar", accelerator="Ctrl+V", command=self.paste_rich)
            m.add_command(label="Pegar sin formato", accelerator="Ctrl+Mayús+V", command=self.paste_plain)
        else:
            m.add_command(label="Copiar con formato", accelerator="Ctrl+C", command=self.copy_rich_view)
            m.add_command(label="Copiar sin formato", command=self.copy_plain_view)
            m.add_command(label="Pegar aquí", accelerator="Ctrl+V", command=lambda: self.paste_rich(from_view=True, at=(e.x, e.y)))
            m.add_command(label="Pegar sin formato", accelerator="Ctrl+Mayús+V", command=lambda: self.paste_plain(from_view=True, at=(e.x, e.y)))
        m.add_separator()
        m.add_command(label="Guía de formatos", accelerator="F1", command=self.show_guide)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()
        return "break"

    def _map_view_selection(self, e):
        """Lleva lo seleccionado en el lector a su sitio en el Markdown: selecciona alli el mismo texto (para los
        formatos de texto) y devuelve las lineas de esos bloques (para titulos, listas...). Sin seleccion, el
        bloque bajo el raton."""
        v = self.view
        try:
            a, b = v.index("sel.first"), v.index("sel.last")
            txt = v.get(a, b)
        except tk.TclError:
            a = b = v.index("@%d,%d" % (e.x, e.y))
            txt = ""
        r = self.renderer
        l1 = r.line_at(a) + 1
        l2 = max(l1, r.line_at(b) + 1 if txt else l1)
        # ultima linea del ultimo bloque: hasta la siguiente linea en blanco
        ed = self.editor
        last = int(ed.index("end-1c").split(".")[0])
        while l2 < last and ed.get("%d.0" % (l2 + 1), "%d.end" % (l2 + 1)).strip() and not txt:
            l2 += 1
        ok_inline = False
        ed.tag_remove("sel", "1.0", "end")
        clean = txt.strip()
        if clean and "\t" not in clean:
            pos = ed.search(clean, "%d.0" % l1, "end", exact=True)
            if pos and int(pos.split(".")[0]) <= max(l2, l1) + 50:
                ed.tag_add("sel", pos, "%s+%dc" % (pos, len(clean)))
                ed.mark_set("insert", "%s+%dc" % (pos, len(clean)))
                ok_inline = True
                l2 = max(l2, int(ed.index("%s+%dc" % (pos, len(clean))).split(".")[0]))
        if txt:
            # para lineas: las que ocupa lo seleccionado en el Markdown
            l2 = max(l1, l2)
        return ok_inline, l1, l2

    def paste_rich(self, from_view=False, at=None):
        """Pegar: si lo copiado trae formato (Word, Writer, Google Docs, una web...), entra como Markdown."""
        html = get_clipboard_html(self.root)
        md = None
        if html:
            try:
                md = html_to_md(html)
            except Exception:
                md = None
        if not md:
            return self.paste_plain(from_view, at)
        self._insert_pasted(md, from_view, at)
        self.flash("Pegado como Markdown (sin formato: Ctrl+Mayús+V)")
        return "break"

    def paste_plain(self, from_view=False, at=None):
        try:
            txt = self.root.clipboard_get()
        except tk.TclError:
            return "break"
        self._insert_pasted(txt, from_view, at)
        return "break"

    def _insert_pasted(self, txt, from_view, at=None):
        ed = self.editor
        ed.configure(autoseparators=False)                 # pegar = un solo paso de Ctrl+Z
        try:
            ed.edit_separator()
            if from_view:
                # en el lector: detras del bloque donde esta el cursor (o el raton), como parrafo aparte
                v = self.view
                try:
                    idx = v.index("@%d,%d" % at) if at else v.index("sel.last")
                except tk.TclError:
                    idx = v.index("insert")
                line = self.renderer.line_at(idx) + 1
                last = int(ed.index("end-1c").split(".")[0])
                while line < last and ed.get("%d.0" % (line + 1), "%d.end" % (line + 1)).strip():
                    line += 1
                if not ed.get("1.0", "end-1c").strip():
                    ed.insert("1.0", txt.rstrip("\n") + "\n")
                else:
                    ed.insert("%d.end" % line, "\n\n" + txt.strip("\n"))
            else:
                try:
                    ed.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                ed.insert("insert", txt)
                ed.see("insert")
            ed.edit_separator()
        finally:
            ed.configure(autoseparators=True)
        self.render_now()
        self.highlight()
        self._update_title()

    def copy_rich_view(self):
        """Ctrl+C en el lector: lo seleccionado, con su formato (y como texto normal para donde no hay formato)."""
        v = self.view
        try:
            a, b = v.index("sel.first"), v.index("sel.last")
        except tk.TclError:
            return "break"
        html, plain = html_from_view(v, a, b, self.renderer.links, images=self.renderer.image_paths)   # con las lineas bajo los titulos
        rich = set_rich_clipboard(self.root, html, plain)
        self.flash("Copiado con formato" if rich else "Copiado (sin formato: este sistema no deja más)")
        return "break"

    def copy_plain_view(self):
        try:
            txt = self.view.get("sel.first", "sel.last")
        except tk.TclError:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(txt)
        self.flash("Copiado sin formato")

    def copy_rich_editor(self):
        """Editor: el Markdown seleccionado, convertido a texto con formato."""
        try:
            src = self.editor.get("sel.first", "sel.last")
        except tk.TclError:
            return
        self._copy_md(src)

    def copy_rich_all(self):
        self._copy_md(self.text())

    def _copy_md(self, src):
        lenient = self.renderer._lenient(src)[0] if self.cfg.get("breaks", True) else src
        html = md_to_html(lenient, self.cfg.get("breaks", True))
        plain = re.sub(r"<[^>]+>", "", html.replace("<br />", "\n")).strip()
        rich = set_rich_clipboard(self.root, html, _html.unescape(plain))
        self.flash("Copiado con formato" if rich else "Copiado (sin formato: este sistema no deja más)")

    def show_guide(self):
        if getattr(self, "_guide", None) is not None:
            try:
                if self._guide.top.winfo_exists():
                    self._guide.top.lift()
                    return
            except tk.TclError:
                pass
        self._guide = GuideWindow(self)

    def toggle_breaks(self):
        self.cfg["breaks"] = bool(self.breaks_var.get())
        self.save_cfg()
        self.render_now()

    # -- un poco de edicion desde el lector -----------------------------------------------------
    TASK_RX = re.compile(r"^(\s*(?:>\s*)*(?:[-*+]|\d+[.)])\s+\[)([ xX])(\])")

    def toggle_task(self, line):
        """Clic en una casilla del lector: [ ] <-> [x] en el texto (como cualquier edicion: se guarda con Ctrl+S
        y se deshace con Ctrl+Z)."""
        now = time.time()
        if getattr(self, "_last_toggle", (None, 0))[0] == line and now - self._last_toggle[1] < 0.35:
            return "break"          # el segundo clic de un doble clic no la vuelve a cambiar
        self._last_toggle = (line, now)
        ln = line + 1
        text = self.editor.get("%d.0" % ln, "%d.end" % ln)
        m = self.TASK_RX.match(text)
        if not m:
            return "break"
        col = m.start(2)
        new = " " if m.group(2) in "xX" else "x"
        ed = self.editor
        ed.configure(autoseparators=False)          # borrar + escribir = un solo paso de Ctrl+Z
        try:
            ed.edit_separator()
            ed.delete("%d.%d" % (ln, col), "%d.%d" % (ln, col + 1))
            ed.insert("%d.%d" % (ln, col), new)
            ed.edit_separator()
        finally:
            ed.configure(autoseparators=True)
        self.render_now()
        self.highlight()
        self._update_title()
        return "break"

    def _edit_here(self, e):
        """Doble clic en el lector: el editor, con el cursor en esa parte del Markdown."""
        idx = self.view.index("@%d,%d" % (e.x, e.y))
        if "task" in self.view.tag_names(idx):
            return "break"
        line = self.renderer.line_at(idx) + 1
        if self.mode == "ver":
            self.set_mode("editar")
        ed = self.editor
        ed.mark_set("insert", "%d.0 lineend" % line)
        ed.see("insert")
        ed.focus_set()
        ed.tag_remove("sel", "1.0", "end")
        self.root.after(30, lambda: (ed.see("insert"), ed.focus_set()))
        return "break"

    def _undo_from_view(self, redo=False):
        try:
            (self.editor.edit_redo if redo else self.editor.edit_undo)()
        except tk.TclError:
            return
        self.render_now()
        self.highlight()
        self._update_title()

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
        if getattr(self, "_about", None) is not None:
            try:
                if self._about.top.winfo_exists():
                    self._about.top.lift()
                    return
            except tk.TclError:
                pass
        self._about = AboutDialog(self)

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
    app = App(root, path)
    if sys.platform == "darwin":
        # macOS no pasa el archivo como argumento: lo manda con un evento (doble clic, "Abrir con", arrastrar al icono)
        root.createcommand("::tk::mac::OpenDocument", lambda *paths: paths and app.open_path(paths[0]))
    root.mainloop()


if __name__ == "__main__":
    main()
