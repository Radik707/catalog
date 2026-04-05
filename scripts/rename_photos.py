#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rename_photos.py — рекурсивное переименование фото из подпапок ПРЕЗЕНТЕР.

Обходит всё дерево папок. Папки без фото (только подпапки) пропускаются,
фото из них обрабатываются в своих конечных подпапках.
Порядок: алфавитный, рекурсивный (сначала содержимое папки, потом вложенные).

Dry-run по умолчанию. Для реального переименования: --apply
"""

import os
import sys
import io

# Форсируем UTF-8 для вывода в Windows-консоль
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SOURCE_DIR = r"C:\Users\olegz\Desktop\ТОРГОВЫЙ\ПРЕЗЕНТЕР\ПРЕЗЕНТЕР"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
START_NUM = 350
DRY_RUN = "--apply" not in sys.argv


def collect_plan(path: str, counter: list, plan: list, indent: int = 0) -> None:
    """
    Рекурсивно обходит дерево папок.
    counter — список из одного int, чтобы передавать по ссылке.
    """
    items = sorted(os.listdir(path))
    subdirs = [i for i in items if os.path.isdir(os.path.join(path, i))]
    images = [i for i in items
              if os.path.isfile(os.path.join(path, i))
              and os.path.splitext(i)[1].lower() in IMAGE_EXTS]

    prefix = "  " * indent
    rel = os.path.relpath(path, SOURCE_DIR)
    label = "." if rel == "." else rel

    if images:
        print(f"\n{prefix}[{label}/]  — {len(images)} фото")
        for filename in images:
            ext = os.path.splitext(filename)[1].lower()
            new_name = f"{counter[0]}{ext}"
            old_path = os.path.join(path, filename)
            new_path = os.path.join(path, new_name)
            plan.append((old_path, new_path))
            print(f"{prefix}  {filename}  →  {new_name}")
            counter[0] += 1
    elif not subdirs:
        print(f"{prefix}[пусто] {label}/")

    for sub in subdirs:
        collect_plan(os.path.join(path, sub), counter, plan, indent + 1)


def apply_plan(plan: list) -> None:
    errors = 0
    for old_path, new_path in plan:
        if os.path.exists(new_path) and old_path != new_path:
            print(f"  ПРОПУСК (файл уже существует): {new_path}")
            errors += 1
            continue
        try:
            os.rename(old_path, new_path)
        except OSError as e:
            print(f"  ОШИБКА: {old_path} → {e}")
            errors += 1

    print(f"\nГотово: {len(plan) - errors}/{len(plan)} файлов переименовано.")
    if errors:
        print(f"Ошибок: {errors}")


if __name__ == "__main__":
    if not os.path.isdir(SOURCE_DIR):
        print(f"Ошибка: папка не найдена: {SOURCE_DIR}")
        sys.exit(1)

    mode = "DRY-RUN (просмотр)" if DRY_RUN else "ПРИМЕНЕНИЕ"
    print(f"=== rename_photos.py  [{mode}] ===")
    print(f"Папка: {SOURCE_DIR}")
    print(f"Нумерация с: {START_NUM}")

    counter = [START_NUM]
    plan = []
    collect_plan(SOURCE_DIR, counter, plan)

    print(f"\nВсего файлов: {len(plan)}")
    if plan:
        _, last_path = plan[-1]
        last_name = os.path.basename(last_path)
        print(f"Диапазон номеров: {START_NUM} – {os.path.splitext(last_name)[0]}")

    if DRY_RUN:
        print("\n--- Это dry-run. Файлы НЕ переименованы. ---")
        print("Для реального переименования запустите:")
        print("  python rename_photos.py --apply")
    else:
        print("\nНачинаю переименование...")
        apply_plan(plan)
