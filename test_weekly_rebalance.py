#!/usr/bin/env python3
"""
测试每周调仓功能
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtest import BacktestEngine

def create_test_data():
    """创建测试数据"""

    # 创建测试信号
    signals = {}

    # 创建测试价格数据
    price_data = {}

    # 创建日期范围：2023年1月到3月
    dates = pd.date_range('2023-01-01', '2023-03-31', freq='D')

    # 创建3只测试股票
    for i in range(3):
        code = f'TEST{i+1:03d}'

        # 创建价格数据：随机走势
        np.random.seed(i)
        prices = []
        base_price = 10.0

        for j, date in enumerate(dates):
            # 模拟价格走势
            if j == 0:
                price = base_price
            else:
                # 随机波动
                change = np.random.normal(0, 0.02)  # 2%的日波动率
                price = prices[-1] * (1 + change)

            prices.append(price)

        # 创建DataFrame
        df = pd.DataFrame({
            'open': [p * 0.99 for p in prices],  # 开盘价略低于收盘价
            'close': prices,
            'high': [p * 1.01 for p in prices],   # 最高价略高于收盘价
            'low': [p * 0.98 for p in prices],    # 最低价略低于收盘价
            'volume': [1000000] * len(prices)     # 固定成交量
        }, index=dates)

        price_data[code] = df

    # 创建每周一的买入信号
    for date in dates:
        if date.weekday() == 0:  # 周一
            date_str = date.strftime('%Y-%m-%d')
            signals[date_str] = [
                {'code': 'TEST001', 'name': '测试股票1'},
                {'code': 'TEST002', 'name': '测试股票2'},
                {'code': 'TEST003', 'name': '测试股票3'}
            ]

    return signals, price_data, dates

def test_without_rebalance():
    """测试不带每周调仓的策略"""
    print("=" * 60)
    print("测试1: 不带每周调仓的策略")
    print("=" * 60)

    signals, price_data, dates = create_test_data()

    backtest = BacktestEngine(
        initial_capital=1000000,
        stop_loss_pct=0.04,
        commission_rate=0.0003,
        rebalance_weekly=False
    )

    results = backtest.run_backtest(
        signals,
        price_data,
        start_date='2023-01-01',
        end_date='2023-03-31'
    )

    backtest.print_results()
    return results

def test_with_rebalance():
    """测试带每周调仓的策略"""
    print("\n" + "=" * 60)
    print("测试2: 带每周调仓的策略 (每周一调仓)")
    print("=" * 60)

    signals, price_data, dates = create_test_data()

    backtest = BacktestEngine(
        initial_capital=1000000,
        stop_loss_pct=0.04,
        commission_rate=0.0003,
        rebalance_weekly=True,
        rebalance_day=0  # 周一调仓
    )

    results = backtest.run_backtest(
        signals,
        price_data,
        start_date='2023-01-01',
        end_date='2023-03-31'
    )

    backtest.print_results()
    return results

def compare_results(results1, results2):
    """比较两种策略的结果"""
    print("\n" + "=" * 60)
    print("策略对比")
    print("=" * 60)

    print(f"{'指标':<20} {'无调仓':>15} {'有调仓':>15} {'差异':>15}")
    print("-" * 65)

    metrics = [
        ('总收益率(%)', 'total_return_pct'),
        ('年化收益率(%)', 'annual_return_pct'),
        ('最大回撤(%)', 'max_drawdown_pct'),
        ('夏普比率', 'sharpe_ratio'),
        ('胜率(%)', 'win_rate_pct'),
        ('交易次数', 'total_trades'),
        ('平均持仓天数', 'avg_holding_days')
    ]

    for name, key in metrics:
        val1 = results1.get(key, 0)
        val2 = results2.get(key, 0)
        diff = val2 - val1

        if '收益率' in name or '回撤' in name or '胜率' in name:
            print(f"{name:<20} {val1:>15.2f} {val2:>15.2f} {diff:>+15.2f}")
        elif '夏普' in name:
            print(f"{name:<20} {val1:>15.2f} {val2:>15.2f} {diff:>+15.2f}")
        else:
            print(f"{name:<20} {val1:>15.0f} {val2:>15.0f} {diff:>+15.0f}")

def main():
    print("每周调仓功能测试")
    print("=" * 60)

    # 测试不带调仓的策略
    results1 = test_without_rebalance()

    # 测试带调仓的策略
    results2 = test_with_rebalance()

    # 比较结果
    compare_results(results1, results2)

    print("\n测试完成!")

if __name__ == "__main__":
    main()