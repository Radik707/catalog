// Утилита форматирования метки свежести данных (решение D-04 из CONTEXT.md).
// Чистая функция без «use client» и без внешних библиотек дат — только нативный Date.
// Логика форматирования:
//   null            → «данные не загружены»
//   сегодня         → «данные за ЧЧ:ММ»
//   вчера           → «данные за вчера, ЧЧ:ММ»
//   раньше          → «данные за D месяца, ЧЧ:ММ»  (напр. «данные за 10 июня, 08:30»)

// Названия месяцев в родительном падеже (для фраз «за 10 июня, ...»).
const MONTHS_GENITIVE: readonly string[] = [
  "января",
  "февраля",
  "марта",
  "апреля",
  "мая",
  "июня",
  "июля",
  "августа",
  "сентября",
  "октября",
  "ноября",
  "декабря",
];

/**
 * Форматирует ЧЧ:ММ с ведущими нулями (08:30, не 8:30).
 */
function formatTime(date: Date): string {
  const h = String(date.getHours()).padStart(2, "0");
  const m = String(date.getMinutes()).padStart(2, "0");
  return `${h}:${m}`;
}

/**
 * Проверяет, является ли дата «сегодня» по календарным суткам (год+месяц+день).
 * НЕ использует скользящее окно 24 ч — сравниваем именно по дате.
 */
function isToday(date: Date, now: Date): boolean {
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  );
}

/**
 * Проверяет, является ли дата «вчера» по календарным суткам.
 */
function isYesterday(date: Date, now: Date): boolean {
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  return (
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate()
  );
}

/**
 * formatSyncTime — форматирует unix-ms метку синхронизации в человекочитаемую строку.
 *
 * @param syncedAt  unix-timestamp в мс (из IDB «syncTimestamp») или null до первой синхронизации
 * @returns         строка для отображения в OfflineBar
 */
export function formatSyncTime(syncedAt: number | null): string {
  // Данных ещё нет — первый запуск без синхронизации
  if (syncedAt === null) {
    return "данные не загружены";
  }

  const date = new Date(syncedAt);
  const now = new Date();
  const time = formatTime(date);

  if (isToday(date, now)) {
    // Сегодня: только время
    return `данные за ${time}`;
  }

  if (isYesterday(date, now)) {
    // Вчера: добавляем «вчера»
    return `данные за вчера, ${time}`;
  }

  // Раньше: день + название месяца в родительном падеже, без года
  const day = date.getDate();
  const month = MONTHS_GENITIVE[date.getMonth()];
  return `данные за ${day} ${month}, ${time}`;
}
