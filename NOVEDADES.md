<!-- NOVEDADES.md -->
# Novedades de md-reader

## 0.2.0 — 2026-11-26
- **Transcripciones desde subtítulos.** *Más → Importar subtítulos* lee `.srt`, `.vtt` o texto con `[hh:mm:ss] HABLANTE texto`, reconoce a los hablantes y puede juntar lo que alguien dice seguido y dejar margen.
- **Estilo de la transcripción**: tiempo, hablante y texto con su color, resaltado, fuente, tamaño, negrita, cursiva, subrayado y mayúsculas; cada opción **para todos o por hablante**. La colocación (salto tras el tiempo, sangría, separador, margen) es la misma para todas las intervenciones. Un cambio se ve al momento en toda la transcripción y se deshace con un solo Ctrl+Z.
- El lector entiende un bloque `<style>` con clases dentro del documento (color, fuente, tamaño, margen, ocultar, mayúsculas), y copiar con formato lleva también fuentes, tamaños y márgenes.

## 0.1.10 — 2026-11-24
- **Actualizador común de py-installer 1.3.0**, el mismo que cam-ui y widget-arena: misma ventana de Actualizaciones (con novedades, «volver a la versión anterior» y, abajo, la versión del actualizador), mismo «avisar al abrir», «actualizar sin preguntar» y «vigilar sola», y el mismo atajo secreto **Ctrl+Shift+Alt+F12** desde cualquier ventana.
- Nunca se reinicia para actualizarse con cambios sin guardar: espera a que guardes.

## 0.1.9 — 2026-11-24
- El atajo secreto de las actualizaciones, **Ctrl+Shift+Alt+F12** (con o sin la tecla Win), funciona desde la ventana principal: abre «Actualizaciones» con la casilla «Vigilar sola, sin avisos» ya visible. Antes solo valía con esa ventana delante.

## 0.1.8 — 2026-11-23
- En el lector, el **doble clic ya no cambia al editor**: selecciona la palabra, como en cualquier lector. Para editar en ese sitio, `Ctrl+E`.

## 0.1.7 — 2026-11-23
- Copiar con formato a Writer (y Word): la línea bajo los títulos y las líneas `---` salen finas, ya no dobles y gruesas.
- Los títulos copiados mantienen la negrita y su tamaño.

## 0.1.6 — 2026-11-23
- **Pegar desde Word, Writer, Google Docs o una web.** `Ctrl+V` convierte lo copiado en Markdown: títulos, negrita, cursiva, subrayado, tachado, colores, resaltado, listas (también las de Word, con sus niveles), casillas, tablas, citas, código y enlaces. Funciona en el editor y también en el lector (lo pegado va detrás del párrafo donde estás).
- `Ctrl+Shift+V` pega solo el texto, sin convertir.
- Copiar con formato y volver a pegar deja el mismo Markdown.

## 0.1.5 — 2026-11-23
- **HTML dentro del Markdown.** `<span style="color:red">`, `<del>`, `<u>`, `<mark>`, `<sub>`, `<sup>`, `<br>`, `<div align="center">`… ya se ven con su formato en lugar de las etiquetas. Los comentarios `<!-- -->` no se muestran. Nada se ejecuta (ni scripts ni estilos de página).
- Copiar con formato conserva los colores, el subrayado y el centrado.
- En el editor, las etiquetas HTML salen en gris.

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
