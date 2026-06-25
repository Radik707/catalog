"use client";

import { useEffect, useRef, useState } from "react";
import { Product } from "@/lib/types";
import { getPackaging } from "@/lib/packaging";
import { PriceForm, effectivePrice } from "@/lib/pricing";

// Просмотрщик-галерея фото на весь экран (lightbox) с «живыми» свайпами.
// Внутри — «плёнка» из трёх кадров: предыдущий | текущий | следующий.
// Кадр едет за пальцем (видно соседнее фото), на отпускании плавно
// доезжает до соседнего товара или пружинит обратно.
//   свайп вправо → предыдущий товар
//   свайп влево  → следующий товар
//   свайп вверх/вниз → закрыть (фон плавно гаснет, кадр уезжает)
// Закрытие также: крестик, клик по чёрному фону, стрелки ‹ ›, клавиши ←/→/Esc.
interface LightboxProps {
  products: Product[]; // только товары с фото, в порядке отображения
  index: number; // индекс текущего товара
  onIndexChange: (newIndex: number) => void;
  onClose: () => void;
  priceForm?: PriceForm; // форма цен (для +5% Ефимовой)
}

// Длительность плавного доезда (мс) — должна совпадать с CSS-transition.
const DURATION = 300;

// Вставляем трансформацию Cloudinary для чёткой полноэкранной версии.
function getHiResUrl(url: string): string {
  return url.replace("/upload/", "/upload/f_auto,q_auto,w_1600/");
}

