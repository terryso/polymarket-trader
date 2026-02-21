---
title: '分析内容语言配置支持'
slug: 'analysis-language-config'
created: '2026-02-22'
status: 'completed'
stepsCompleted: [1, 2, 3, 4, 5, 6]
adversarial_review: passed
tech_stack:
  - Python 3.10+
  - Pydantic 2.x
  - pydantic-settings
files_to_modify:
  - src/config.py
  - src/analysis/prompts.py
  - src/analysis/llm_analyzer.py
  - tests/test_config.py
  - tests/test_analysis/test_prompts.py
  - .env.example
code_patterns:
  - BaseEnvSettings 继承自 BaseSettings
  - 使用 Literal 类型约束枚举值
  - 使用 Field(alias="...") 自定义环境变量名
  - 系统提示词为模块级常量字符串
  - 使用 patch.dict(os.environ, ...) 测试环境变量
test_patterns:
  - pytest + unittest.mock.patch.dict
  - 测试默认值和自定义值
  - 测试验证错误 (pytest.raises)
---

## Review Notes
- Adversarial review completed
- Findings: 12 total, 3 fixed, 9 skipped (noise/uncertain)
- Resolution approach: Auto-fix
- Fixed: F3 (logging), F5 (unknown language warning), F11 (whitespace handling)
- Additional tests added: 16 total (8 config tests, 8 prompt tests)

# Tech-Spec: 分析内容语言配置支持

**Created:** 2026-02-22

## Overview

### Problem Statement

预测记录详情中的分析过程（reasoning）和关键假设（key_assumptions）目前都是英文输出，因为 LLM 系统提示词是英文的。用户希望支持中英文切换，让分析内容以用户偏好的语言输出。

### Solution

在配置中添加 `analysis_language` 选项（支持 "zh" 和 "en"），修改 LLM 系统提示词根据配置动态注入语言指令，让 LLM 直接输出对应语言的分析内容。

### Scope

**In Scope:**
- `src/config.py` 添加 `analysis_language` 配置项，默认 "zh"
- `src/analysis/prompts.py` 修改系统提示词为动态函数
- `src/analysis/llm_analyzer.py` 调用新的提示词函数
- `.env.example` 添加新配置说明
- 相关单元测试更新

**Out of Scope:**
- 前端修改（无需改动，直接显示 LLM 输出）
- 历史数据翻译
- Telegram 通知语言（可作为后续优化）

## Context for Development

### Codebase Patterns

**配置模式 (config.py):**
```python
class LLMSettings(BaseEnvSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=_get_env_file(),
        extra="ignore",
    )
    api_key: str = Field(default="", description="...")
```

**提示词模式 (prompts.py):**
```python
MARKET_ANALYST_SYSTEM_PROMPT = """You are an expert..."""

def build_market_analysis_prompt(market: Market) -> str:
    return f"""Analyze the following..."""
```

### Files to Reference

| File | Purpose |
| ---- | ------- |
| src/config.py | `LLMSettings` 类定义，`_SettingsProxy.ENV_VARS_TO_CLEAR` |
| src/analysis/prompts.py | `MARKET_ANALYST_SYSTEM_PROMPT` 常量 |
| src/analysis/llm_analyzer.py | LLM 调用，使用系统提示词，已导入 `settings` |
| tests/test_config.py | 配置测试模式参考 |
| tests/test_analysis/test_prompts.py | 提示词测试模式参考 |

### Technical Decisions

1. **配置位置**: 在 `LLMSettings` 中添加，因为是 LLM 输出相关配置
2. **类型**: 使用 `Literal["zh", "en"]` 约束有效值（小写）
3. **默认值**: "zh"（中文），符合用户主要场景
4. **提示词改造**: 将常量改为函数，末尾追加语言指令
5. **向后兼容**: 保留 `MARKET_ANALYST_SYSTEM_PROMPT` 作为默认英文版本，添加 deprecation 警告
6. **大小写处理**: 使用 validator 将输入转换为小写

## Implementation Plan

### Tasks

