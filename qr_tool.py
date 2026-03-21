from __future__ import annotations
import os
import re
import sys
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional
import math
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    CircleModuleDrawer,
    RoundedModuleDrawer,
    SquareModuleDrawer,
)
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageColor

# ─────────────────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────────────────
VERSION    = "1.1.0"
OUTPUT_DIR = Path("qr_output")
DIVIDER    = "─" * 52
HEAVY      = "═" * 52

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────
#  Enums
# ─────────────────────────────────────────────────────────

class QRStyle(Enum):
    SQUARE  = "square"
    ROUNDED = "rounded"
    CIRCLE  = "circle"

    @classmethod
    def choices(cls) -> list[str]:
        return [m.value.capitalize() for m in cls]


class QRColor(Enum):
    # (label, fill, background)
    BLACK          = ("Black",          "black",   "white")
    BLUE           = ("Blue",           "#1a73e8", "white")
    RED            = ("Red",            "#e53935", "white")
    GREEN          = ("Green",          "#2e7d32", "white")
    PURPLE         = ("Purple",         "#6a1b9a", "white")
    WHITE_ON_BLACK = ("White on Black", "white",   "black")

    def __init__(self, label: str, fill: str, back: str) -> None:
        self.label = label
        self.fill  = fill
        self.back  = back

    @classmethod
    def choices(cls) -> list[str]:
        return [m.label for m in cls]


# ─────────────────────────────────────────────────────────
#  QR Config
# ─────────────────────────────────────────────────────────

@dataclass
class QRConfig:
    """All parameters needed to render one QR code image."""

    data      : str
    filename  : str
    style     : QRStyle          = QRStyle.SQUARE
    color     : QRColor          = QRColor.BLACK
    logo_path : Optional[Path]   = None
    box_size  : int              = 10
    border    : int              = 4

    @property
    def output_path(self) -> Path:
        return OUTPUT_DIR / self.filename


# ─────────────────────────────────────────────────────────
#  QR Generator
# ─────────────────────────────────────────────────────────

class QRGenerator:
    _DRAWER_MAP: dict[QRStyle, type] = {
        QRStyle.SQUARE  : SquareModuleDrawer,
        QRStyle.ROUNDED : RoundedModuleDrawer,
        QRStyle.CIRCLE  : CircleModuleDrawer,
    }

    # Logo display constants
    _LOGO_MAX_PX    : int   = 200    # cap logo longest side at this many pixels
    _LOGO_ZONE_RATIO: float = 0.28   # logo zone <= 28 % of QR width (H = 30 % tolerance)
    _LOGO_PADDING   : int   = 12     # solid bg padding around logo (px)

    @classmethod
    def build(cls, cfg: QRConfig) -> Path:
        # ── Step 1: dry-run to learn module count ────────────────────────────
        qr_probe = qrcode.QRCode(
            version          = 1,
            error_correction = qrcode.constants.ERROR_CORRECT_H,
            box_size         = 1,           # size irrelevant for probe
            border           = cfg.border,
        )
        qr_probe.add_data(cfg.data)
        qr_probe.make(fit=True)

        # Total modules across one axis (data + 2 × border)
        modules = qr_probe.modules_count + cfg.border * 2

        # ── Step 2: compute box_size ──────────────────────────────────────────
        box_size = cfg.box_size   # default (no logo)

        if cfg.logo_path and cfg.logo_path.exists():
            with Image.open(cfg.logo_path) as raw_logo:
                lw, lh = raw_logo.size

            # Cap logo at _LOGO_MAX_PX on its longest side
            scale    = min(1.0, cls._LOGO_MAX_PX / max(lw, lh))
            logo_w   = int(lw * scale)
            logo_h   = int(lh * scale)

            # Zone = logo + padding on every side
            zone_px  = max(logo_w, logo_h) + cls._LOGO_PADDING * 2

            # QR must be wide enough so zone / qr_width <= _LOGO_ZONE_RATIO
            min_qr_px = zone_px / cls._LOGO_ZONE_RATIO
            box_size  = max(cfg.box_size, math.ceil(min_qr_px / modules))

        # ── Step 3: render at final box_size ─────────────────────────────────
        qr = qrcode.QRCode(
            version          = qr_probe.version,
            error_correction = qrcode.constants.ERROR_CORRECT_H,
            box_size         = box_size,
            border           = cfg.border,
        )
        qr.add_data(cfg.data)
        qr.make(fit=True)

        img = cls._render(qr, cfg)

        if cfg.logo_path and cfg.logo_path.exists():
            img = cls._embed_logo(
                img,
                cfg.logo_path,
                back_color = cfg.color.back,
                max_px     = cls._LOGO_MAX_PX,
                padding    = cls._LOGO_PADDING,
            )

        img.save(cfg.output_path)
        return cfg.output_path

    # --------------------------------------------------

    @classmethod
    def _render(cls, qr: qrcode.QRCode, cfg: QRConfig) -> Image.Image:
        from PIL import ImageOps

        fill_rgb = ImageColor.getrgb(cfg.color.fill)
        back_rgb = ImageColor.getrgb(cfg.color.back)
        WHITE    = (255, 255, 255)
        BLACK    = (0,   0,   0  )

        if fill_rgb == WHITE and back_rgb == BLACK:
            color_mask = SolidFillColorMask(front_color=BLACK, back_color=WHITE)
            img = qr.make_image(
                image_factory = StyledPilImage,
                module_drawer = cls._DRAWER_MAP[cfg.style](),
                color_mask    = color_mask,
            ).convert("RGB")
            return ImageOps.invert(img)

        color_mask = SolidFillColorMask(front_color=fill_rgb, back_color=back_rgb)
        return qr.make_image(
            image_factory = StyledPilImage,
            module_drawer = cls._DRAWER_MAP[cfg.style](),
            color_mask    = color_mask,
        ).convert("RGB")

    @staticmethod
    def _embed_logo(
        qr_img    : Image.Image,
        logo_path : Path,
        back_color: str = "white",
        max_px    : int = 200,
        padding   : int = 12,
    ) -> Image.Image:
        """
        Paste a logo at the center of the QR image inside a solid-color box.

        The QR has already been scaled in build() to fit the logo correctly,
        so here we only apply the max_px cap (same value used in build()),
        add padding, and composite onto the QR center.

        Layout:
            ┌──────────────────────┐
            │   solid bg (padding) │  <- back_color of QR
            │   ┌──────────────┐   │
            │   │     logo     │   │
            │   └──────────────┘   │
            └──────────────────────┘
        """
        logo  = Image.open(logo_path).convert("RGBA")

        # Apply the same cap used in build() so sizes stay consistent
        scale = min(1.0, max_px / max(logo.width, logo.height))
        new_w = int(logo.width  * scale)
        new_h = int(logo.height * scale)
        if scale < 1.0:
            logo = logo.resize((new_w, new_h), Image.LANCZOS)

        # Solid-color background block
        bg_w    = logo.width  + padding * 2
        bg_h    = logo.height + padding * 2
        bg      = Image.new("RGBA", (bg_w, bg_h), back_color + "FF"
                            if len(back_color) == 7 else back_color)
        bg.paste(logo, (padding, padding), mask=logo)

        # Center on QR
        cx = (qr_img.width  - bg_w) // 2
        cy = (qr_img.height - bg_h) // 2
        qr_img.paste(bg.convert("RGB"), (cx, cy))

        return qr_img


