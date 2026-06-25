"use client";

import { useEffect, useState } from "react";
import { useOnlineStatus } from "@/lib/useOnlineStatus";

// Ник бота MAX берём из окружения (как у Telegram-кнопки).
// Если не задан — кнопка не рендерится (фича выключена).
const MAX_BOT = process.env.NEXT_PUBLIC_MAX_BOT;

export default function MaxButton() {
  const [pulse, setPulse] = useState(false);
  // Хук состояния сети — true при наличии подключения, false в офлайне.
  // Поведение синхронно с TelegramButton: офлайн → кнопка приглушена и не кликается.
  const isOnline = useOnlineStatus();

  useEffect(() => {
    // Анимация пульсации при первом посещении (отдельный ключ от Telegram-кнопки).
    const visited = sessionStorage.getItem("max_btn_seen");
    if (!visited) {
      setPulse(true);
      sessionStorage.setItem("max_btn_seen", "1");
      const timer = setTimeout(() => setPulse(false), 5000);
      return () => clearTimeout(timer);
    }
  }, []);

  if (!MAX_BOT) return null;

  function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    // У MAX ссылка https://max.ru/<bot> — это universal link: если приложение
    // установлено, откроется оно, иначе — веб-версия max.ru. Отдельная схема
    // max:// и ручной fallback (как tg:// у Telegram) не нужны.
    window.open(`https://max.ru/${MAX_BOT}`, "_blank");
  }

  return (
    <button
      // Офлайн: onClick не вызывается (кнопка не открывает MAX).
      onClick={isOnline ? handleClick : undefined}
      disabled={!isOnline}
      // Плавающая иконка расположена НАД кнопкой Telegram (bottom-24 против bottom-6),
      // чтобы две иконки не перекрывались и стояли стопкой в правом нижнем углу.
      // Фон — фирменный сине-фиолетовый градиент MAX.
      className={`fixed bottom-24 right-4 z-50 flex items-center justify-center w-14 h-14 rounded-full shadow-lg bg-gradient-to-br from-[#2D9CFF] to-[#9B4DFF] text-white transition-transform
        ${isOnline ? `hover:scale-110 active:scale-95 ${pulse ? "animate-pulse" : ""}` : "opacity-50 cursor-not-allowed"}`}
      aria-label={isOnline ? "Открыть чат в MAX" : "Нет сети"}
      title={isOnline ? "💬 Написать нам в MAX" : "Нет сети — откройте MAX при подключении"}
    >
      {/* Иконка чат-облака (универсальный знак мессенджера). Реальный логотип MAX
          можно подставить позже отдельным SVG — на поведение кнопки не влияет. */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="currentColor"
        className="w-7 h-7"
      >
        <path d="M12 2C6.477 2 2 5.94 2 10.8c0 2.77 1.46 5.24 3.75 6.86-.13 1.1-.6 2.5-1.45 3.62-.18.24 0 .58.3.52 1.86-.4 3.5-1.1 4.6-1.86.9.2 1.84.31 2.8.31 5.523 0 10-3.94 10-8.8S17.523 2 12 2z" />
      </svg>
    </button>
  );
}