- [x] **Task 1: 添加 analysis_language 配置项**
  - File: `src/config.py`
  - Action: 在 `LLMSettings` 类中添加新字段，包含大小写处理
  - Details:
    ```python
    from typing import Literal

    # 在 LLMSettings 类中添加
    analysis_language: Literal["zh", "en"] = Field(
        default="zh",
        alias="ANALYSIS_LANGUAGE",
        description="Language for LLM analysis output (zh=Chinese, en=English)",
    )

    @field_validator("analysis_language", mode="before")
    @classmethod
    def normalize_analysis_language(cls, v: str) -> str:
        """Normalize language to lowercase."""
        if isinstance(v, str):
            return v.lower()
        return v
    ```
  - 同时更新 `_SettingsProxy.ENV_VARS_TO_CLEAR` 列表，添加 `"ANALYSIS_LANGUAGE"`

- [x] **Task 2: 重构提示词为动态函数**
  - File: `src/analysis/prompts.py`
  - Action:
    1. 添加 `LanguageType` 类型别名和 `LANGUAGE_INSTRUCTIONS` 映射
    2. 创建 `get_market_analyst_system_prompt(language: LanguageType)` 函数
    3. 保留 `MARKET_ANALYST_SYSTEM_PROMPT` 并添加 deprecation 警告
  - Details:
    ```python
    import warnings
    from typing import Literal

    # 类型定义
    LanguageType = Literal["zh", "en"]

    # 语言指令映射
    LANGUAGE_INSTRUCTIONS: dict[LanguageType, str] = {
        "zh": "\n\n**IMPORTANT: Please output all analysis content (reasoning and key_assumptions) in Chinese (中文).**",
        "en": "",  # English is the default, no additional instruction needed
    }

    def get_market_analyst_system_prompt(language: LanguageType = "en") -> str:
        """Get market analyst system prompt with language instruction.

        Args:
            language: Output language ("zh" for Chinese, "en" for English)

        Returns:
            System prompt string with language instruction appended
        """
        # 原有的系统提示词内容
        base_prompt = """You are an expert prediction market analyst with deep knowledge of:
- Political events and elections
- Economic indicators and trends
- Technology and crypto markets
- Sports and entertainment outcomes
..."""  # 保持原有内容不变

        instruction = LANGUAGE_INSTRUCTIONS.get(language, "")
        if instruction == "" and language not in LANGUAGE_INSTRUCTIONS:
            # 未知语言，记录日志但使用默认（空）
            import logging
            logging.getLogger(__name__).warning(
                f"Unknown language '{language}', using default (English)"
            )
        return base_prompt + instruction

    # 向后兼容 - 添加 deprecation 警告
    def _get_deprecated_constant() -> str:
        warnings.warn(
            "MARKET_ANALYST_SYSTEM_PROMPT is deprecated. "
            "Use get_market_analyst_system_prompt() instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        return get_market_analyst_system_prompt("en")

    MARKET_ANALYST_SYSTEM_PROMPT = _get_deprecated_constant()
    ```
  - 更新 `__all__` 导出列表，添加 `get_market_analyst_system_prompt`, `LanguageType`, `LANGUAGE_INSTRUCTIONS`

- [x] **Task 3: 更新 llm_analyzer.py 使用动态提示词**
  - File: `src/analysis/llm_analyzer.py`
  - Action: 修改导入和 `analyze_market` 方法中的 LLM 调用
  - Details:
    ```python
    # 修改导入 (llm_analyzer.py 已导入 settings，无需额外导入)
    from src.analysis.prompts import (
        get_market_analyst_system_prompt,  # 替换 MARKET_ANALYST_SYSTEM_PROMPT
        build_market_analysis_prompt,
        parse_llm_analysis_response,
    )

    # 修改 _call_llm 函数 (在 analyze_market 方法内)
    def _call_llm() -> str:
        with LLMClient() as client:
            return client.chat_with_system(
                system_prompt=get_market_analyst_system_prompt(settings.llm.analysis_language),
                user_prompt=user_prompt,
            )
    ```

