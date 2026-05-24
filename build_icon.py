"""Generate icon.ico for the DMX512 Controller application."""
import struct, os, sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QImage


def _make_icon_pixmap(size):
    """Draw the DMX icon at the given size using QPainter."""
    p = QPixmap(size, size)
    p.fill(Qt.transparent)
    q = QPainter(p)
    q.setRenderHint(QPainter.Antialiasing)
    inset = max(2, size // 16)
    q.setBrush(QColor("#007aff"))
    q.setPen(Qt.NoPen)
    q.drawEllipse(inset, inset, size - 2 * inset, size - 2 * inset)
    d = size // 4
    q.setBrush(QColor("#4da6ff"))
    q.drawEllipse(d, d, size - 2 * d, size - 2 * d)
    d = size // 3
    q.setBrush(QColor("#007aff"))
    q.drawEllipse(d, d, size - 2 * d, size - 2 * d)
    q.setPen(QColor("#ffffff"))
    font_size = max(6, size // 4)
    f = QFont("Arial", font_size, QFont.Bold)
    q.setFont(f)
    q.drawText(QRect(0, 0, size, size), Qt.AlignCenter, "DMX")
    q.end()
    return p


def _bgra_data(size):
    """Return (xor_mask, and_mask) in BMP DIB format for ICO."""
    p = _make_icon_pixmap(size)
    img = p.toImage().convertToFormat(QImage.Format_ARGB32)

    row_pitch = (size * 32 + 31) // 32 * 4  # 4-byte aligned row in bytes
    xor_data = bytearray()
    for y in range(size - 1, -1, -1):  # bottom-up (BMP convention)
        for x in range(size):
            px = img.pixel(x, y)
            xor_data.extend([
                (px >> 0) & 0xFF,   # B
                (px >> 8) & 0xFF,   # G
                (px >> 16) & 0xFF,  # R
                (px >> 24) & 0xFF,  # A
            ])
        pad = row_pitch - size * 4
        if pad:
            xor_data.extend(b"\x00" * pad)

    and_pitch = ((size + 31) // 32) * 4
    and_data = bytearray(and_pitch * size)
    return bytes(xor_data), bytes(and_data)


def build_ico(output_path="icon.ico", sizes=(16, 32, 48, 64)):
    """Generate a multi-resolution .ico file."""
    entries = []
    all_data = bytearray()
    offset = 6 + len(sizes) * 16

    for sz in sizes:
        xor_data, and_mask = _bgra_data(sz)

        bih = struct.pack(
            "<IiiHHIIiiII",
            40, sz, sz * 2, 1, 32, 0, 0, 0, 0, 0, 0,
        )
        data = bih + xor_data + and_mask

        ico_w = sz if sz < 256 else 0
        ico_h = sz if sz < 256 else 0
        entry = struct.pack(
            "<BBBBHHII", ico_w, ico_h, 0, 0, 1, 32, len(data), offset
        )
        entries.append(entry)
        all_data.extend(data)
        offset += len(data)

    with open(output_path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, len(sizes)))
        for e in entries:
            f.write(e)
        f.write(bytes(all_data))
    return output_path


if __name__ == "__main__":
    app = QApplication(sys.argv)
    path = build_ico()
    print(f"Created {os.path.getsize(path)} bytes: {path}")
