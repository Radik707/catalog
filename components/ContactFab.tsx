"use client";

import { useEffect, useState } from "react";
import { useOnlineStatus } from "@/lib/useOnlineStatus";
// Роль пользователя: для «Клиента» поднимаем FAB выше нижней панели вкладок (D-10)
import { useRole } from "@/lib/useRole";

// Ники каналов из окружения (как было у отдельных кнопок).
const BOT_USERNAME = process.env.NEXT_PUBLIC_BOT_USERNAME; // Telegram
const MAX_BOT = process.env.NEXT_PUBLIC_MAX_BOT; // MAX

// SVG-глиф Telegram (самолётик)
function TelegramGlyph({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L7.17 13.67l-2.96-.924c-.64-.203-.658-.64.136-.954l11.57-4.461c.537-.194 1.006.131.978.89z" />
    </svg>
  );
}

// SVG-глиф MAX (чат-облако)
function MaxGlyph({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 2C6.477 2 2 5.94 2 10.8c0 2.77 1.46 5.24 3.75 6.86-.13 1.1-.6 2.5-1.45 3.62-.18.24 0 .58.3.52 1.86-.4 3.5-1.1 4.6-1.86.9.2 1.84.31 2.8.31 5.523 0 10-3.94 10-8.8S17.523 2 12 2z" />
    </svg>
  );
}

export default function ContactFab() {
  // open — раскрыт ли FAB на отдельные иконки
  const [open, setOpen] = useState(false);
  const [pulse, setPulse] = useState(false);
  // Состояние сети: офлайн → FAB приглушён и не раскрывается (как раньше у кнопок).
  const isOnline = useOnlineStatus();
  // Роль: для «Клиента» поднимаем контейнер выше нижней панели вкладок (D-10, план 18-02).
  // До ready флаг не критичен — кнопка просто остаётся на bottom-6 (без мелькания).
  const { role } = useRole();

  useEffect(() => {
    // Пульсация основной иконки при первом визите
    const visited = sessionStorage.getItem("contact_fab_seen");
    if (!visited) {
      setPulse(true);
      sessionStorage.setItem("contact_fab_seen", "1");
      const t = setTimeout(() => setPulse(false), 5000);
      return () => clearTimeout(t);
    }
  }, []);

  // Если оба канала не настроены — кнопку не показываем вовсе.
  if (!BOT_USERNAME && !MAX_BOT) return null;

  // Открыть чат Telegram: пробуем приложение через tg://, иначе веб-версия.
  function openTelegram() {
    setOpen(false);
    const appUrl = `tg://resolve?domain=${BOT_USERNAME}`;
    const webUrl = `https://t.me/${BOT_USERNAME}`;
    window.location.href = appUrl;
    // Запасной вариант: если приложение не установлено — через 1.5 с откроем веб.
    // Если приложение перехватило переход (вкладка ушла в фон) — отменяем веб-вкладку.
    const timer = setTimeout(() => window.open(webUrl, "_blank"), 1500);
    const cancelFallback = () => {
      if (document.hidden) clearTimeout(timer);
    };
    document.addEventListener("visibilitychange", cancelFallback, { once: true });
  }

  // Открыть чат MAX: universal link https://max.ru/<bot> (приложение или веб сам выберет).
  function openMax() {
    setOpen(false);
    window.open(`https://max.ru/${MAX_BOT}`, "_blank");
  }

  // Тап по основной иконке: офлайн — игнор; иначе раскрыть/свернуть.
  function toggle() {
    if (!isOnline) return;
    setOpen((v) => !v);
  }

  // Класс анимации появления дочерней иконки (выезжает снизу-вверх).
  const childCls = (shown: boolean) =>
    `absolute right-0 transition-all duration-200 ease-out ${
      shown ? "opacity-100 translate-y-0 pointer-events-auto" : "opacity-0 translate-y-3 pointer-events-none"
    }`;

  // Позиция контейнера: для «Клиента» поднимаем выше панели вкладок (64px + запас),
  // для «Торгового» оставляем исходный bottom-6. Дочерние иконки позиционированы
  // относительно контейнера, поэтому смещаются вместе с ним автоматически (D-10).
  const fabBottomClass = role === "client" ? "bottom-24" : "bottom-6";

  return (
    <>
      {/* Прозрачная подложка: тап мимо — свернуть. Только когда раскрыто. */}
      {open && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      <div className={`fixed ${fabBottomClass} right-4 z-50`}>
        {/* Дочерняя иконка MAX — выше всех */}
        {MAX_BOT && (
          <button
            onClick={openMax}
            className={`${childCls(open)} bottom-[10.5rem] w-14 h-14 rounded-full shadow-lg flex items-center justify-center text-white bg-gradient-to-br from-[#2D9CFF] to-[#9B4DFF] hover:scale-110 active:scale-95`}
            aria-label="Написать в MAX"
            title="💬 Написать в MAX"
          >
            <MaxGlyph className="w-7 h-7" />
          </button>
        )}

        {/* Дочерняя иконка Telegram */}
        {BOT_USERNAME && (
          <button
            onClick={openTelegram}
            className={`${childCls(open)} bottom-[5.5rem] w-14 h-14 rounded-full shadow-lg flex items-center justify-center text-white bg-[#0088cc] hover:scale-110 active:scale-95`}
            aria-label="Написать в Telegram"
            title="💬 Написать в Telegram"
          >
            <TelegramGlyph className="w-7 h-7" />
          </button>
        )}

        {/* Основная иконка: половина Telegram + половина MAX. По тапу — раскрытие. */}
        <button
          onClick={toggle}
          disabled={!isOnline}
          className={`relative w-14 h-14 rounded-full shadow-lg overflow-hidden transition-transform
            ${isOnline ? `hover:scale-110 active:scale-95 ${pulse && !open ? "animate-pulse" : ""}` : "opacity-50 cursor-not-allowed"}`}
          aria-label={isOnline ? (open ? "Свернуть" : "Связаться с нами") : "Нет сети"}
          aria-expanded={open}
          title={isOnline ? "Связаться с нами" : "Нет сети"}
        >
          {open ? (
            // Раскрыто — показываем «×» на нейтральном фоне
            <span className="absolute inset-0 flex items-center justify-center bg-gray-700 text-white text-2xl leading-none">
              ×
            </span>
          ) : (
            // Свёрнуто — две половины: слева Telegram, справа MAX
            <>
              <span className="absolute inset-y-0 left-0 w-1/2 flex items-center justify-center bg-[#0088cc] text-white">
                <TelegramGlyph className="w-5 h-5 -mr-1" />
              </span>
              <span className="absolute inset-y-0 right-0 w-1/2 flex items-center justify-center bg-gradient-to-br from-[#2D9CFF] to-[#9B4DFF] text-white">
                <MaxGlyph className="w-5 h-5 -ml-1" />
              </span>
              {/* Тонкая белая разделительная полоса по центру */}
              <span className="absolute inset-y-1 left-1/2 w-px -translate-x-1/2 bg-white/60" />
            </>
          )}
        </button>
      </div>
    </>
  );
}