# ─────────────────────────────────────────────────────────
#  QR Reader
# ─────────────────────────────────────────────────────────

class QRReader:

    @staticmethod
    def read(image_path: Path) -> list[str]:
        img = Image.open(image_path)

        # Strategy 1 — pyzbar (preferred, supports multiple codes per image)
        try:
            from pyzbar.pyzbar import decode
            return [obj.data.decode("utf-8") for obj in decode(img)]
        except ImportError:
            pass

        # Strategy 2 — OpenCV fallback
        try:
            import cv2 # type: ignore
            import numpy as np
            cv_img       = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            detector     = cv2.QRCodeDetector()
            data, _, _   = detector.detectAndDecode(cv_img)
            return [data] if data else []
        except ImportError:
            pass

        raise ImportError(
            "No QR decoding library found.\n"
            "  Install pyzbar  :  pip install pyzbar\n"
            "  Install OpenCV  :  pip install opencv-python"
        )


# ─────────────────────────────────────────────────────────
#  Data Builders  (pure functions, no I/O, easily testable)
# ─────────────────────────────────────────────────────────

def _require_email(address: str) -> None:
    if not re.match(r"[^@]+@[^@]+\.[^@]+", address):
        raise ValueError(f"Invalid email address: {address!r}")


def build_text(text: str) -> str:
    return text


def build_number(number: str) -> str:
    if not re.match(r"^[\d\s+\-.()/]+$", number):
        raise ValueError(f"Invalid number value: {number!r}")
    return number


def build_url(url: str) -> str:
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def build_email(address: str, subject: str = "", body: str = "") -> str:
    _require_email(address)
    params: list[str] = []
    if subject: params.append(f"subject={subject}")
    if body:    params.append(f"body={body}")
    query = ("?" + "&".join(params)) if params else ""
    return f"mailto:{address}{query}"


def build_phone(phone: str) -> str:
    digits = re.sub(r"[^\d+]", "", phone)
    return f"tel:{digits}"


def build_sms(phone: str, message: str = "") -> str:
    digits = re.sub(r"[^\d+]", "", phone)
    return f"sms:{digits}" + (f"?body={message}" if message else "")


