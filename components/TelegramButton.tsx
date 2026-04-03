"use client";

import { useEffect, useState } from "react";

const BOT_USERNAME = process.env.NEXT_PUBLIC_BOT_USERNAME;

export default function TelegramButton() {
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    // Анимация пульсации при первом посещении
    const visited = sessionStorage.getItem("tg_btn_seen");
    if (!visited) {
      setPulse(true);
      sessionStorage.setItem("tg_btn_seen", "1");
      const timer = setTimeout(() => setPulse(false), 5000);
      return () => clearTimeout(timer);
    }
  }, []);

  if (!BOT_USERNAME) return null;

  function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    // Пробуем открыть Telegram-приложение через tg:// протокол
    const appUrl = `tg://resolve?domain=${BOT_USERNAME}`;
    const webUrl = `https://t.me/${BOT_USERNAME}`;
    window.location.href = appUrl;
    // Если приложение не установлено — через 1.5 сек открываем веб-версию
    setTimeout(() => {
      window.open(webUrl, "_blank");
    }, 1500);
  }

  return (
    <button
      onClick={handleClick}
      className={`fixed bottom-6 right-4 z-50 flex items-center justify-center w-14 h-14 rounded-full shadow-lg bg-[#0088cc] text-white transition-transform hover:scale-110 active:scale-95 ${pulse ? "animate-pulse" : ""}`}
      aria-label="Открыть Telegram-помощника"
      title="💬 Спросить помощника"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="currentColor"
        className="w-7 h-7"
      >
        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L7.17 13.67l-2.96-.924c-.64-.203-.658-.64.136-.954l11.57-4.461c.537-.194 1.006.131.978.89z" />
      </svg>
    </button>
  );
}
