# test_md_reader.py
"""Pruebas de md-reader con una ventana de verdad (en Linux, con xvfb-run).
Uso:  xvfb-run -a python tests/test_md_reader.py"""
import os
import sys
import tempfile
import re
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
TMP = tempfile.mkdtemp(prefix="mdr-test-")
os.environ["APPDATA"] = os.environ["XDG_CONFIG_HOME"] = os.path.join(TMP, "cfg")

import tkinter as tk                      # noqa: E402
from tkinter import messagebox            # noqa: E402
import md_reader                          # noqa: E402


def ok(c, m):
    if not c:
        sys.exit("FALLO: " + m)
    print("ok -", m)


def pump(root, ms=60):
    end = time.time() + ms / 1000.0
    while time.time() < end:
        root.update()
        time.sleep(0.01)


DOC = "# Hola\r\n\r\nTexto con **negrita** y un [salto](#segunda).\r\n\r\n" + "relleno\r\n\r\n" * 60 + "## Segunda\r\n\r\n| a | b |\r\n|---|---|\r\n| 1 | 2 |\r\n"
p = os.path.join(TMP, "doc.md")
with open(p, "wb") as f:
    f.write(b"\xef\xbb\xbf" + DOC.encode("utf-8"))

root = tk.Tk()
root.geometry("900x600")
app = md_reader.App(root, p)
pump(root, 300)

view = app.view.get("1.0", "end")
ok("Hola" in view and "**" not in view, "abre y da formato (sin los asteriscos)")
i = app.view.search("negrita", "1.0")
ok(any(t.startswith("f_s_") and t.split("_")[3] == "1" for t in app.view.tag_names(i)), "la negrita sale en negrita")
ok([h[1] for h in app.renderer.headings] == ["Hola", "Segunda"], "titulos detectados para el indice")
ok(not app.dirty(), "recien abierto, sin cambios")
ok(app.newline == "\r\n" and app._bom, "detecta saltos de Windows y BOM")

# enlace a una seccion
app.view.yview_moveto(0)
app.follow_link("#segunda")
pump(root)
ok(app.view.index("@0,0").split(".")[0] != "1", "el enlace #segunda baja hasta la seccion")

# editar en modo dividido: la vista se actualiza
app.set_mode("dividido")
app.editor.insert("end", "\nNuevo parrafo añadido\n")
pump(root, 400)
ok("Nuevo parrafo añadido" in app.view.get("1.0", "end"), "editar actualiza la vista")
ok(app.dirty() and "•" in root.title(), "marca cambios sin guardar en el titulo")

# guardar: mismo formato de archivo
ok(app.save(), "guardar")
raw = open(p, "rb").read()
ok(raw.startswith(b"\xef\xbb\xbf") and b"\r\n" in raw and b"\n\n" not in raw.replace(b"\r\n", b""), "conserva BOM y saltos de Windows")
ok("Nuevo parrafo añadido" in raw.decode("utf-8-sig"), "guarda el texto")
ok(not app.dirty() and "•" not in root.title(), "tras guardar, sin cambios pendientes")

# cambio fuera del programa: se recarga solo
time.sleep(0.05)
with open(p, "w", encoding="utf-8") as f:
    f.write("# Cambiado fuera\n")
os.utime(p, None)
pump(root, 1500)
ok("Cambiado fuera" in app.text() and "Cambiado fuera" in app.view.get("1.0", "end"), "recarga si cambia fuera")

# cambio fuera con cambios sin guardar: avisa, no pisa
app.editor.insert("end", "mio\n")
pump(root, 100)
time.sleep(0.05)
with open(p, "w", encoding="utf-8") as f:
    f.write("# Otra vez\n")
pump(root, 1500)
ok("mio" in app.text() and app.notice.winfo_ismapped(), "con cambios sin guardar, avisa en vez de recargar")
app._hide_notice()

# buscar
app.set_mode("ver")
app.open_find()
app.find_var.set("cambiado")
pump(root)
ok(len(app._find_hits) == 1 and "1 de 1" in app.find_info.cget("text"), "buscar")
app.close_find()

