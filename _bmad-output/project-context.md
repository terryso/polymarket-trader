---
project_name: 'polymarket-trader'
user_name: 'Nick'
date: '2026-02-15'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'critical_rules']
status: 'complete'
rule_count: 45
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### Backend (Python)

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | ≥3.10 | Runtime |
| FastAPI | ≥0.109.0 | Web framework |
| Pydantic | v2 (≥2.0.0) | Data validation |
| pydantic-settings | ≥2.0.0 | Configuration |
| aiosqlite | ≥0.19.0 | Async SQLite |
| APScheduler | ≥3.10.0 | Task scheduling |
| colorlog | ≥6.7.0 | Colored logging |
| openai | ≥1.0.0 | LLM API (GLM compatible) |
| py-clob-client | ≥0.1.0 | Polymarket API |

### Frontend (React)

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.3.1 | UI framework |
| TypeScript | 5.8.3 | Type system |
| Vite | 5.4.19 | Build tool |
| Tailwind CSS | 3.4.17 | Styling |
| TanStack Query | 5.83.0 | Data fetching |
| React Router | 6.30.1 | Routing |
| Recharts | 2.15.4 | Charts |
| shadcn/ui | 50+ components | UI components |

### Dev Tools

| Tool | Config |
|------|--------|
| black | line-length: 88 |
| isort | profile: black |
| mypy | strict mode (disallow_untyped_defs) |
| pytest | asyncio_mode: auto |
| Vitest | jsdom environment |

---

## Critical Implementation Rules

### Language-Specific Rules

#### Python

**Type Annotations (mypy strict mode):**
- ALL functions must have complete type annotations
- Use `list[Model]` syntax (Python 3.10+), not `List[Model]`
- Use `Model | None` for optional, not `Optional[Model]`

```python
# ✅ Correct
def get_market(market_id: str) -> Market | None:
    ...

# ❌ Wrong - mypy will reject
def get_market(market_id):
    ...
```

**Pydantic v2 Patterns:**
- Use `model_config = SettingsConfigDict(...)` not `class Config`
- Use `@field_validator` not `@validator`
- Use `Field(default=...)` for field definitions

```python
class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_")

    api_key: str = Field(default="", description="API key")

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        return v
```

**Async Patterns:**
- Use `aiosqlite` for database operations
- Never use blocking IO in async functions
- Use `asyncio` for concurrent operations

#### TypeScript

**Path Aliases:**
- ALWAYS use `@/` alias for imports from `src/`
- NEVER use deep relative paths like `../../../`

```typescript
// ✅ Correct
import { StatCard } from "@/components/dashboard/StatCard";

// ❌ Wrong
import { StatCard } from "../../../components/dashboard/StatCard";
```

**Interface vs Type:**
- Prefer `interface` for object shapes
- Use `type` only for unions, intersections, or primitives

**Async/Await:**
- ALWAYS use `async/await` syntax
- NEVER mix with `.then()` chains

### Framework-Specific Rules

#### FastAPI

**Router Organization:**
- Routers in `src/dashboard/routes/` by resource
- Use `APIRouter` with prefix and tags

```python
router = APIRouter(prefix="/api/markets", tags=["markets"])

@router.get("/{market_id}")
async def get_market(market_id: str) -> MarketResponse:
    ...
```

**Dependency Injection:**
- Use `Annotated[..., Depends()]` pattern

```python
from typing import Annotated

@router.get("/protected")
async def protected_route(
    user: Annotated[User, Depends(get_current_user)]
):
    ...
```

**Response Models:**
- ALWAYS define `response_model` for type safety

```python
@router.get("/markets", response_model=list[MarketResponse])
async def list_markets() -> list[MarketResponse]:
    ...
```

#### React

**Component Structure:**
- Function components only (no class components)
- Define Props interface above component

```typescript
interface StatCardProps {
  icon: ReactNode;
  title: string;
  value: string;
}

export function StatCard({ icon, title, value }: StatCardProps) {
  return <div>...</div>;
}
```

**Data Fetching:**
- Use TanStack Query for all server state
- Custom hooks in `hooks/` directory

```typescript
// hooks/useMarkets.ts
export function useMarkets() {
  return useQuery({ queryKey: ["markets"], queryFn: fetchMarkets });
}
```

**shadcn/ui Usage:**
- Components in `components/ui/` (already installed)
- Use `cn()` from `@/lib/utils` for class merging

```typescript
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

<div className={cn("base-class", condition && "conditional-class")}>
```

**State Management:**
- TanStack Query for server state
- React Context or useState for UI state
- NO Redux/MobX/etc.

### Testing Rules

#### Python (pytest)

**Test Organization:**
- Mirror `src/` structure in `tests/`
- Shared fixtures in `conftest.py`

```
tests/
├── conftest.py
├── test_models/
├── test_api/
├── test_analysis/
└── test_trading/
```

