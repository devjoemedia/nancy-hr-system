"""Employee profile pictures and the company logo (web version).

Pictures are copied into the ``photos`` folder (next to the database),
resized so they never exceed PHOTO_MAX_SIZE, and saved as
``<employee code>.png``. The employees table only stores the file name.

JPEG support needs Pillow:  pip install pillow
"""

import io
import os

from hr.database import APP_DIR

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError:          # the rest of the app still works without it
    Image = ImageDraw = ImageOps = None

PHOTO_DIR = os.path.join(APP_DIR, "photos")
LOGO_NAMES = ("logo.jpeg", "logo.jpg", "logo.png")
PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png")
PHOTO_MAX_SIZE = (400, 400)
AVATAR_COLORS = ["#C0501E", "#2E7D5B", "#3A5A8C", "#B4881C", "#7A3E8C", "#1F7A8C"]
PILLOW_MISSING = "Profile pictures need Pillow. Install it with:  pip install pillow"


class PhotoError(Exception):
    """Raised when a picture cannot be used."""


def photo_path(filename):
    return os.path.join(PHOTO_DIR, filename) if filename else None


def save_photo(source, employee_id, name=None):
    """Copy ``source`` into the photos folder and return the new file name.

    ``source`` is a file path, or an open file (e.g. a web upload) whose
    original file name is given as ``name``.
    """
    if Image is None:
        raise PhotoError(PILLOW_MISSING)
    if not (name or source).lower().endswith(PHOTO_EXTENSIONS):
        raise PhotoError("Please choose a .jpg, .jpeg or .png picture.")
    filename = f"{employee_id}.png"
    if not employee_id or os.path.basename(filename) != filename or ".." in filename:
        raise PhotoError("The employee code can't contain slashes or '..'.")

    try:
        with Image.open(source) as picture:
            # Phone photos store their rotation separately; apply it.
            picture = ImageOps.exif_transpose(picture).convert("RGBA")
    except (OSError, ValueError) as error:
        raise PhotoError(f"Could not open the picture:\n{error}")

    picture.thumbnail(PHOTO_MAX_SIZE)
    os.makedirs(PHOTO_DIR, exist_ok=True)
    picture.save(photo_path(filename), "PNG")
    return filename


def delete_photo(filename):
    path = photo_path(filename)
    if path and os.path.exists(path):
        os.remove(path)


def initials(first_name, last_name):
    """"Kofi Ansah" -> "KA"."""
    return ((first_name or "")[:1] + (last_name or "")[:1]).upper() or "?"


def avatar_color(key, first_name, last_name):
    """A steady background colour for someone's initials."""
    seed = sum(ord(ch) for ch in (key or first_name or "") + (last_name or ""))
    return AVATAR_COLORS[seed % len(AVATAR_COLORS)]


def find_logo(folder=APP_DIR):
    """Return the path of the logo in ``folder`` (any capitalisation), or None."""
    try:
        files = os.listdir(folder)
    except OSError:
        return None
    for wanted in LOGO_NAMES:
        for name in files:
            if name.lower() == wanted:
                return os.path.join(folder, name)
    return None


def logo_png(path, max_size=(640, 640)):
    """The logo as PNG bytes with the plain area around it made transparent.

    Returns ``None`` if Pillow is missing or the file can't be read.
    """
    if Image is None:
        return None
    try:
        with Image.open(path) as picture:
            picture = picture.convert("RGBA")
    except (OSError, ValueError):
        return None

    width, height = picture.size
    for corner in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        ImageDraw.floodfill(picture, corner, (0, 0, 0, 0), thresh=40)
    picture.thumbnail(max_size, Image.LANCZOS)

    buffer = io.BytesIO()
    picture.save(buffer, "PNG")
    return buffer.getvalue()
