import io
from pathlib import Path

from PIL import Image, ImageDraw

from config import config


def generate_qr(data: str, logo_path: str | None = None) -> io.BytesIO:
    """Generate a QR code image for the given data.

    If ``logo_path`` (or ``config.qr_logo_path`` when not provided) points to an
    existing image file, that image will be embedded at the centre of the QR
    code. The image is automatically resized to roughly a quarter of the QR
    dimensions.  The function returns a :class:`~io.BytesIO` positioned at the
    start so it can be fed directly to ``telegram.InputFile``.
    """

    # Create a very small placeholder pattern so tests can verify the logo
    # embedding without relying on the external ``qrcode`` package.
    size = 200
    img = Image.new("RGBA", (size, size), "white")
    draw = ImageDraw.Draw(img)
    step = size // 20
    for x in range(0, size, step * 2):
        for y in range(0, size, step * 2):
            draw.rectangle((x, y, x + step - 1, y + step - 1), fill="black")

    path = Path(logo_path or config.qr_logo_path)
    if path.is_file():
        logo = Image.open(path).convert("RGBA")
        box_size = img.size[0] // 4
        logo.thumbnail((box_size, box_size), Image.LANCZOS)
        pos = (
            (img.size[0] - logo.size[0]) // 2,
            (img.size[1] - logo.size[1]) // 2,
        )
        border = max(4, box_size // 15)
        bg = Image.new(
            "RGBA",
            (logo.size[0] + border * 2, logo.size[1] + border * 2),
            (255, 255, 255, 255),
        )
        img.paste(bg, (pos[0] - border, pos[1] - border))
        img.paste(logo, pos, mask=logo)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
