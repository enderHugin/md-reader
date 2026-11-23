<!-- NOVEDADES.md -->
# Novedades de md-reader

## 0.1.4 — 2026-11-23
- **Copiar con formato** para pegar en Word, Writer, correo…:
  - En el lector, `Ctrl+C` copia lo seleccionado con su formato (títulos, negrita, cursiva, tachado, listas, casillas, tablas, código, citas, enlaces, imágenes y líneas). Donde no se admite formato (Bloc de notas…) se pega como texto normal.
  - En el editor, `Ctrl+C` sigue copiando el Markdown; con el botón derecho, *Copiar con formato*.
  - *Más ▸ Copiar todo con formato*: el documento entero, listo para pegar.

## 0.1.3 — 2026-11-22
- **Ya no se come saltos de línea.** Cada salto de línea del texto se respeta (como en Obsidian o en los comentarios de GitHub). Una lista numerada se reconoce aunque vaya pegada a una línea de texto o empiece por un número distinto de 1. Para el Markdown estricto: *Más ▸ Respetar los saltos de línea*.
- Los párrafos vuelven a tener su separación.
- **Guía de formatos** (`F1`, o *Más ▸ Guía de formatos*): cada formato con cómo se escribe y cómo se ve.
- **Botón derecho** sobre lo seleccionado, en el editor o en el lector: negrita, cursiva, tachado, código, enlace, títulos, listas, casillas, cita o bloque de código. Si ya lo tiene, lo quita. Se deshace con `Ctrl+Z`.
- `Ctrl+K` en el editor: enlace.

## 0.1.2 — 2026-11-22
- **Un poco de edición en el lector**:
  - Clic en una casilla de tarea (☐/☑) para marcarla o desmarcarla: cambia `[ ]` ↔ `[x]` en el texto, queda «sin guardar» como cualquier edición y se deshace con `Ctrl+Z`.
  - **Doble clic** en cualquier parte del lector: abre el editor con el cursor en esa línea del Markdown (en modo Dual, sin cambiar de modo).

## 0.1.1 — 2026-11-21
- **Abre los .md con doble clic**: el instalador añade md-reader al «Abrir con» de los .md y .markdown (Windows y macOS). En Windows, para que se abran siempre con él: clic derecho ▸ Abrir con ▸ Elegir otra aplicación ▸ md-reader ▸ «Usar siempre».
- En macOS, md-reader abre el archivo con el que lo lanzas (doble clic, «Abrir con» o arrastrándolo al icono).
- El instalador se llama ahora como el programa: md-reader-instalar.cmd / md-reader-instalar-macos.zip.

## 0.1.0 — 2026-11-21
- Primera versión: lee Markdown con formato (títulos, listas, tareas, tablas, código, citas, enlaces, imágenes), en modo claro u oscuro.
- Tres modos: lector, editor (el texto Markdown tal cual) y dual (los dos a la vez; lo que escribes se ve al momento). `Ctrl+E` cambia entre lector y editor.
- Índice lateral, buscar, zoom, recientes, recarga automática si el archivo cambia fuera.
- Instalador de un clic y actualizaciones automáticas (py-installer).
- «Acerca de» con una pequeña demo del modo Dual que se escribe sola, y apoyo en Ko-fi.
- Página propia con demo en vivo, descarga según tu sistema y ES/EN.