- [x] **Task 4: 更新 .env.example**
  - File: `.env.example`
  - Action: 添加新配置项说明
  - Details:
    ```bash
    # LLM Analysis Language (zh=Chinese, en=English)
    # Default: zh
    ANALYSIS_LANGUAGE=zh
    ```

- [x] **Task 5: 添加配置测试**
  - File: `tests/test_config.py`
  - Action: 添加 `TestLLMSettingsAnalysisLanguage` 测试类
  - Details:
    ```python
    class TestLLMSettingsAnalysisLanguage:
        """Tests for analysis_language configuration."""

        def test_default_value_is_zh(self) -> None:
            """Test default value is Chinese."""
            for key in ["ANALYSIS_LANGUAGE"]:
                os.environ.pop(key, None)
            settings = LLMSettings()
            assert settings.analysis_language == "zh"

        def test_env_override_to_en(self) -> None:
            """Test environment variable override to English."""
            with patch.dict(os.environ, {"ANALYSIS_LANGUAGE": "en"}):
                settings = LLMSettings()
                assert settings.analysis_language == "en"

        def test_env_override_to_zh(self) -> None:
            """Test environment variable override to Chinese."""
            with patch.dict(os.environ, {"ANALYSIS_LANGUAGE": "zh"}):
                settings = LLMSettings()
                assert settings.analysis_language == "zh"

        def test_case_insensitive_uppercase(self) -> None:
            """Test uppercase value is normalized to lowercase."""
            with patch.dict(os.environ, {"ANALYSIS_LANGUAGE": "EN"}):
                settings = LLMSettings()
                assert settings.analysis_language == "en"

        def test_case_insensitive_mixed(self) -> None:
            """Test mixed case value is normalized to lowercase."""
            with patch.dict(os.environ, {"ANALYSIS_LANGUAGE": "Zh"}):
                settings = LLMSettings()
                assert settings.analysis_language == "zh"

        def test_invalid_value_rejected(self) -> None:
            """Test invalid language value is rejected."""
            with patch.dict(os.environ, {"ANALYSIS_LANGUAGE": "fr"}):
                with pytest.raises(PydanticValidationError):
                    LLMSettings()
    ```

- [x] **Task 6: 更新提示词测试**
  - File: `tests/test_analysis/test_prompts.py`
  - Action: 更新导入，添加语言相关测试
  - Details:
    ```python
    import warnings

    from src.analysis.prompts import (
        get_market_analyst_system_prompt,
        LANGUAGE_INSTRUCTIONS,
        MARKET_ANALYST_SYSTEM_PROMPT,
        # ... 其他导入
    )

    class TestGetMarketAnalystSystemPrompt:
        """Tests for get_market_analyst_system_prompt function."""

        def test_default_is_english(self) -> None:
            """Test default language is English."""
            prompt = get_market_analyst_system_prompt()
            assert "prediction market analyst" in prompt

        def test_chinese_contains_language_instruction(self) -> None:
            """Test Chinese prompt contains language instruction."""
            prompt = get_market_analyst_system_prompt("zh")
            assert "中文" in prompt

        def test_english_no_extra_instruction(self) -> None:
            """Test English prompt has no extra language instruction."""
            prompt = get_market_analyst_system_prompt("en")
            assert "中文" not in prompt

        def test_backward_compatibility_constant_with_warning(self) -> None:
            """Test MARKET_ANALYST_SYSTEM_PROMPT constant works with deprecation warning."""
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                prompt = MARKET_ANALYST_SYSTEM_PROMPT
                assert prompt is not None
                assert len(prompt) > 100
                # Should emit deprecation warning
                assert len(w) >= 1
                assert issubclass(w[0].category, DeprecationWarning)
                assert "deprecated" in str(w[0].message).lower()

    # 更新 TestPromptsConstants 使用新函数
    class TestPromptsConstants:
        def test_system_prompt_exists(self) -> None:
            prompt = get_market_analyst_system_prompt()
            assert prompt is not None
            assert len(prompt) > 100

        def test_system_prompt_contains_json_format(self) -> None:
            prompt = get_market_analyst_system_prompt()
            assert "JSON" in prompt
            assert "predicted_probability" in prompt
    ```

