"""Generate deterministic PWA icons for TimeTrack."""
from PIL import Image, ImageDraw, ImageFont
import os

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'icons')
os.makedirs(ICON_DIR, exist_ok=True)

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

BG = (247, 247, 247, 255)
SURFACE = (255, 255, 255, 255)
INK = (36, 36, 36, 255)
MUTED = (222, 222, 222, 255)
ACCENT = (159, 79, 53, 255)


def load_font(size):
    paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
    ]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


for size in SIZES:
    img = Image.new('RGBA', (size, size), BG)
    draw = ImageDraw.Draw(img)
    scale = size / 512

    margin = round(68 * scale)
    radius = round(54 * scale)
    card = [margin, margin, size - margin, size - margin]
    draw.rounded_rectangle(card, radius=radius, fill=SURFACE, outline=MUTED, width=max(round(6 * scale), 1))

    bar_w = max(round(20 * scale), 3)
    bar_x = margin + round(50 * scale)
    bar_y0 = margin + round(76 * scale)
    bar_y1 = size - margin - round(76 * scale)
    draw.rounded_rectangle(
        [bar_x, bar_y0, bar_x + bar_w, bar_y1],
        radius=max(round(10 * scale), 2),
        fill=ACCENT
    )

    font = load_font(round(178 * scale))
    text = 'TT'
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = bar_x + bar_w + round(48 * scale)
    text_y = (size - text_h) / 2 - round(18 * scale)
    draw.text((text_x, text_y), text, font=font, fill=INK)

    underline_y = text_y + text_h + round(24 * scale)
    underline_w = max(text_w - round(12 * scale), round(120 * scale))
    draw.rounded_rectangle(
        [text_x + round(8 * scale), underline_y, text_x + underline_w, underline_y + max(round(10 * scale), 2)],
        radius=max(round(5 * scale), 1),
        fill=ACCENT
    )

    out = os.path.join(ICON_DIR, f'icon-{size}x{size}.png')
    img.save(out, 'PNG')
    print(f'Generated {out}')

print('Done!')
