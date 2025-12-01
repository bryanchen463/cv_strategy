#!/usr/bin/env python3
"""
简化版每日选股运行脚本
"""

import akshare as ak
import pandas as pd
import datetime
import time
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 策略参数设置
# ==========================================
STRATEGY_PARAMS = {
    'start_date': '20230101',      # 数据开始时间（用于计算均线）
    'ma_short': 5,                 # 短期均线 (5日线)
    'ma_mid': 20,                  # 中期均线
    'ma_trend': 60,                # 趋势均线 (60日线)
    'high_window': 60,             # 创新高的时间窗口 (60日新高)
    'recent_days': 20,             # "屡创新高"考察的最近天数
    'pullback_lookback': 5,        # 回调考察窗口 (看过去几天是否跌下来过)
}


def add_market_prefix(code):
    """为股票代码添加市场前缀"""
    if not isinstance(code, str):
        code = str(code)
    code = code.strip()

    if code.startswith(('sh', 'sz', 'bj')):
        return code

    if code.startswith(('600', '601', '603', '605', '688', '689')):
        return f"sh{code}"
    elif code.startswith(('000', '001', '002', '003', '300', '301')):
        return f"sz{code}"
    elif code.startswith('920'):
        return f"bj{code}"
    else:
        return f"sz{code}"


def get_stock_data(symbol, max_retries=2):
    """获取单只股票的日线数据"""
    symbol_with_prefix = add_market_prefix(symbol)

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(0.3 * attempt)

            df = ak.stock_zh_a_daily(
                symbol=symbol_with_prefix,
                start_date=STRATEGY_PARAMS['start_date'],
                end_date=datetime.datetime.now().strftime('%Y%m%d'),
                adjust="qfq"
            )

            if df is None or df.empty:
                continue

            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = df.sort_index()
            return df

        except Exception:
            continue

    return None


def calculate_indicators(df):
    """计算技术指标"""
    df['MA5'] = df['close'].rolling(window=STRATEGY_PARAMS['ma_short']).mean()
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['MA60'] = df['close'].rolling(window=STRATEGY_PARAMS['ma_trend']).mean()
    df['Rolling_Max'] = df['high'].rolling(window=STRATEGY_PARAMS['high_window']).max()
    return df


def check_strategy(df):
    """核心选股逻辑"""
    if len(df) < STRATEGY_PARAMS['high_window'] + 5:
        return False, "数据不足"

    today = df.iloc[-1]
    last_few_days = df.iloc[-STRATEGY_PARAMS['recent_days']:]

    # 条件1: 双均线多头
    cond_trend_up = (today['close'] > today['MA60']) and (today['MA20'] > today['MA60'])
    if not cond_trend_up:
        return False, "趋势未确立"

    # 条件2: 屡创新高
    recent_max = last_few_days['high'].max()
    global_rolling_max = df['Rolling_Max'].iloc[-1]
    cond_new_high = recent_max >= global_rolling_max * 0.99
    if not cond_new_high:
        return False, "近期未创出新高"

    # 条件3: 回调
    pullback_window = df.iloc[-STRATEGY_PARAMS['pullback_lookback']:-1]
    cond_pullback = (pullback_window['close'] < pullback_window['MA5']).any()
    drawdown = (recent_max - today['close']) / recent_max
    cond_reasonable_drop = 0.03 < drawdown < 0.20
    if not (cond_pullback or cond_reasonable_drop):
        return False, "近期没有明显回调"

    # 条件4: 站稳5日线
    cond_stand_firm = today['close'] > today['MA5']
    cond_is_red = today['close'] > today['open']
    if not (cond_stand_firm and cond_is_red):
        return False, "今日未站稳5日线或收阴"

    return True, f"现价:{today['close']:.2f}, 回撤:{drawdown*100:.1f}%"


