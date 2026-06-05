"use client";

import { useEffect, useRef } from "react";
import { Product } from "@/lib/types";
import { getPackaging } from "@/lib/packaging";

// Просмотрщик-галерея фото на весь экран (lightbox).
// Показывает фото товара по центру на тёмном фоне с подписью снизу
// (название + цена + фасовка) и позволяет листать товары:
//   свайп вправо / стрелка ← / кнопка слева  → предыдущий товар
//   свайп влево  / стрелка → / кнопка справа → следующий товар
// Закрытие: крестик, клик по чёрному фону, свайп вверх/вниз, Esc.
interface LightboxProps {
  products: Product[]; // только товары с фото, в порядке отображения
  index: number; // индекс текущего товара
  onIndexChange: (newIndex: number) => void;
  onClose: () => void;
}

// Вставляем трансформацию Cloudinary, чтобы получить чёткую полноэкранную версию.
// Из ".../upload/v123/catalog/001.png" делаем
// ".../upload/f_auto,q_auto,w_1600/v123/catalog/001.png".
function getHiResUrl(url: string): string {
  return url.replace("/upload/", "/upload/f_auto,q_auto,w_1600/");
}

export default function Lightbox({
  products,
  index,
  onIndexChange,
  onClose,
}: LightboxProps) {
  const product = products[index];

  const hasPrev = index > 0;
  const hasNext = index < products.length - 1;

  const goPrev = () => {
    if (hasPrev) onIndexChange(index - 1);
  };
  const goNext = () => {
    if (hasNext) onIndexChange(index + 1);
  };

  // Координаты начала касания — для определения направления взмаха.
  const touchStart = useRef<{ x: number; y: number } | null>(null);

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStart.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStart.current) return;
    const dx = e.changedTouches[0].clientX - touchStart.current.x;
    const dy = e.changedTouches[0].clientY - touchStart.current.y;
    touchStart.current = null;

    // Горизонтальный взмах преобладает → листаем товары.
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 50) {
      if (dx > 0) goPrev(); // свайп вправо → предыдущий
      else goNext(); // свайп влево → следующий
      return;
    }
    // Вертикальный взмах больше порога → закрываем.
    if (Math.abs(dy) > 80) onClose();
  };

  // Клавиатура: ← предыдущий, → следующий, Esc закрыть.
  // Блокировка прокрутки фона на время показа.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft") {
        if (index > 0) onIndexChange(index - 1);
      } else if (e.key === "ArrowRight") {
        if (index < products.length - 1) onIndexChange(index + 1);
      }
    };
    document.addEventListener("keydown", onKey);

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [index, products.length, onIndexChange, onClose]);

  if (!product) return null;

  const packaging = getPackaging(product.group, product.name);

  return (
    // Клик по тёмному фону закрывает просмотрщик.
    <div
      className="fixed inset-0 z-50 flex flex-col bg-black/90"
      onClick={onClose}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      role="dialog"
      aria-modal="true"
      aria-label={product.name}
    >
      {/* Кнопка закрытия */}
      <button
        onClick={onClose}
        className="absolute top-3 right-3 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-2xl leading-none text-white hover:bg-white/20 focus:outline-none"
        aria-label="Закрыть"
      >
        ✕
      </button>

      {/* Стрелка «предыдущий» */}
      {hasPrev && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            goPrev();
          }}
          className="absolute left-2 top-1/2 z-10 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-3xl leading-none text-white hover:bg-white/20 focus:outline-none"
          aria-label="Предыдущее фото"
        >
          ‹
        </button>
      )}

      {/* Стрелка «следующий» */}
      {hasNext && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            goNext();
          }}
          className="absolute right-2 top-1/2 z-10 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-3xl leading-none text-white hover:bg-white/20 focus:outline-none"
          aria-label="Следующее фото"
        >
          ›
        </button>
      )}

      {/* Область фото. Чёрные поля вокруг — это пустое место контейнера,
          клик по ним закрывает окно. Клик по самому фото — не закрывает. */}
      <div className="flex flex-1 items-center justify-center overflow-hidden p-4">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={getHiResUrl(product.imageUrl as string)}
          alt={product.name}
          className="max-h-full max-w-full object-contain"
          onClick={(e) => e.stopPropagation()}
        />
      </div>

      {/* Подпись снизу: название + цена + фасовка */}
      <div
        className="px-5 pb-6 pt-2 text-center text-white"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-base font-medium leading-snug">{product.name}</p>
        <p className="mt-1 text-lg font-bold">
          {product.price.toFixed(2)} ₽
          {packaging && (
            <span className="ml-2 text-sm font-normal text-white/70">
              {packaging}
            </span>
          )}
        </p>
      </div>
    </div>
  );
}
