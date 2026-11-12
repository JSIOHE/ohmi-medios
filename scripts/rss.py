"""Captura diaria de titulares de medios del sector por RSS.

Lee config/feeds.txt, guarda cada titular nuevo (fecha, medio, titular, enlace, temas)
en data/medios_AAAA-MM.csv y deja un control del lote en data/control_medios.csv.
No resume ni interpreta nada: copia lo que publica el medio. Solo usa la biblioteca estándar.
"""
import csv, datetime, email.utils, os, sys, unicodedata, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMPOS = ["fecha", "medio", "titular", "enlace", "temas", "capturado"]


def lineas(nombre):
    with open(os.path.join(ROOT, "config", nombre), encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def plano(texto):
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def fecha_iso(texto):
    texto = (texto or "").strip()
    if not texto:
        return ""
    try:
        return email.utils.parsedate_to_datetime(texto).date().isoformat()
    except Exception:
        pass
    try:
        return datetime.datetime.fromisoformat(texto.replace("Z", "+00:00")).date().isoformat()
    except Exception:
        return ""


def sin_ns(tag):
    return tag.split("}")[-1]


def leer_feed(xml_bytes):
    """Devuelve [(fecha, titular, enlace)] de un RSS o Atom."""
    raiz = ET.fromstring(xml_bytes)
    salida = []
    for nodo in raiz.iter():
        if sin_ns(nodo.tag) not in ("item", "entry"):
            continue
        titulo = enlace = fecha = ""
        for hijo in nodo:
            nombre = sin_ns(hijo.tag)
            if nombre == "title":
                titulo = " ".join((hijo.text or "").split())
            elif nombre == "link":
                enlace = (hijo.text or "").strip() or hijo.attrib.get("href", "")
            elif nombre in ("pubDate", "published", "updated", "date") and not fecha:
                fecha = fecha_iso(hijo.text)
        if titulo and enlace:
            salida.append((fecha, titulo, enlace))
    return salida


def temas_de(titular, temas):
    t = " " + plano(titular) + " "
    hallados = [nombre for nombre, palabras in temas
                if any((" " + p + " ") in t.replace(",", " ").replace(".", " ").replace(":", " ") for p in palabras)]
    return "|".join(hallados) if hallados else "Sin tema"


def cargar_temas():
    temas = []
    for l in lineas("temas.txt"):
        nombre, palabras = l.split(";", 1)
        temas.append((nombre.strip(), [plano(p.strip()) for p in palabras.split(",") if p.strip()]))
    return temas


def enlaces_guardados(carpeta):
    vistos = set()
    for nombre in os.listdir(carpeta):
        if nombre.startswith("medios_") and nombre.endswith(".csv"):
            with open(os.path.join(carpeta, nombre), encoding="utf-8", newline="") as f:
                for fila in csv.DictReader(f, delimiter=";"):
                    vistos.add(fila["enlace"])
    return vistos


def guardar(carpeta, filas):
    por_mes = {}
    for fila in filas:
        por_mes.setdefault(fila["fecha"][:7], []).append(fila)
    for mes, grupo in por_mes.items():
        ruta = os.path.join(carpeta, "medios_%s.csv" % mes)
        nuevo = not os.path.exists(ruta)
        with open(ruta, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";")
            if nuevo:
                w.writeheader()
            w.writerows(sorted(grupo, key=lambda x: (x["fecha"], x["medio"], x["enlace"])))


def main(descargar=None):
    carpeta = os.path.join(ROOT, "data")
    os.makedirs(carpeta, exist_ok=True)
    temas = cargar_temas()
    vistos = enlaces_guardados(carpeta)
    ahora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    hoy = ahora[:10]
    nuevas, control = [], []
    for l in lineas("feeds.txt"):
        medio, url = [x.strip() for x in l.split(";", 1)]
        try:
            if descargar:
                datos = descargar(url)
            else:
                pet = urllib.request.Request(url, headers={"User-Agent": "ohmi-captura/1.0 (lector RSS)"})
                with urllib.request.urlopen(pet, timeout=30) as r:
                    datos = r.read()
            items = leer_feed(datos)
            n = 0
            for fecha, titulo, enlace in items:
                if enlace in vistos:
                    continue
                vistos.add(enlace)
                nuevas.append({"fecha": fecha or hoy, "medio": medio, "titular": titulo, "enlace": enlace,
                               "temas": temas_de(titulo, temas), "capturado": ahora})
                n += 1
            control.append([ahora, medio, "ok", len(items), n, ""])
        except Exception as e:  # un medio caído no debe parar a los demás
            control.append([ahora, medio, "error", 0, 0, str(e)[:200]])
    guardar(carpeta, nuevas)
    ruta = os.path.join(carpeta, "control_medios.csv")
    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        if nuevo:
            w.writerow(["capturado", "medio", "estado", "titulares_en_feed", "titulares_nuevos", "error"])
        w.writerows(control)
    for c in control:
        print(";".join(str(x) for x in c))
    return 1 if control and all(c[2] == "error" for c in control) else 0


if __name__ == "__main__":
    sys.exit(main())