export default function Lightbox({
  products,
  index,
  onIndexChange,
  onClose,
  priceForm = "2",
}: LightboxProps) {
  const product = products[index];
  const hasPrev = index > 0;
  const hasNext = index < products.length - 1;

  // Смещение «плёнки» относительно центрированного состояния (в пикселях).
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  // dragging — палец на экране (transition выключен, кадр следует за пальцем).
  const [dragging, setDragging] = useState(false);
  // instant — мгновенный сброс без анимации (после доезда до соседнего кадра).
  const [instant, setInstant] = useState(false);

  const startRef = useRef<{ x: number; y: number } | null>(null);
  const axisRef = useRef<"h" | "v" | null>(null);
  const animatingRef = useRef(false);

  // ── Плавный доезд до соседнего товара ──
  const animateNext = () => {
    if (!hasNext || animatingRef.current) return;
    animatingRef.current = true;
    setDragging(false);
    setInstant(false);
    setOffset({ x: -window.innerWidth, y: 0 }); // уезжаем влево до следующего
    window.setTimeout(() => {
      // Меняем товар и мгновенно возвращаем плёнку в центр (без анимации).
      setInstant(true);
      onIndexChange(index + 1);
      setOffset({ x: 0, y: 0 });
      requestAnimationFrame(() =>
        requestAnimationFrame(() => {
          setInstant(false);
          animatingRef.current = false;
        })
      );
    }, DURATION);
  };

  const animatePrev = () => {
    if (!hasPrev || animatingRef.current) return;
    animatingRef.current = true;
    setDragging(false);
    setInstant(false);
    setOffset({ x: window.innerWidth, y: 0 }); // уезжаем вправо до предыдущего
    window.setTimeout(() => {
      setInstant(true);
      onIndexChange(index - 1);
      setOffset({ x: 0, y: 0 });
      requestAnimationFrame(() =>
        requestAnimationFrame(() => {
          setInstant(false);
          animatingRef.current = false;
        })
      );
    }, DURATION);
  };

  // ── Плавное закрытие: кадр уезжает по вертикали, затем закрываем ──
  const closeWithAnim = (sign: number) => {
    if (animatingRef.current) return;
    animatingRef.current = true;
    setDragging(false);
    setInstant(false);
    setOffset({ x: 0, y: sign * window.innerHeight });
    window.setTimeout(onClose, DURATION - 50);
  };

  // ── Обработка касаний ──
  const handleTouchStart = (e: React.TouchEvent) => {
    if (animatingRef.current) return;
    startRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    axisRef.current = null;
    setDragging(true);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!startRef.current) return;
    const dx = e.touches[0].clientX - startRef.current.x;
    const dy = e.touches[0].clientY - startRef.current.y;

    // Определяем ось жеста после небольшого сдвига и фиксируем её.
    if (!axisRef.current) {
      if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
        axisRef.current = Math.abs(dx) > Math.abs(dy) ? "h" : "v";
      } else {
        return;
      }
    }

    if (axisRef.current === "h") {
      let ddx = dx;
      // Сопротивление на краях списка (нет соседнего кадра).
      if ((dx > 0 && !hasPrev) || (dx < 0 && !hasNext)) ddx = dx * 0.3;
      setOffset({ x: ddx, y: 0 });
    } else {
      setOffset({ x: 0, y: dy });
    }
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const start = startRef.current;
    const axis = axisRef.current;
    startRef.current = null;
    axisRef.current = null;
    setDragging(false);

    if (!start || !axis) {
      setOffset({ x: 0, y: 0 });
      return;
    }

    const dx = e.changedTouches[0].clientX - start.x;
    const dy = e.changedTouches[0].clientY - start.y;

    if (axis === "h") {
      const w = window.innerWidth;
      // Сдвинули больше четверти экрана → листаем, иначе пружиним обратно.
      if (dx <= -w * 0.22 && hasNext) animateNext();
      else if (dx >= w * 0.22 && hasPrev) animatePrev();
      else setOffset({ x: 0, y: 0 });
    } else {
      if (Math.abs(dy) > 120) closeWithAnim(dy > 0 ? 1 : -1);
      else setOffset({ x: 0, y: 0 });
    }
  };

  // Клавиатура: ← предыдущий, → следующий, Esc закрыть. Блокировка прокрутки фона.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft") animatePrev();
      else if (e.key === "ArrowRight") animateNext();
    };
    document.addEventListener("keydown", onKey);

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, products.length]);

  if (!product) return null;

  // Прозрачность фона: при вертикальном свайпе плавно гаснет.
  const fade =
    axisRef.current === "v" ? Math.min(Math.abs(offset.y) / 600, 0.6) : 0;

  // Один кадр «плёнки» с фото и подписью. null → пустой (на краях списка).
  const renderSlide = (p: Product | null, key: string) => {
    if (!p) return <div key={key} className="h-full w-screen shrink-0" />;
    const packaging = getPackaging(p.group, p.name);
    return (
      <div key={key} className="flex h-full w-screen shrink-0 flex-col">
        {/* Область фото. Клик по чёрным полям закрывает, по фото — нет. */}
        <div className="flex flex-1 items-center justify-center overflow-hidden p-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={getHiResUrl(p.imageUrl as string)}
            alt={p.name}
            draggable={false}
            className="max-h-full max-w-full select-none object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
        {/* Подпись снизу: название + цена + фасовка */}
        <div className="px-5 pb-6 pt-2 text-center text-white" onClick={(e) => e.stopPropagation()}>
          <p className="text-base font-medium leading-snug">{p.name}</p>
          <p className="mt-1 text-lg font-bold">
            {effectivePrice(p, priceForm).toFixed(2)} ₽
            {packaging && (
              <span className="ml-2 text-sm font-normal text-white/70">{packaging}</span>
            )}
          </p>
        </div>
      </div>
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden"
      style={{
        backgroundColor: `rgba(0,0,0,${0.9 - fade})`,
        touchAction: "none",
      }}
      onClick={onClose}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      role="dialog"
      aria-modal="true"
      aria-label={product.name}
    >
      {/* Кнопка закрытия */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
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
            animatePrev();
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
            animateNext();
          }}
          className="absolute right-2 top-1/2 z-10 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-3xl leading-none text-white hover:bg-white/20 focus:outline-none"
          aria-label="Следующее фото"
        >
          ›
        </button>
      )}

      {/* «Плёнка» из трёх кадров. Центрирована смещением -100vw,
          поверх него добавляется смещение пальца offset. */}
      <div
        className="flex h-full"
        style={{
          transform: `translate3d(calc(-100vw + ${offset.x}px), ${offset.y}px, 0)`,
          transition: dragging || instant ? "none" : `transform ${DURATION}ms ease`,
        }}
      >
        {renderSlide(hasPrev ? products[index - 1] : null, "prev")}
        {renderSlide(product, "cur")}
        {renderSlide(hasNext ? products[index + 1] : null, "next")}
      </div>
    </div>
  );
}
