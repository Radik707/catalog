// Подсказка по ручной установке PWA — зависит от браузера.
// Назначение: у каждого мобильного браузера свой пункт меню для установки/
// добавления на главный экран и свои формулировки. Этот помощник по строке
// User-Agent определяет браузер и возвращает точную инструкцию, чтобы шторка
// в InstallPrompt.tsx показывала шаги именно под текущий браузер.
//
// Используется как запасной путь, когда системное окно установки недоступно
// (браузер его не поддерживает ИЛИ временно блокирует после отказа).

/** Готовая подсказка под конкретный браузер */
export interface InstallHint {
  /** Отображаемое имя браузера (для заголовка/текста) */
  browser: string;
  /** Шаги инструкции — показываются нумерованным списком */
  steps: string[];
  /**
   * true — в этом браузере «ярлык» открывается обычной вкладкой (не на весь
   * экран). Тогда дополнительно советуем Chrome для полноэкранного приложения.
   * Пример: Яндекс.Браузер добавляет закладку-ярлык, а не настоящее PWA.
   */
  recommendChrome: boolean;
}

/**
 * Определяет браузер по User-Agent и возвращает инструкцию по установке.
 * Порядок проверок важен: специфичные браузеры (Yandex/Opera/Samsung/Edge)
 * содержат «Chrome» в UA, поэтому их проверяем ДО обычного Chrome.
 */
export function getInstallHint(ua: string): InstallHint {
  const isYandex = /YaBrowser/i.test(ua);
  const isOpera = /OPR\/|OPiOS|Opera/i.test(ua);
  const isSamsung = /SamsungBrowser/i.test(ua);
  const isEdge = /Edg(A|iOS)?\//i.test(ua);
  const isFirefox = /Firefox|FxiOS/i.test(ua);
  const isChrome =
    /Chrome|CriOS/i.test(ua) &&
    !isYandex &&
    !isOpera &&
    !isSamsung &&
    !isEdge;

  if (isYandex) {
    return {
      browser: "Яндекс.Браузер",
      steps: [
        "Откройте меню браузера — три точки ⋮ вверху",
        "Выберите «Добавить ярлык на рабочий стол» и подтвердите",
      ],
      recommendChrome: true, // ярлык в Яндексе открывается во вкладке, не на весь экран
    };
  }

  if (isOpera) {
    return {
      browser: "Opera",
      steps: [
        "Откройте меню Opera (значок Opera внизу или ⋮)",
        "Выберите «Добавить на» → «Главный экран» и подтвердите",
      ],
      recommendChrome: false,
    };
  }

  if (isSamsung) {
    return {
      browser: "Samsung Internet",
      steps: [
        "Откройте меню — три полоски ☰ внизу",
        "Выберите «Добавить страницу на» → «Главный экран»",
      ],
      recommendChrome: false,
    };
  }

  if (isEdge) {
    return {
      browser: "Microsoft Edge",
      steps: [
        "Откройте меню — три точки ··· внизу",
        "Выберите «Добавить на телефон» → «Установить»",
      ],
      recommendChrome: false,
    };
  }

  if (isFirefox) {
    return {
      browser: "Firefox",
      steps: [
        "Откройте меню — три точки ⋮ вверху",
        "Выберите «Установить» или «Добавить на главный экран»",
      ],
      recommendChrome: false,
    };
  }

  if (isChrome) {
    return {
      browser: "Chrome",
      steps: [
        "Откройте меню браузера — три точки ⋮ вверху справа",
        "Выберите «Установить приложение» и подтвердите",
      ],
      recommendChrome: false,
    };
  }

  // Неизвестный браузер — универсальная подсказка со всеми вариантами названий
  return {
    browser: "ваш браузер",
    steps: [
      "Откройте меню браузера (⋮ или ☰)",
      "Найдите пункт «Установить приложение», «Добавить на главный экран» или «Добавить ярлык на рабочий стол» и подтвердите",
    ],
    recommendChrome: false,
  };
}
