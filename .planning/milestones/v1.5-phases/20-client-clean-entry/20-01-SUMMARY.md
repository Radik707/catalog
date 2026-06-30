---
phase: 20-client-clean-entry
plan: "01"
subsystem: ui-header
tags: [role-gate, client-ux, ssr-safe, header-cleanup]
dependency_graph:
  requires: [lib/useRole.tsx, components/BottomTabBar.tsx]
  provides: [components/HeaderPrimaryAction.tsx, components/CartIcon.tsx, components/CatalogNav.tsx]
  affects: [app/catalog/[secret]/layout.tsx — компоновка шапки через дочерние гейты]
tech_stack:
  added: []
  patterns: [SSR-safe role gate (резерв места до ready), role-conditional render, useRole hook]
key_files:
  modified:
    - components/HeaderPrimaryAction.tsx
    - components/CartIcon.tsx
    - components/CatalogNav.tsx
decisions:
  - "Гейт роли внутри клиентских компонентов (не в серверном layout.tsx) — layout async, useRole недоступен"
  - "До ready — резерв места (h-9 w-9 / w-9 h-9), не null — предотвращает сдвиг шапки при гидратации"
  - "CartIcon: useCartContext вызывается безусловно перед гейтом роли — правило хуков React"
  - "CatalogNav без структурных изменений: flex-1 уже передаёт освободившееся место разделам"
metrics:
  duration: "15 мин"
  completed: "2026-06-30"
  tasks_completed: 3
  files_changed: 3
---

# Этап 20 План 01: Чистая шапка клиента — SUMMARY

**Одна строка:** Убраны дубли нижних табов из шапки роли client (♥/🛒 → null), ряд разделов получает освободившееся место через flex-1, SSR-safe гейт useRole во всех трёх компонентах.

## Что сделано

Разгружена шапка роли «Клиент» — убраны верхние дубли нижних табов:
- `HeaderPrimaryAction`: у client больше не рендерит `FavoritesIcon` → возвращает `null` (♥ уже в BottomTabBar)
- `CartIcon`: добавлен гейт `useRole`, у client возвращает `null` (🛒 уже в BottomTabBar), у sales без изменений
- `CatalogNav`: без структурных правок — через `flex-1` ряд разделов автоматически занимает освободившееся место

Роль «Торговый» (sales) не изменена: ↻ SyncButton + ⚙ + 🛒 на месте.

## Задачи и коммиты

| Задача | Описание | Коммит |
|--------|----------|--------|
| 1 | HeaderPrimaryAction: убрать ♥ у client | b52b3ba |
| 2 | CartIcon: скрыть 🛒 у client, гейт useRole | d884af9 |
| 3 | CatalogNav: комментарий о передаче места разделам | 47639f5 |

## Отклонения от плана

Нет — план выполнен точно как написан.

## Угрозы (STRIDE T-20-01, T-20-02, T-20-03)

- **T-20-01 (Tampering localStorage):** `useRole` уже валидирует значение — только "sales"/"client", битое → дефолт "client". Нейтральная клиентская шапка (только ⚙) без падения. ✅ Покрыто.
- **T-20-02 (DoS гидратации):** Все три компонента используют резерв места до `ready` (не `null`) — раскладка не прыгает. ✅ Покрыто.
- **T-20-03 (Info Disclosure):** Правки чисто презентационные, новых сетевых поверхностей нет. ✅ Accepted.

## Threat Flags

Нет — этап не добавляет сетевых поверхностей, токенов, PII.

## Известные стабы

Нет.

## Проверка сборки

`npm run build` — ✅ прошёл без ошибок и предупреждений.

## Отложенная приёмка (после деплоя)

Задача 4 (checkpoint:human-verify) — визуальная приёмка на проде. Координатор соберёт её после `git push`.

**Пункты проверки для владельца:**
1. Телефон, роль «Клиент»: в шапке справа ТОЛЬКО шестерёнка ⚙ — без сердечка ♥ и корзины 🛒. Снизу — табы Каталог · Избранное · Корзина.
2. Ряд разделов в шапке виден и удобно листается, иконки не теснятся.
3. Переключить роль на «Торговый» (⚙ → роль): шапка возвращается к ↻ + ⚙ + 🛒, нижних табов нет.
4. Перезагрузить страницу в роли «Клиент» — шапка не прыгает/мелькает при загрузке.

## Self-Check: PASSED

| Проверка | Результат |
|----------|-----------|
| components/HeaderPrimaryAction.tsx | FOUND |
| components/CartIcon.tsx | FOUND |
| components/CatalogNav.tsx | FOUND |
| .planning/phases/20-client-clean-entry/20-01-SUMMARY.md | FOUND |
| Коммит b52b3ba | FOUND |
| Коммит d884af9 | FOUND |
| Коммит 47639f5 | FOUND |
| npm run build | PASSED |
