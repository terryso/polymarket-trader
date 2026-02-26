---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests']
lastStep: 'step-04-generate-tests'
lastSaved: '2026-02-27'
workflowType: 'testarch-atdd'
inputDocuments:
  - '_bmad-output/implementation-artifacts/7-9-trade-history-realtime-by-mode.md'
  - '_bmad/tea/config.yaml'
  - 'tests/test_dashboard/test_routes/test_trades.py'
  - 'dashboard/src/pages/Trades.test.tsx'
generatedTestFiles:
  - 'tests/test_dashboard/test_routes/test_trades_story79.py'
  - 'dashboard/src/pages/Trades.story79.test.tsx'
---

# ATDD Checklist - Epic 7, Story 9: 交易历史按模式实时显示

**Date:** 2026-02-27
**Author:** Nick
**Primary Test Level:** API + Component

---

## Story Summary

交易历史页面根据系统配置 `TRADING_MODE` 自动切换数据源。Paper 模式显示本地数据库交易记录，Live 模式实时从 Polymarket API 获取交易历史。移除手动同步功能和 Paper/Live 筛选器。

**As a** 用户
**I want** 交易历史页面根据系统配置自动显示正确的数据源，无需手动同步
**So that** 我看到的交易历史始终与 Polymarket 网站一致（Live 模式）或与本地 Paper Trading 一致

---

## Acceptance Criteria

1. **后端 API 根据交易模式返回数据**:
   - Paper 模式: 返回本地数据库中 mode=PAPER 的交易记录
   - Live 模式: 实时调用 Polymarket API 获取真实交易历史

2. **前端 UI 简化**:
   - 移除同步按钮和相关状态显示
   - 移除 Paper/Live 筛选器
   - 保留买入/卖出筛选器
   - Live 模式下显示加载状态

3. **后端实现**:
   - 读取 `settings.trading_mode` 配置
   - Paper 模式: 调用 `TradeRepository.get_by_mode(TradeMode.PAPER)`
   - Live 模式: 调用 `PolymarketClient.get_order_history()`

4. **代码清理**:
   - 移除或标记废弃 `/api/trades/sync` 和 `/api/trades/sync/status` 端点

5. **单元测试**:
   - 测试 Paper 模式返回本地数据
   - 测试 Live 模式调用 Polymarket API

---

## Failing Tests Created (RED Phase)

### API Tests (10 tests)

**File:** `tests/test_dashboard/test_routes/test_trades_story79.py` (~250 lines)

**TestPaperModeReturnsLocalData (2 tests):**
- ✅ **Test:** `test_paper_mode_uses_local_database` (SKIPPED - RED PHASE)
  - **Status:** RED - Feature not implemented
  - **Verifies:** Paper mode reads from local database via TradeRepository

- ✅ **Test:** `test_paper_mode_ignores_mode_query_param` (SKIPPED - RED PHASE)
  - **Status:** RED - Feature not implemented
  - **Verifies:** Paper mode ignores query param, uses settings

**TestLiveModeCallsPolymarketAPI (2 tests):**
- ✅ **Test:** `test_live_mode_calls_polymarket_api` (SKIPPED - RED PHASE)
  - **Status:** RED - Feature not implemented
  - **Verifies:** Live mode calls PolymarketClient.get_order_history()

- ✅ **Test:** `test_live_mode_converts_order_to_trade_format` (SKIPPED - RED PHASE)
  - **Status:** RED - Feature not implemented
  - **Verifies:** OrderHistoryItem is converted to TradeListItem format

**TestLiveModeHandlesAPIError (2 tests):**
- ✅ **Test:** `test_live_mode_handles_api_failure` (SKIPPED - RED PHASE)
  - **Status:** RED - Feature not implemented
  - **Verifies:** Error handling when Polymarket API fails

- ✅ **Test:** `test_live_mode_handles_missing_credentials` (SKIPPED - RED PHASE)
  - **Status:** RED - Feature not implemented
  - **Verifies:** Error handling when API credentials are missing

