// Единственная точка доступа к IndexedDB в проекте.
// Все операции с локальной базой данных каталога — только через этот модуль.
// Модуль клиентский — не импортировать в серверный код (lib/sheets.ts и т.д.).

import { openDB } from "idb";
import type { IDBPDatabase } from "idb";
import type { Product } from "@/lib/types";

// ─── Константы схемы базы ─────────────────────────────────────────────────────

/** Имя базы IndexedDB (видно в DevTools → Application → IndexedDB) */
const DB_NAME = "catalog-db";

/**
 * Версия схемы базы. При изменении формата Product — увеличить на 1
 * и добавить ветку миграции в upgrade-колбэк ниже.
 */
const DB_VERSION = 1;

/** Хранилище (object store) для массива товаров */
const PRODUCTS_STORE = "products";

/** Хранилище для метаданных синхронизации (timestamp, prevImageUrls и т.д.) */
const META_STORE = "meta";

/**
 * Фиксированный ключ, под которым хранится весь массив Product[].
 * Выбран упрощённый формат: один ключ → весь массив, а не record-per-item.
 * Это оптимально для нашего сценария: чтение и запись всегда атомарны.
 */
const PRODUCTS_KEY = "all";

// ─── Открытие базы ────────────────────────────────────────────────────────────

/** Кэш Promise соединения — один openDB на жизнь вкладки */
let dbPromise: Promise<IDBPDatabase> | null = null;

/**
 * Открывает (или возвращает уже открытое) соединение с базой catalog-db.
 * Upgrade-колбэк создаёт stores только при их отсутствии — задел под версионирование:
 * при росте DB_VERSION колбэк вызывается с прежним oldVersion и может мигрировать
 * данные/пересоздать stores без потери каталога (угроза T-11-02).
 */
function getDb(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db, oldVersion) {
        // Создаём stores только если их нет — безопасно при любом oldVersion
        if (!db.objectStoreNames.contains(PRODUCTS_STORE)) {
          // Без keyPath/autoIncrement — пишем по явному ключу PRODUCTS_KEY
          db.createObjectStore(PRODUCTS_STORE);
        }
        if (!db.objectStoreNames.contains(META_STORE)) {
          // Произвольные пары ключ/значение (syncTimestamp, prevImageUrls и др.)
          db.createObjectStore(META_STORE);
        }

        // Пример миграции при повышении версии:
        // if (oldVersion < 2) { /* добавить индекс, перенести поле и т.д. */ }
        void oldVersion; // подавляем предупреждение «переменная не используется»
      },
    });
  }
  return dbPromise;
}

// ─── Публичный API ────────────────────────────────────────────────────────────

/**
 * Читает сохранённый массив товаров из IndexedDB.
 * Возвращает пустой массив [] при первом запуске (данных ещё нет).
 * Никогда не возвращает undefined — вызывающий код не обязан проверять на null.
 */
export async function getProducts(): Promise<Product[]> {
  const db = await getDb();
  const result = await db.get(PRODUCTS_STORE, PRODUCTS_KEY);
  // Первый запуск — хранилище пусто; возвращаем [], чтобы не ломать витрину
  return (result as Product[] | undefined) ?? [];
}

/**
 * Записывает массив товаров в IndexedDB.
 * Перезаписывает предыдущее значение целиком (атомарная операция).
 */
export async function saveProducts(products: Product[]): Promise<void> {
  const db = await getDb();
  await db.put(PRODUCTS_STORE, products, PRODUCTS_KEY);
}

/**
 * Читает произвольное метаданное по ключу.
 * Используется для: syncTimestamp, prevImageUrls (задел для этапов 12–13).
 * Возвращает undefined, если ключ не существует.
 */
export async function getMeta<T = unknown>(key: string): Promise<T | undefined> {
  const db = await getDb();
  return db.get(META_STORE, key) as Promise<T | undefined>;
}

/**
 * Сохраняет произвольное метаданное по ключу.
 * Перезаписывает предыдущее значение, если ключ уже существует.
 */
export async function saveMeta(key: string, value: unknown): Promise<void> {
  const db = await getDb();
  await db.put(META_STORE, value, key);
}