def build_wifi(ssid: str, password: str = "",
               security: str = "WPA", hidden: bool = False) -> str:
    return f"WIFI:T:{security};S:{ssid};P:{password};H:{'true' if hidden else 'false'};;"


def build_vcard(name: str, phone: str = "", email: str = "",
                org: str = "", url: str = "", address: str = "") -> str:
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{name}"]
    if phone:   lines.append(f"TEL:{phone}")
    if email:   lines.append(f"EMAIL:{email}")
    if org:     lines.append(f"ORG:{org}")
    if url:     lines.append(f"URL:{url}")
    if address: lines.append(f"ADR:;;{address};;;;")
    lines.append("END:VCARD")
    return "\n".join(lines)


def build_geo(lat: str, lon: str) -> str:
    try:
        float(lat); float(lon)
    except ValueError:
        raise ValueError("Latitude and longitude must be valid decimal numbers.")
    return f"geo:{lat},{lon}"


# ─────────────────────────────────────────────────────────
#  CLI Helpers
# ─────────────────────────────────────────────────────────

def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_header(text: str) -> None:
    print(f"\n{HEAVY}\n  {text}\n{HEAVY}")


def prompt(label: str, required: bool = True) -> str:
    while True:
        val = input(f"  > {label}: ").strip()
        if val or not required:
            return val
        print("  [!] This field is required.")


def prompt_optional(label: str) -> str:
    return prompt(label, required=False)


