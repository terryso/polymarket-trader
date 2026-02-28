# Test Design: Epic 5 - Paper Trading 模拟交易

**Date:** 2026-02-28
**Author:** Nick
**Status:** Draft

---

## Executive Summary

**Scope:** Epic-Level test design for Epic 5 - Paper Trading 模拟交易

**Risk Summary:**

- Total risks identified: 6
- High-priority risks (≥6): 2
- Critical categories: DATA, TECH

**Coverage Summary:**

- P0 scenarios: 6 (8-12 hours)
- P1 scenarios: 11 (10-15 hours)
- P2/P3 scenarios: 6 (4-8 hours)
- **Total effort**: 22-35 hours (~3-5 days)

---

## Not in Scope

| Item | Reasoning | Mitigation |
|------|-----------|------------|
| **Live Trading** | Epic 5 仅覆盖 Paper Trading 模式 | Epic 10+ 单独测试 Live Trading |
| **LLM API 集成** | Epic 3 已覆盖 LLM 分析器 | 依赖 Epic 3 测试通过 |
| **Polymarket API** | Epic 2 已覆盖市场数据获取 | 依赖 Epic 2 测试通过 |
| **数据库迁移** | Epic 1 已覆盖基础设施 | 使用 test fixtures 隔离 |

---

## Risk Assessment

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
| ------- | -------- | ----------- | ----------- | ------ | ----- | ---------- | ----- | -------- |
| R-001 | DATA | 交易金额计算精度错误导致资金损失 | 2 | 3 | **6** | 1. 使用 Decimal 类型<br>2. 添加精度边界测试<br>3. 验证 shares = amount / price | QA Team | Sprint 结束 |
| R-002 | TECH | 并发交易导致持仓状态不一致 | 2 | 3 | **6** | 1. 添加并发测试<br>2. 验证 ThreadSafeState 锁机制<br>3. 测试批量处理边界 | Dev Team | Sprint 结束 |

### Medium-Priority Risks (Score 4-5)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
| ------- | -------- | ----------- | ----------- | ------ | ----- | ---------- | ----- |
| R-003 | DATA | PnL 计算公式错误导致收益统计失真 | 2 | 2 | 4 | 验证 BUY_YES/BUY_NO 两种 PnL 公式 | QA Team |
| R-004 | DATA | 统计数据记录遗漏导致报表不完整 | 2 | 2 | 4 | 验证统计记录完整性和准确性 | QA Team |

### Low-Priority Risks (Score 1-3)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
| ------- | -------- | ----------- | ----------- | ------ | ----- | ------ |
| R-005 | BUS | 交易执行失败但状态未正确回滚 | 1 | 3 | 3 | Monitor |
| R-006 | BUS | 持仓超限检查失效导致过度投资 | 1 | 3 | 3 | Monitor |

### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)

---

## Entry Criteria

- [x] Epic 1-4 相关测试已通过
- [ ] 测试数据库已初始化 (SQLite in-memory)
- [ ] Test fixtures 和 factories 已准备
- [ ] 代码已部署到测试环境

## Exit Criteria

- [ ] 所有 P0 测试通过
- [ ] 所有 P1 测试通过 (或失败已 triage)
- [ ] 无 open high-priority / high-severity bugs
- [ ] `src/trading/` 覆盖率 ≥ 80%

---

## Test Coverage Plan

> **Note:** P0/P1/P2/P3 = priority and risk level, NOT execution timing. See Execution Strategy section for timing.

### P0 (Critical)

**Criteria:** Blocks core journey + High risk (≥6) + No workaround

| Test ID | Requirement | Test Level | Risk Link | Status | Notes |
| ------- | ----------- | ---------- | --------- | ------ | ----- |
| 5.2-UNIT-001 | BUY_YES 交易成功 | Unit | R-001 | ✅ 已有 | 验证完整交易流程 |
| 5.2-UNIT-002 | BUY_NO 交易成功 | Unit | R-001 | ✅ 已有 | 验证完整交易流程 |
| 5.2-UNIT-003 | 份额计算精度 | Unit | R-001 | ⚠️ 需加强 | 极端边界测试 |
| 5.3-INT-001 | 批量市场处理 | Integration | R-002 | ⚠️ 需加强 | 添加并发测试 |
| 5.4-UNIT-001 | BUY_YES PnL 计算 | Unit | R-003 | ❌ 需新增 | 核心计算公式 |
| 5.4-UNIT-002 | BUY_NO PnL 计算 | Unit | R-003 | ❌ 需新增 | 核心计算公式 |

