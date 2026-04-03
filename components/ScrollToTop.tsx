"use client";

import { useState, useEffect, useRef } from "react";

interface ScrollToTopProps {
  viewMode: "list" | "grid";
}

export default function ScrollToTop({ viewMode }: ScrollToTopProps) {
  const [visible, setVisible] = useState(false);
  const [clickable, setClickable] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const threshold = viewMode === "grid" ? 1800 : 1500;

  useEffect(() => {
    const onScroll = () => {
      const shouldShow = window.scrollY > threshold;

      setVisible((prev) => {
        if (shouldShow === prev) return prev;

        if (shouldShow) {
          // Стала видимой — разрешить клик через 500ms
          timerRef.current = setTimeout(() => setClickable(true), 500);
        } else {
          // Скрылась — сразу запретить клик
          if (timerRef.current) clearTimeout(timerRef.current);
          setClickable(false);
        }

        return shouldShow;
      });
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [threshold]);

  return (
    <button
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      aria-label="Прокрутить вверх"
      style={{
        position: "fixed",
        top: "16px",
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 50,
        width: "44px",
        height: "44px",
        borderRadius: "50%",
        opacity: visible ? 0.5 : 0,
        pointerEvents: visible && clickable ? "auto" : "none",
        transition: "opacity 300ms ease",
      }}
      className="flex items-center justify-center bg-gray-800 text-white shadow-lg active:opacity-80"
    >
      <svg
        className="w-5 h-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2.5}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
      </svg>
    </button>
  );
}
