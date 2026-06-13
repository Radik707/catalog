"use client";

// Клиентский компонент-«остров»: баннер установки PWA.
// Два режима (по платформе, D-02/D-03 из CONTEXT.md):
//   1. Android: фирменный баннер снизу с кнопкой «Установить» → системный диалог.
//   2. iOS:     bottom-sheet с пошаговой инструкцией «Поделиться → На экран Домой».
//
// Условие показа: НЕ показываем, если:
//   - isStandalone (приложение уже установлено, D-04)
//   - dismissed    (пользователь уже закрыл, D-04)
//   - !engaged     (сигнал вовлечённости ещё не наступил, D-01)
//   - platform === "installed" или "unsupported"
//   - Android: дополнительно проверяем canPromptAndroid
//
// forceOpen (D-05): открывает шторку принудительно из панели настроек,
// даже если dismissed — пользователь сам попросил показать.
//
// Позиционирование: fixed bottom-0, z-[60] — выше контента и выше
// плавающей кнопки Telegram (z-50), чтобы баннер/шторка не перекрывались
// ей в нижнем углу (WR-01). Safe-area (D-07): pb-[env(safe-area-inset-bottom)].
// Брендинг (D-08): белый фон, синий акцент bg-blue-600.

import { useInstallPromptContext } from "@/components/InstallPromptProvider";
// Подсказка по ручной установке под конкретный браузер (Яндекс, Opera, Chrome…)
import { getInstallHint } from "@/lib/browserInstallHint";

