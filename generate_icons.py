"""Generate simple PWA icons for TimeTrack."""
from PIL import Image, ImageDraw, ImageFont
import os

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'icons')
os.makedirs(ICON_DIR, exist_ok=True)

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

for size in SIZES:
    img = Image.new('RGBA', (size, size), (15, 23, 42, 255))  # dark bg
    draw = ImageDraw.Draw(img)

    # Draw a clock-like circle
    margin = size // 8
    cx, cy = size // 2, size // 2
    r = size // 2 - margin

    # Outer ring
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        outline=(99, 102, 241, 255),  # accent indigo
        width=max(size // 20, 2)
    )

    # Clock hands
    lw = max(size // 30, 2)
    # Hour hand (pointing to ~10 o'clock)
    draw.line(
        [(cx, cy), (cx - r * 0.35, cy - r * 0.45)],
        fill=(139, 92, 246, 255),  # purple
        width=lw + 1
    )
    # Minute hand
    draw.line(
        [(cx, cy), (cx + r * 0.15, cy - r * 0.6)],
        fill=(34, 211, 238, 255),  # cyan
        width=lw
    )
    # Center dot
    dot_r = max(size // 25, 2)
    draw.ellipse(
        [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
        fill=(99, 102, 241, 255)
    )

    out = os.path.join(ICON_DIR, f'icon-{size}x{size}.png')
    img.save(out, 'PNG')
    print(f'Generated {out}')

print('Done!')