# tema y zoom
app.set_theme("oscuro")
ok(app.view.cget("bg") == md_reader.THEMES["oscuro"]["doc_bg"], "tema oscuro")
app.set_theme("claro")
ok(app.view.cget("bg") == md_reader.THEMES["claro"]["doc_bg"], "tema claro")
app.set_zoom(1.5)
ok(abs(app.zoom - 1.5) < 1e-6, "zoom")
app.set_zoom(1.0)

# Ctrl+E: lector <-> editor
app.set_mode("ver"); app.toggle_edit()
ok(app.mode == "editar", "Ctrl+E pasa del lector al editor")
app.toggle_edit()
ok(app.mode == "ver", "y vuelve al lector")

# Ctrl+B en el editor: envuelve la seleccion en ** (y no hace lo de tkinter)
app.set_mode("editar")
app.editor.delete("1.0", "end")
app.editor.insert("1.0", "palabra")
app.editor.tag_add("sel", "1.0", "1.7")
app.editor.focus_force()
app.wrap_sel("**")
ok(app.text() == "**palabra**", "negrita con Ctrl+B")

# documento nuevo y "descartar": sin dialogos de verdad
messagebox.askyesnocancel = lambda *a, **k: False
app.new()
ok(app.text() == "" and app.path is None, "documento nuevo")

# documento raro: no debe romper la vista
app.set_mode("ver")
app.editor.insert("1.0", "<div>html</div>\n\n- [ ] tarea\n  1. dentro\n\n> cita\n> > anidada\n\n![no existe](nada.png)\n\n```\n```\n")
app.render_now()
ok("tarea" in app.view.get("1.0", "end") and "☐" in app.view.get("1.0", "end"), "html, tareas, listas y citas anidadas, imagen que falta")
# un poco de edicion desde el lector: casillas y doble clic
app.set_mode("ver")
src = "# Tareas\n\nIntro.\n\n- [ ] uno\n- [x] dos\n\n> - [ ] en cita\n\nFinal del texto.\n"
app.editor.delete("1.0", "end")
app.editor.insert("1.0", src)
app.saved_text = src
app.render_now()
pump(root, 200)
tasks = sorted(t for t in app.view.tag_names() if t.startswith("task_"))
ok(tasks == ["task_4", "task_5", "task_7"], "casillas clicables con su linea del Markdown (%s)" % tasks)


