"""
带回测功能的选股策略主程序
策略：双均线多头 + 屡创新高 + 回调 + 站稳5日线
回测：最高点回撤4%后清仓
"""

import akshare as ak
import pandas as pd
import datetime
import time
import warnings
warnings.filterwarnings('ignore')

from backtest import BacktestEngine

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

# 回测参数
BACKTEST_PARAMS = {
    'initial_capital': 1000000,    # 初始资金100万
    'stop_loss_pct': 0.04,         # 止损比例4%
    'commission_rate': 0.0003,     # 佣金率万分之三
    'rebalance_weekly': False,     # 是否启用每周调仓
    'rebalance_day': 0,            # 调仓日（0=周一，1=周二，...，6=周日）
    'backtest_start': '2023-01-01',
    'backtest_end': '2023-12-01'
}


def add_market_prefix(code):
    """
    为股票代码添加市场前缀
    规则:
    - 600, 601, 603, 605, 688, 689 开头 -> sh (上海)
    - 000, 001, 002, 003, 300, 301 开头 -> sz (深圳)
    - 其他 -> 保持原样
    """
    if not isinstance(code, str):
        code = str(code)

    # 去除可能的空格和特殊字符
    code = code.strip()

    # 如果已经有前缀，直接返回
    if code.startswith(('sh', 'sz', 'bj')):
        return code

    # 根据代码开头添加前缀
    if code.startswith(('600', '601', '603', '605', '688', '689')):
        return f"sh{code}"
    elif code.startswith(('000', '001', '002', '003', '300', '301')):
        return f"sz{code}"
    elif code.startswith('920'):  # 北交所
        return f"bj{code}"
    else:
        # 无法识别，尝试添加sz前缀（大多数A股在深圳）
        return f"sz{code}"


def get_stock_data(symbol, start_date=None, end_date=None, max_retries=2):
    """
    获取单只股票的日线数据
    symbol: 股票代码，如 "600519" 或 "sh600519"
    start_date: 开始日期，格式：'YYYYMMDD'
    end_date: 结束日期，格式：'YYYYMMDD'
    max_retries: 最大重试次数
    """
    # 确保有市场前缀
    symbol_with_prefix = add_market_prefix(symbol)

    # 使用默认日期
    if start_date is None:
        start_date = STRATEGY_PARAMS['start_date']
    if end_date is None:
        end_date = datetime.datetime.now().strftime('%Y%m%d')

    for attempt in range(max_retries):
        try:
            # 添加重试延迟
            if attempt > 0:
                time.sleep(0.3 * attempt)  # 指数退避

            # 使用 stock_zh_a_daily 接口获取数据
            df = ak.stock_zh_a_daily(
                symbol=symbol_with_prefix,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )

            if df is None or df.empty:
                if attempt < max_retries - 1:
                    continue
                return None

            # 数据已经包含 'date', 'open', 'close', 'high', 'low', 'volume' 等列
            # 确保日期格式正确
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

            # 按日期排序
            df = df.sort_index()

            return df

        except Exception as e:
            error_msg = str(e)
            # 如果是特定错误，重试
            if 'date' in error_msg or 'Connection' in error_msg or 'Remote' in error_msg:
                if attempt < max_retries - 1:
                    continue
                else:
                    return None
            else:
                return None

    return None


def calculate_indicators(df):
    """
    计算技术指标
    """
    # 1. 计算均线
    df['MA5'] = df['close'].rolling(window=STRATEGY_PARAMS['ma_short']).mean()
    df['MA10'] = df['close'].rolling(window=10).mean()  # 新增10日线，用于观察短期趋势交叉
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['MA60'] = df['close'].rolling(window=STRATEGY_PARAMS['ma_trend']).mean()

    # 2. 计算N日最高价 (用于判断"新高")
    df['Rolling_Max'] = df['high'].rolling(window=STRATEGY_PARAMS['high_window']).max()

    return df


