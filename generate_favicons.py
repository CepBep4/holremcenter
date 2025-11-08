#!/usr/bin/env python3
"""
Скрипт для генерации PNG favicon из SVG файла.
Требует установки: pip install cairosvg pillow
"""

import os
import sys

try:
    import cairosvg
except ImportError:
    print("Ошибка: библиотека cairosvg не установлена.")
    print("Установите её командой: pip install cairosvg")
    sys.exit(1)

# Размеры для генерации
SIZES = {
    'favicon-16x16.png': 16,
    'favicon-32x32.png': 32,
    'apple-touch-icon.png': 180,
    'android-chrome-192x192.png': 192,
    'android-chrome-512x512.png': 512,
}

def generate_favicons(svg_path='static/icon.svg', output_dir='static'):
    """Генерирует PNG файлы разных размеров из SVG"""
    
    if not os.path.exists(svg_path):
        print(f"Ошибка: файл {svg_path} не найден!")
        return False
    
    print(f"Генерация favicon из {svg_path}...")
    
    for filename, size in SIZES.items():
        output_path = os.path.join(output_dir, filename)
        try:
            cairosvg.svg2png(
                url=svg_path,
                write_to=output_path,
                output_width=size,
                output_height=size
            )
            print(f"✓ Создан {output_path} ({size}x{size}px)")
        except Exception as e:
            print(f"✗ Ошибка при создании {output_path}: {e}")
            return False
    
    print("\n✓ Все favicon файлы успешно созданы!")
    return True

if __name__ == '__main__':
    generate_favicons()