- [x] **Task 7: 运行完整测试套件验证**
  - Action: 运行 `pytest tests/` 确保所有现有测试通过
  - 验证没有破坏其他使用 `MARKET_ANALYST_SYSTEM_PROMPT` 的测试

### Acceptance Criteria

- [x] **AC1: 配置默认值**
  - Given: 未设置 `ANALYSIS_LANGUAGE` 环境变量
  - When: 加载 `LLMSettings()`
  - Then: `settings.analysis_language` 返回 `"zh"`

- [x] **AC2: 配置环境变量覆盖**
  - Given: 设置 `ANALYSIS_LANGUAGE=en`
  - When: 加载 `LLMSettings()`
  - Then: `settings.analysis_language` 返回 `"en"`

- [x] **AC3: 配置大小写不敏感**
  - Given: 设置 `ANALYSIS_LANGUAGE=EN` 或 `En` 或 `ZH`
  - When: 加载 `LLMSettings()`
  - Then: 值被规范化为小写 `"en"` 或 `"zh"`

- [x] **AC4: 配置验证**
  - Given: 设置 `ANALYSIS_LANGUAGE=fr`（无效值）
  - When: 加载 `LLMSettings()`
  - Then: 抛出 `ValidationError`

- [x] **AC5: 中文提示词包含语言指令**
  - Given: 调用 `get_market_analyst_system_prompt("zh")`
  - When: 获取返回的提示词
  - Then: 提示词包含 "中文" 指令

- [x] **AC6: 英文提示词正常**
  - Given: 调用 `get_market_analyst_system_prompt("en")`
  - When: 获取返回的提示词
  - Then: 提示词是有效的英文系统提示词，不含 "中文"

- [x] **AC7: 向后兼容带警告**
  - Given: 代码使用 `MARKET_ANALYST_SYSTEM_PROMPT` 常量
  - When: 导入并使用该常量
  - Then: 返回有效的英文系统提示词，并发出 `DeprecationWarning`

- [x] **AC8: LLM 分析器集成**
  - Given: 配置 `ANALYSIS_LANGUAGE=zh`
  - When: 调用 `LLMAnalyzer.analyze_market()`
  - Then: 传递给 LLM 的系统提示词包含中文输出指令

- [x] **AC9: 所有测试通过**
  - Given: 完成所有代码修改
  - When: 运行 `pytest tests/`
  - Then: 所有测试通过，无回归

## Additional Context

### Dependencies

| 类型 | 说明 |
|------|------|
| 内部依赖 | `llm_analyzer.py` 已导入 `settings`，可直接使用 |
| 外部依赖 | 无 |

### Testing Strategy

**单元测试:**
1. `tests/test_config.py` - 配置加载、验证、大小写处理
2. `tests/test_analysis/test_prompts.py` - 提示词生成、deprecation 警告

**回归测试:**
- 运行完整测试套件 `pytest tests/` 确保无破坏性变更

**手动测试步骤:**
1. 设置 `.env`: `ANALYSIS_LANGUAGE=zh`
2. 运行市场分析
3. 检查数据库中 `reasoning` 字段是否为中文

### Migration Guide

**用户如何切换语言：**

1. 编辑 `.env` 文件：
   ```bash
   # 中文输出（默认）
   ANALYSIS_LANGUAGE=zh

   # 或英文输出
   ANALYSIS_LANGUAGE=en
   ```

2. 重启应用，新分析将使用新语言

3. 注意：已存在的历史分析记录不会改变

### Notes

**风险点:**
- LLM 可能不完全遵循语言指令（概率性问题）
- 已使用 `**IMPORTANT**` 强调语言指令

**已知限制:**
- 只影响新生成的分析，历史数据保持不变
- 用户提示词（市场信息）保持英文，仅系统提示词添加语言指令

**未来考虑:**
- 可扩展支持更多语言（如 `ja`, `ko`）
- Telegram 通知语言配置
