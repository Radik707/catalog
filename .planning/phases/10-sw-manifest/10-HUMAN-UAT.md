---
status: partial
phase: 10-sw-manifest
source: [10-VERIFICATION.md]
started: 2026-06-12
updated: 2026-06-12
---

## Current Test

[ожидает живой проверки на устройстве]

## Tests

### 1. Установка PWA и запуск в standalone-режиме
expected: После `npm run build && npm start` открыть секретный URL каталога в Chrome (desktop или Android) → в меню браузера появляется «Установить приложение» → после установки каталог запускается БЕЗ адресной строки браузера (standalone), сразу на нужной секретной ссылке. Под иконкой — «Вкусный Дом», иконка синяя с «ВД».
result: [pending]
note: Все машинно-проверяемые предпосылки подтверждены координатором (SW activated, manifest валиден, иконки корректны, заголовки /sw.js верны). Не воспроизводится в автотесте — требует реального жеста установки на устройстве пользователя. Firefox (Playwright) не показывает Chrome-промпт установки. iOS-установка проверяется отдельно на этапе 14.

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
