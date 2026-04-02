"""
fix_photo_paths.py — Убрать пути из колонки C в photo_manual.xlsx
Оставляет только имя файла (например Screenshot_24.png)
"""
import sys
import re
import openpyxl
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SHEET_PATH = PROJECT_ROOT / "photo_manual.xlsx"

# Все варианты префиксов (регистронезависимо, слэши в любом направлении)
PREFIX_PATTERN = re.compile(
    r'^(?:file:///)?[A-Za-z]:[/\\]catalog[/\\]photos[/\\]',
    re.IGNORECASE,
)

wb = openpyxl.load_workbook(SHEET_PATH)
ws = wb["Товары"]

fixed = 0
examples = []

for row in ws.iter_rows(min_row=2):
    cell = row[2]  # колонка C
    val = cell.value
    if not val:
        continue
    s = str(val).strip()
    new_val = PREFIX_PATTERN.sub("", s)
    if new_val != s:
        if len(examples) < 5:
            examples.append((s, new_val))
        cell.value = new_val
        fixed += 1

wb.save(SHEET_PATH)

print(f"Исправлено ячеек: {fixed}")
print()
for before, after in examples:
    print(f"  ДО:    {before}")
    print(f"  ПОСЛЕ: {after}")
    print()
