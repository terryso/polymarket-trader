# Story 8.6: 运行脚本与进程管理

## Story

As a **用户**,
I want **有便捷的脚本来启动、停止和监控系统**,
So that **日常运维简单可靠**.

## Related Epic

Epic 8: 系统调度与自动化运行

## Requirements

- **NFR1**: 系统可用性 > 99% uptime
- **NFR2**: 市场检查频率每 1-4 小时
- **NFR10**: 崩溃后自动恢复、状态持久化
- **AR4**: 使用 APScheduler 进行定时任务调度

## Acceptance Criteria

### AC1: 启动脚本 (`scripts/run.sh`)

**Given** 所有组件已实现
**When** 创建 `scripts/run.sh`
**Then** 脚本应包含:
- 激活虚拟环境
- 支持 `--mode` 参数 (paper/live)
- 支持 `--config` 参数指定配置文件
- 创建 PID 文件 (`.bot.pid`)
- 将输出重定向到 `logs/bot.log`
- 支持后台运行 (`--daemon`)

```bash
#!/bin/bash
# 启动系统
source .venv/bin/activate
python -m src.main --mode paper
```

### AC2: 停止脚本 (`scripts/stop.sh`)

**Given** 系统正在运行
**When** 创建 `scripts/stop.sh`
**Then** 脚本应包含:
- 读取 PID 文件
- 发送 SIGTERM 信号 (优雅关闭)
- 等待进程结束 (超时 30 秒)
- 超时后发送 SIGKILL (强制终止)
- 清理 PID 文件
- 记录停止日志

```bash
#!/bin/bash
# 优雅停止系统
kill -TERM $(cat .bot.pid)
```

### AC3: 状态检查脚本 (`scripts/status.sh`)

**Given** Dashboard API 已实现
**When** 创建 `scripts/status.sh`
**Then** 脚本应包含:
- 调用 `http://localhost:8000/api/status` API
- 以易读格式显示状态信息
- 返回适当的退出码 (0=运行中, 1=停止, 2=错误)
- 支持 JSON 输出模式 (`--json`)

```bash
#!/bin/bash
# 检查系统状态
curl http://localhost:8000/api/status
```

### AC4: PID 文件管理

**Given** 系统启动和停止脚本
**When** 实现进程管理
**Then** 应包含:
- PID 文件路径: `.bot.pid`
- 启动时写入当前进程 PID
- 停止时清理 PID 文件
- 检测 PID 文件是否存在以防止重复启动
- 记录启动日志到 `logs/bot.log`

### AC5: Systemd 服务文件模板 (可选)

**Given** 运行脚本已实现
**When** 创建 systemd 服务文件
**Then** 创建 `scripts/polymarket-trader.service`:
- 配置服务描述和依赖
- 配置用户和工作目录
- 配置环境变量
- 配置自动重启策略
- 配置日志输出

### AC6: 其他运维脚本

**Given** 基本脚本已实现
**When** 添加辅助脚本
**Then** 创建以下脚本:
- `scripts/restart.sh` - 重启系统
- `scripts/logs.sh` - 查看日志 (支持 `-f` 跟踪模式)
- `scripts/health_check.sh` - 健康检查脚本

## Technical Notes

### 文件结构

```
scripts/
├── run.sh           # 启动脚本
├── stop.sh          # 停止脚本
├── restart.sh       # 重启脚本
├── status.sh        # 状态检查
├── logs.sh          # 日志查看
├── health_check.sh  # 健康检查
└── polymarket-trader.service  # systemd 服务文件
```

### 环境变量

脚本应支持以下环境变量:
- `BOT_MODE` - 运行模式 (paper/live)
- `BOT_CONFIG` - 配置文件路径
- `BOT_LOG_LEVEL` - 日志级别

### 错误处理

- 启动前检查虚拟环境是否存在
- 启动前检查依赖是否已安装
- 启动前检查配置文件是否存在
- 检查端口是否被占用

## Dependencies

- Story 8.1: APScheduler 调度器配置
- Story 8.2: 定时任务配置
- Story 8.3: 主入口与启动流程
- Story 8.4: 自动恢复机制
- Story 8.5: 错误处理与告警
- Story 7.5: 系统状态 API (用于 status.sh)

## Definition of Done

- [ ] 所有脚本文件已创建并具有可执行权限
- [ ] 脚本支持所有必需的命令行参数
- [ ] PID 文件管理正常工作
- [ ] 日志正确输出到指定文件
- [ ] systemd 服务文件模板已创建
- [ ] 脚本有适当的错误处理和退出码
- [ ] 所有脚本经过手动测试验证
- [ ] 脚本包含帮助信息 (`--help`)
