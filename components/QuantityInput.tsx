"use client";

import { useState, useRef, useEffect } from "react";

// Редактируемое количество: цифра, по тапу превращается в числовое поле.
// На телефоне открывается числовая клавиатура (inputMode="numeric"),
// допускаются только цифры 0-9, при фокусе текст выделяется — ввод сразу
// заменяет старое значение. Пустое поле при потере фокуса — откат к прежнему.
interface QuantityInputProps {
  value: number;
  // Максимум (остаток). При превышении значение обрезается.
  max?: number;
  // Применить новое значение. 0 родитель трактует как удаление позиции.
  onCommit: (v: number) => void;
  // Классы для отображаемой цифры и поля (ширина/размер/цвет текста).
  className?: string;
}

export default function QuantityInput({
  value,
  max,
  onCommit,
  className = "",
}: QuantityInputProps) {
  // Режим редактирования и текущий черновик ввода (строкой — допускаем пустое).
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value));
  const inputRef = useRef<HTMLInputElement>(null);

  // При входе в режим правки — выделяем всё, чтобы ввод заменял значение.
  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const startEdit = () => {
    setDraft(String(value));
    setEditing(true);
  };

  const commit = () => {
    setEditing(false);
    const raw = draft.trim();
    // Пустое поле — откат к прежнему значению (ничего не меняем)
    if (raw === "") return;
    let n = parseInt(raw, 10);
    if (Number.isNaN(n)) return;
    if (n < 0) n = 0;
    if (typeof max === "number" && n > max) n = max;
    if (n !== value) onCommit(n);
  };

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        value={draft}
        // Оставляем только цифры
        onChange={(e) => setDraft(e.target.value.replace(/[^0-9]/g, ""))}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            inputRef.current?.blur();
          } else if (e.key === "Escape") {
            setEditing(false);
          }
        }}
        // Клик не должен всплывать (переворот карточки / переход)
        onClick={(e) => e.stopPropagation()}
        className={`text-center font-semibold rounded border border-blue-400 outline-none ${className}`}
      />
    );
  }

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        startEdit();
      }}
      aria-label="Изменить количество"
      className={`text-center font-semibold ${className}`}
    >
      {value}
    </button>
  );
}
