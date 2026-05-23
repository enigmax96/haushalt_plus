"""
Generates app/static/icon.png (180x180) for the iOS home screen icon.
Run once on the Pi after deployment:  python generate_icon.py
Requires Pillow:  pip install Pillow
"""
import os
from PIL import Image, ImageDraw, ImageFont

SIZE   = 180
RADIUS = 38
BG     = (146, 64, 14)    # amber-800
FG     = (254, 243, 199)  # amber-50

img  = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=RADIUS, fill=BG + (255,))

font = None
candidates = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
]
for path in candidates:
    if os.path.exists(path):
        font = ImageFont.truetype(path, 72)
        break
if font is None:
    font = ImageFont.load_default()

text = 'H+'
bbox = draw.textbbox((0, 0), text, font=font)
x = (SIZE - (bbox[2] - bbox[0])) // 2 - bbox[0]
y = (SIZE - (bbox[3] - bbox[1])) // 2 - bbox[1]
draw.text((x, y), text, fill=FG, font=font)

out = os.path.join(os.path.dirname(__file__), 'app', 'static', 'icon.png')
rgb = Image.new('RGB', (SIZE, SIZE), BG)
rgb.paste(img, mask=img.split()[3])
rgb.save(out)
print(f'Icon gespeichert: {out}')
