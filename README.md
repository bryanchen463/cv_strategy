# A股选股策略系统

## 策略概述

### 选股策略
1. **双均线多头排列**：MA20 > MA60，且股价在MA60之上
2. **屡创新高**：最近20天内创出60日新高
3. **经历回调**：过去5天曾跌破MA5或有3%-20%的合理回撤
4. **站稳5日线**：今日收盘价在MA5之上且收阳线

### 回测策略
- **买入**：每日选出的股票按等权重买入
- **卖出**：在最高点回撤4%后清仓
- **每周调仓**：可选功能，每周固定日期重新平衡投资组合
- **资金管理**：初始资金100万，单只股票最多占用20%资金
- **交易成本**：佣金率万分之三

## 文件结构

```
A_stock/
├── main.py                    # 原始选股程序（已修复）
├── main_with_backtest.py      # 带回测功能的主程序
├── backtest.py                # 回测引擎模块
├── run_daily.py              # 运行每日选股（简化版）
└── README.md                 # 说明文档
```

## 使用方法

### 1. 运行每日选股
```bash
# 使用原始程序（快速选股）
python main.py

# 使用带回测的程序（交互式）
python main_with_backtest.py
# 然后选择选项1

# 使用简化版（非交互式）
python run_daily.py
```

### 2. 运行历史回测
```bash
# 使用交互式程序
python main_with_backtest.py
# 然后选择选项2

# 直接运行回测（示例数据）
python -c "from main_with_backtest import run_backtest; run_backtest()"
```

### 3. 自定义回测参数
修改 `main_with_backtest.py` 中的 `BACKTEST_PARAMS`：
```python
BACKTEST_PARAMS = {
    'initial_capital': 1000000,    # 初始资金
    'stop_loss_pct': 0.04,         # 止损比例（4%）
    'commission_rate': 0.0003,     # 佣金率
    'rebalance_weekly': False,     # 是否启用每周调仓
    'rebalance_day': 0,            # 调仓日（0=周一，1=周二，...，6=周日）
    'backtest_start': '2023-01-01',
    'backtest_end': '2023-12-01'
}
```

### 4. 使用每周调仓功能
```bash
# 使用交互式程序配置每周调仓
python main_with_backtest.py
# 然后选择选项3配置回测参数
# 再选择选项2运行回测

# 或者直接修改参数后运行
python -c "
from main_with_backtest import run_backtest
import main_with_backtest as m
m.BACKTEST_PARAMS['rebalance_weekly'] = True
m.BACKTEST_PARAMS['rebalance_day'] = 0  # 周一调仓
run_backtest()
"

## 回测结果解读

回测结果包含以下指标：
- **总收益率**：整个回测期间的总收益
- **年化收益率**：折算到每年的收益率
- **最大回撤**：投资组合从最高点到最低点的最大跌幅
- **夏普比率**：风险调整后的收益（>1表示较好）
- **胜率**：盈利交易占总交易的比例
- **平均持仓天数**：股票平均持有时间

## 注意事项

1. **数据来源**：使用akshare获取实时数据，需要网络连接
2. **交易时间**：选股策略在交易日运行效果最佳
3. **回测限制**：历史回测使用示例数据，实际回测需要历史选股信号
4. **风险提示**：本策略仅供参考，实际投资需谨慎

## 依赖包

```bash
pip install akshare pandas numpy
```

## 策略优化建议

1. **参数优化**：可以调整均线周期、回撤阈值等参数
2. **风险控制**：可以添加最大持仓限制、单日最大亏损限制
3. **信号过滤**：可以添加成交量、换手率等过滤条件
4. **多策略组合**：可以结合其他技术指标或基本面指标