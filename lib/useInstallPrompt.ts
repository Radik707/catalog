"use client";

// Хук-детектор платформы установки и состояния подсказки «Добавить на экран».
// ПОЧЕМУ отдельный хук: логику детекта платформы и хранение события beforeinstallprompt
// нужно держать в одном месте — баннер (план 02) и кнопка настроек (план 02) делят
// ОДНО перехваченное событие. Хук вызывается ровно один раз в InstallPromptProvider.
//
// Поддерживаемые платформы:
//  - android  → есть событие beforeinstallprompt (Chrome/Edge на Android)
//  - ios      → iPhone/iPad без standalone (Safari; своя инструкция «Поделиться → Домой»)
//  - installed → приложение уже запущено в режиме standalone (установлено)
//  - unsupported → ни одно из условий не выполнено (Desktop Chrome до события, Firefox и т.д.)

import { useState, useEffect, useRef, useCallback } from "react";

// Расширяем тип Event, чтобы TypeScript знал о prompt() и userChoice.
// Этот интерфейс — браузерный стандарт, но в @types/web он добавлен не везде.
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  readonly userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

/** Тип платформы, определяемой хуком при монтировании */
export type InstallPlatform =
  | "android"
  | "ios"
  | "installed"
  | "unsupported";

/** Полный результат хука — всё, что нужно баннеру и кнопке настроек */
export interface UseInstallPromptResult {
  /** Определённая платформа установки */
  platform: InstallPlatform;
  /** true — событие beforeinstallprompt перехвачено и ещё не использовано */
  canPromptAndroid: boolean;
  /** true — приложение запущено в standalone-режиме (уже установлено) */
  isStandalone: boolean;
  /** true — пользователь ранее закрыл подсказку (флаг из localStorage) */
  dismissed: boolean;
  /** true — сработал сигнал вовлечённости: прошёл таймер ИЛИ был скролл */
  engaged: boolean;
  /**
   * true — шторка открыта принудительно из панели настроек (D-05).
   * Игнорирует dismissed и engaged — пользователь сам попросил показать.
   */
  forceOpen: boolean;
  /**
   * Вызывает нативный диалог установки Android.
   * Обнуляет сохранённое событие после использования.
   */
  promptInstall: () => Promise<void>;
  /**
   * Ставит флаг «закрыто» — баннер больше не появляется автоматически.
   * Пишет флаг в localStorage (обёрнуто в try/catch — грабли приватного режима iOS).
   */
  dismiss: () => void;
  /**
   * Открывает iOS-шторку из панели настроек (D-05).
   * Устанавливает forceOpen=true — шторка показывается даже при dismissed.
   * На Android — вызывает promptInstall() напрямую.
   */
  openFromSettings: () => Promise<void>;
}

/** Ключ localStorage для флага «подсказка закрыта» */
const DISMISSED_KEY = "pwa-install-dismissed";

/** Порог скролла (px) для сигнала вовлечённости */
const SCROLL_THRESHOLD = 100;

/** Таймер вовлечённости (мс) — 25 секунд */
const ENGAGEMENT_TIMER_MS = 25_000;

/**
 * useInstallPrompt — обнаруживает платформу установки и управляет состоянием
 * подсказки «Добавить каталог на экран».
 *
 * SSR-safe: все обращения к window/navigator — внутри useEffect (только клиент).
 * Начальные значения нейтральны — не вызывают мигания при гидратации.
 */
