# -*- coding: utf-8 -*-
"""
Генератор иконок PWA для каталога «Вкусный Дом».
Создаёт 4 PNG-иконки: синий фон #2563eb + белая монограмма «ВД».
Запускать один раз — иконки временные, заменяемые без правки кода (D-05).
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

# Фирменный синий цвет — совпадает с Tailwind bg-blue-600 (D-06)
BLUE = (37, 99, 235)   # #2563eb
WHITE = (255, 255, 255)

# Шрифт для монограммы
FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"

# Целевая папка
OUTPUT_DIR = "C:/catalog/public/icons"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def draw_rounded_icon(size, radius_ratio=0.18, safe_zone=1.0):
    """
    Создаёт PNG-изображение: синий квадрат с монограммой «ВД».
    safe_zone — коэффициент размера монограммы относительно иконки
    (для maskable — ~0.5, чтобы буквы вошли в safe-zone ~80%).
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Радиус скругления (для обычных иконок)
    radius = int(size * radius_ratio)

    # Рисуем скруглённый прямоугольник
    draw.rounded_rectangle(
        [(0, 0), (size - 1, size - 1)],
        radius=radius,
        fill=BLUE,
    )

    # Монограмма «ВД» — размер шрифта зависит от safe_zone
    font_size = int(size * safe_zone * 0.52)
    font = ImageFont.truetype(FONT_PATH, font_size)

    text = "ВД"
    # Измеряем размер текста
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (size - text_w) // 2 - bbox[0]
    text_y = (size - text_h) // 2 - bbox[1]

    draw.text((text_x, text_y), text, fill=WHITE, font=font)

    return img


def draw_no_alpha(size):
    """
    Иконка без прозрачности (для apple-touch-icon — iOS скругляет сам).
    Прямые углы, сплошной синий фон (D-04).
    """
    img = Image.new("RGB", (size, size), BLUE)
    draw = ImageDraw.Draw(img)

    font_size = int(size * 0.52)
    font = ImageFont.truetype(FONT_PATH, font_size)

    text = "ВД"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (size - text_w) // 2 - bbox[0]
    text_y = (size - text_h) // 2 - bbox[1]

    draw.text((text_x, text_y), text, fill=WHITE, font=font)

    return img


def draw_maskable(size):
    """
    Maskable-иконка: монограмма в safe-zone ~80% от центра.
    Фон заполняет весь квадрат без скругления и прозрачности (D-04).
    Буквы меньше — чтобы Android adaptive-маска не обрезала их.
    """
    img = Image.new("RGBA", (size, size), BLUE + (255,))
    draw = ImageDraw.Draw(img)

    # safe-zone = 80% — монограмма занимает ~40% от ширины иконки
    font_size = int(size * 0.8 * 0.42)
    font = ImageFont.truetype(FONT_PATH, font_size)

    text = "ВД"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (size - text_w) // 2 - bbox[0]
    text_y = (size - text_h) // 2 - bbox[1]

    draw.text((text_x, text_y), text, fill=WHITE, font=font)

    return img


# --- Генерация иконок ---

# icon-192x192.png — стандартная PWA-иконка (D-04)
img_192 = draw_rounded_icon(192)
img_192.save(os.path.join(OUTPUT_DIR, "icon-192x192.png"), "PNG")
print("OK icon-192x192.png")

# icon-512x512.png — стандартная PWA-иконка большая (D-04)
img_512 = draw_rounded_icon(512)
img_512.save(os.path.join(OUTPUT_DIR, "icon-512x512.png"), "PNG")
print("OK icon-512x512.png")

# icon-512x512-maskable.png — maskable с safe-zone (D-04)
img_maskable = draw_maskable(512)
img_maskable.save(os.path.join(OUTPUT_DIR, "icon-512x512-maskable.png"), "PNG")
print("OK icon-512x512-maskable.png")

# apple-touch-icon.png — 180x180, без прозрачности (D-04)
img_apple = draw_no_alpha(180)
img_apple.save(os.path.join(OUTPUT_DIR, "apple-touch-icon.png"), "PNG")
print("OK apple-touch-icon.png")

print("All icons generated in", OUTPUT_DIR)
