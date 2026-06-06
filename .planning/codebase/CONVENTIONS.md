# Coding Conventions

**Analysis Date:** 2026-06-06

## Language Layers

The project uses **two separate languages** with different conventions:

| Layer | Language | Location |
|-------|----------|----------|
| Frontend + Bot | TypeScript | `app/`, `components/`, `lib/`, `bot/` |
| Tooling + Scripts | Python | `scripts/`, `uploader/`, `admin_bot/` |

---

## TypeScript / React Conventions

### Naming Patterns

**Files:**
- React components: `PascalCase.tsx` — e.g., `ProductCard.tsx`, `CatalogView.tsx`, `CartProvider.tsx`
- Hooks: `camelCase.ts` with `use` prefix — e.g., `useCart.ts`
- Utilities / lib: `camelCase.ts` — e.g., `sheets.ts`, `types.ts`, `packaging.ts`
- API routes: `route.ts` (Next.js convention) — e.g., `app/api/products/route.ts`
- Bot modules: `camelCase.ts` by responsibility — e.g., `consultant.ts`, `cart-store.ts`, `system-prompt.ts`

**Components:**
- Always PascalCase function names matching filename: `export default function ProductCard(...)`
- Sub-components defined in the same file use PascalCase: `function PhotoPlaceholder(...)`

**Variables and functions:**
- camelCase throughout: `activeGroup`, `setLightboxIndex`, `openLightbox`, `handleAIMessage`
- Boolean state variables use `is` prefix: `isLoaded`, `inStock`, `inCart`

**Types and interfaces:**
- PascalCase with explicit `interface` keyword: `interface ProductCardProps`, `interface CartContextValue`
- Exported interfaces in separate file: `lib/types.ts` — `export interface Product`

**Constants:**
- SCREAMING_SNAKE_CASE for module-level constants: `CART_KEY`, `CACHE_TTL_MS`, `MENU_BUTTONS`, `BADGE_STYLES`, `GROUP_ORDER`

### Directives

**Client components:**
- All interactive components start with `'use client';` (single quotes, top of file, before imports)
- Hooks files also start with `'use client';` — e.g., `useCart.ts`
- Server-only files (API routes, lib/sheets.ts) have no directive

**Force dynamic:**
- API routes that must not be cached use `export const dynamic = 'force-dynamic';` — `app/api/products/route.ts`

### Import Organization

**Order (observed pattern):**
1. React hooks: `import { useState, useMemo } from "react";`
2. Next.js imports: `import Image from "next/image";`
3. Internal lib types: `import { Product } from "@/lib/types";`
4. Internal lib utilities: `import { getPackaging } from "@/lib/packaging";`
5. Internal components: `import AddToCartButton from "./AddToCartButton";`

**Path aliases:**
- `@/*` maps to project root (configured in `tsconfig.json`)
- Use `@/lib/...` for lib imports, `./ComponentName` for sibling components

**Quotes:** Double quotes for imports in TypeScript files

### TypeScript Strictness

- `strict: true` in `tsconfig.json` — all strict checks enabled
- `noEmit: true` — TypeScript used for type-checking only, not compilation
- `skipLibCheck: true` — library type errors suppressed
- Optional chaining used throughout: `product.badge?`, `ctx.from?.first_name`, `onPhotoOpen?.()`
- Explicit `undefined` returns for optional fields: `badge: row[6] || undefined`
- Type assertions sparingly: `err as Record<string, unknown>` in catch blocks

### Component Design

**All components are functional with hooks:**
```typescript
export default function ComponentName({ prop1, prop2 = defaultValue }: ComponentNameProps) {
  const [state, setState] = useState(initial);
  // ...
  return (...);
}
```

**Props interfaces defined immediately before the component:**
```typescript
interface ProductCardProps {
  product: Product;
  showPhotos?: boolean;
  viewMode?: "list" | "grid" | "presentation";
}

export default function ProductCard({ product, showPhotos = true, viewMode = "list" }: ProductCardProps) {
```

**Default prop values** declared in function signature destructuring, not inside component body.

**useMemo for derived data** — always used when filtering/transforming product arrays:
```typescript
const filtered = useMemo(() => {
  // filtering logic
}, [products, activeGroup, search]);
```

**useCallback for event handlers** in custom hooks to avoid re-renders:
```typescript
const addToCart = useCallback((product: Product) => { ... }, []);
```

### Styling

**Tailwind CSS only — no CSS modules, no inline style objects (except transforms):**
- All layout/spacing/color via Tailwind utility classes
- Inline `style` objects used ONLY for CSS properties not available in Tailwind:
  - `style={{ perspective: "1000px" }}` — 3D perspective
  - `style={{ transformStyle: "preserve-3d", transform: ... }}` — 3D flip
  - `style={{ backfaceVisibility: "hidden" }}` — flip back face

**Responsive prefix order:** mobile first, then `sm:`, `lg:` prefixes

**Color palette (consistent across project):**
- Primary action: `bg-blue-600 text-white`, hover: `active:bg-blue-700`
- In-stock accent: `text-emerald-600` / `text-emerald-700`
- Neutral background: `bg-gray-50`, `bg-gray-100`
- Flip back face: `bg-amber-50`

### Error Handling in TypeScript

**API/fetch errors:**
```typescript
if (!res.ok) {
  console.error("Ошибка Google Sheets API:", res.status, await res.text());
  return [];
}
```

**Missing env vars — fail fast with guard:**
```typescript
if (!SHEETS_ID || !API_KEY) {
  console.error("Не заданы GOOGLE_SHEETS_ID или GOOGLE_API_KEY");
  return [];
}
```