export default function InstallPrompt() {
  const {
    platform,
    canPromptAndroid,
    isStandalone,
    dismissed,
    engaged,
    forceOpen,
    promptInstall,
    showInstallHelp,
    dismiss,
  } = useInstallPromptContext();

  // Уже установлено или неподдерживаемая платформа — ничего не показываем
  if (isStandalone || platform === "installed" || platform === "unsupported") {
    return null;
  }

  // Android: авто-баннер показываем при перехваченном событии + вовлечённости
  // и пока не закрыт (D-01). Исключение — forceOpen из настроек, когда события
  // нет (уже использовано ИЛИ Chrome «на паузе» после отказа): тогда ниже
  // покажем инструкцию-шторку про меню браузера.
  if (platform === "android") {
    const showAutoBanner = canPromptAndroid && engaged && !dismissed;
    const showManualSheet = forceOpen && !canPromptAndroid;
    if (!showAutoBanner && !showManualSheet) {
      return null;
    }
  }

  // iOS: ждём сигнала вовлечённости; forceOpen игнорирует dismissed (D-05)
  if (platform === "ios") {
    if (!engaged && !forceOpen) {
      return null;
    }
    if (dismissed && !forceOpen) {
      return null;
    }
  }

  // -----------------------------------------------------------------------
  // Ветка Android — инструкция по ручной установке (forceOpen без события).
  // Возникает, когда пользователь нажал «Установить приложение» в настройках,
  // а системное окно недоступно (событие использовано / Chrome на «паузе»
  // после отказа). Показываем, как поставить через меню браузера.
  // -----------------------------------------------------------------------
  if (platform === "android" && forceOpen && !canPromptAndroid) {
    // Определяем браузер и берём инструкцию именно под него (Яндекс, Opera,
    // Samsung, Firefox, Edge, Chrome или универсальную). navigator доступен —
    // шторка рендерится только на клиенте по действию пользователя.
    const hint =
      typeof navigator !== "undefined"
        ? getInstallHint(navigator.userAgent)
        : getInstallHint("");

    return (
      <div
        className="fixed bottom-0 left-0 right-0 z-[60] bg-white shadow-[0_-4px_16px_rgba(0,0,0,0.15)] rounded-t-2xl animate-[slideUp_0.25s_ease-out]"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        <div className="max-w-screen-2xl mx-auto px-5 pt-4 pb-3">
          {/* Шапка: заголовок + крестик */}
          <div className="flex items-center justify-between mb-3">
            <p className="text-base font-semibold text-gray-900">
              Установить приложение
            </p>
            <button
              onClick={dismiss}
              aria-label="Закрыть инструкцию установки"
              className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-600 transition-colors rounded-full hover:bg-gray-100"
            >
              ✕
            </button>
          </div>

          {/* ГЛАВНЫЙ путь — скачать готовое приложение (.apk).
              Работает с ЛЮБОГО браузера, включая Яндекс: скачал файл →
              открыл → разрешил установку → приложение на весь экран. */}
          <a
            href="/app/vkusnyi-dom.apk"
            download="vkusnyi-dom.apk"
            className="block w-full py-3 mb-2 text-center text-sm font-semibold text-white bg-blue-600 rounded-lg transition-colors hover:bg-blue-700 active:bg-blue-800"
          >
            ⬇ Скачать приложение
          </a>
          <p className="text-xs text-gray-500 mb-4">
            После скачивания откройте файл и нажмите «Установить». Если телефон
            предупредит про «неизвестный источник» — это нормально, разрешите
            установку один раз. Приложение появится на главном экране и откроется
            на весь экран.
          </p>

          {/* Запасной путь — через меню браузера */}
          <p className="text-xs font-medium text-gray-400 mb-2">
            Или вручную{hint.browser === "ваш браузер" ? "" : ` (${hint.browser})`}:
          </p>

          {/* Инструкция: шаги под конкретный браузер */}
          <div className="space-y-3 mb-4">
            {hint.steps.map((step, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="shrink-0 w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center mt-0.5">
                  {i + 1}
                </div>
                <p className="text-sm text-gray-800">{step}</p>
              </div>
            ))}
          </div>

          {/* Если у браузера нет полноэкранной установки (напр. Яндекс) —
              честно объясняем и даём кнопку «Открыть в Chrome», где приложение
              ставится по-настоящему (на весь экран). */}
          {hint.recommendChrome && (
            <div className="mb-3">
              <p className="text-xs text-gray-500 mb-2 bg-blue-50 rounded-lg px-3 py-2">
                💡 Этот браузер добавляет только ярлык-вкладку — настоящее
                приложение на весь экран он ставить не умеет. Это умеет{" "}
                <span className="font-semibold">Chrome</span>: откройте каталог
                там и нажмите «Установить приложение».
              </p>
              <button
                onClick={() => {
                  // Открываем текущую страницу в Chrome через Android-intent.
                  // Если Chrome не установлен — fallback на обычное открытие по https.
                  const path =
                    window.location.host +
                    window.location.pathname +
                    window.location.search;
                  const fallback = encodeURIComponent(window.location.href);
                  window.location.href =
                    `intent://${path}#Intent;scheme=https;package=com.android.chrome;` +
                    `S.browser_fallback_url=${fallback};end`;
                }}
                className="w-full py-2.5 text-sm font-semibold text-white bg-blue-600 rounded-lg transition-colors hover:bg-blue-700 active:bg-blue-800"
              >
                Открыть в Chrome для установки
              </button>
            </div>
          )}

          {/* Подсказка про «паузу» браузера после отказа */}
          <p className="text-xs text-gray-400 mb-3">
            Если всплывающая кнопка «Установить» не срабатывает — браузер временно
            блокирует своё окно после отказа. Меню браузера работает всегда.
          </p>

          <button
            onClick={dismiss}
            className="w-full py-2.5 text-sm font-medium text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Понятно
          </button>
        </div>
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Ветка Android — фирменный баннер снизу (D-02)
  // -----------------------------------------------------------------------
  if (platform === "android") {
    return (
      // Внешний контейнер: fixed снизу, полная ширина, фирменные цвета
      <div
        className="fixed bottom-0 left-0 right-0 z-[60] bg-white shadow-[0_-4px_12px_rgba(0,0,0,0.12)] rounded-t-2xl"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        {/* Внутреннее содержимое: горизонтальная компоновка */}
        <div className="max-w-screen-2xl mx-auto px-4 py-3 flex items-center gap-3">
          {/* Иконка приложения */}
          <div className="shrink-0 w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center">
            <span className="text-2xl text-white select-none">📦</span>
          </div>

          {/* Текст приглашения */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 leading-tight">
              Добавьте каталог на экран
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              Открывайте одним касанием, работает офлайн
            </p>
          </div>

          {/* Кнопка установки */}
          <button
            onClick={async () => {
              // Пробуем системное окно установки Android.
              const outcome = await promptInstall();
              // Если браузер не показал окно (отказ ранее / «пауза» / нет
              // поддержки) — открываем шторку с инструкцией по ручной установке,
              // чтобы нажатие не было «пустым».
              if (outcome !== "accepted") {
                showInstallHelp();
              }
              // При accepted хук переключит platform="installed" — баннер исчезнет.
            }}
            className="shrink-0 px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg transition-colors hover:bg-blue-700 active:bg-blue-800"
          >
            Установить
          </button>

          {/* Крестик «Позже» */}
          <button
            onClick={dismiss}
            aria-label="Закрыть подсказку об установке"
            className="shrink-0 w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-600 transition-colors rounded-full hover:bg-gray-100"
          >
            ✕
          </button>
        </div>
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Ветка iOS — bottom-sheet с инструкцией (D-03)
  // -----------------------------------------------------------------------
  if (platform === "ios") {
    return (
      // Внешний контейнер: fixed снизу, белый фон, скруглённые верхние углы, тень
      <div
        className="fixed bottom-0 left-0 right-0 z-[60] bg-white shadow-[0_-4px_16px_rgba(0,0,0,0.15)] rounded-t-2xl animate-[slideUp_0.25s_ease-out]"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        <div className="max-w-screen-2xl mx-auto px-5 pt-4 pb-3">
          {/* Шапка шторки: заголовок + крестик */}
          <div className="flex items-center justify-between mb-3">
            <p className="text-base font-semibold text-gray-900">
              Добавить каталог на экран
            </p>
            <button
              onClick={dismiss}
              aria-label="Закрыть инструкцию установки"
              className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-600 transition-colors rounded-full hover:bg-gray-100"
            >
              ✕
            </button>
          </div>

          {/* Пошаговая инструкция (D-03): понятна без техзнаний */}
          <div className="space-y-3 mb-4">
            {/* Шаг 1 */}
            <div className="flex items-start gap-3">
              <div className="shrink-0 w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center mt-0.5">
                1
              </div>
              <div>
                <p className="text-sm text-gray-800">
                  Нажмите кнопку{" "}
                  <span className="font-semibold text-blue-600">«Поделиться»</span>{" "}
                  внизу экрана
                </p>
                {/* Иконка системной кнопки «Поделиться» в Safari */}
                <div className="mt-1 inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-100 rounded-lg">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="text-blue-600"
                    aria-hidden="true"
                  >
                    {/* Иконка «квадрат со стрелкой вверх» — стандартный символ Поделиться в Safari */}
                    <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                    <polyline points="16 6 12 2 8 6" />
                    <line x1="12" y1="2" x2="12" y2="15" />
                  </svg>
                  <span className="text-xs text-gray-700">Поделиться</span>
                </div>
              </div>
            </div>

            {/* Шаг 2 */}
            <div className="flex items-start gap-3">
              <div className="shrink-0 w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center mt-0.5">
                2
              </div>
              <p className="text-sm text-gray-800">
                Прокрутите список вниз и выберите{" "}
                <span className="font-semibold text-blue-600">
                  «На экран "Домой"»
                </span>
              </p>
            </div>

            {/* Шаг 3 */}
            <div className="flex items-start gap-3">
              <div className="shrink-0 w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center mt-0.5">
                3
              </div>
              <p className="text-sm text-gray-800">
                Нажмите{" "}
                <span className="font-semibold text-blue-600">«Добавить»</span>{" "}
                в правом верхнем углу
              </p>
            </div>
          </div>

          {/* Кнопка закрытия */}
          <button
            onClick={dismiss}
            className="w-full py-2.5 text-sm font-medium text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Понятно, позже
          </button>
        </div>
      </div>
    );
  }

  // Для unsupported/installed — уже отработано выше
  return null;
}