def click_tag(tag):
    a = app.view.tag_ranges(tag)[0]
    x, y, w, h = app.view.bbox(a)
    app.view.event_generate("<Motion>", x=x + w // 2, y=y + h // 2)
    app.view.event_generate("<Button-1>", x=x + w // 2, y=y + h // 2)
    app.view.event_generate("<ButtonRelease-1>", x=x + w // 2, y=y + h // 2)
    pump(root, 120)


click_tag("task_4")
ok(app.text().splitlines()[4] == "- [x] uno", "clic en ☐ la marca en el texto")
ok("☑" in app.view.get("1.0", "end") and app.dirty(), "se ve marcada y queda sin guardar")
time.sleep(0.4)
click_tag("task_5")
ok(app.text().splitlines()[5] == "- [ ] dos", "clic en ☑ la desmarca")
time.sleep(0.4)
click_tag("task_7")
ok(app.text().splitlines()[7] == "> - [x] en cita", "tambien dentro de una cita")
app._undo_from_view()
ok(app.text().splitlines()[7] == "> - [ ] en cita", "Ctrl+Z desde el lector la deshace")

i = app.view.search("Final del texto", "1.0")
x, y, w, h = app.view.bbox(i)
app._edit_here(type("E", (), {"x": x + 5, "y": y + h // 2})())     # Tk no deja simular un doble clic
pump(root, 150)
ok(app.mode == "editar" and app.editor.index("insert").split(".")[0] == "10", "doble clic: al editor, en esa linea (%s)" % app.editor.index("insert"))

# saltos de linea y listas "como se escriben"
app.set_mode("ver")
src = "Primera linea\nsegunda linea\n\n**Titulo**\n3. tres\n4. cuatro\n"
app.editor.delete("1.0", "end")
app.editor.insert("1.0", src)
app.render_now()
v = app.view.get("1.0", "end")
ok("Primera linea\nsegunda linea" in v, "un salto simple se respeta")
ok("3.\ttres" in v and "Titulo\n" in v, "una lista que empieza en 3, pegada al texto, se reconoce")
ok(any(t.startswith("li_") for t in app.view.tag_names(app.view.search("tres", "1.0"))), "y se pinta como lista")
app.cfg["breaks"] = False
app.render_now()
v = app.view.get("1.0", "end")
ok("Primera linea segunda linea" in v and "Titulo 3. tres" in v, "en Markdown estricto, como CommonMark")
app.cfg["breaks"] = True
src = "Parrafo uno.\n\nParrafo dos.\n"
app.editor.delete("1.0", "end")
app.editor.insert("1.0", src)
app.render_now()
ok(app.view.get("1.0", "end").startswith("Parrafo uno.\n\nParrafo dos"), "los parrafos tienen su separacion")

# casillas con el mapa de lineas (lista pegada a un texto)
src = "Tareas\n2. [ ] dos\n3. [ ] tres\n"
app.editor.delete("1.0", "end")
app.editor.insert("1.0", src)
app.render_now()
tasks = sorted(t for t in app.view.tag_names() if t.startswith("task_"))
ok(tasks == ["task_1", "task_2"], "casillas en su linea aunque se anada una linea al pintar (%s)" % tasks)
app.toggle_task(2)
ok(app.text().splitlines()[2] == "3. [x] tres", "y se marcan en su sitio")

# formatos
app.set_mode("editar")
app.editor.delete("1.0", "end")
app.editor.insert("1.0", "hola mundo")
app.editor.tag_add("sel", "1.5", "1.10")
app.fmt_inline("**")
ok(app.text() == "hola **mundo**", "negrita")
app.fmt_inline("**")
ok(app.text() == "hola mundo", "y quitarla")
app.editor.tag_remove("sel", "1.0", "end")
app.editor.tag_add("sel", "1.0", "1.5")
app.fmt_inline("~~")
ok(app.text() == "~~hola~~ mundo", "tachado (sin el espacio del borde)")
app.editor.edit_undo()
ok(app.text() == "hola mundo", "Ctrl+Z en un paso")
app.editor.delete("1.0", "end")
app.editor.insert("1.0", "uno\ndos\ntres")
app.editor.tag_add("sel", "1.0", "3.4")
app.fmt_lines("ol")
ok(app.text() == "1. uno\n2. dos\n3. tres", "lista numerada")
app.fmt_lines("task")
ok(app.text() == "- [ ] uno\n- [ ] dos\n- [ ] tres", "casillas (cambia de tipo de lista)")
app.fmt_lines("task")
ok(app.text() == "uno\ndos\ntres", "y quitarlas")
app.editor.tag_remove("sel", "1.0", "end")
app.editor.mark_set("insert", "2.1")
app.fmt_lines("h2")
ok(app.text().splitlines()[1] == "## dos", "titulo en la linea del cursor")
app.editor.tag_remove("sel", "1.0", "end")
app.editor.tag_add("sel", "1.0", "1.3")
app.fmt_link()
ok(app.text().splitlines()[0] == "[uno](https://)" and app.editor.get("sel.first", "sel.last") == "https://", "enlace, con la direccion lista para escribirla")

# formato desde el lector: lo seleccionado se encuentra en el Markdown
app.set_mode("ver")
app.editor.delete("1.0", "end")
app.editor.insert("1.0", "# Titulo\n\nUn texto con palabras para marcar.\n")
app.render_now()
i = app.view.search("palabras", "1.0")
app.view.tag_add("sel", i, "%s+8c" % i)
x, y, w, h = app.view.bbox(i)
okin, l1, l2 = app._map_view_selection(type("E", (), {"x": x, "y": y})())
ok(okin and app.editor.get("sel.first", "sel.last") == "palabras" and l1 == 3, "lector: encuentra lo seleccionado en el Markdown")
app.fmt_inline("*")
ok("con *palabras* para" in app.text() and "palabras" in app.view.get("1.0", "end") and "*" not in app.view.get("1.0", "end"), "lector: cursiva aplicada y pintada")
i = app.view.search("Titulo", "1.0")
x, y, w, h = app.view.bbox(i)
app.view.tag_remove("sel", "1.0", "end")
okin, l1, l2 = app._map_view_selection(type("E", (), {"x": x + 2, "y": y + 2})())
app.fmt_lines("h3", l1, l2)
ok(app.text().splitlines()[0] == "### Titulo", "lector: cambiar el nivel de un titulo")

# copiar con formato
src = "# Titulo\n\nTexto con **negrita** y *cursiva* y [enlace](https://example.com).\n\n- uno\n- [x] hecha\n  - dentro\n\n| a | b |\n|---|---|\n| 1 | `2` |\n\n```\nx = 1\n```\n"
app.set_mode("ver")
app.editor.delete("1.0", "end")
app.editor.insert("1.0", src)
app.render_now()
h, plain = md_reader.html_from_view(app.view, "1.0", "end-1c", app.renderer.links, images=app.renderer.image_paths)
ok(h.startswith("<h1>Titulo</h1>\n<hr>"), "copiar: titulo, con su linea debajo")
ok("<b>negrita</b>" in h and "<i>cursiva</i>" in h and '<a href="https://example.com">enlace</a>' in h, "copiar: negrita, cursiva, enlace")
ok("<ul>\n<li>uno" in h and "<li>☑ hecha" in h and h.count("<ul>") == 2, "copiar: listas anidadas y casillas (sin las vinetas pintadas)")
ok("<table" in h and "<th " in h and "<code" in h and "<pre" in h and "x = 1" in h, "copiar: tabla y codigo")
i = app.view.search("negrita", "1.0")
h2, p2 = md_reader.html_from_view(app.view, i, "%s+12c" % i, app.renderer.links)
ok(h2 == "<p><b>negrita</b> y *</p>".replace(" *", " ") or h2.startswith("<p><b>negrita</b>"), "copiar medio parrafo: solo lo seleccionado (%s)" % h2)
ok(p2 == "negrita y cu", "y el texto normal (%r)" % p2)
cf = md_reader.cf_html("<b>ñ</b>")
hdr = cf.decode("utf-8")
sf, ef = int(re.search(r"StartFragment:(\d+)", hdr).group(1)), int(re.search(r"EndFragment:(\d+)", hdr).group(1))
sh, eh = int(re.search(r"StartHTML:(\d+)", hdr).group(1)), int(re.search(r"EndHTML:(\d+)", hdr).group(1))
ok(cf[sf:ef] == "<b>ñ</b>".encode("utf-8") and cf[sh:sh + 6] == b"<html>" and eh == len(cf), "formato HTML del portapapeles de Windows (posiciones en bytes)")
mh = md_reader.md_to_html("**a**\n- [ ] b\n")
ok("<strong>a</strong>" in mh and "☐ b" in mh, "copiar desde el editor: Markdown a HTML")

# HTML dentro del Markdown
app.editor.delete("1.0", "end")
app.editor.insert("1.0", '<!-- oculto -->\nTexto <span style="color:red">rojo</span> y <del>fuera **b**</del> H<sub>2</sub>O<br>sigue\n\n<div align="center">Centro <b>x</b></div>\n')
app.render_now()
pump(root, 100)
v = app.view.get("1.0", "end")
rr = app.view.tag_ranges("hc_ff0000")
ok("oculto" not in v and "<span" not in v and "<del" not in v, "HTML: las etiquetas y comentarios no se ven")
ok(rr and app.view.get(rr[0], rr[1]) == "rojo", "HTML: color en linea")
st = app.view.tag_ranges("s")
ok(st and "fuera" in app.view.get(st[0], st[-1]), "HTML: <del> tacha")
ok("\nsigue" in v and app.view.tag_ranges("sub"), "HTML: <br> y <sub>")
cr = app.view.tag_ranges("center")
ok(cr and "Centro" in app.view.get(cr[0], cr[1]), "HTML: bloque centrado")
h, _ = md_reader.html_from_view(app.view, "1.0", "end", app.renderer.links)
ok('color:#ff0000' in h and "<s>" in h and "text-align:center" in h, "HTML: se copia con color y centrado")

# pegar con formato (Word, Writer, Google Docs, web) -> Markdown
H2M = md_reader.html_to_md
word = ("<p class=MsoNormal>Hola <b>negrita</b> <span style='color:red'>rojo</span><o:p></o:p></p>"
        "<p class=MsoListParagraph style='mso-list:l0 level1 lfo1'><![if !supportLists]><span style='mso-list:Ignore'>·<span>&nbsp; </span></span><![endif]>uno</p>"
        "<p class=MsoListParagraph style='mso-list:l0 level2 lfo1'><![if !supportLists]><span style='mso-list:Ignore'>o<span>&nbsp; </span></span><![endif]>dos</p>")
ok(H2M(word) == 'Hola **negrita** <span style="color:red">rojo</span>\n\n- uno\n    - dos', "pegar de Word: parrafo, color y lista con niveles")
ok(H2M('<b style="font-weight:normal" id="docs-internal-guid-1"><h2><span style="font-weight:400">S</span></h2><p><span style="font-weight:700">F</span> n</p></b>') == "## S\n\n**F** n", "pegar de Google Docs")
ok(H2M("<table><tr><td>a</td><td>b</td></tr><tr><td>1|2</td><td>x</td></tr></table>") == "| a | b |\n|---|---|\n| 1\\|2 | x |", "pegar una tabla")
ok(H2M("<p>5 * 3 y - no</p><p>1. no</p>") == "5 \\* 3 y - no\n\n1\\. no", "pegar: lo que no es Markdown no se vuelve Markdown")
src = "# T\n\nTexto **b** y *i* ~~s~~ `c` [l](https://a.b)\n\n- [ ] tarea\n- [x] hecha\n\n1. uno\n2. dos\n\n> cita\n\n| a | b |\n|---|---|\n| 1 | 2 |"
ok(H2M(md_reader.md_to_html(src, True)) == src, "copiar con formato y volver a pegar: el mismo Markdown")
ok(md_reader.cf_html_fragment(md_reader.cf_html("<b>ñ</b>")) == "<b>ñ</b>", "leer el HTML del portapapeles de Windows")
real = md_reader.get_clipboard_html
md_reader.get_clipboard_html = lambda r: "<p>Pegado <i>it</i></p>"
app.editor.delete("1.0", "end")
app.editor.insert("1.0", "antes\n")
app.editor.mark_set("insert", "end-1c")
app.editor.event_generate("<<Paste>>")
pump(root, 50)
ok(app.text() == "antes\nPegado *it*" and "Pegado it" in app.view.get("1.0", "end"), "Ctrl+V en el editor: entra como Markdown")
app.editor.edit_undo()
pump(root, 30)
ok(app.text() == "antes\n", "y se deshace de una vez")
app.view.mark_set("insert", "1.0")
app.paste_rich(from_view=True)
pump(root, 50)
ok(app.text().startswith("antes\n\nPegado *it*"), "pegar desde el lector: detras del bloque")
md_reader.get_clipboard_html = lambda r: None
root.clipboard_clear(); root.clipboard_append("**solo texto**")
app.editor.delete("1.0", "end")
app.editor.event_generate("<<Paste>>")
pump(root, 30)
ok(app.text().strip() == "**solo texto**", "sin formato en el portapapeles: se pega el texto tal cual")
md_reader.get_clipboard_html = real

# guia
app.show_guide()
pump(root, 200)
g = app._guide
ok(g.top.winfo_exists() and "Guía de formatos" in g.t.get("1.0", "end") and len(g.r.headings) > 8, "guia de formatos (F1)")
g.top.destroy()

root.destroy()
print("TODO OK")
