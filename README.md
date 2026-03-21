# QR Tool 🔲

> **QR code generator and reader built in Python.**  
> Supports 9 data types, 3 styles, 6 color presets, and optional logo embedding.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)]()

---

## ✨ Features

| Feature | Details |
|---|---|
| **Data types** | Text, Number, URL, Email, Phone, SMS, WiFi, vCard, Geo |
| **Styles** | Square, Rounded, Circle |
| **Colors** | 6 color presets (Black, Blue, Red, Green, Purple, White-on-Black) |
| **Logo embed** | Paste your logo/icon at the center of any QR code |
| **QR Reader** | Decode QR images via `pyzbar` or `opencv-python` |
| **Output** | PNG images saved to `./qr_output/` |

---

## 📦 Requirements

```
Python 3.9+
qrcode[pil]
Pillow
```

**Optional — needed only for reading QR codes:**
```
pyzbar       (recommended)
opencv-python
```

---

## 🚀 Installation

```bash
# 1. Clone the repo
git clone https://github.com/n-o-name-1/qr-tool.git
cd qr-tool

# 2. Install dependencies
pip install qrcode[pil] pillow

# 3. (Optional) Install QR reader
pip install pyzbar
```

---

## ▶️ Usage

```bash
python qr_tool.py
```

You will see an interactive menu:

```

 ██████╗ ██████╗      ████████╗ ██████╗  ██████╗ ██╗
██╔═══██╗██╔══██╗     ╚══██╔══╝██╔═══██╗██╔═══██╗██║
██║   ██║██████╔╝        ██║   ██║   ██║██║   ██║██║
██║▄▄ ██║██╔══██╗        ██║   ██║   ██║██║   ██║██║
╚██████╔╝██║  ██║        ██║   ╚██████╔╝╚██████╔╝███████╗
 ╚══▀▀═╝ ╚═╝  ╚═╝        ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝

QR Code Generator & Reader  v1.0.0
Author  : https://github.com/n-o-name-1
Telegram : https://t.me/n_o_name_1
License : MIT
 ──────────────────────────────────────────────────

    1.  Create QR Code
    2.  Read   QR Code
    3.  About
    4.  Exit
```

---

## 🖨 Creating a QR Code

Select **Create**, then follow the prompts:

```
Step 1 → Choose data type  (e.g. WiFi, URL, vCard …)
Step 2 → Fill in fields    (SSID, password, etc.)
Step 3 → Choose QR style   (Square / Rounded / Circle)
Step 4 → Choose color      (6 presets)
Step 5 → Set filename      (or keep default)
Step 6 → Add logo          (optional — path to .png)
```

Output is saved to `./qr_output/<filename>.png`.

---

## 📷 Reading a QR Code

Select **Read**, enter the image path, and the decoded content is printed:

```
  > Image file path: qr_output/qr_wifi.png

  ────────────────────────────────────────────────────
  Found 1 QR code(s):

  [1]  WIFI:T:WPA;S:MyNetwork;P:MyPassword;H:false;;
```

---

## 🗂 Supported Data Types

### 1. Text
Any plain string — notes, messages, IDs.

### 2. Number
Numeric values — product codes, serial numbers.

### 3. URL
Web links. Automatically prepends `https://` if missing.

### 4. Email
Encodes a `mailto:` URI with optional subject and body.

### 5. Phone
Encodes a `tel:` URI that opens the phone dialer on scan.

### 6. SMS
Encodes an `sms:` URI with an optional pre-filled message.

### 7. WiFi
Encodes WiFi credentials. Most Android and iOS cameras will **auto-connect** on scan.

```
Security options: WPA/WPA2 | WEP | Open (no password)
```

### 8. vCard (Contact)
Encodes a vCard 3.0 contact card.  
Scanning saves the contact directly to the phone.

```
Fields: Name, Phone, Email, Organization, Website, Address
```

### 9. Geo Location
Encodes GPS coordinates as a `geo:` URI.  
Scanning opens the maps app at that location.

---

## 📁 Project Structure

```
qr-tool/
├── qr_tool.py       ← Main application (all-in-one)
├── qr_output/       ← Generated QR images (auto-created)
├── README.md
└── LICENSE
```

---

## 🧱 Architecture

The code follows clean Python practices:

| Concept | Usage |
|---|---|
| `dataclass` | `QRConfig` — typed, immutable config object |
| `Enum` | `QRStyle`, `QRColor` — safe, readable constants |
| `class` | `QRGenerator`, `QRReader` — single-responsibility classes |
| Pure functions | `build_url()`, `build_wifi()` etc. — no side effects, easily testable |
| Strategy pattern | `QRReader` tries `pyzbar` then falls back to OpenCV |
| Registry pattern | `DATA_TYPES` list maps each type to its collector function |
| `pathlib.Path` | All file paths use `Path` — cross-platform, safe |

---

## 🛠 Advanced: Use as a library

```python
from qr_tool import QRGenerator, QRConfig, QRStyle, QRColor
from qr_tool import build_wifi, build_vcard, build_url

# WiFi QR with rounded style
cfg = QRConfig(
    data      = build_wifi(ssid="HomeNet", password="s3cr3t"),
    filename  = "wifi.png",
    style     = QRStyle.ROUNDED,
    color     = QRColor.BLUE,
)
path = QRGenerator.build(cfg)
print(f"Saved to {path}")

# vCard with logo
from pathlib import Path
cfg = QRConfig(
    data      = build_vcard(name="Alice", phone="+1234567890"),
    filename  = "alice.png",
    style     = QRStyle.CIRCLE,
    color     = QRColor.PURPLE,
    logo_path = Path("logo.png"),
)
QRGenerator.build(cfg)
```

---

## 📋 Requirements

Create `requirements.txt`:

```
qrcode[pil]>=7.4
Pillow>=10.0
```

Optional reader:
```
pyzbar>=0.1.9
```

Install with:
```bash
pip install -r requirements.txt
```
Or 
```bash
python -m pip install qrcode[pil] pillow
```
---

## 🪟 Windows Users — Troubleshooting

If `import qrcode` fails even after `pip install`:

```bash
# Use the exact Python that runs your script
python -m pip install qrcode[pil] pillow

# Verify installation
python -c "import qrcode; print(qrcode.__version__)"
```

---

## 📄 License

This project is licensed under the **MIT License** — free to use, modify, and distribute.

---

## 🤝 Contributing

Pull requests are welcome!  
Please open an issue first to discuss major changes.

---

*Made with Python 🐍*