def check_strategy(df, symbol, stock_name="未知"):
    """
    核心选股逻辑
    """
    if len(df) < STRATEGY_PARAMS['high_window'] + 5:
        return False, "数据不足"

    # 获取最新的一行数据和前几天的数据
    today = df.iloc[-1]
    last_few_days = df.iloc[-STRATEGY_PARAMS['recent_days']:]  # 最近N天

    # ---------------------------------------------------
    # 条件1: 屡创新高 + 双均线趋势 (Trend Alignment)
    # 逻辑:
    # A. 当前价格 > MA60
    # B. [新增] MA20 > MA60 (中期趋势均线多头排列，确保趋势稳健)
    # C. 最近20天内，曾经出现过 60日内的新高
    # ---------------------------------------------------
    cond_trend_up = (today['close'] > today['MA60']) and (today['MA20'] > today['MA60'])

    # 检查最近一段时间的最高价是否接近整个周期的最高价
    recent_max = last_few_days['high'].max()
    global_rolling_max = df['Rolling_Max'].iloc[-1]
    cond_new_high = recent_max >= global_rolling_max * 0.99

    if not cond_trend_up:
        return False, "趋势未确立(MA20<MA60或股价破位)"

    if not cond_new_high:
        return False, "近期未创出新高"

    # ---------------------------------------------------
    # 条件2: 跌下来 (回调)
    # 逻辑: 过去5天曾跌破MA5 或 有合理回撤
    # ---------------------------------------------------
    pullback_window = df.iloc[-STRATEGY_PARAMS['pullback_lookback']:-1]  # 不包含今天
    cond_pullback = (pullback_window['close'] < pullback_window['MA5']).any()

    # 回撤幅度计算
    drawdown = (recent_max - today['close']) / recent_max
    cond_reasonable_drop = 0.03 < drawdown < 0.20

    if not (cond_pullback or cond_reasonable_drop):
        return False, "近期没有明显回调"

    # ---------------------------------------------------
    # 条件3: 再上涨并站稳5日线
    # ---------------------------------------------------
    cond_stand_firm = today['close'] > today['MA5']
    cond_is_red = today['close'] > today['open']

    # 额外观察：短期均线是否也金叉 (MA5 > MA10) ? 这不是硬性条件，但加分
    is_golden_cross = today['MA5'] > today['MA10']
    trend_strength = "强" if is_golden_cross else "弱"

    if cond_stand_firm and cond_is_red:
        return True, f"入选(趋势{trend_strength})! 现价:{today['close']:.2f}, 回撤:{drawdown*100:.1f}%, MA20>MA60"
    else:
        return False, "今日未站稳5日线或收阴"


def get_top_inflow_sectors(top_n=3):
    """
    获取资金流入最多的前N个板块及其成分股
    """
    print(f"正在获取资金流入前 {top_n} 的板块...")
    try:
        # 获取行业资金流排名 (东方财富接口)
        # indicator="今日" 获取实时/当日数据
        df_flow = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")

        if df_flow is None or df_flow.empty:
            print("未能获取到行业资金流数据")
            return []

        # 确保由于单位问题（如'亿','万'）导致的字符串排序错误，这里尝试清理数据
        target_col = '今日主力净流入-净额'
        if target_col not in df_flow.columns:
            # 尝试模糊匹配列名
            cols = [c for c in df_flow.columns if '主力净流入' in c and '净额' in c]
            if cols:
                target_col = cols[0]
            else:
                print("无法找到资金流列，请检查接口返回")
                return []

        # 转换数值类型 (处理可能存在的非数值字符)
        df_flow[target_col] = pd.to_numeric(df_flow[target_col], errors='coerce')

        # 按净流入倒序排列
        df_flow = df_flow.sort_values(by=target_col, ascending=False)

        # 取前N个板块
        top_sectors = df_flow.head(top_n)

        sector_stocks = []
        for index, row in top_sectors.iterrows():
            sector_name = row['名称']
            flow_amount = row[target_col]

            # 转换单位显示，方便阅读
            flow_str = f"{flow_amount / 100000000:.2f}亿" if abs(flow_amount) > 100000000 else f"{flow_amount / 10000:.2f}万"
            print(f"  -> 选中板块: 【{sector_name}】 (主力净流入: {flow_str})")

            # 获取板块成分股
            try:
                df_cons = ak.stock_board_industry_cons_em(symbol=sector_name)
                # df_cons 通常包含 '代码', '名称' 等列
                for _, stock in df_cons.iterrows():
                    sector_stocks.append({
                        'code': stock['代码'],
                        'name': stock['名称'],
                        'sector': sector_name  # 记录来源板块
                    })
            except Exception as e:
                print(f"    获取板块 {sector_name} 成分股失败: {e}")

        return sector_stocks

    except Exception as e:
        print(f"获取板块资金流失败: {e}")
        return []


def run_daily_selection(test_date=None):
    """
    运行每日选股
    test_date: 测试日期，格式：'YYYY-MM-DD'，如果为None则使用最新日期
    """
    if test_date:
        print(f"运行选股策略 (测试日期: {test_date})")
        # 注意：这里简化处理，实际需要根据test_date获取数据
        # 由于akshare接口限制，这里暂时使用最新数据
        pass

    print("策略逻辑: 双均线多头(MA20>MA60) + 屡创新高 + 经历回调 + 今日站稳MA5")
    print("股票池来源: 今日资金净流入最多的前3个板块")

    # 获取动态股票池
    stock_list = get_top_inflow_sectors(top_n=3)

    if not stock_list:
        print("未获取到任何股票，请检查网络或休市时间。")
        return []

    print(f"共获取到 {len(stock_list)} 只股票待扫描...")

    selected_stocks = []
    processed_count = 0

    for stock in stock_list:
        symbol = stock['code']
        name = stock['name']
        sector = stock.get('sector', '未知')

        # 简单过滤：跳过ST和退市股
        if 'ST' in name or '退' in name:
            continue

        # 显示进度
        processed_count += 1
        if processed_count % 20 == 0 or processed_count == len(stock_list):
            print(f"进度: {processed_count}/{len(stock_list)}...")

        df = get_stock_data(symbol)

        if df is not None and len(df) > STRATEGY_PARAMS['high_window']:
            df = calculate_indicators(df)
            is_selected, reason = check_strategy(df, symbol, name)

            if is_selected:
                print(f"✓ {symbol} {name}: {reason}")
                selected_stocks.append({
                    'code': symbol,
                    'name': name,
                    'sector': sector,
                    'reason': reason,
                    'close_price': df['close'].iloc[-1]
                })

        # 避免请求过于频繁，添加适当延迟
        time.sleep(0.1)

    print(f"\n选股完成，共选中 {len(selected_stocks)} 只股票")

    if selected_stocks:
        result_df = pd.DataFrame(selected_stocks)
        cols = ['sector', 'code', 'name', 'close_price', 'reason']
        print(result_df[cols].to_string(index=False))

    return selected_stocks


