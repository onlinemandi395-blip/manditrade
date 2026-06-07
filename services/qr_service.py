from __future__ import annotations

from io import BytesIO


class QRService:
    def build_qr_png_bytes(self, payload: str) -> bytes:
        normalized_payload = str(payload or "").strip()
        if not normalized_payload:
            return b""
        try:
            import qrcode
        except Exception:
            return b""
        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(normalized_payload)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
