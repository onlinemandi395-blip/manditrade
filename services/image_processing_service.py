from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


class ImageProcessingService:
    def process_product_image(self, uploaded_file, output_size: tuple[int, int] = (800, 800), watermark_text: str = "MandiTrade") -> bytes:
        with Image.open(uploaded_file) as image:
            image = image.convert("RGB")
            width, height = image.size
            edge = min(width, height)
            left = max((width - edge) // 2, 0)
            top = max((height - edge) // 2, 0)
            image = image.crop((left, top, left + edge, top + edge))
            image = image.resize(output_size, Image.Resampling.LANCZOS)

            overlay = Image.new("RGBA", output_size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            font_size = max(20, output_size[0] // 24)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            padding = 18
            x = output_size[0] - text_width - padding
            y = output_size[1] - text_height - padding
            draw.rounded_rectangle(
                (x - 12, y - 8, x + text_width + 12, y + text_height + 8),
                radius=8,
                fill=(0, 0, 0, 90),
            )
            draw.text((x, y), watermark_text, fill=(255, 255, 255, 170), font=font)
            image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

            output = BytesIO()
            image.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()
