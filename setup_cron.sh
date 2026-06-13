#!/bin/bash
# Ai足势 - 设置定时任务

echo "=========================================="
echo "⚽ Ai足势 - 设置自动预测定时任务"
echo "=========================================="
echo ""

# 获取当前目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="$SCRIPT_DIR/python-scripts/generate_predictions.py"
LOG_FILE="$SCRIPT_DIR/logs/predict.log"

# 检查 Python 脚本
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ 找不到预测脚本: $PYTHON_SCRIPT"
    exit 1
fi

# 创建日志目录
mkdir -p "$SCRIPT_DIR/logs"

# 检查 Firebase 配置
if [ ! -f "$SCRIPT_DIR/serviceAccountKey.json" ]; then
    echo "⚠️  警告：找不到 serviceAccountKey.json"
    echo "请从 Firebase 控制台下载服务账号密钥"
    echo "位置：Firebase 控制台 → 项目设置 → 服务账号 → 生成新私钥"
    echo ""
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查 Python 依赖
echo "📦 检查 Python 依赖..."
python3 -c "import pandas" 2>/dev/null || pip3 install pandas
python3 -c "import numpy" 2>/dev/null || pip3 install numpy
python3 -c "import scipy" 2>/dev/null || pip3 install scipy
python3 -c "import requests" 2>/dev/null || pip3 install requests
python3 -c "import firebase_admin" 2>/dev/null || pip3 install firebase-admin

echo ""
echo "⏰ 设置定时任务..."
echo ""
echo "请选择执行频率："
echo "1. 每天凌晨 2:00（推荐）"
echo "2. 每天凌晨 3:00"
echo "3. 每天凌晨 4:00"
echo "4. 自定义时间"
echo ""

read -p "请选择 [1-4]: " choice

case $choice in
    1) CRON_TIME="0 2 * * *" ;;
    2) CRON_TIME="0 3 * * *" ;;
    3) CRON_TIME="0 4 * * *" ;;
    4)
        read -p "输入小时 (0-23): " hour
        read -p "输入分钟 (0-59): " minute
        CRON_TIME="$minute $hour * * *"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

# 生成 cron 命令
CRON_CMD="$CRON_TIME cd $SCRIPT_DIR && python3 $PYTHON_SCRIPT >> $LOG_FILE 2>&1"

# 检查是否已存在
if crontab -l 2>/dev/null | grep -q "$PYTHON_SCRIPT"; then
    echo ""
    echo "⚠️  检测到已存在的定时任务"
    read -p "是否替换？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        crontab -l 2>/dev/null | grep -v "$PYTHON_SCRIPT" | crontab -
    else
        echo "取消操作"
        exit 0
    fi
fi

# 添加定时任务
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo ""
echo "=========================================="
echo "✅ 定时任务设置成功！"
echo "=========================================="
echo ""
echo "📅 执行时间: $CRON_TIME"
echo "📝 日志文件: $LOG_FILE"
echo ""
echo "查看当前定时任务："
echo "  crontab -l"
echo ""
echo "查看执行日志："
echo "  tail -f $LOG_FILE"
echo ""
echo "删除定时任务："
echo "  crontab -e  # 然后删除对应行"
echo ""