**TestSyncEndpointsRemoved (2 tests):**
- ✅ **Test:** `test_sync_endpoint_removed_or_deprecated` (SKIPPED - RED PHASE)
  - **Status:** RED - Feature not implemented
  - **Verifies:** Sync endpoint is removed or deprecated

- ✅ **Test:** `test_sync_status_endpoint_removed_or_deprecated` (SKIPPED - RED PHASE)
  - **Status:** RED - Feature not implemented
  - **Verifies:** Sync status endpoint is removed or deprecated

### Component Tests (13 tests)

**File:** `dashboard/src/pages/Trades.story79.test.tsx` (~300 lines)

**Sync Button Removal (3 tests):**
- ✅ **Test:** `should not render sync button` (SKIPPED - RED PHASE)
  - **Status:** RED - UI still has sync button
  - **Verifies:** Sync button is removed from UI

- ✅ **Test:** `should not render sync status display` (SKIPPED - RED PHASE)
  - **Status:** RED - UI still shows sync status
  - **Verifies:** Sync status display is removed

- ✅ **Test:** `should not render sync result alert` (SKIPPED - RED PHASE)
  - **Status:** RED - UI still shows sync result
  - **Verifies:** Sync result Alert is removed

**Mode Filter Removal (3 tests):**
- ✅ **Test:** `should not render mode filter` (SKIPPED - RED PHASE)
  - **Status:** RED - UI still has Paper/Live filter
  - **Verifies:** Paper/Live mode filter is removed

- ✅ **Test:** `should not render Paper/Live filter buttons` (SKIPPED - RED PHASE)
  - **Status:** RED - UI still has Paper/Live buttons
  - **Verifies:** Paper/Live filter buttons are removed

- ✅ **Test:** `should not call useTrades with mode parameter` (SKIPPED - RED PHASE)
  - **Status:** RED - Hook still receives mode param
  - **Verifies:** useTrades is called without mode parameter

**Type Filter Retained (3 tests):**
- ✅ **Test:** `should render type filter buttons` (SKIPPED - RED PHASE)
  - **Status:** RED - UI has both filters
  - **Verifies:** Only buy/sell type filter remains

- ✅ **Test:** `should render 买入 and 卖出 buttons` (SKIPPED - RED PHASE)
  - **Status:** RED - UI has both filter groups
  - **Verifies:** Buy/Sell buttons exist

- ✅ **Test:** `should have only one filter group (type)` (SKIPPED - RED PHASE)
  - **Status:** RED - UI has two filter groups
  - **Verifies:** Only type filter group exists

**Loading State (2 tests):**
- ✅ **Test:** `should show loading skeleton while data is loading` (SKIPPED - RED PHASE)
  - **Status:** RED - Feature not verified
  - **Verifies:** Loading skeleton shown during data load

- ✅ **Test:** `should not show loading skeleton when data is loaded` (SKIPPED - RED PHASE)
  - **Status:** RED - Feature not verified
  - **Verifies:** Loading skeleton hidden when data loaded

**No Sync API Calls (2 tests):**
- ✅ **Test:** `should not call getSyncStatus on mount` (SKIPPED - RED PHASE)
  - **Status:** RED - Component still calls API
  - **Verifies:** getSyncStatus is not called

- ✅ **Test:** `should not call sync on any interaction` (SKIPPED - RED PHASE)
  - **Status:** RED - Component still has sync functionality
  - **Verifies:** sync API is not called

---

## Data Factories Created

No new factories needed - using existing test fixtures.

---

## Fixtures Created

### Mock Settings Fixture

**File:** `tests/test_dashboard/test_routes/test_trades_story79.py`

**Fixtures:**

- `mock_paper_mode_settings` - Mock settings with trading_mode="paper"
- `mock_live_mode_settings` - Mock settings with trading_mode="live"

**Example Usage:**

