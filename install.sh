#!/bin/bash
# install.sh - agent-symphony 一键安装脚本
#
# 用法:
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/fuguang8848/agent-symphony/main/install.sh)"
#
# 或 clone 后运行:
#   bash <(cat install.sh)

set -e

REPO="fuguang8848/agent-symphony"
INSTALL_DIR="${HOME}/.openclaw/agent-symphony"
PYTHON_PKG_DIR="${HOME}/.local/lib/python3.12/site-packages"
OPENCLAW_SKILLS_DIR="${HOME}/.openclaw/plugin-skills"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   agent-symphony 一键安装                ║"
echo "║   交响乐技能家族 - OpenClaw 多技能协作   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 1. 检查 OpenClaw
info "检查 OpenClaw..."
if ! command -v openclaw &>/dev/null; then
    error "OpenClaw 未安装，请先安装 OpenClaw"
    exit 1
fi
info "✅ OpenClaw 已安装: $(openclaw --version 2>&1 | head -1)"

# 2. 检查 Python
info "检查 Python..."
if ! command -v python3 &>/dev/null; then
    error "Python3 未安装"
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
info "✅ Python $PYTHON_VERSION"

# 3. Clone 或更新仓库
if [ -d "$INSTALL_DIR/.git" ]; then
    info "更新已有安装..."
    cd "$INSTALL_DIR"
    git pull --ff origin main 2>/dev/null || warn "git pull 失败，跳过"
else
    info "克隆 agent-symphony..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    # 优先用 ghproxy 加速
    git clone --depth 1 "https://ghproxy.net/https://github.com/${REPO}.git" "$INSTALL_DIR" 2>/dev/null \
        || git clone --depth 1 "https://github.com/${REPO}.git" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
info "当前版本: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"

# 4. 安装 Python 依赖
info "安装 Python 依赖..."
pip install --upgrade pip --quiet 2>/dev/null || true
pip install -e . --break-system-packages --quiet 2>/dev/null \
    || pip install -e . --user --quiet 2>/dev/null \
    || warn "pip install 失败，请手动运行: pip install -e '$INSTALL_DIR'"

# 5. 检查依赖
info "检查依赖..."
python3 -c "import fastapi, uvicorn, httpx, pydantic" 2>/dev/null \
    && info "✅ Python 依赖已安装" \
    || error "Python 依赖缺失，请手动运行: pip install -e '$INSTALL_DIR'"

# 6. 配置
info "配置..."
CONFIG_FILE="${HOME}/.agent-symphony/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    mkdir -p "$(dirname "$CONFIG_FILE")"
    cat > "$CONFIG_FILE" << 'EOF'
{
  "llm": {
    "provider": "minimax",
    "model": "MiniMax-M2.7",
    "api_key": "YOUR_API_KEY_HERE",
    "base_url": "https://api.minimaxi.com/anthropic"
  },
  "server": {
    "host": "127.0.0.1",
    "port": 18081
  },
  "memory": {
    "dir": "REPLACE_ME"
  },
  "search": {
    "script_path": "REPLACE_ME"
  }
}
EOF
    sed -i "s|REPLACE_ME|${HOME}/.agent-symphony/memory|g" "$CONFIG_FILE"
    sed -i "s|REPLACE_ME|${HOME}/.openclaw/workspace/tools/search-v.py|g" "$CONFIG_FILE"
    info "✅ 配置文件已创建: $CONFIG_FILE"
    info "⚠️  请填写 API key: $CONFIG_FILE"
else
    info "✅ 配置文件已存在: $CONFIG_FILE"
fi

# 7. 复制 symphony skill 到 OpenClaw
SKILL_DIR="${OPENCLAW_SKILLS_DIR}/symphony"
if [ ! -d "$SKILL_DIR" ]; then
    info "安装 OpenClaw skill..."
    mkdir -p "$SKILL_DIR"
    cp "$INSTALL_DIR/symphony/SKILL.md" "$SKILL_DIR/"
    cp "$INSTALL_DIR/symphony/handler.js" "$SKILL_DIR/"
    info "✅ symphony skill 已安装: $SKILL_DIR"
else
    info "✅ symphony skill 已存在: $SKILL_DIR"
fi

# 8. 创建 systemd 服务（可选）
if command -v systemctl &>/dev/null && [ -d "${HOME}/.config/systemd/user" ]; then
    info "创建 systemd 服务..."
    mkdir -p "${HOME}/.config/systemd/user"
    cat > "${HOME}/.config/systemd/user/agent-symphony.service" << EOF
[Unit]
Description=agent-symphony RPC server
After=network.target openclaw-gateway.service

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 -m server.symphony_server
Restart=on-failure
RestartSec=5
Environment="PYTHONPATH=$INSTALL_DIR"

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload 2>/dev/null && info "✅ systemd 服务已创建" || true
fi

# 9. 启动服务
info "启动 agent-symphony 服务..."
if pgrep -f "server.symphony_server" > /dev/null; then
    info "服务已在运行"
else
    nohup python3 -m server.symphony_server > "${HOME}/.agent-symphony/server.log" 2>&1 &
    sleep 2
    if curl -s http://127.0.0.1:18081/health > /dev/null 2>&1; then
        info "✅ 服务已启动 (PID: $!)"
    else
        warn "服务启动可能失败，请检查: ${HOME}/.agent-symphony/server.log"
    fi
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   安装完成！                             ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "下一步："
echo "  1. 填写 API key: vim $CONFIG_FILE"
echo "  2. 重启服务: cd $INSTALL_DIR && python3 -m server.symphony_server"
echo "  3. OpenClaw 中说 '启动交响乐' 即可使用"
echo ""
echo "常用命令："
echo "  查看状态: curl http://127.0.0.1:18081/health"
echo "  查看日志: tail -f ${HOME}/.agent-symphony/server.log"
echo "  服务管理: systemctl --user restart agent-symphony"
echo ""
