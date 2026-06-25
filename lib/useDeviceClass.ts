"use client";

import { useEffect, useState } from "react";

// Хук определения класса устройства.
// Различить «дюймы» в вебе нельзя, поэтому используем приближение:
//   планшет ≈ сенсорный экран (pointer: coarse) И ширина ≥ 768px.
// Телефон  → сенсор + узкий экран; ПК → мышь (pointer: fine) — оба «не планшет».
// Это управляет выбором угловой кнопки карточки (стрелки vs сердечко)
// и видом по умолчанию на телефоне.
const TABLET_QUERY = "(pointer: coarse) and (min-width: 768px)";

export function useDeviceClass() {
  // SSR-safe: до монтирования считаем «не планшет» (false), чтобы серверный
  // и первый клиентский рендер совпадали и не было hydration mismatch.
  const [isTabletLike, setIsTabletLike] = useState(false);
  // Признак, что хук уже отработал на клиенте (значение достоверно).
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia(TABLET_QUERY);
    const apply = () => setIsTabletLike(mq.matches);
    apply();
    setReady(true);
    // Реагируем на смену ориентации/окна (планшет ↔ телефон по ширине).
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  return { isTabletLike, ready };
}
