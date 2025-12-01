#!/bin/bash
# A股选股策略 - Cron Job 设置脚本

echo "=== 设置每日选股定时任务 ==="
echo "当前时间: $(date)"
echo "工作目录: $(pwd)"

# 获取Python路径
PYTHON_PATH=$(which python3)
echo "Python路径: $PYTHON_PATH"

# 获取脚本绝对路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SELECTION_SCRIPT="$SCRIPT_DIR/run_daily_selection.py"
echo "选股脚本: $SELECTION_SCRIPT"

# 检查脚本是否存在
if [ ! -f "$SELECTION_SCRIPT" ]; then
    echo "错误: 选股脚本不存在: $SELECTION_SCRIPT"
    exit 1
fi

# 创建日志目录
LOG_DIR="$SCRIPT_DIR/logs"
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    echo "创建日志目录: $LOG_DIR"
fi

# 创建cron job配置
CRON_JOB="0 8 * * * cd $SCRIPT_DIR && $PYTHON_PATH $SELECTION_SCRIPT >> $LOG_DIR/selection_$(date +\%Y\%m\%d).log 2>&1"

echo ""
echo "=== 将要添加的Cron Job ==="
echo "$CRON_JOB"
echo ""

# 询问用户是否要添加
read -p "是否添加此cron job? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 添加cron job
    (crontab -l 2>/dev/null; echo "# A股每日选股 - 北京时间8点"; echo "$CRON_JOB") | crontab -

    echo "Cron job已添加!"
    echo ""
    echo "=== 当前Cron任务列表 ==="
    crontab -l
else
    echo "已取消。"
    echo ""
    echo "你可以手动添加以下cron job:"
    echo "$CRON_JOB"
fi

echo ""
echo "=== 手动添加说明 ==="
echo "1. 运行: crontab -e"
echo "2. 添加以下行:"
echo "   # A股每日选股 - 北京时间8点"
echo "   0 8 * * * cd $SCRIPT_DIR && $PYTHON_PATH $SELECTION_SCRIPT >> $LOG_DIR/selection_\$(date +\\%Y\\%m\\%d).log 2>&1"
echo "3. 保存并退出"