"use client";

// Клиентский хук синхронизации каталога — «мозг» офлайн-режима.
// Реализует стратегию stale-while-revalidate (D-01):
//   1. Мгновенно читает Product[] из IndexedDB → выдаёт в UI без задержки.
//   2. Параллельно делает fetch /api/products → бесшовно подменяет данные.
// Слушает события online/offline → при появлении сети подтягивает данные сам (D-03).
// Ошибка сервера = поведение «как офлайн»: данные из IDB остаются, UI не ломается (D-04).

import { useState, useEffect, useRef, useCallback } from "react";
import type { Product } from "@/lib/types";
import {
  getProducts,
  saveProducts,
  getMeta,
  saveMeta,
} from "@/lib/catalogDb";
// Умная предзагрузка только новых фото после успешного обновления каталога (D-04)
import { syncPhotos } from "@/lib/syncPhotos";

// ─── Типы ────────────────────────────────────────────────────────────────────

/**
 * Три состояния, которые различает хук — нужны для правильного рендера в UI:
 *  "loading"       — IDB пуст, идёт первый fetch (показываем скелетон, D-02).
 *  "ready"         — данные есть (из IDB или с сервера) — показываем каталог.
 *  "empty-offline" — IDB пуст И сети нет / fetch упал (D-03 заглушка без данных).
 */
export type CatalogStatus = "loading" | "ready" | "empty-offline";

/** Публичный контракт хука */
export interface UseCatalogSyncResult {
  /** Текущий массив товаров (мгновенно из IDB, затем обновляется с сервера) */
  products: Product[];
  /** Состояние сети (navigator.onLine, обновляется по событиям online/offline) */
  isOnline: boolean;
  /** Unix-timestamp (мс) последней успешной синхронизации, или null до первой */
  syncedAt: number | null;
  /** Статус загрузки — для скелетона, заглушки и витрины */
  status: CatalogStatus;
  /**
   * Ручная синхронизация для кнопки «Обновить» (D-01/SYNC-01).
   * Обновляет И данные каталога, И diff-предзагрузку новых фото.
   * sync() стабильна через useCallback([]) — защита от гонки встроена (CR-02).
   */
  refetch: () => Promise<void>;
}

// ─── Хук ─────────────────────────────────────────────────────────────────────

/**
 * useCatalogSync — единственная точка получения данных каталога на клиенте.
 * Подключается к CatalogView вместо пропа products из page.tsx (план 03).
 */
