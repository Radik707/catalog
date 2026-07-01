"use client";

// Лёгкий просмотр фото «поближе» (не на весь экран — это Lightbox).
// Тап по миниатюре в режимах «Список» (клиент) и «Быстрый набор» (агент)
// открывает фото увеличенным примерно на треть экрана: затемнённая подложка,
// плавное «раскрытие» с лёгким зумом, тап в любом месте (или Esc) закрывает.
//
// Рендерится ЧЕРЕЗ ПОРТАЛ в document.body: карточки списка/сетки обёрнуты в
// CSS-трансформацию (perspective/rotateY для флипа), а `position: fixed` внутри
// трансформированного предка позиционируется относительно него, а не окна —
// портал выносит оверлей наружу, чтобы фото всегда центрировалось по экрану.

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Image from "next/image";

interface ImagePeekProps {
  src: string;
  alt: string;
  onClose: () => void;
}

export default function ImagePeek({ src, alt, onClose }: ImagePeekProps) {
  // mounted — портал доступен только на клиенте (нет document на сервере).
  const [mounted, setMounted] = useState(false);
  // shown — управляет анимацией «раскрытия»: стартуем с уменьшенного/прозрачного.
  const [shown, setShown] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Следующий кадр — включаем финальное состояние, чтобы сработал transition.
    const raf = requestAnimationFrame(() => setShown(true));
    // Esc закрывает (на ПК); на телефоне — тап по подложке.
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  if (!mounted) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-6"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      {/* Белая карточка с увеличенным фото (~1/3 экрана). Клик по самому фото
          не закрывает (stopPropagation) — закрывает тап по затемнённому фону. */}
      <div
        className="relative rounded-2xl bg-white p-2 shadow-2xl"
        style={{
          transform: shown ? "scale(1)" : "scale(0.85)",
          opacity: shown ? 1 : 0,
          transition: "transform 0.15s ease-out, opacity 0.15s ease-out",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Контейнер фиксированного размера ~треть экрана; фото вписывается (object-contain).
            unoptimized + тот же URL, что у миниатюры — попадание в кэш SW (работает офлайн). */}
        <div className="relative h-[38vh] max-h-[360px] w-[78vw] max-w-[400px]">
          <Image src={src} alt={alt} fill unoptimized className="object-contain rounded-lg" />
        </div>
      </div>
    </div>,
    document.body,
  );
}
