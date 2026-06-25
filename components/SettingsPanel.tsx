"use client";

import { useState } from "react";
import {
  useCatalogSettings,
  PRESENTATION_PRESETS,
  GridPreset,
  ViewMode,
} from "./CatalogSettings";
// Контекст установки PWA — для пункта «Установить приложение» (D-05, PWA-02)
import { useInstallPromptContext } from "@/components/InstallPromptProvider";
// Синхронизация каталога — кнопка ↻ переехала из шапки сюда, в панель настроек
import { useCatalogSyncContext } from "@/components/CatalogSyncProvider";

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
    priceForm,
    setPriceForm,
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

          {/* Форма цен: 1-я — +5% на товары Ефимовой; 2-я — базовые цены */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Форма</span>
            <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs">
              <button
                onClick={() => setPriceForm("1")}
                className={`px-3 py-1.5 transition-colors ${
                  priceForm === "1" ? "bg-blue-500 text-white" : "bg-white text-gray-500"
                }`}
              >
                1-я
              </button>
              <button
                onClick={() => setPriceForm("2")}
                className={`px-3 py-1.5 transition-colors ${
                  priceForm === "2" ? "bg-blue-500 text-white" : "bg-white text-gray-500"
                }`}
              >
                2-я
              </button>
            </div>
          </div>

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
          {/* Обновление каталога — переехало из шапки (кнопка ↻) сюда */}
          <PanelSyncButton />

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

// Кнопка «Обновить каталог» внутри панели настроек.
// Логика та же, что у бывшей кнопки ↻ в шапке: refetch + индикатор busy/done.
// Офлайн — кнопка неактивна (нечего тянуть без сети).
function PanelSyncButton() {
  const { refetch, isOnline } = useCatalogSyncContext();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const handleRefresh = async () => {
    if (!isOnline || busy) return;
    setBusy(true);
    try {
      await refetch();
    } finally {
      setBusy(false);
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    }
  };

  return (
    <button
      onClick={handleRefresh}
      disabled={!isOnline || busy}
      title={!isOnline ? "Нужен интернет для обновления" : "Обновить каталог"}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
        !isOnline
          ? "border-gray-200 bg-gray-50 text-gray-400 cursor-not-allowed"
          : "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 hover:border-blue-300"
      }`}
    >
      {/* Иконка: галочка после успеха, иначе круговая стрелка (вращается при busy) */}
      {done ? (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      ) : (
        <svg
          className={`h-4 w-4${busy ? " animate-spin" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.8}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
          />
        </svg>
      )}
      <span>{busy ? "Обновляем…" : done ? "Готово" : "Обновить каталог"}</span>
    </button>
  );
}
