"""assets/partfocus.ico aus der App-Palette erzeugen.

Vier Stimmen als Tonspuren übereinander; drei treten zurück, eine steht hell
im Vordergrund - die Stimme im Fokus. Als Skript, damit sich das Icon bei
geänderter Palette neu erzeugen lässt.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw

from partfocus.theme import LIGHT

SIZES = [16, 24, 32, 48, 64, 128, 256]
ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "assets" / "partfocus.ico"
PREVIEW = ROOT / "assets" / "partfocus.png"
SS = 4  # überabtasten, dann verkleinern: glatte Kanten auch bei 16 px
FOCUS = 1  # die hervorgehobene Spur, von oben gezählt


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    return tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))


def _mix(a, b, t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _stroke(d: ImageDraw.ImageDraw, pts, width: float, colour) -> None:
    """Linie als dicht gesetzte Kreise: gleichmäßig dick, runde Enden, keine Fransen."""
    r = width / 2
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        steps = max(1, int(math.hypot(x1 - x0, y1 - y0) / max(r / 3, 0.5)))
        for k in range(steps + 1):
            x, y = x0 + (x1 - x0) * k / steps, y0 + (y1 - y0) * k / steps
            d.ellipse([x - r, y - r, x + r, y + r], fill=colour)


def draw(size: int) -> Image.Image:
    big = size * SS
    s = big / 256
    accent = _rgb(LIGHT.accent)
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle([0, 0, big - 1, big - 1], int(48 * s), fill=accent)

    white = (255, 255, 255)
    faint = _mix(accent, white, 0.42)
    left, right = 44 * s, 212 * s
    bars = size <= 32  # Wellen verschwimmen klein: dort gerade Balken
    rows = [64, 110, 158, 198]
    for i, y in enumerate(rows):
        focus = i == FOCUS
        colour = white if focus else faint
        y *= s
        if bars:
            width = (30 if focus else 18) * s
            _stroke(d, [(left, y), (right, y)], width, colour)
            continue
        width = (18 if focus else 11) * s
        amp = (16 if focus else 6) * s
        waves = 2.0 if focus else 3.0
        pts = [(left + (right - left) * t / 120,
                y + amp * math.sin(2 * math.pi * waves * t / 120 + i * 1.3) * math.sin(math.pi * t / 120))
               for t in range(121)]
        _stroke(d, pts, width, colour)
    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    frames = [draw(size) for size in SIZES]
    frames[-1].save(TARGET, format="ICO", sizes=[(s, s) for s in SIZES], append_images=frames[:-1])
    frames[-1].save(PREVIEW)
    print("wrote", TARGET, TARGET.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
