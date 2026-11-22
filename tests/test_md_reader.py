# test_md_reader.py
"""Pruebas de md-reader con una ventana de verdad (en Linux, con xvfb-run).
Uso:  xvfb-run -a python tests/test_md_reader.py"""
import os
import sys
import tempfile
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

root.destroy()
print("TODO OK")
