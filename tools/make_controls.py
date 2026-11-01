"""assets/controls: Häkchen und Pfeil für das Stylesheet aus der App-Palette erzeugen.

Qt-Stylesheets können beides nicht zeichnen und brauchen Bilder. Jeweils in zwei
Größen; die @2x-Datei nimmt Qt bei Skalierung über 100 % von selbst.
"""
from pathlib import Path

from PIL import Image, ImageDraw

from partfocus.theme import DARK, LIGHT

TARGET = Path(__file__).resolve().parent.parent / "assets" / "controls"
SS = 8  # überabtasten, dann verkleinern: glatte Kanten
CHEVRON = "#8A7F6C"  # auf beiden Papierfeldern über 3:1, darum nur eine Datei


def stroke(size: int, points: list[tuple[float, float]], width: float, colour: str) -> Image.Image:
    """Linie mit runden Enden; Punkte in Anteilen der Kantenlänge."""
    big = size * SS
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    xy = [(x * big, y * big) for x, y in points]
    w = round(width * big)
    d.line(xy, fill=colour, width=w, joint="curve")
    for x, y in (xy[0], xy[-1]):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=colour)
    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    tick = [(0.2, 0.52), (0.42, 0.74), (0.8, 0.28)]
    arrow = [(0.2, 0.36), (0.5, 0.66), (0.8, 0.36)]
    for name, size, points, width, colour in (("check-light", 14, tick, 0.14, LIGHT.on_accent),
                                              ("check-dark", 14, tick, 0.14, DARK.on_accent),
                                              ("chevron", 10, arrow, 0.15, CHEVRON)):
        stroke(size, points, width, colour).save(TARGET / f"{name}.png")
        stroke(size * 2, points, width, colour).save(TARGET / f"{name}@2x.png")
    print("wrote", sorted(p.name for p in TARGET.iterdir()))


if __name__ == "__main__":
    main()