def numbered_menu(options: list[str], header: str = "Choose an option") -> int:
    print(f"\n  {header}\n")
    for i, opt in enumerate(options, 1):
        print(f"    {i:>2}.  {opt}")
    print(f"\n{DIVIDER}")
    while True:
        raw = input("  > Your choice: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)
        print(f"  [!] Enter a number between 1 and {len(options)}.")


def pick_style() -> QRStyle:
    idx = numbered_menu(QRStyle.choices(), "QR Module Style") - 1
    return list(QRStyle)[idx]


def pick_color() -> QRColor:
    idx = numbered_menu(QRColor.choices(), "QR Color") - 1
    return list(QRColor)[idx]


# ─────────────────────────────────────────────────────────
#  Data-Type Registry
# ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DataTypeEntry:
    label   : str
    filename: str
    collect : Callable[[], str]   # returns ready-to-encode payload


def _collect_text() -> str:
    return build_text(prompt("Text content"))

def _collect_number() -> str:
    return build_number(prompt("Numeric value"))

def _collect_url() -> str:
    return build_url(prompt("URL (e.g. https://example.com)"))

def _collect_email() -> str:
    return build_email(
        address = prompt("Email address"),
        subject = prompt_optional("Subject (optional)"),
        body    = prompt_optional("Body (optional)"),
    )

def _collect_phone() -> str:
    return build_phone(prompt("Phone number (e.g. +1-800-555-0199)"))

def _collect_sms() -> str:
    return build_sms(
        phone   = prompt("Phone number"),
        message = prompt_optional("Pre-filled message (optional)"),
    )

def _collect_wifi() -> str:
    ssid     = prompt("Network name (SSID)")
    password = prompt_optional("Password (leave blank for open network)")
    sec_vals = ["WPA", "WEP", "nopass"]
    idx      = numbered_menu(["WPA / WPA2  (recommended)", "WEP", "No password  (open)"],
                             "Security type") - 1
    return build_wifi(ssid=ssid, password=password, security=sec_vals[idx])

def _collect_vcard() -> str:
    return build_vcard(
        name    = prompt("Full name"),
        phone   = prompt_optional("Phone (optional)"),
        email   = prompt_optional("Email (optional)"),
        org     = prompt_optional("Organization (optional)"),
        url     = prompt_optional("Website (optional)"),
        address = prompt_optional("Address (optional)"),
    )

def _collect_geo() -> str:
    return build_geo(
        lat = prompt("Latitude  (e.g. 40.7128)"),
        lon = prompt("Longitude (e.g. -74.0060)"),
    )


DATA_TYPES: list[DataTypeEntry] = [
    DataTypeEntry("Text",            "qr_text.png",   _collect_text),
    DataTypeEntry("Number",          "qr_number.png", _collect_number),
    DataTypeEntry("URL",             "qr_url.png",    _collect_url),
    DataTypeEntry("Email",           "qr_email.png",  _collect_email),
    DataTypeEntry("Phone",           "qr_phone.png",  _collect_phone),
    DataTypeEntry("SMS",             "qr_sms.png",    _collect_sms),
    DataTypeEntry("WiFi",            "qr_wifi.png",   _collect_wifi),
    DataTypeEntry("vCard (Contact)", "qr_vcard.png",  _collect_vcard),
    DataTypeEntry("Geo Location",    "qr_geo.png",    _collect_geo),
]


# ─────────────────────────────────────────────────────────
#  Application Screens
# ─────────────────────────────────────────────────────────

def screen_create() -> None:
    print_header("Create QR Code")

    # 1 — Pick data type
    type_idx = numbered_menu([e.label for e in DATA_TYPES], "Data Type") - 1
    entry    = DATA_TYPES[type_idx]

    # 2 — Collect payload
    print(f"\n  [{entry.label}]  Fill in the required fields:\n")
    try:
        data = entry.collect()
    except ValueError as exc:
        print(f"\n  [!] Validation error: {exc}")
        input("\n  Press Enter to go back...")
        return

    # 3 — Appearance
    style = pick_style()
    color = pick_color()

    # 4 — Output filename
    print(f"\n{DIVIDER}")
    custom   = prompt_optional("Output filename (blank = default)")
    filename = entry.filename
    if custom:
        filename = custom if custom.endswith(".png") else custom + ".png"

    # 5 — Optional logo
    logo_raw  = prompt_optional("Logo path for center embed (optional)")
    logo_path: Optional[Path] = None
    if logo_raw:
        p = Path(logo_raw)
        if p.exists():
            logo_path = p
        else:
            print("  [!] Logo file not found — skipping.")

    # 6 — Build
    cfg = QRConfig(
        data      = data,
        filename  = filename,
        style     = style,
        color     = color,
        logo_path = logo_path,
    )

    try:
        out = QRGenerator.build(cfg)
        print(f"\n{HEAVY}")
        print(f"   Saved to: {out.resolve()}")
        print(HEAVY)
    except Exception as exc:
        log.exception("Generation failed")
        print(f"\n  [!] Error: {exc}")

    input("\n  Press Enter to return to menu...")

def screen_read() -> None:
    print_header("Read QR Code")

    path = Path(prompt("Image file path (e.g. qr_output/qr_url.png)"))

    if not path.exists():
        print(f"\n  [!] File not found: {path}")
        input("  Press Enter to go back...")
        return

    try:
        results = QRReader.read(path)
    except ImportError as exc:
        print(f"\n  [!] {exc}")
        input("  Press Enter to go back...")
        return
    except Exception as exc:
        log.exception("Read failed")
        print(f"\n  [!] Could not read image: {exc}")
        input("  Press Enter to go back...")
        return

    print(f"\n{DIVIDER}")
    if results:
        print(f"  Found {len(results)} QR code(s):\n")
        for i, code in enumerate(results, 1):
            print(f"  [{i}]  {code}")
    else:
        print("  No QR code detected in the image.")
    print(f"{DIVIDER}")

    input("  Press Enter to return to menu...")

def screen_about() -> None:
    print_header(f"QR Tool  v{VERSION}")
    print(f"""
  Supported data types : Text, Number, URL, Email, Phone,
                         SMS, WiFi, vCard, Geo Location

  QR styles            : Square, Rounded, Circle
  Color presets        : {len(list(QRColor))} options

  QR reading requires  : pip install pyzbar
                      or pip install opencv-python

  Output folder        : ./{OUTPUT_DIR}/

  GitHub  : https://github.com/n-o-name-1/qr-tool
  License : MIT
""")
    input("  Press Enter to go back...")

# ─────────────────────────────────────────────────────────
#  Main Loop
# ─────────────────────────────────────────────────────────

MAIN_MENU_OPTIONS = ["Create QR Code", "Read QR Code", "About", "Exit"]
MAIN_ACTIONS: dict[int, Callable[[], None]] = {
    1: screen_create,
    2: screen_read,
    3: screen_about,
    4: lambda: sys.exit(0),
}

def main() -> None:
    while True:
        clear_screen()
        print(f"""
               
  ██████╗ ██████╗     ████████╗ ██████╗  ██████╗ ██╗
██╔═══██╗██╔══██╗     ╚══██╔══╝██╔═══██╗██╔═══██╗██║
██║   ██║██████╔╝        ██║   ██║   ██║██║   ██║██║
██║▄▄ ██║██╔══██╗        ██║   ██║   ██║██║   ██║██║
╚██████╔╝██║  ██║        ██║   ╚██████╔╝╚██████╔╝███████╗
 ╚══▀▀═╝ ╚═╝  ╚═╝        ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝

QR Code Generator & Reader  v1.1.0
Author  : https://github.com/n-o-name-1
Telegram : https://t.me/n_o_name_1
License : MIT

{HEAVY}

    1.  Create QR Code
    2.  Read   QR Code
    3.  About
    4.  Exit

{DIVIDER}""")
        raw = input("  > Your choice: ").strip()
        if raw.isdigit() and int(raw) in MAIN_ACTIONS:
            clear_screen()
            MAIN_ACTIONS[int(raw)]()
        else:
            print("  [!] Invalid choice. Please enter 1-4.")


if __name__ == "__main__":
    main()