export function useCatalogSync(): UseCatalogSyncResult {
  // Инициализируем isOnline безопасно: на сервере navigator недоступен,
  // поэтому начальное значение всегда true — на клиенте исправится в useEffect.
  const [products, setProducts] = useState<Product[]>([]);
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [syncedAt, setSyncedAt] = useState<number | null>(null);
  const [status, setStatus] = useState<CatalogStatus>("loading");

  // useRef-флаг: navigator.storage.persist() вызываем только один раз
  // (после первой успешной синхронизации с сервером).
  const persistCalledRef = useRef(false);

  // Счётчик «поколений» синхронизации. Параллельные вызовы sync() (первый при
  // монтировании + повтор по событию online) могут завершиться в любом порядке.
  // Актуальным считаем только самый свежий вызов — запоздавший ответ старого
  // запроса НЕ должен перезаписать новые данные (защита от гонки, CR-02).
  const syncGenRef = useRef(0);
  // Флаг «компонент жив»: запрещаем setState после размонтирования.
  const mountedRef = useRef(true);

  // Таймаут запроса к серверу (мс): «висящая» сеть не должна держать вечный скелетон.
  const FETCH_TIMEOUT_MS = 10_000;

  // ─── Основная функция синхронизации ────────────────────────────────────────

  const sync = useCallback(async () => {
    // Помечаем этот вызов новым поколением. isCurrent() == true, пока вызов
    // остаётся самым свежим И компонент не размонтирован.
    const myGen = ++syncGenRef.current;
    const isCurrent = () => mountedRef.current && myGen === syncGenRef.current;

    // Шаг 1: Мгновенно читаем данные из IndexedDB — пользователь видит каталог
    // без ожидания сети. Это и есть «stale» часть stale-while-revalidate (D-01).
    let cached: Product[] = [];
    try {
      cached = await getProducts();
    } catch (err) {
      // Если IDB недоступна (редкий случай: приватный режим iOS) — работаем без кэша.
      console.warn("[useCatalogSync] Не удалось прочитать IDB:", err);
    }

    if (cached.length > 0 && isCurrent()) {
      // Кэш есть → мгновенно показываем товары, не ждём сети
      setProducts(cached);
      setStatus("ready");
    }

    // Шаг 2: Читаем timestamp последней синхронизации из meta
    try {
      const ts = await getMeta<number>("syncTimestamp");
      if (ts !== undefined && isCurrent()) setSyncedAt(ts);
    } catch {
      // Не критично — timestamp покажет null
    }

    // Шаг 3: Проверяем сеть. Обращаемся к navigator только здесь (внутри callback),
    // никогда на верхнем уровне модуля — иначе SSR падает (Next.js серверная сборка).
    const online =
      typeof navigator !== "undefined" ? navigator.onLine : true;

    if (!online) {
      // Нет сети — fetch не делаем; если кэш пустой → заглушка
      if (cached.length === 0 && isCurrent()) {
        setStatus("empty-offline");
      }
      // Если кэш есть — status уже "ready", оставляем как есть
      return;
    }

    // Шаг 4: Онлайн → fetch свежих данных с сервера (revalidate-часть SWR).
    // D-04: любой сбой (сеть, не-2xx, таймаут) = вести себя как офлайн.
    // AbortController + setTimeout прерывают «висящий» запрос (WR-01).
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
      const res = await fetch("/api/products", { signal: controller.signal });
      if (!res.ok) {
        // Сервер ответил ошибкой — трактуем как офлайн (D-04)
        throw new Error(`HTTP ${res.status}`);
      }

      // WR-02: сервер обязан вернуть массив. Если придёт объект ошибки/мусор —
      // НЕ затираем им офлайн-кэш, уходим в ветку «как офлайн».
      const data: unknown = await res.json();
      if (!Array.isArray(data)) {
        throw new Error("Ответ /api/products не является массивом");
      }
      const fresh = data as Product[];

      const now = Date.now();
      // Применяем результат только если это всё ещё самый свежий вызов (CR-02):
      // и в UI, и в IndexedDB — чтобы экран и кэш не разъехались.
      if (isCurrent()) {
        // Бесшовная подмена: хук возвращает новый массив, CatalogView перерисовывает
        // список. Компонент НЕ размонтируется → позиция прокрутки, открытый раздел
        // и фильтры сохраняются (они в состоянии CatalogView).
        setProducts(fresh);
        // Сохраняем свежие данные в IndexedDB для следующего офлайн-запуска
        await saveProducts(fresh);
        await saveMeta("syncTimestamp", now);
        // Поток 4 (ARCHITECTURE.md): fetch → saveProducts → saveMeta(syncTimestamp) →
        // syncPhotos(diff новых фото) → setStatus("ready").
        // syncPhotos сам читает/пишет prevImageUrls — отдельного saveMeta не нужен.
        await syncPhotos(fresh);
        setSyncedAt(now);
        setStatus("ready");
      }

      // Шаг 5: Однократный вызов persist() после первой успешной синхронизации.
      // Борьба с 7-дневным eviction на iOS — браузер не должен вытеснять наши данные.
      // Guard: не все браузеры поддерживают Storage API; результат не критичен.
      if (!persistCalledRef.current && navigator.storage?.persist) {
        persistCalledRef.current = true;
        await navigator.storage.persist().catch(() => {
          // Отказ persist() не является ошибкой — просто логируем
          console.warn("[useCatalogSync] navigator.storage.persist() отклонён браузером");
        });
      }
    } catch (err) {
      // D-04: сбой fetch (сеть, не-2xx, таймаут/abort, не-массив) = вести себя как офлайн.
      // Технические подробности в консоль для отладки — в UI ничего не пробрасываем.
      console.warn("[useCatalogSync] Не удалось получить данные с сервера:", err);

      if (cached.length === 0 && isCurrent()) {
        // Кэша нет и сервер упал → показываем заглушку «Подключитесь к интернету»
        setStatus("empty-offline");
      }
      // Если кэш есть — пользователь уже видит товары (status "ready"), оставляем как есть
    } finally {
      clearTimeout(timeoutId);
    }
  }, []); // sync не зависит от внешнего состояния — зависимости стабильны (refs)

  // ─── Эффект монтирования ────────────────────────────────────────────────────

  useEffect(() => {
    // Компонент смонтирован — разрешаем setState (важно для повторного маунта
    // в React StrictMode, где эффект отрабатывает дважды).
    mountedRef.current = true;

    // Исправляем начальное значение isOnline — читаем настоящее состояние на клиенте
    // (на сервере navigator недоступен, поэтому делаем это в useEffect).
    if (typeof navigator !== "undefined") {
      setIsOnline(navigator.onLine);
    }

    // Первичная синхронизация при монтировании компонента
    sync();

    // Обработчики событий сети
    const handleOnline = () => {
      // D-03: при появлении сети — подтягиваем данные без ручного действия агента
      setIsOnline(true);
      sync();
    };

    const handleOffline = () => {
      setIsOnline(false);
      // При уходе в офлайн данные из IDB по-прежнему доступны — ничего не сбрасываем
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Cleanup: снимаем подписки при размонтировании (Claude's Discretion — обязательно)
    return () => {
      // Запрещаем setState от «висящих» промисов sync() после размонтирования (CR-02)
      mountedRef.current = false;
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [sync]); // sync — стабильная ссылка через useCallback([])

  // refetch: sync — стабильная ссылка (useCallback([])); защита от гонки уже встроена
  return { products, isOnline, syncedAt, status, refetch: sync };
}