def main(return_data=False):
    """
    运行选股策略

    Args:
        return_data: 如果为True，返回选股数据而不是打印

    Returns:
        如果return_data为True，返回选股结果字典
    """
    if not return_data:
        print("=" * 60)
        print("A股选股策略 - 简化版")
        print("策略: 双均线多头 + 屡创新高 + 回调 + 站稳5日线")
        print("建议: 买入后最高点回撤4%清仓")
        print("=" * 60)

    # 获取板块资金流
    print("获取资金流入最多的3个板块...")
    try:
        df_flow = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
        if df_flow is None or df_flow.empty:
            print("获取板块数据失败")
            return

        target_col = '今日主力净流入-净额'
        if target_col not in df_flow.columns:
            cols = [c for c in df_flow.columns if '主力净流入' in c and '净额' in c]
            if cols:
                target_col = cols[0]
            else:
                print("无法找到资金流列")
                return

        df_flow[target_col] = pd.to_numeric(df_flow[target_col], errors='coerce')
        df_flow = df_flow.sort_values(by=target_col, ascending=False)
        top_sectors = df_flow.head(3)

        stock_list = []
        for _, row in top_sectors.iterrows():
            sector_name = row['名称']
            flow_amount = row[target_col]
            flow_str = f"{flow_amount/100000000:.2f}亿" if abs(flow_amount) > 100000000 else f"{flow_amount/10000:.2f}万"
            print(f"  【{sector_name}】 (净流入: {flow_str})")

            try:
                df_cons = ak.stock_board_industry_cons_em(symbol=sector_name)
                for _, stock in df_cons.iterrows():
                    stock_list.append({
                        'code': stock['代码'],
                        'name': stock['名称'],
                        'sector': sector_name
                    })
            except Exception as e:
                print(f"    获取成分股失败: {e}")

    except Exception as e:
        print(f"获取板块数据失败: {e}")
        return

    if not stock_list:
        print("未获取到股票列表")
        return

    print(f"\n共获取到 {len(stock_list)} 只股票，开始扫描...")

    # 扫描股票
    selected_stocks = []
    for i, stock in enumerate(stock_list):
        symbol = stock['code']
        name = stock['name']

        if 'ST' in name or '退' in name:
            continue

        if (i + 1) % 20 == 0:
            print(f"进度: {i+1}/{len(stock_list)}...")

        df = get_stock_data(symbol)
        if df is not None and len(df) > STRATEGY_PARAMS['high_window']:
            df = calculate_indicators(df)
            is_selected, reason = check_strategy(df)

            if is_selected:
                print(f"✓ {symbol} {name}: {reason}")
                selected_stocks.append({
                    '板块': stock['sector'],
                    '代码': symbol,
                    '名称': name,
                    '最新价': df['close'].iloc[-1],
                    '理由': reason
                })

        time.sleep(0.1)

    # 输出结果
    if not return_data:
        print("\n" + "=" * 60)
        print(f"选股完成！共选中 {len(selected_stocks)} 只股票")
        print("=" * 60)

        if selected_stocks:
            result_df = pd.DataFrame(selected_stocks)
            print(result_df.to_string(index=False))

            print("\n交易建议:")
            print("1. 等权重买入选中的股票")
            print("2. 每只股票买入后，记录买入价和最高价")
            print("3. 当股价从最高点回撤4%时，立即清仓")
            print("4. 严格控制单只股票仓位（建议不超过总资金的20%）")
            print("\n每周调仓建议:")
            print("1. 建议每周一重新运行本程序，获取最新选股结果")
            print("2. 卖出所有持仓，等权重买入新选出的股票")
            print("3. 这样可以确保投资组合始终持有当前最强的股票")
            print("4. 每周调仓可以避免\"锚定效应\"，及时跟上市场热点")
        else:
            print("今日未选出符合条件的股票")

        print("\n风险提示：股市有风险，投资需谨慎")

    # 返回数据
    if return_data:
        # 计算统计信息
        by_sector = {}
        by_trend = {'强': 0, '弱': 0}

        for stock in selected_stocks:
            sector = stock['板块']
            by_sector[sector] = by_sector.get(sector, 0) + 1

            # 简单判断趋势强度：价格高于MA5为强，否则为弱
            # 这里简化处理，实际应该计算真实趋势
            stock['趋势强度'] = '强'  # 暂时标记为强，实际应该根据技术指标判断

        stats = {
            'total': len(selected_stocks),
            'by_sector': by_sector,
            'by_trend': by_trend
        }

        return {
            'date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'stocks': selected_stocks,
            'stats': stats,
            'strategy_params': STRATEGY_PARAMS
        }
    else:
        return None


if __name__ == "__main__":
    main()