**Total P0:** 6 scenarios, ~8-12 hours

### P1 (High)

**Criteria:** Important features + Medium risk + Common workflows

| Test ID | Requirement | Test Level | Risk Link | Status | Notes |
| ------- | ----------- | ---------- | --------- | ------ | ----- |
| 5.2-UNIT-004 | 无效金额拒绝 (0/负数) | Unit | R-005 | ✅ 已有 | 输入验证 |
| 5.2-UNIT-005 | 无效价格拒绝 (None/0/1) | Unit | R-005 | ✅ 已有 | 边界条件 |
| 5.2-UNIT-006 | 极端金额边界 | Unit | R-001 | ⚠️ 需加强 | 精度边界 |
| 5.3-UNIT-003 | 风险检查拒绝处理 | Unit | R-006 | ✅ 已有 | 风控逻辑 |
| 5.3-UNIT-005 | 仓位计算正常 | Unit | - | ✅ 已有 | 金额计算 |
| 5.3-UNIT-006 | 仓位计算边界 (min/max) | Unit | R-001 | ✅ 已有 | 边界条件 |
| 5.4-UNIT-003 | 总 PnL 汇总 | Unit | R-003 | ⚠️ 需加强 | 汇总逻辑 |
| 5.5-UNIT-001 | 每日统计计算 | Unit | R-004 | ✅ 已有 | 统计逻辑 |
| 5.5-UNIT-002 | 胜率计算 | Unit | R-004 | ⚠️ 需加强 | 公式验证 |
| 5.1-INT-001 | TradeRepo.save 持久化 | Integration | - | ✅ 已有 | 数据库操作 |
| 5.2-INT-001 | 完整交易流程集成 | Integration | - | ✅ 已有 | 端到端流程 |

**Total P1:** 11 scenarios, ~10-15 hours

### P2 (Medium)

**Criteria:** Secondary features + Low risk + Edge cases

| Test ID | Requirement | Test Level | Risk Link | Status | Notes |
| ------- | ----------- | ---------- | --------- | ------ | ----- |
| 5.1-UNIT-002 | TradeType 枚举完整性 | Unit | - | ✅ 已有 | 枚举验证 |
| 5.1-INT-002 | TradeRepo 外键约束 | Integration | - | ⚠️ 需加强 | 约束验证 |
| 5.4-INT-001 | PnL 实时更新 | Integration | R-003 | ⚠️ 需加强 | 实时计算 |
| 5.5-INT-001 | 统计持久化 | Integration | R-004 | ✅ 已有 | 数据库操作 |
| 5.5-INT-002 | 统计查询 API | Integration | - | ⚠️ 需加强 | API 验证 |
| 5.3-INT-002 | 批量处理含失败 | Integration | - | ✅ 已有 | 错误处理 |

**Total P2:** 6 scenarios, ~4-8 hours

### P3 (Low)

**Criteria:** Nice-to-have + Exploratory + Performance benchmarks

**当前无 P3 测试需求** - 所有核心功能已覆盖在 P0-P2 中。

---

## Execution Strategy

### PR Check (每次提交)

**触发条件:** 每次 PR 提交
**测试范围:** P0 单元测试 + P1 集成测试
**预期时长:** < 5 分钟

```bash
pytest tests/test_trading/ -v -k "paper_trading or executor" --ignore=tests/integration
```

### Nightly (每日凌晨)

**触发条件:** 每日凌晨定时执行
**测试范围:** P0 + P1 全量测试
**预期时长:** ~15 分钟

```bash
pytest tests/test_trading/ tests/integration/test_paper_trading_integration.py tests/integration/test_executor_integration.py -v
```

### Pre-Release (发布前)

**触发条件:** 版本发布前
**测试范围:** P0 + P1 + P2 全量 + 覆盖率报告
**预期时长:** ~30 分钟

```bash
pytest tests/test_trading/ tests/integration/ -v --cov=src/trading --cov-report=html
```

---

## Resource Estimates

### Test Development Effort

| Priority | Count | Hours/Test | Total Hours | Notes |
|----------|-------|------------|-------------|-------|
| P0 | 6 | 1.5-2 | 8-12 | 新增 2 + 加强 2 + 已有 2 |
| P1 | 11 | 0.8-1.2 | 10-15 | 加强 5 + 已有 6 |
| P2 | 6 | 0.5-1 | 4-8 | 加强 4 + 已有 2 |
| **Total** | **23** | **-** | **22-35** | **~3-5 days** |

### Prerequisites

**Test Data:**