def configure_backtest():
    """
    配置回测参数
    """
    print("配置回测参数:")

    # 是否启用每周调仓
    while True:
        rebalance = input("是否启用每周调仓? (y/n): ").strip().lower()
        if rebalance in ['y', 'yes', '是']:
            BACKTEST_PARAMS['rebalance_weekly'] = True

            # 选择调仓日
            day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            print("请选择调仓日:")
            for i, name in enumerate(day_names):
                print(f"  {i}. {name}")

            while True:
                try:
                    day_choice = int(input("请输入选择 (0-6): ").strip())
                    if 0 <= day_choice <= 6:
                        BACKTEST_PARAMS['rebalance_day'] = day_choice
                        print(f"已选择每周{day_names[day_choice]}调仓")
                        break
                    else:
                        print("请输入0-6之间的数字")
                except ValueError:
                    print("请输入有效的数字")
            break
        elif rebalance in ['n', 'no', '否']:
            BACKTEST_PARAMS['rebalance_weekly'] = False
            print("禁用每周调仓")
            break
        else:
            print("请输入 y/n 或 是/否")

    return BACKTEST_PARAMS


def run_backtest():
    """
    运行历史回测
    """
    print("=" * 60)
    print("开始历史回测")
    print("=" * 60)

    # 配置回测参数
    configure_backtest()

    # 这里需要模拟历史选股过程
    # 由于akshare接口限制，我们无法直接获取历史某日的板块资金流
    # 这里简化处理：使用固定的测试日期进行回测演示

    # 创建回测引擎
    backtest = BacktestEngine(
        initial_capital=BACKTEST_PARAMS['initial_capital'],
        stop_loss_pct=BACKTEST_PARAMS['stop_loss_pct'],
        commission_rate=BACKTEST_PARAMS['commission_rate'],
        rebalance_weekly=BACKTEST_PARAMS['rebalance_weekly'],
        rebalance_day=BACKTEST_PARAMS['rebalance_day']
    )

    # 模拟历史选股信号（这里需要实际的历史数据）
    # 由于数据获取限制，这里创建一个示例信号
    example_signals = {
        '2023-03-01': [
            {'code': '000001', 'name': '平安银行'},
            {'code': '600519', 'name': '贵州茅台'}
        ],
        '2023-06-01': [
            {'code': '300308', 'name': '中际旭创'},
            {'code': '002415', 'name': '海康威视'}
        ]
    }

    # 获取价格数据
    price_data = {}
    all_codes = set()
    for date_str, stocks in example_signals.items():
        for stock in stocks:
            all_codes.add(stock['code'])

    print(f"获取{len(all_codes)}只股票的历史价格数据...")
    for code in all_codes:
        df = get_stock_data(
            code,
            start_date='20230101',
            end_date='20231201'
        )
        if df is not None:
            price_data[code] = df
            print(f"  {code}: {len(df)}个交易日数据")
        else:
            print(f"  {code}: 获取数据失败")

    # 运行回测
    results = backtest.run_backtest(
        example_signals,
        price_data,
        start_date=BACKTEST_PARAMS['backtest_start'],
        end_date=BACKTEST_PARAMS['backtest_end']
    )

    # 打印结果
    backtest.print_results()

    return results


def main():
    """
    主函数
    """
    print("=" * 60)
    print("A股选股策略系统 (带回测功能)")
    print("=" * 60)

    while True:
        print("\n请选择操作:")
        print("1. 运行今日选股")
        print("2. 运行历史回测")
        print("3. 配置回测参数")
        print("4. 退出")

        choice = input("请输入选择 (1-4): ").strip()

        if choice == '1':
            # 运行今日选股
            selected_stocks = run_daily_selection()
            if selected_stocks:
                print(f"\n今日共选出 {len(selected_stocks)} 只符合条件的股票")
            else:
                print("\n今日未选出符合条件的股票")

        elif choice == '2':
            # 运行历史回测
            run_backtest()

        elif choice == '3':
            # 配置回测参数
            configure_backtest()

        elif choice == '4':
            print("退出程序")
            break

        else:
            print("无效选择，请重新输入")


if __name__ == "__main__":
    main()