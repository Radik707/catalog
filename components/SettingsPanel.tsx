"use client";

import {
  useCatalogSettings,
  PRESENTATION_PRESETS,
  GridPreset,
  ViewMode,
} from "./CatalogSettings";
// Контекст установки PWA — для пункта «Установить приложение» (D-05, PWA-02)
import { useInstallPromptContext } from "@/components/InstallPromptProvider";

// Выпадающая панель настроек отображения. Появляется под синей шапкой
// при нажатии на шестерёнку, закрывается тапом мимо или повторным нажатием.
export default function SettingsPanel() {
  const {
    viewMode,
    setViewMode,
    gridPreset,
    setGridPreset,
    showPhotos,
    setShowPhotos,
    showPrices,
    setShowPrices,
    panelOpen,
    setPanelOpen,
  } = useCatalogSettings();

  // Состояние установки PWA: платформа, standalone-режим, функция открытия (D-05)
  const { platform, isStandalone, openFromSettings } = useInstallPromptContext();

  if (!panelOpen) return null;

  const views: { key: ViewMode; label: string }[] = [
    { key: "list", label: "☰ Список" },
    { key: "grid", label: "⊞ Сетка" },
    { key: "presentation", label: "◳ Презентация" },
  ];

  return (
    <>
      {/* Прозрачная подложка — тап мимо закрывает панель */}
      <div
        className="fixed inset-0 z-30"
        onClick={() => setPanelOpen(false)}
      />

      {/* Сама панель — закреплена под шапкой (высота шапки 48px = top-12) */}
      <div className="fixed top-12 left-0 right-0 z-40 border-b border-gray-200 bg-white shadow-lg">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          {/* Вид отображения */}
          <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs">
            {views.map((v) => (
              <button
                key={v.key}
                onClick={() => setViewMode(v.key)}
                className={`px-3 py-1.5 transition-colors ${
                  viewMode === v.key ? "bg-blue-500 text-white" : "bg-white text-gray-500"
                }`}
              >
                {v.label}
              </button>
            ))}
          </div>

          {/* Фото вкл/выкл */}
          <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs">
            <button
              onClick={() => setShowPhotos(true)}
              className={`px-3 py-1.5 transition-colors ${
                showPhotos ? "bg-blue-500 text-white" : "bg-white text-gray-500"
              }`}
            >
              С фото
            </button>
            <button
              onClick={() => setShowPhotos(false)}
              className={`px-3 py-1.5 transition-colors ${
                !showPhotos ? "bg-blue-500 text-white" : "bg-white text-gray-500"
              }`}
            >
              Без фото
            </button>
          </div>

          {/* Переключатель цен: зелёный ₽ — цены видны, красный перечёркнутый — скрыты */}
          <button
            onClick={() => setShowPrices(!showPrices)}
            aria-label={showPrices ? "Цены показаны" : "Цены скрыты"}
            className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-base font-bold transition-colors ${
              showPrices
                ? "border-green-500 bg-green-50 text-green-600"
                : "border-red-500 bg-red-50 text-red-600 line-through"
            }`}
          >
            ₽
          </button>

          {/* Плотность сетки — только в режиме презентации */}
          {viewMode === "presentation" && (
            <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs">
              {(Object.keys(PRESENTATION_PRESETS) as GridPreset[]).map((key) => (
                <button
                  key={key}
                  onClick={() => setGridPreset(key)}
                  className={`px-3 py-1.5 transition-colors ${
                    gridPreset === key ? "bg-blue-500 text-white" : "bg-white text-gray-500"
                  }`}
                >
                  {PRESENTATION_PRESETS[key].label}
                </button>
              ))}
            </div>
          )}

          {/*
            Кнопка «Установить приложение» (D-05, PWA-02).
            Скрывается, только если приложение уже в standalone-режиме
            (устанавливать нечего) или платформа не поддерживает установку.
            На Android доступна ВСЕГДА: если системное событие готово —
            openFromSettings() вызовет нативный диалог; если нет (уже использовано
            или Chrome на «паузе» после отказа) — покажет инструкцию-шторку про
            меню браузера. Так у пользователя всегда есть рабочий путь установки.
          */}
          {!isStandalone && (platform === "ios" || platform === "android") && (
            <button
              onClick={() => {
                // Android: вызываем нативный диалог установки
                // iOS: открываем bottom-sheet с инструкцией (forceOpen игнорирует dismissed)
                void openFromSettings();
                // Закрываем панель настроек после нажатия
                setPanelOpen(false);
              }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-blue-200 bg-blue-50 text-blue-700 text-xs font-medium transition-colors hover:bg-blue-100 hover:border-blue-300"
            >
              <span>📲</span>
              <span>Установить приложение</span>
            </button>
          )}
        </div>
      </div>
    </>
  );
}
