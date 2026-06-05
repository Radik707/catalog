"use client";

import { useEffect } from "react";
import Image from "next/image";

// Просмотрщик фото на весь экран (lightbox).
// Открывается по тапу на фото товара, показывает чёткую версию по центру
// на тёмном фоне с подписью снизу (название + цена + фасовка).
interface LightboxProps {
  imageUrl: string; // оригинальный URL Cloudinary
  name: string;
  price: number;
  packaging?: string;
  onClose: () => void;
}

// Вставляем трансформацию Cloudinary, чтобы получить чёткую полноэкранную версию.
// Из ".../upload/v123/catalog/001.png" делаем
// ".../upload/f_auto,q_auto,w_1600/v123/catalog/001.png".
function getHiResUrl(url: string): string {
  return url.replace("/upload/", "/upload/f_auto,q_auto,w_1600/");
}

export default function Lightbox({
  imageUrl,
  name,
  price,
  packaging,
  onClose,
}: LightboxProps) {
  // Закрытие по Esc + блокировка прокрутки фона на время показа.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  return (
    // Клик по тёмному фону закрывает просмотрщик.
    <div
      className="fixed inset-0 z-50 flex flex-col bg-black/90"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={name}
    >
      {/* Кнопка закрытия */}
      <button
        onClick={onClose}
        className="absolute top-3 right-3 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-2xl leading-none text-white hover:bg-white/20 focus:outline-none"
        aria-label="Закрыть"
      >
        ✕
      </button>

      {/* Фото по центру. Клик по самому фото не закрывает окно. */}
      <div className="relative m-4 flex-1" onClick={(e) => e.stopPropagation()}>
        <Image
          src={getHiResUrl(imageUrl)}
          alt={name}
          fill
          sizes="100vw"
          className="object-contain"
          priority
        />
      </div>

      {/* Подпись снизу: название + цена + фасовка */}
      <div
        className="px-5 pb-6 pt-2 text-center text-white"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-base font-medium leading-snug">{name}</p>
        <p className="mt-1 text-lg font-bold">
          {price.toFixed(2)} ₽
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
