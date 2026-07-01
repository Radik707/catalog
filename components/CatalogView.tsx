"use client";

import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { usePathname } from "next/navigation";
import { Product } from "@/lib/types";
import ProductCard from "./ProductCard";
import SearchBar from "./SearchBar";
import ScrollToTop from "./ScrollToTop";
import Lightbox from "./Lightbox";
import { useCatalogSettings, PRESENTATION_PRESETS } from "./CatalogSettings";
import { useNav, NavMode } from "./NavProvider";
// Плотная строка режима «Быстрый набор» — рендерится вместо ProductCard в effectiveMode === "quick"
import QuickOrderRow from "@/components/QuickOrderRow";
// Единый экземпляр sync из провайдера — разделяется с кнопкой ↻ в шапке (план 02)
import { useCatalogSyncContext } from "@/components/CatalogSyncProvider";
// Избранное клиента — для режима «fav» (фильтр только избранных товаров)
import { useFavoritesContext } from "@/components/FavoritesProvider";
// Роль пользователя (client/sales) — гейт строки повтора (D-06, HOME-02)
import { useRole } from "@/lib/useRole";
// История заказов клиента — для строки «↻ Повторить последний заказ» (HOME-02)
import { useOrderHistoryContext } from "@/components/OrderHistoryProvider";
// Корзина — addToCartWithQuantity для повтора (D-05, план 19-01)
import { useCartContext } from "@/components/CartProvider";
// Чистый хелпер классификации позиций повтора (план 19-01)
import { classifyReorder, ReorderResult } from "@/lib/reorder";
// Общая модалка-сводка повтора (вынесена в план 20-02)
import ReorderSummaryModal from "@/components/ReorderSummaryModal";
// Хук истории поиска — localStorage, офлайн-безопасно (SRCH-01, D-07/D-08)
import { useSearchHistory } from "@/lib/useSearchHistory";

interface CatalogViewProps {
  // products теперь опциональный: при отсутствии данные берутся из useCatalogSync (офлайн-режим)
  products?: Product[];
  // Начальный режим из URL (?filter=hit|new) — для внешних ссылок
  initialMode?: NavMode;
}

