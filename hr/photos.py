"""Employee profile pictures.

Pictures are copied into the ``photos`` folder (next to the database),
resized so they never exceed PHOTO_MAX_SIZE, and saved as
``<employee code>.png``. The employees table only stores the file name.

JPEG support needs Pillow:  pip install pillow
"""

import math
import os

from hr.database import APP_DIR

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk
except ImportError:          # the rest of the app still works without it
    Image = ImageDraw = ImageFont = ImageOps = ImageTk = None

PHOTO_DIR = os.path.join(APP_DIR, "photos")
LOGO_NAMES = ("logo.jpeg", "logo.jpg", "logo.png")
PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png")
PHOTO_MAX_SIZE = (400, 400)
AVATAR_COLORS = ["#C0501E", "#2E7D5B", "#3A5A8C", "#B4881C", "#7A3E8C", "#1F7A8C"]
PILLOW_AVAILABLE = Image is not None
PILLOW_MISSING = "Profile pictures need Pillow. Install it with:  pip install pillow"


class PhotoError(Exception):
    """Raised when a picture cannot be used."""


def photo_path(filename):
    return os.path.join(PHOTO_DIR, filename) if filename else None


def save_photo(source, employee_id):
    """Copy ``source`` into the photos folder and return the new file name."""
    if Image is None:
        raise PhotoError(PILLOW_MISSING)
    if not source.lower().endswith(PHOTO_EXTENSIONS):
        raise PhotoError("Please choose a .jpg, .jpeg or .png picture.")

    try:
        with Image.open(source) as picture:
            # Phone photos store their rotation separately; apply it.
            picture = ImageOps.exif_transpose(picture).convert("RGBA")
    except (OSError, ValueError) as error:
        raise PhotoError(f"Could not open the picture:\n{error}")

    picture.thumbnail(PHOTO_MAX_SIZE)
    os.makedirs(PHOTO_DIR, exist_ok=True)
    filename = f"{employee_id}.png"
    picture.save(photo_path(filename), "PNG")
    return filename


def delete_photo(filename):
    path = photo_path(filename)
    if path and os.path.exists(path):
        os.remove(path)


def load_thumbnail(path, size):
    """Return a Tk image of the picture at ``path`` fitted inside ``size``.

    Returns ``None`` when there is no picture or it cannot be read.
    Keep a reference to the result, or Tk will discard the image.
    """
    if Image is None or not path or not os.path.exists(path):
        return None
    try:
        with Image.open(path) as picture:
            picture = picture.convert("RGBA")
    except (OSError, ValueError):
        return None
    picture.thumbnail(size)
    return ImageTk.PhotoImage(picture)


def initials(first_name, last_name):
    """"Kofi Ansah" -> "KA"."""
    return ((first_name or "")[:1] + (last_name or "")[:1]).upper() or "?"


def _avatar_font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:            # Pillow older than 10.1
        return ImageFont.load_default()


def make_avatar(filename, first_name, last_name, size=36, key=""):
    """Return a round Tk image: the employee's photo, or their initials.

    ``key`` (e.g. the employee code) picks a steady background colour for
    the initials. Returns ``None`` when Pillow is not installed.
    Keep a reference to the result, or Tk will discard the image.
    """
    if Image is None:
        return None

    big = size * 3               # draw large, then shrink for smooth edges
    picture = None
    path = photo_path(filename)
    if path and os.path.exists(path):
        try:
            with Image.open(path) as img:
                picture = ImageOps.fit(img.convert("RGBA"), (big, big))
            # Put see-through PNGs on white before cutting the circle.
            picture = Image.alpha_composite(
                Image.new("RGBA", (big, big), "white"), picture)
        except (OSError, ValueError):
            picture = None

    if picture is None:
        seed = sum(ord(ch) for ch in (key or first_name or "") + (last_name or ""))
        picture = Image.new("RGBA", (big, big), AVATAR_COLORS[seed % len(AVATAR_COLORS)])
        ImageDraw.Draw(picture).text(
            (big / 2, big / 2), initials(first_name, last_name),
            fill="white", font=_avatar_font(int(big * 0.42)), anchor="mm")

    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, big - 1, big - 1), fill=255)
    picture.putalpha(mask)
    return ImageTk.PhotoImage(picture.resize((size, size), Image.LANCZOS))


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


def load_logo(max_size, background):
    """Return ``(image, problem)`` for the company logo.

    ``image`` is a Tk image or ``None``; when it is ``None``, ``problem``
    says why, so it can be shown on screen. With Pillow, the plain area
    around the logo is filled with ``background`` so it blends into the page.
    """
    path = find_logo()
    if path is None:
        return None, ("Logo not shown: put logo.jpeg (or logo.jpg / logo.png) in\n"
                      + APP_DIR)
    name = os.path.basename(path)

    if Image is None:
        if not name.lower().endswith(".png"):
            return None, ("Logo not shown: JPEG logos need Pillow.\n"
                          "Install it with:  pip install pillow")
        import tkinter as tk
        try:
            picture = tk.PhotoImage(file=path)
        except tk.TclError:
            return None, f"Logo not shown: {name} could not be opened."
        shrink = math.ceil(max(picture.width() / max_size[0],
                               picture.height() / max_size[1], 1))
        return picture.subsample(shrink), None

    try:
        with Image.open(path) as picture:
            picture = picture.convert("RGB")
    except (OSError, ValueError):
        return None, f"Logo not shown: {name} could not be opened."

    fill = Image.new("RGB", (1, 1), background).getpixel((0, 0))
    width, height = picture.size
    for corner in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        ImageDraw.floodfill(picture, corner, fill, thresh=40)

    picture.thumbnail(max_size, Image.LANCZOS)
    return ImageTk.PhotoImage(picture), None
