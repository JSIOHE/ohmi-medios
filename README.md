# OHMI · titulares de medios del sector energético

Cada día, a las 05:15 UTC, una automatización lee los RSS de los medios de `config/feeds.txt` y guarda en `data/medios_AAAA-MM.csv` la fecha, el medio, el titular, el enlace y el tema de cada titular nuevo. `data/control_medios.csv` registra cuántos titulares dio cada medio y si alguno falló.

Solo guarda titulares y enlaces que los propios medios publican; no guarda el texto de los artículos ni datos personales.

- **Añadir o quitar medios:** `config/feeds.txt` (un medio por línea: `nombre;dirección del RSS`).
- **Cambiar los temas:** `config/temas.txt` (un tema por línea: `tema;palabras separadas por comas`).