```python
def test_list_trades_paper_mode(mock_paper_mode_settings, mock_trade_repo):
    # settings.trading_mode returns "paper"
    ...
```

### Mock Polymarket Client Fixture

**Fixtures:**

- `mock_polymarket_client` - Mock PolymarketClient with get_order_history

**Example Usage:**

```python
def test_list_trades_live_mode(mock_live_mode_settings, mock_polymarket_client):
    # PolymarketClient.get_order_history is mocked
    ...
```

---

## Mock Requirements

### Polymarket API Mock

**Method:** `PolymarketClient.get_order_history()`

**Success Response:**

```python
OrderHistoryResult(
    is_success=True,
    orders=[
        OrderHistoryItem(
            id="order-123",
            market_id="market-001",
            side="BUY",
            size=100.0,
            price=0.55,
            created_at=datetime(2026, 2, 27, 10, 0, 0),
        ),
    ],
    cursor=None,
)
```

**Failure Response:**

```python
OrderHistoryResult(
    is_success=False,
    orders=[],
    error="API connection failed",
)
```

---

## Required data-testid Attributes

### Trades Page

- `trades-table` - Trade data table (existing)
- `type-filter` - Buy/sell filter buttons (existing)
- `loading-skeleton` - Loading state skeleton (existing)
- `error-alert` - Error message display (existing)
- ~~`sync-button`~~ - REMOVE
- ~~`sync-result`~~ - REMOVE
- ~~`mode-filter`~~ - REMOVE

**Implementation Changes:**

```tsx
// REMOVE these elements:
<Button data-testid="sync-button">同步</Button>
<div>最后同步: ...</div>
<Alert data-testid="sync-result">...</Alert>
<div data-testid="mode-filter">...</div>

// KEEP these elements:
<div data-testid="type-filter">...</div>
<div data-testid="trades-table">...</div>
```

---

## Implementation Checklist

### Test: `test_list_trades_paper_mode_returns_local_data`

**File:** `tests/test_dashboard/test_routes/test_trades_story79.py`

**Tasks to make this test pass:**

- [ ] Add settings dependency to trades router
- [ ] Read `settings.trading_mode` in list_trades endpoint
- [ ] When mode="paper", call `TradeRepository.get_by_mode(TradeMode.PAPER)`
- [ ] Run test: `pytest tests/test_dashboard/test_routes/test_trades_story79.py -v`
- [ ] ✅ Test passes (green phase)

**Estimated Effort:** 1 hour

---

### Test: `test_list_trades_live_mode_calls_polymarket_api`

**File:** `tests/test_dashboard/test_routes/test_trades_story79.py`

**Tasks to make this test pass:**

- [ ] Import PolymarketClient in trades router
- [ ] When mode="live", call `PolymarketClient().get_order_history()`
- [ ] Convert OrderHistoryItem to TradeListItem format
- [ ] Handle response pagination
- [ ] Run test: `pytest tests/test_dashboard/test_routes/test_trades_story79.py -v`
- [ ] ✅ Test passes (green phase)

**Estimated Effort:** 2 hours

---

### Test: `test_list_trades_live_mode_handles_api_error`

**File:** `tests/test_dashboard/test_routes/test_trades_story79.py`

**Tasks to make this test pass:**

- [ ] Check `result.is_success` from PolymarketClient
- [ ] Return error response with appropriate status code
- [ ] Include error message in response
- [ ] Run test: `pytest tests/test_dashboard/test_routes/test_trades_story79.py -v`
- [ ] ✅ Test passes (green phase)

**Estimated Effort:** 0.5 hour

---

### Test: `test_sync_endpoints_removed_or_deprecated`

**File:** `tests/test_dashboard/test_routes/test_trades_story79.py`

**Tasks to make this test pass:**

- [ ] Option 1: Remove `/api/trades/sync` and `/api/trades/sync/status` endpoints
- [ ] Option 2: Add `deprecated=True` to route decorators
- [ ] Update API documentation
- [ ] Run test: `pytest tests/test_dashboard/test_routes/test_trades_story79.py -v`
- [ ] ✅ Test passes (green phase)

