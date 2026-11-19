"""Изображения для Botanical Spy: безопасная перекодировка (без EXIF/GPS) и объективные пиксельные измерения."""
import base64
import io
import uuid
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

MAX_SIDE = 1568            # рекомендуемый максимум для vision-моделей
MAX_UPLOAD = 10 * 1024 * 1024


class ImageError(ValueError):
    pass


def open_image(data: bytes) -> Image.Image:
    if len(data) > MAX_UPLOAD:
        raise ImageError("Файл больше 10 МБ")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as e:
        raise ImageError("Не удалось прочитать изображение") from e
    return img


def safe_exif(img: Image.Image) -> dict:
    """Только безобидные поля EXIF. GPS и серийные номера сознательно не читаем."""
    out = {}
    try:
        exif = img.getexif()
        sub = exif.get_ifd(ExifTags.IFD.Exif) if exif else {}
    except Exception:  # noqa: BLE001 — повреждённый EXIF не должен ломать расследование
        return out
    dt = sub.get(ExifTags.Base.DateTimeOriginal) or exif.get(ExifTags.Base.DateTime) if exif else None
    if dt:
        try:
            out["taken_at_local"] = datetime.strptime(str(dt), "%Y:%m:%d %H:%M:%S").isoformat()
        except ValueError:
            pass
    flash = sub.get(ExifTags.Base.Flash)
    if flash is not None:
        out["flash_fired"] = bool(int(flash) & 1)
    return out


def normalized(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    return img


def save_clean(img: Image.Image, upload_dir: Path, prefix: str) -> str:
    """Сохраняет перекодированный JPEG без метаданных. Возвращает URL /uploads/..."""
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}-{uuid.uuid4().hex[:10]}.jpg"
    img.save(upload_dir / name, "JPEG", quality=88)
    return f"/uploads/{name}"


def to_base64_jpeg(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return base64.standard_b64encode(buf.getvalue()).decode()


def _pixels(img: Image.Image) -> list:
    getter = getattr(img, "get_flattened_data", None) or img.getdata   # Pillow 13+ / старые версии
    return list(getter())


def pixel_stats(img: Image.Image) -> dict:
    """Объективные измерения по пикселям — это факты о снимке, а не о мире."""
    small = img.copy()
    small.thumbnail((256, 256))
    stat = ImageStat.Stat(small)
    r, g, b = stat.mean
    hsv = small.convert("HSV")
    pixels = _pixels(small)
    hsv_px = _pixels(hsv)
    n = len(pixels)
    green = sum(1 for (h, s, v) in hsv_px if 50 <= h <= 125 and s > 50 and v > 40) / n
    magenta = sum(1 for (h, s, v) in hsv_px if (200 <= h <= 245) and s > 90 and v > 60) / n
    dark = sum(1 for p in pixels if sum(p) / 3 < 40) / n
    blown = sum(1 for p in pixels if min(p) > 245) / n
    gray = small.convert("L")
    brightness = ImageStat.Stat(gray).mean[0]
    contrast = ImageStat.Stat(gray).stddev[0]
    edges = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).var[0]
    sat = ImageStat.Stat(hsv.getchannel("S")).mean[0]
    return {
        "width": img.width, "height": img.height,
        "brightness": round(brightness, 1),        # 0..255
        "contrast": round(contrast, 1),
        "saturation": round(sat, 1),               # 0..255
        "warmth": round(r - b, 1),                 # >0 тёплый, <0 холодный баланс
        "green_share": round(green, 3),
        "magenta_share": round(magenta, 3),        # характерно для фиолетовых фитоламп
        "dark_share": round(dark, 3),
        "overexposed_share": round(blown, 3),
        "sharpness": round(edges, 1),
        "mean_rgb": [round(r), round(g), round(b)],
    }