export default function CatalogView({ products: productsProp, initialMode }: CatalogViewProps) {
  // Настройки отображения (управляются шестерёнкой в шапке)
  const { viewMode, gridPreset, showPhotos, showPrices, priceForm, priceColor } = useCatalogSettings();
  // Состояние навигации (режим, раздел, подгруппа) — из общего контекста
  const { mode, section, subgroup, setMode } = useNav();
  // Избранное — для режима «fav»
  const { isFavorite } = useFavoritesContext();

  const [search, setSearch] = useState("");
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  // ─── Хуки для строки повтора (D-06, HOME-02) ────────────────────────────────
  // ВАЖНО: все хуки вызываются БЕЗУСЛОВНО и ВЫШЕ ранних return (правило хуков).
  const { role, ready } = useRole();
  const { entries: orderEntries } = useOrderHistoryContext();
  const { addToCartWithQuantity } = useCartContext();

  // Состояние сводки повтора: null — не показана; заполнена после нажатия кнопки
  const [reorderSummary, setReorderSummary] = useState<(ReorderResult & { secret: string }) | null>(null);

  // ─── Хук истории поиска (SRCH-01, D-07/D-08) ────────────────────────────────
  // ВАЖНО: хук вызывается БЕЗУСЛОВНО и ВЫШЕ ранних return (правило хуков).
  const { entries: searchEntries, addQuery, removeQuery, clearHistory } = useSearchHistory();

  // ─── Очередь перевёрнутых карточек: максимум 2 одновременно ──────────────────
  // Состояние переворота поднято из карточки на уровень списка, чтобы можно было
  // ограничить число открытых оборотов. При перевороте третьей карточки самая
  // старая (FIFO) автоматически возвращается лицевой стороной.
  const [flippedIds, setFlippedIds] = useState<string[]>([]);
  const handleFlipChange = useCallback((id: string, next: boolean) => {
    setFlippedIds((prev) => {
      if (next) {
        if (prev.includes(id)) return prev;
        // Добавляем в конец и оставляем только две последние — старую закрываем.
        return [...prev, id].slice(-2);
      }
      // Ручное закрытие оборота (тап по обороту) — убираем из очереди.
      return prev.filter((x) => x !== id);
    });
  }, []);

  // Ref памяти прокрутки — объявлен здесь (выше ранних return); эффекты,
  // зависящие от status, заданы ниже, после вычисления самого status.
  const scrollRestoredRef = useRef(false);

  // Читаем единственный экземпляр sync из провайдера (CatalogSyncProvider в layout).
  // Хук вызывается БЕЗУСЛОВНО (правило хуков — нельзя в ветке условия).
  // Когда проп передан — данные хука игнорируются, используется проп.
  const sync = useCatalogSyncContext();

  // Текущий путь — нужен для извлечения secret без его хардкода (паттерн SettingsPanel)
  const pathname = usePathname();

  // Рабочий массив: проп имеет приоритет (обратная совместимость / тесты);
  // при отсутствии пропа — данные приходят из IndexedDB через хук (офлайн-источник).
  const products = productsProp ?? sync.products;

  // Статус загрузки берём из хука только когда проп не передан.
  // Когда проп передан — данные уже готовы, статус "ready".
  const status = productsProp !== undefined ? "ready" : sync.status;

  // ─── Память места прокрутки (возврат из корзины) ────────────────────────────
  // При переходе в корзину CatalogView размонтируется, при возврате — создаётся
  // заново, и браузер теряет позицию прокрутки. Сохраняем её в sessionStorage и
  // восстанавливаем при возврате, чтобы клиент вернулся на то же место списка.
  // Восстановление позиции один раз, как только данные готовы.
  useEffect(() => {
    if (status !== "ready" || scrollRestoredRef.current) return;
    let saved: string | null = null;
    try {
      saved = sessionStorage.getItem("catalog-scroll");
    } catch {
      // sessionStorage недоступен (приватный режим и т.п.) — просто без восстановления
    }
    // Флаг ставим ПОСЛЕ чтения: до этого момента сохранение запрещено, чтобы
    // авто-скролл Next.js «вверх» при монтировании не затёр сохранённое значение.
    scrollRestoredRef.current = true;
    const y = saved ? parseInt(saved, 10) : 0;
    if (y > 0) {
      // Два кадра — чтобы карточки успели отрисоваться и страница набрала высоту.
      requestAnimationFrame(() => requestAnimationFrame(() => window.scrollTo(0, y)));
    }
  }, [status]);

  // Непрерывное сохранение текущей позиции прокрутки (после восстановления).
  useEffect(() => {
    const onScroll = () => {
      if (!scrollRestoredRef.current) return;
      try {
        sessionStorage.setItem("catalog-scroll", String(window.scrollY));
      } catch {
        // молча игнорируем — память места не критична
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // ─── Выезжающая строка поиска (reveal-on-scroll-up) ─────────────────────────
  // Чтобы клиенту не приходилось листать в самый верх ради поиска: при прокрутке
  // ВНИЗ тонкая панель поиска прячется (уезжает под шапку), при прокрутке ВВЕРХ —
  // снова выезжает. У самого верха страницы — всегда видна.
  const [searchVisible, setSearchVisible] = useState(true);
  const lastScrollYRef = useRef(0);
  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY;
      const last = lastScrollYRef.current;
      if (y < 80) {
        setSearchVisible(true); // у верха — всегда показываем
      } else if (y > last + 6) {
        setSearchVisible(false); // листают вниз — прячем
      } else if (y < last - 6) {
        setSearchVisible(true); // листают вверх — показываем
      }
      lastScrollYRef.current = y;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Однократно применяем режим из URL (например, ссылка ?filter=hit)
  useEffect(() => {
    if (initialMode && initialMode !== "catalog") setMode(initialMode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Запись поискового запроса в историю — по debounce 800мс на непустое значение
  useEffect(() => {
    if (!search.trim()) return;
    const timer = setTimeout(() => {
      addQuery(search.trim());
    }, 800);
    return () => clearTimeout(timer);
  }, [search, addQuery]);

  // ─── Обработчик кнопки «↻ Повторить последний заказ» ────────────────────────
  // Логика по образцу handleRepeat в orders/page.tsx (строки 40-58)
  const handleRepeatLast = useCallback(() => {
    const entry = orderEntries[orderEntries.length - 1];
    if (!entry) return;

    // Классифицируем позиции прошлого заказа против актуального каталога
    const result = classifyReorder(entry.items, products, priceForm);

    // Добавляем в корзину позиции с исходом added и price_changed
    for (const line of result.lines) {
      if ((line.outcome === "added" || line.outcome === "price_changed") && line.product) {
        addToCartWithQuantity(line.product, line.addedQty ?? line.historyItem.quantity);
      }
    }

    // Извлекаем secret из pathname: /catalog/<uuid>/... → <uuid>
    const secretMatch = pathname.match(/\/catalog\/([^/]+)/);
    const secret = secretMatch ? secretMatch[1] : "";

    // Открываем сводку результата (D-07)
    setReorderSummary({ ...result, secret });
  }, [orderEntries, products, priceForm, addToCartWithQuantity, pathname]);

  // Плоский список — при активном поиске ИЛИ в режимах Хит/Новинка
  const isFlat = Boolean(search.trim()) || mode !== "catalog";

  // ВАЖНО (правило хуков): все useMemo ниже вызываются БЕЗУСЛОВНО и ВЫШЕ любых
  // ранних return по статусу. Иначе при переходе loading → ready число вызванных
  // хуков меняется и React падает: "Rendered more hooks than during the previous render".

  // Плоско отфильтрованные товары: режим (бейдж) + поиск по названию
  const flatFiltered = useMemo(() => {
    if (!isFlat) return [];
    const q = search.trim().toLowerCase();
    return products.filter((p) => {
      if (p.stock <= 1) return false;
      if (mode === "hit" && p.badge !== "хит") return false;
      if (mode === "new" && p.badge !== "новинка") return false;
      if (mode === "fav" && !isFavorite(p.id)) return false;
      if (q && !p.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [products, search, isFlat, mode, isFavorite]);

  // Группировка раздел → подгруппа → товары (режим «Каталог»).
  // Учитывает выбранные раздел и подгруппу (фильтр). «Новинки» — первым разделом.
  const grouped = useMemo(() => {
    let visible = products.filter((p) => p.stock > 1);
    if (section) visible = visible.filter((p) => (p.section || "Новинки") === section);
    if (subgroup)
      visible = visible.filter((p) => (p.subgroup || p.category || "—") === subgroup);

    const map = new Map<string, Map<string, Product[]>>();
    for (const p of visible) {
      const sec = p.section || "Новинки";
      const sub = p.subgroup || p.category || "—";
      if (!map.has(sec)) map.set(sec, new Map());
      const subMap = map.get(sec)!;
      if (!subMap.has(sub)) subMap.set(sub, []);
      subMap.get(sub)!.push(p);
    }

    // «Новинки» — первым разделом
    if (map.has("Новинки")) {
      const novinki = map.get("Новинки")!;
      map.delete("Новинки");
      const reordered = new Map<string, Map<string, Product[]>>();
      reordered.set("Новинки", novinki);
      map.forEach((v, k) => reordered.set(k, v));
      return reordered;
    }
    return map;
  }, [products, section, subgroup]);

  // Сколько товаров показано (для счётчика в строке поиска)
  const groupedCount = useMemo(() => {
    let n = 0;
    grouped.forEach((subMap) => subMap.forEach((items) => (n += items.length)));
    return n;
  }, [grouped]);

  // Источник фото для просмотрщика
  const photoProducts = useMemo(() => {
    if (isFlat) return flatFiltered.filter((p) => p.imageUrl);
    const list: Product[] = [];
    grouped.forEach((subMap) => subMap.forEach((items) => list.push(...items)));
    return list.filter((p) => p.imageUrl);
  }, [isFlat, flatFiltered, grouped]);

  // ─── Состояние «первая загрузка» (D-02): скелетон-карточки ─────────────────
  // IDB пуст, идёт fetch — показываем серые контуры в сетке витрины, не спиннер.
  if (status === "loading") {
    return (
      <div className="min-h-screen flex flex-col">
        {/* Строка поиска — отображаем, но неактивна пока нет данных; пропсы истории опущены (опциональны) */}
        <SearchBar value="" onChange={() => {}} count={0} />
        {/* Сетка скелетон-карточек: те же классы что у обычной сетки */}
        <div className="flex-1 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-2 p-2">
          {Array.from({ length: 12 }).map((_, i) => (
            // Скелетон-карточка: имитирует пропорции реальной карточки с фото
            <div key={i} className="bg-white rounded-lg overflow-hidden shadow-sm border border-gray-100">
              {/* Блок-заглушка фото (квадратный, как у карточки) */}
              <div className="aspect-square bg-gray-200 animate-pulse" />
              <div className="p-2 space-y-2">
                {/* Полоска-заглушка названия товара */}
                <div className="h-3 bg-gray-200 rounded animate-pulse" />
                <div className="h-3 bg-gray-200 rounded animate-pulse w-3/4" />
                {/* Полоска-заглушка цены */}
                <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2 mt-1" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ─── Состояние «офлайн без данных» (D-03): дружелюбная заглушка ────────────
  // IDB пуст И нет сети — каталог ни разу не открывался онлайн.
  // Как только сеть появится — хук подтянет данные сам (событие online), без кнопки.
  if (status === "empty-offline") {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center max-w-xs">
          {/* Иконка отсутствия сети — нейтральная, не тревожная */}
          <div className="text-6xl mb-4">📵</div>
          <h2 className="text-lg font-semibold text-gray-700 mb-2">
            Каталог ещё не загружен
          </h2>
          <p className="text-sm text-gray-500 leading-relaxed">
            Подключитесь к интернету один раз — и дальше каталог будет работать
            даже без сети.
          </p>
        </div>
      </div>
    );
  }

  // ─── Готовое состояние (status === "ready"): обычный рендер каталога ────────
  // Хуки выше уже вычислены; ниже — только не-хуковая логика рендера.

  const openLightbox = (product: Product) => {
    const idx = photoProducts.findIndex((p) => p.id === product.id);
    if (idx !== -1) setLightboxIndex(idx);
  };

  const preset = PRESENTATION_PRESETS[gridPreset];

  // Эффективный режим с SSR-safe гейтом роли (D-02, QORD-04, T-21-03):
  // если сохранён quick, но роль не sales или ready ещё не пришёл — откатываемся
  // к presentation, чтобы клиент не видел агентский режим даже на первом кадре.
  const effectiveMode =
    viewMode === "quick" && !(ready && role === "sales") ? "presentation" : viewMode;

  // Класс контейнера товаров — зависит от effectiveMode (не viewMode напрямую).
  // quick: тот же flex-1 что и list — плотный список без сетки (D-09, QORD-05).
  // Виртуализацию ~800 строк НЕ вводим заранее (D-09) — рендерим как режим «Список»;
  // при реальных тормозах следующий шаг — react-virtual или аналог.
  const containerClass =
    effectiveMode === "list" || effectiveMode === "quick"
      ? "flex-1"
      : effectiveMode === "presentation"
      ? `flex-1 grid ${preset.cols} gap-1.5 p-1.5`
      : "flex-1 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-2 p-2"; // десктоп xl/2xl

  const visibleCount = isFlat ? flatFiltered.length : groupedCount;

  // Карточка товара (общий рендер для обеих веток).
  // В режиме quick рендерим QuickOrderRow вместо ProductCard (QORD-01, D-03).
  const renderCard = (product: Product) => {
    if (effectiveMode === "quick") {
      return (
        <QuickOrderRow
          key={product.id}
          product={product}
          priceForm={priceForm}
        />
      );
    }
    return (
      <ProductCard
        key={product.id}
        product={product}
        showPhotos={showPhotos}
        showPrices={showPrices}
        viewMode={effectiveMode === "list" ? "list" : effectiveMode === "grid" ? "grid" : "presentation"}
        onPhotoOpen={() => openLightbox(product)}
        presentationSizes={effectiveMode === "presentation" ? preset.sizes : undefined}
        priceForm={priceForm}
        priceColor={priceColor}
        flipped={flippedIds.includes(product.id)}
        onFlipChange={(next) => handleFlipChange(product.id, next)}
      />
    );
  };

  // Гейт строки повтора (D-06, HOME-02, T-20-10):
  // показываем только при ready + роль client + непустая история заказов.
  // До ready — строки нет (нет сдвига раскладки при гидратации).
  const showRepeatRow = ready && role === "client" && orderEntries.length > 0;

  return (
    <div className="min-h-screen flex flex-col">
      {/* В режиме quick ScrollToTop ведёт себя как list (плотный список без сетки) */}
      <ScrollToTop viewMode={effectiveMode === "list" || effectiveMode === "quick" ? "list" : "grid"} />

      {/* Строка поиска — липкая под шапкой (top-12) с выездом при прокрутке вверх.
          z-40 ниже синей шапки (z-50): спрятанная панель уезжает под неё. */}
      <div
        className="sticky top-12 z-40 transition-transform duration-200 will-change-transform"
        style={{ transform: searchVisible ? "translateY(0)" : "translateY(-130%)" }}
      >
        <SearchBar
          value={search}
          onChange={setSearch}
          count={visibleCount}
          history={searchEntries}
          onPickHistory={(q) => setSearch(q)}
          onRemoveHistory={removeQuery}
          onClearHistory={clearHistory}
        />
      </div>

      {/* Строка «↻ Повторить последний заказ» — компактная одна строка, только client (HOME-02) */}
      {showRepeatRow && (
        <div className="bg-white border-b border-gray-100 px-4 py-2 flex items-center">
          <button
            onClick={handleRepeatLast}
            className="w-full py-2 bg-blue-600 text-white text-sm font-semibold rounded-xl active:bg-blue-700 transition-colors"
          >
            ↻ Повторить последний заказ
          </button>
        </div>
      )}

      {isFlat ? (
        // Плоский список: поиск или режимы Хит/Новинка
        <div className={containerClass}>
          {flatFiltered.length > 0 ? (
            flatFiltered.map(renderCard)
          ) : (
            <div className="px-4 py-12 text-center text-gray-400">
              {mode === "fav" && !search.trim() ? (
                <>
                  <p className="text-lg">В избранном пока пусто</p>
                  <p className="text-sm mt-1">
                    Нажмите ♥ на карточке товара, чтобы добавить его сюда
                  </p>
                </>
              ) : (
                <>
                  <p className="text-lg">Ничего не найдено</p>
                  <p className="text-sm mt-1">Попробуйте изменить фильтр или поиск</p>
                </>
              )}
            </div>
          )}
        </div>
      ) : groupedCount === 0 ? (
        <div className="px-4 py-12 text-center text-gray-400">
          <p className="text-lg">Здесь пока нет товаров</p>
        </div>
      ) : (
        // Групповой режим: заголовки раздел → подгруппа + карточки
        Array.from(grouped.entries()).map(([sec, subMap]) => (
          <div key={sec}>
            <h2 className="text-lg font-bold text-gray-800 px-4 pt-5 pb-2">{sec}</h2>
            {Array.from(subMap.entries()).map(([sub, items]) => (
              <div key={sub}>
                <h3 className="text-sm font-semibold text-gray-500 px-4 pt-3 pb-1.5 uppercase tracking-wide">
                  {sub}{" "}
                  <span className="font-normal text-gray-400">({items.length})</span>
                </h3>
                <div className={containerClass}>{items.map(renderCard)}</div>
              </div>
            ))}
          </div>
        ))
      )}

      {/* Полноэкранный просмотрщик-галерея фото */}
      {lightboxIndex !== null && photoProducts.length > 0 && (
        <Lightbox
          products={photoProducts}
          index={lightboxIndex}
          onIndexChange={setLightboxIndex}
          onClose={() => setLightboxIndex(null)}
          priceForm={priceForm}
        />
      )}

      {/* Сводка повтора — общая модалка (вынесена в план 20-02) */}
      {reorderSummary && (
        <ReorderSummaryModal
          result={reorderSummary}
          secret={reorderSummary.secret}
          onClose={() => setReorderSummary(null)}
        />
      )}
    </div>
  );
}