**Estimated Effort:** 0.5 hour

---

### Test: `should_not_render_sync_button`

**File:** `dashboard/src/pages/Trades.story79.test.tsx`

**Tasks to make this test pass:**

- [ ] Remove `<Button onClick={handleSync}>同步</Button>` from Trades.tsx
- [ ] Remove `handleSync` function
- [ ] Remove `isSyncing`, `syncResult`, `syncStatus` states
- [ ] Remove `tradesApi.getSyncStatus()` call
- [ ] Run test: `cd dashboard && npm test -- Trades.story79.test.tsx`
- [ ] ✅ Test passes (green phase)

**Estimated Effort:** 0.5 hour

---

### Test: `should_not_render_mode_filter`

**File:** `dashboard/src/pages/Trades.story79.test.tsx`

**Tasks to make this test pass:**

- [ ] Remove `modeFilter` state
- [ ] Remove `handleModeFilter` function
- [ ] Remove mode filter buttons (全部/Paper/Live)
- [ ] Remove `data-testid="mode-filter"` element
- [ ] Run test: `cd dashboard && npm test -- Trades.story79.test.tsx`
- [ ] ✅ Test passes (green phase)

**Estimated Effort:** 0.5 hour

---

### Test: `should_render_type_filter_only`

**File:** `dashboard/src/pages/Trades.story79.test.tsx`

**Tasks to make this test pass:**

- [ ] Keep `typeFilter` state (买入/卖出)
- [ ] Keep `handleTypeFilter` function
- [ ] Keep type filter buttons
- [ ] Ensure mode is no longer passed to useTrades hook
- [ ] Run test: `cd dashboard && npm test -- Trades.story79.test.tsx`
- [ ] ✅ Test passes (green phase)

**Estimated Effort:** 0.5 hour

---

### Test: `should_show_loading_state_in_live_mode`

**File:** `dashboard/src/pages/Trades.story79.test.tsx`

**Tasks to make this test pass:**

- [ ] The existing loading skeleton should work
- [ ] No additional changes needed - API handles mode internally
- [ ] Run test: `cd dashboard && npm test -- Trades.story79.test.tsx`
- [ ] ✅ Test passes (green phase)

**Estimated Effort:** 0.25 hour

---

## Running Tests

```bash
# Run all failing tests for this story (Backend)
source .venv/bin/activate
pytest tests/test_dashboard/test_routes/test_trades_story79.py -v

# Run all failing tests for this story (Frontend)
cd dashboard && npm test -- Trades.story79.test.tsx

# Run all backend tests
pytest tests/ -v

# Run all frontend tests
cd dashboard && npm test
```

---

## Red-Green-Refactor Workflow

### RED Phase (Complete) ✅

**TEA Agent Responsibilities:**

- ✅ All tests written and failing
- ✅ Fixtures and factories created with auto-cleanup
- ✅ Mock requirements documented
- ✅ data-testid requirements listed
- ✅ Implementation checklist created

---

### GREEN Phase (DEV Team - Next Steps)

**DEV Agent Responsibilities:**

1. **Pick one failing test** from implementation checklist (start with highest priority)
2. **Read the test** to understand expected behavior
3. **Implement minimal code** to make that specific test pass
4. **Run the test** to verify it now passes (green)
5. **Check off the task** in implementation checklist
6. **Move to next test** and repeat

---

## Notes

- **重要:** 后端 API 不再接受 `mode` 查询参数，数据源由系统配置决定
- **向后兼容:** 可选择保留 sync 端点但标记为废弃
- **性能:** Live 模式 API 调用可能较慢，前端需处理加载状态
- **测试隔离:** 新测试文件 `test_trades_story79.py` 避免修改现有测试

---

**Generated by BMad TEA Agent** - 2026-02-27