**Context null guard — throw immediately:**
```typescript
if (!ctx) throw new Error('useCartContext must be used inside CartProvider');
```

**Bot error handler — always reply with fallback, never re-throw:**
```typescript
try {
  // ...
} catch (err: unknown) {
  console.error("handleAIMessage error:", ...);
  await ctx.reply(FALLBACK_MESSAGE);
}
```

**localStorage access — wrapped in try/catch silently:**
```typescript
try {
  return raw ? JSON.parse(raw) : [];
} catch {
  return [];
}
```

### Logging

- `console.error(...)` for errors — messages in Russian
- `console.error(...)` with structured object for bot errors (include status, message, raw)
- No `console.log` in production paths — only `console.error`

---

## Python Conventions

### Naming Patterns

**Files:** `snake_case.py` — `upload.py`, `apply_manual_sheet.py`, `make_manual_sheet.py`

**Functions:** `snake_case` — `load_badges()`, `get_badge()`, `parse_excel_file()`, `resolve_photo_key()`

**Variables:** `snake_case` — `badges_path`, `name_lower`, `badge_key`, `url_index`

**Constants:** `SCREAMING_SNAKE_CASE` — `SCRIPT_DIR`, `PROJECT_ROOT`, `DEFAULT_EXCEL_DIR`, `KNOWN_LOGICAL_FOLDERS`

**Type annotations:** Used in function signatures for Python 3.10+:
```python
def resolve_photo_key(raw_file: str, url_index: dict[str, str]) -> str:
def build_url_index() -> dict[str, str]:
def load_existing(path: Path) -> dict:
```

### Module Header Pattern

Every script starts with a docstring describing:
1. Script name and purpose
2. Usage examples with CLI arguments
3. Configuration requirements (env vars, files)

```python
"""
script_name.py — Short description

Usage:
    python script_name.py
    python script_name.py --dry-run

Configuration:
    ENV_VAR=value
"""
```

### Path Handling

**Always use `pathlib.Path`, never string concatenation:**
```python
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
badges_path = SCRIPT_DIR / "badges.json"
```

### Logging Pattern

Every script uses `logging` module (not `print`) for operational messages:
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

log.info("Found %d products", len(products))
log.warning("File not found: %s", path)
log.error("Cannot read: %s", filepath)
```

**`print()` used only for user-facing summary output at script end** — not for debug/info.

### CLI Arguments Pattern

All scripts support `--dry-run` (and optionally `--append`, `--rebuild`, `--path`):
```python
parser = argparse.ArgumentParser(description="...")
parser.add_argument("--dry-run", action="store_true", help="...")
args = parser.parse_args()
```

Scripts exit with `raise SystemExit(1)` (not `sys.exit(1)`) on fatal errors.

### Override-JSON Pattern

**Central pattern for data overrides across all scripts:**
- JSON files in `scripts/` act as override layers: `badges.json`, `photo_overrides.json`, `description_overrides.json`, `category_map.json`, `photo_urls.json`
- Scripts load override files with graceful fallback if file missing:
```python
def load_badges() -> dict:
    badges_path = SCRIPT_DIR / "badges.json"
    if not badges_path.exists():
        log.warning("File badges.json not found — badges disabled")
        return {"исключения": [], "новинка": [], "хит": [], "акция": []}
    with open(badges_path, "r", encoding="utf-8") as f:
        return json.load(f)
```
- Merging pattern (new data wins over existing):
```python
merged = {**existing, **new_data}
```
- Lookup is always case-insensitive partial match:
```python
if substring.lower() in name_lower:
```

### Error Handling in Python

**Never silently swallow exceptions in main logic.** Catch specific exceptions and log them:
```python
try:
    price = float(b)
except (ValueError, TypeError):
    log.warning("Cannot read price: '%s' (row: %s)", b, name)
    continue
```

**Missing files: log + return empty, not raise** (for override files):
```python
if not badges_path.exists():
    log.warning("...")
    return {}
```

**Critical missing files: log + SystemExit(1)** (for required inputs):
```python
if not SHEET_PATH.exists():
    log.error("File not found: %s", SHEET_PATH)
    raise SystemExit(1)
```

### Comments

**All comments in Russian** — this is an explicit project requirement for new files.

**Docstrings on every function** explaining what it does and its return value:
```python
def get_badge(name: str, badges: dict) -> str:
    """Определить метку для товара по его названию.

    Приоритет: исключения → новинка → хит → акция.
    Поиск по частичному совпадению, регистронезависимый.
    """
```

**Inline comments** for non-obvious logic — e.g., why a specific regex, why a priority order.

**Section separators** with `# ──` style for long functions:
```python
# ── Обновить photo_overrides.json ─────────────────────────────────────────
```

### Encoding

All Python files use UTF-8 explicitly:
```python
sys.stdout.reconfigure(encoding="utf-8")
# and for file reads:
with open(path, "r", encoding="utf-8") as f:
```

---

## Cross-Cutting Rules

**Russian UI text everywhere** — all user-visible strings, error messages, log messages, and comments are in Russian.

**`--dry-run` flag** is required in all Python scripts that write files or make API calls. Dry-run mode prints what would be done without doing it.

**File encoding** — always specify `encoding="utf-8"` in Python file operations.

**JSON persistence** — always `ensure_ascii=False, indent=2` when writing JSON files:
```python
json.dump(data, f, ensure_ascii=False, indent=2)
```

---

*Convention analysis: 2026-06-06*
