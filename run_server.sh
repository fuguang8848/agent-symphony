#!/bin/bash
# 启动 agent-symphony 服务

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${HOME}/.agent-symphony/logs"
PID_FILE="${HOME}/.agent-symphony/server.pid"

mkdir -p "$LOG_DIR"

start() {
    echo "启动 agent-symphony 服务..."
    cd "$SCRIPT_DIR"
    nohup python3 -m server.symphony_server > "$LOG_DIR/server.log" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2
    if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "✅ 服务已启动 (PID: $(cat "$PID_FILE"))"
        echo "   日志: $LOG_DIR/server.log"
    else
        echo "❌ 启动失败，请查看日志"
        cat "$LOG_DIR/server.log"
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" && echo "✅ 服务已停止"
            rm -f "$PID_FILE"
        else
            echo "服务未运行"
            rm -f "$PID_FILE"
        fi
    else
        echo "服务未运行"
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ 服务运行中 (PID: $PID)"
            return 0
        fi
    fi
    echo "❌ 服务未运行"
    return 1
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) stop; start ;;
    status) status ;;
    *) echo "用法: $0 {start|stop|restart|status}" ;;
esac