**Fixtures:**
```python
# Use fixtures from conftest.py
def test_get_market(mock_settings, sample_market_data):
    ...

# Async fixtures with pytest_asyncio
@pytest_asyncio.fixture
async def mock_db_connection():
    conn = AsyncMock()
    yield conn
```

**Async Tests:**
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

#### React (Vitest + Testing Library)

**Test Structure:**
- Test files: `ComponentName.test.tsx`
- Location: Same directory as component

```typescript
import { render, screen } from "@testing-library/react";

describe("StatCard", () => {
  it("renders title and value", () => {
    render(<StatCard icon={<span />} title="Test" value="$100" />);
    expect(screen.getByText("Test")).toBeInTheDocument();
  });
});
```

**Mocking TanStack Query:**
```typescript
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } }
});

const wrapper = ({ children }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

render(<Component />, { wrapper });
```

### Code Quality & Style Rules

#### Naming Conventions

| Category | Python | TypeScript |
|----------|--------|------------|
| Files | `snake_case.py` | `PascalCase.tsx` |
| Classes | `PascalCase` | `PascalCase` |
| Functions/Methods | `snake_case()` | `camelCase()` |
| Variables | `snake_case` | `camelCase` |
| Constants | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` |
| Interfaces | - | `PascalCase` |
| Private members | `_leading_underscore` | `#private` or `_prefix` |

#### Project Structure

```
polymarket-trader/
├── src/                    # Python backend
│   ├── models/             # Pydantic models
│   ├── api/                # API clients
│   ├── core/               # Core logic
│   ├── analysis/           # Analysis modules
│   ├── trading/            # Trading modules
│   ├── storage/            # Data storage
│   ├── dashboard/          # FastAPI routes
│   └── utils/              # Utilities
├── dashboard/              # React frontend
│   └── src/
│       ├── components/     # UI components
│       │   ├── ui/         # shadcn/ui
│       │   ├── dashboard/  # Business components
│       │   └── layout/     # Layout components
│       ├── pages/          # Page components
│       ├── hooks/          # Custom hooks
│       ├── lib/            # Utilities
│       └── types/          # TypeScript types
└── tests/                  # Python tests
```

#### Logging Format

```
{timestamp} | {level:8} | {thread:12} | {module} | {emoji} {message}
```

**Emoji Usage:**
| Operation | Emoji |
|-----------|-------|
| Success | ✅ |
| Warning | ⚠️ |
| Error | ❌ |
| Trade | 💰 |
| Analysis | 🧠 |
| Data | 📊 |
| Network | 🌐 |

### Critical Don't-Miss Rules

#### Security

**Sensitive Information Handling:**
- API Keys: Log shows only first 4 chars → `"sk-xxxx****"`
- Private Keys: Completely hidden → `"[PRIVATE_KEY]"`
- Wallet Addresses: First 6 + last 4 → `"0x1234...5678"`
- NEVER hardcode secrets in code
- Use `.env` file with `chmod 600` permissions

**Log Sanitization (auto-handled by SanitizingFilter):**
```python
# Sensitive data is automatically masked
logger.info(f"API Key: {api_key}")  # Auto-sanitized
```

#### Exception Handling

**Use Project Exception Hierarchy:**
```python
from src.exceptions import (
    BotError, ConfigurationError, NetworkError,
    TradingError, ValidationError, RateLimitError,
    TimeoutError, InsufficientFundsError, RiskLimitExceededError
)

try:
    result = await api_call()
except NetworkError as e:
    logger.error(f"❌ Network error: {e}")
except ValidationError as e:
    logger.warning(f"⚠️ Validation error: {e}")
except Exception as e:
    logger.critical(f"🔥 Unexpected error: {e}")
    raise
```

#### API Integration

**Polymarket API:**
- Use `py-clob-client` library
- All prices are 0-1 range (NOT 0-100)
- YES price + NO price = 1

**LLM API (GLM):**
- Uses OpenAI-compatible protocol
- Base URL: `https://open.bigmodel.cn/api/paas/v4`
- Model: `glm-4`

#### Database

- Location: `data/polymarket.db`
- Use `aiosqlite` for async operations
- DateTime format: `"2026-02-15 10:30:00"`

#### React Anti-Patterns

```typescript
// ❌ NEVER modify state directly
state.items.push(newItem);

// ✅ Always create new state
setState(prev => [...prev, newItem]);

// ❌ NEVER use async in useEffect directly
useEffect(async () => { ... }, []);

// ✅ Use proper async pattern or TanStack Query
useEffect(() => {
  fetchData().then(setData);
}, []);
```

#### Performance

```python
# ❌ NEVER query in loop
for market in markets:
    await db.execute("INSERT ...", (market,))

# ✅ Use batch operations
await db.executemany("INSERT ...", [(m,) for m in markets])
```

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**
- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

---

_Last Updated: 2026-02-15_