- `create_trade()` factory - 已有 fixture
- `create_market()` factory - 已有 fixture
- `create_prediction()` factory - 已有 fixture
- `create_position()` factory - 已有 fixture

**Tooling:**

- pytest + pytest-asyncio - 已配置
- pytest-cov - 已配置
- aiosqlite (in-memory) - 已配置

**Environment:**

- Python 3.10+ - 已满足
- SQLite in-memory database - 已满足

---

## Quality Gate Criteria

### Pass/Fail Thresholds

- **P0 pass rate**: 100% (no exceptions)
- **P1 pass rate**: ≥95% (waivers required for failures)
- **P2 pass rate**: ≥90% (informational)
- **High-risk mitigations**: 100% complete or approved waivers

### Coverage Targets

- **Critical paths (src/trading/)**: ≥80%
- **Risk-covered scenarios**: 100% for R-001, R-002
- **Business logic**: ≥70%

### Non-Negotiable Requirements

- [ ] 所有 P0 测试通过
- [ ] 高风险项 (R-001, R-002) 必须有测试覆盖
- [ ] 交易金额计算精度测试必须包含边界值

---

## Mitigation Plans

### R-001: 交易金额计算精度错误 (Score: 6)

**Mitigation Strategy:**
1. 使用 Python `decimal.Decimal` 类型进行金额计算
2. 添加精度边界测试 (极小/极大金额、价格)
3. 验证 `shares = amount / price` 公式在边界条件下的精度

**Owner:** QA Team
**Timeline:** Sprint 结束前
**Status:** Planned
**Verification:** 测试用例覆盖所有精度边界场景

### R-002: 并发交易导致持仓状态不一致 (Score: 6)

**Mitigation Strategy:**
1. 添加 `asyncio.gather()` 并发执行测试
2. 验证 `ThreadSafeState` 锁机制正确性
3. 测试批量处理边界条件 (同时处理 10+ 市场)

**Owner:** Dev Team
**Timeline:** Sprint 结束前
**Status:** Planned
**Verification:** 并发测试通过，无竞态条件

---

## Assumptions and Dependencies

### Assumptions

1. Epic 1-4 的测试已通过，基础设施功能正常
2. LLM 分析器返回有效的 `PredictionResult`
3. 数据库操作使用 aiosqlite 异步执行
4. Paper Trading 不需要真实 API 调用

### Dependencies

1. Epic 1 测试通过 - 数据库和配置系统可用
2. Epic 2 测试通过 - 市场数据模型可用
3. Epic 3 测试通过 - LLM 预测模型可用
4. Epic 4 测试通过 - 风险控制器可用

### Risks to Plan

- **Risk:** 并发测试可能需要额外的 mock 设置
  - **Impact:** 延迟 R-002 缓解
  - **Contingency:** 使用 `unittest.mock.AsyncMock` 简化测试

---

## Interworking & Regression

| Service/Component | Impact | Regression Scope |
|-------------------|--------|------------------|
| **RiskController** | 交易前风险检查 | `test_risk_control.py` 必须通过 |
| **ThreadSafeState** | 资金和持仓状态 | `test_state.py` 必须通过 |
| **TradeRepository** | 交易记录持久化 | `test_trade_repo.py` 必须通过 |
| **PositionManager** | 持仓管理 | `test_position_manager.py` 必须通过 |

---

## Appendix

### Knowledge Base References

- `risk-governance.md` - Risk classification framework
- `probability-impact.md` - Risk scoring methodology
- `test-levels-framework.md` - Test level selection
- `test-priorities-matrix.md` - P0-P3 prioritization

### Related Documents

- PRD: `_bmad-output/planning-artifacts/prd.md`
- Epic: `_bmad-output/planning-artifacts/epics.md` (Epic 5)
- Architecture: `_bmad-output/planning-artifacts/architecture.md`

### Existing Test Files

- `tests/test_trading/test_paper_trading.py` - Story 5.2 (600+ lines)
- `tests/test_trading/test_executor.py` - Story 5.3 (750+ lines)
- `tests/test_trading/test_position_manager.py` - Story 5.4
- `tests/test_trading/test_statistics_recorder.py` - Story 5.5
- `tests/test_models/test_trade.py` - Story 5.1
- `tests/test_storage/test_repositories/test_trade_repo.py` - Story 5.1
- `tests/integration/test_paper_trading_integration.py` - Integration
- `tests/integration/test_executor_integration.py` - Integration

---

**Generated by**: BMad TEA Agent - Test Architect Module
**Workflow**: `_bmad/tea/testarch/test-design`
**Version**: 4.0 (BMad v6)
