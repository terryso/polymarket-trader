#!/bin/bash

# Polymarket Trader 本地启动脚本
# 确保在正确的目录和使用正确的虚拟环境

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Polymarket Trader 本地启动脚本"
echo "=========================================="
echo ""
echo "工作目录: $SCRIPT_DIR"

# 1. 停止旧服务
echo ""
echo "[1/5] 停止旧服务..."
pkill -9 -f "src.main" 2>/dev/null || true
pkill -9 -f "uvicorn" 2>/dev/null || true
rm -f "$SCRIPT_DIR/.bot.pid"
sleep 2

# 再次确认
if pgrep -f "src.main" >/dev/null 2>&1; then
    echo "警告: 仍有 src.main 进程在运行"
    pgrep -f "src.main"
fi

# 2. 检查端口
echo ""
echo "[2/5] 检查端口 8000..."
if lsof -i :8000 >/dev/null 2>&1; then
    echo "端口 8000 被占用，尝试释放..."
    lsof -ti :8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi
echo "端口 8000 已就绪"

# 3. 激活虚拟环境
echo ""
echo "[3/5] 激活虚拟环境..."
VENV_PATH="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "错误: 虚拟环境不存在: $VENV_PATH"
    exit 1
fi

# 激活虚拟环境
source "$VENV_PATH/bin/activate"

# 确认使用虚拟环境的 Python
PYTHON_PATH="$VENV_PATH/bin/python"
if [ ! -f "$PYTHON_PATH" ]; then
    echo "错误: Python 不存在: $PYTHON_PATH"
    exit 1
fi

echo "Python: $(which python)"
echo "Python 版本: $(python --version)"

# 4. 检查 .env 文件
echo ""
echo "[4/5] 检查配置文件..."
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "警告: .env 文件不存在"
fi

# 5. 启动服务
echo ""
echo "[5/5] 启动服务..."
MODE="${1:-live}"
echo "模式: $MODE"
echo ""

# 使用绝对路径启动
exec python -m src.main --mode "$MODE"