export function useInstallPrompt(): UseInstallPromptResult {
  // Платформа — начальное значение «unsupported» (нейтральное, безопасно для SSR)
  const [platform, setPlatform] = useState<InstallPlatform>("unsupported");

  // true — приложение в standalone (уже установлено)
  const [isStandalone, setIsStandalone] = useState<boolean>(false);

  // true — событие beforeinstallprompt перехвачено и доступно для вызова
  const [canPromptAndroid, setCanPromptAndroid] = useState<boolean>(false);

  // true — пользователь ранее закрыл подсказку (читается из localStorage)
  const [dismissed, setDismissed] = useState<boolean>(false);

  // true — сработал сигнал вовлечённости (таймер или скролл)
  const [engaged, setEngaged] = useState<boolean>(false);

  // true — шторка открыта принудительно из панели настроек (D-05)
  const [forceOpen, setForceOpen] = useState<boolean>(false);

  // Сохранённое событие beforeinstallprompt — в ref, чтобы promptInstall()
  // имел к нему доступ без лишних ре-рендеров.
  const deferredPromptRef = useRef<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    // Всё, что связано с window/navigator — только на клиенте.
    if (typeof window === "undefined") return;

    // --- Детект standalone (D-04) ---
    // matchMedia — стандарт; navigator.standalone — Safari-специфика для iOS.
    const standaloneQuery = window.matchMedia("(display-mode: standalone)");
    const standaloneNow =
      standaloneQuery.matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true;

    setIsStandalone(standaloneNow);

    if (standaloneNow) {
      // Уже установлено — остальная логика не нужна
      setPlatform("installed");
      return;
    }

    // --- Чтение флага dismissed из localStorage (D-04) ---
    // Оборачиваем в try/catch: приватный режим iOS бросает исключение (T-12-02).
    try {
      const stored = localStorage.getItem(DISMISSED_KEY);
      if (stored === "1") {
        setDismissed(true);
      }
    } catch {
      // В приватном режиме iOS localStorage недоступен — деградируем к «показать как обычно»
    }

    // --- Детект iOS (D-03) ---
    // UA содержит iPhone/iPad/iPod И не находимся в standalone.
    const ua = navigator.userAgent;
    const isIosSafari = /iPhone|iPad|iPod/.test(ua);

    if (isIosSafari) {
      setPlatform("ios");
      // На iOS нет beforeinstallprompt — продолжаем только для сигнала вовлечённости
    }

    // --- Детект Android (D-02) ---
    // Слушаем beforeinstallprompt — браузер пришлёт его сам, если все критерии выполнены.
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault(); // Отключаем дефолтный мини-баннер браузера
      deferredPromptRef.current = e as BeforeInstallPromptEvent;
      setPlatform("android");
      setCanPromptAndroid(true);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);

    // --- Сигнал вовлечённости (D-01) ---
    // Ставим engaged=true при первом из двух событий: таймер ИЛИ скролл.
    let engagementFired = false;

    const fireEngagement = () => {
      if (engagementFired) return;
      engagementFired = true;
      setEngaged(true);
    };

    // Таймер — 25 секунд на странице
    const timer = setTimeout(fireEngagement, ENGAGEMENT_TIMER_MS);

    // Скролл — порог SCROLL_THRESHOLD px (что бы ни наступило раньше)
    const handleScroll = () => {
      if (window.scrollY >= SCROLL_THRESHOLD) {
        fireEngagement();
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });

    // --- Cleanup ---
    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("scroll", handleScroll);
      clearTimeout(timer);
    };
  }, []); // Эффект без зависимостей — запускается один раз при монтировании

  /**
   * Вызывает нативный диалог установки Android.
   * После использования обнуляет сохранённое событие (нельзя вызвать дважды).
   */
  const promptInstall = useCallback(async () => {
    const prompt = deferredPromptRef.current;
    if (!prompt) return;

    // Вызываем нативный промпт браузера
    await prompt.prompt();

    // Ждём выбора пользователя
    const { outcome } = await prompt.userChoice;

    // Независимо от выбора — событие использовано, обнуляем
    deferredPromptRef.current = null;
    setCanPromptAndroid(false);

    if (outcome === "accepted") {
      // Пользователь принял — ставим флаг «уже установлено»
      setPlatform("installed");
      setIsStandalone(true);
    }
    // При dismissed — баннер сам закроет себя через dismiss()
  }, []);

  /**
   * Закрывает подсказку и запоминает это навсегда в localStorage.
   * Баннер не появится при следующих визитах.
   * Также сбрасывает forceOpen — шторка закрывается даже при принудительном открытии.
   */
  const dismiss = useCallback(() => {
    setDismissed(true);
    setForceOpen(false);
    // Оборачиваем в try/catch — приватный режим iOS (T-14-01, T-12-02)
    try {
      localStorage.setItem(DISMISSED_KEY, "1");
    } catch {
      // Деградируем молча: флаг живёт только в памяти сессии
    }
  }, []);

  /**
   * Открывает подсказку из панели настроек (D-05).
   * На iOS — устанавливает forceOpen=true, шторка появится даже при dismissed.
   * На Android — вызывает нативный диалог установки напрямую.
   */
  const openFromSettings = useCallback(async () => {
    if (platform === "ios") {
      // Сбрасываем dismissed чтобы dismiss() из шторки мог снова его поставить
      setForceOpen(true);
    } else if (platform === "android") {
      // Для Android сразу вызываем нативный диалог
      await promptInstall();
    }
  }, [platform, promptInstall]);

  return {
    platform,
    canPromptAndroid,
    isStandalone,
    dismissed,
    engaged,
    forceOpen,
    promptInstall,
    dismiss,
    openFromSettings,
  };
}
