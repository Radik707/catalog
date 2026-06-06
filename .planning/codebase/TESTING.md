# Testing Patterns

**Analysis Date:** 2026-06-06

## Test Framework

**Runner:** None — no automated test framework is installed or configured.

**Assertion Library:** None.

**Test Config:** No `jest.config.*`, `vitest.config.*`, or any test configuration file exists.

**Test Files:** No `*.test.*` or `*.spec.*` files found anywhere in the repository.

**Dev Dependencies:** `package.json` contains no testing libraries (no jest, vitest, @testing-library, mocha, etc.).

---

## Current Verification Approach

Since there are no automated tests, verification is done through a combination of manual steps and built-in tooling:

### TypeScript Type Checking

**Command:**
```bash
npx tsc --noEmit
```

**What it checks:**
- Type correctness across all `app/`, `components/`, `lib/`, `bot/` files
- `tsconfig.json` has `strict: true` — catches null issues, missing properties, wrong types
- Scripts directory is **excluded** from TypeScript: `"exclude": ["node_modules", "scripts"]`

**When to run:** Before committing any `.ts` or `.tsx` changes.

### Next.js Build Check

**Command:**
```bash
npm run build
```

**What it checks:**
- TypeScript compilation errors (next build runs tsc internally)
- Missing imports, broken paths
- Server/client component boundary violations (`'use client'` missing)
- Build-time rendering errors (missing env vars cause getProducts to return `[]`)

**Important:** After any `upload.py` run, the `.next` cache must be cleared before building:
```powershell
Remove-Item -Recurse -Force C:\catalog\.next
npm run build
```

**When to run:** After every data update and before every deploy.

### Development Server Manual Testing

**Command:**
```bash
npm run dev
```

**What it verifies:**
- UI renders correctly in browser
- Cart add/remove/update works (localStorage persistence)
- Category filter and search filter products correctly
- Flip animation works on product cards
- Lightbox opens and navigates photos
- Telegram deep link is generated correctly on cart page

**Manual test checklist (no automation):**
- Open catalog URL with secret → products load
- Switch between List / Grid / Presentation modes
- Add item to cart, verify counter in header
- Open cart, verify Telegram button generates correct link
- Filter by category, verify correct products shown
- Search for product name, verify filtering

### Python Script Verification

**Dry-run mode (every script supports it):**
```bash
python scripts/upload.py --dry-run           # парсинг без записи в Google Sheet
python scripts/apply_manual_sheet.py --dry-run  # показать привязки без сохранения
python scripts/make_manual_sheet.py --dry-run   # показать что будет добавлено
python scripts/upload_photos.py --dry-run       # показать фото без загрузки
```

**Syntax check via py_compile:**
```bash
python -m py_compile scripts/upload.py
python -m py_compile scripts/apply_manual_sheet.py
```

**What Python scripts output for verification:**
- `upload.py` logs count of parsed products per supplier file and total rows written to Google Sheet
- `apply_manual_sheet.py` prints summary: `Привязано фото: N (новых: X, обновлено: Y)`
- `upload_photos.py` logs each uploaded file with its Cloudinary URL

### Google Sheets Verification

After running `upload.py`, manually verify in Google Sheets:
- Row count matches expected product count
- Badge column populated correctly
- ImageUrl column has Cloudinary URLs
- Spot-check price/stock values match source Excel files

---

## What Is NOT Tested

The following areas have zero automated test coverage:

**Frontend components:**
- `ProductCard` flip behavior
- `CatalogView` filtering/search logic
- `useCart` hook localStorage persistence
- `AddToCartButton` quantity limits
- `Lightbox` gallery navigation

**API routes:**
- `app/api/products/route.ts` — Google Sheets parsing
- `app/api/bot/route.ts` — Telegram webhook auth

**Bot logic:**
- `bot/ai/consultant.ts` — Gemini function calling loop
- `bot/services/cart-store.ts` — Vercel KV operations
- `bot/handlers/` — all handler logic

**Python scripts:**
- `upload.py` — Excel parsing, category mapping, badge assignment
- `apply_manual_sheet.py` — photo key resolution, override merging
- `make_manual_sheet.py` — Excel generation logic

---

## Risk Areas Without Test Coverage

**High risk:**

- `lib/packaging.ts` — 40+ conditional rules for packaging labels. No tests means silent regressions when adding new rules. A new rule at lower priority can shadow existing correct matches.

- `scripts/upload.py` — Core data pipeline. If Excel format from a supplier changes, parsing silently returns wrong data (wrong columns). Only detected when catalog looks wrong in browser.

- `bot/ai/consultant.ts` — Function call loop has hardcoded `iterations < 5` guard. Gemini API behavior changes (e.g., returning unexpected function call names) would silently fall through to FALLBACK_MESSAGE without clear logging of which tool failed.

**Medium risk:**

- `bot/services/cart-store.ts` — Vercel KV TTL is 24 hours hardcoded. No validation that KV is reachable before cart operations — all errors return empty cart silently.

- `lib/useCart.ts` — localStorage hydration runs in `useEffect`. If localStorage is corrupted, `JSON.parse` catches the error and returns `[]` (cart lost silently, no user notification).

---

## If Tests Were Added

If the project grows to the point of needing tests, the recommended approach:

**Framework:** Vitest (compatible with Vite/Next.js, native TypeScript support, no babel config needed)

**Priority order for first tests:**
1. `lib/packaging.ts` — pure function, easy to unit test, high business value
2. `scripts/upload.py` — test `parse_excel_file()` with sample xlsx fixtures using pytest
3. `lib/useCart.ts` — test with `@testing-library/react-hooks`

**Install:**
```bash
npm install --save-dev vitest @vitest/coverage-v8
# Python tests:
pip install pytest
```

**Test file location pattern (if adopted):**
- Co-located: `lib/packaging.test.ts` next to `lib/packaging.ts`
- Python: `scripts/tests/test_upload.py`

---

*Testing analysis: 2026-06-06*
