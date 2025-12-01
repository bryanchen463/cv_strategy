"""
回测模块
策略：每天选出的股票在最高点回撤4%后清仓
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class BacktestEngine:
    """回测引擎"""

    def __init__(self, initial_capital=1000000, stop_loss_pct=0.04, commission_rate=0.0003,
                 rebalance_weekly=False, rebalance_day=0):
        """
        初始化回测引擎

        Parameters:
        -----------
        initial_capital : float
            初始资金
        stop_loss_pct : float
            止损比例（从最高点回撤多少百分比后清仓）
        commission_rate : float
            交易佣金率（默认万分之三）
        rebalance_weekly : bool
            是否启用每周调仓
        rebalance_day : int
            调仓日（0=周一，1=周二，...，6=周日）
        """
        self.initial_capital = initial_capital
        self.stop_loss_pct = stop_loss_pct
        self.commission_rate = commission_rate
        self.rebalance_weekly = rebalance_weekly
        self.rebalance_day = rebalance_day  # 0=Monday, 1=Tuesday, ..., 6=Sunday

        # 回测结果
        self.results = {}
        self.portfolio_history = []
        self.trade_history = []

    def run_backtest(self, signals, price_data, start_date=None, end_date=None):
        """
        运行回测

        Parameters:
        -----------
        signals : dict
            信号字典，格式：{date: [{'code': '000001', 'name': '股票名'}, ...]}
        price_data : dict
            价格数据字典，格式：{code: pd.DataFrame}
        start_date : str
            回测开始日期，格式：'YYYY-MM-DD'
        end_date : str
            回测结束日期，格式：'YYYY-MM-DD'

        Returns:
        --------
        dict : 回测结果
        """
        print("开始回测...")
        print(f"回测参数: 初始资金={self.initial_capital:,}元, 止损比例={self.stop_loss_pct*100}%")
        if self.rebalance_weekly:
            day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            print(f"每周调仓: 启用 (调仓日: {day_names[self.rebalance_day]})")

        # 初始化
        capital = self.initial_capital
        positions = {}  # 当前持仓 {code: {'shares': 数量, 'avg_price': 平均成本, 'max_price': 最高价}}
        portfolio_value = capital

        # 获取所有交易日
        all_dates = self._get_all_trading_dates(signals, price_data, start_date, end_date)

        print(f"回测期间: {all_dates[0]} 到 {all_dates[-1]}, 共{len(all_dates)}个交易日")

        # 按日期循环
        for i, current_date in enumerate(all_dates):
            date_str = current_date.strftime('%Y-%m-%d')

            # 1. 检查并更新持仓的最高价
            positions = self._update_positions_high(positions, price_data, current_date)

            # 2. 检查止损条件
            positions, capital, trades_today = self._check_stop_loss(
                positions, price_data, capital, current_date, date_str
            )

            # 3. 执行买入信号（如果有）
            if date_str in signals:
                buy_signals = signals[date_str]
                positions, capital, new_trades = self._execute_buy_signals(
                    buy_signals, positions, price_data, capital, current_date, date_str
                )
                trades_today.extend(new_trades)

            # 4. 如果是调仓日，执行每周调仓
            if self.rebalance_weekly and self._is_rebalance_day(current_date):
                positions, capital, rebalance_trades = self._execute_weekly_rebalance(
                    positions, price_data, capital, current_date, date_str, signals.get(date_str, [])
                )
                trades_today.extend(rebalance_trades)

            # 5. 计算当日持仓市值
            portfolio_value = self._calculate_portfolio_value(positions, price_data, capital, current_date)

            # 6. 记录当日状态
            self._record_daily_status(date_str, positions, capital, portfolio_value, trades_today)

            # 显示进度
            if (i + 1) % 50 == 0 or i == len(all_dates) - 1:
                print(f"进度: {i+1}/{len(all_dates)} ({date_str}), 组合价值: {portfolio_value:,.2f}元")

        # 计算回测结果
        self._calculate_results(all_dates)

        print("回测完成!")
        return self.results

    def _get_all_trading_dates(self, signals, price_data, start_date, end_date):
        """获取所有交易日"""
        all_dates = set()

        # 从信号中获取日期
        for date_str in signals.keys():
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                all_dates.add(date)
            except:
                pass

        # 从价格数据中获取日期
        for code, df in price_data.items():
            if df is not None and not df.empty:
                dates = df.index.tolist()
                all_dates.update(dates)

        # 转换为列表并排序
        all_dates = sorted(list(all_dates))

        # 应用日期范围过滤
        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            all_dates = [d for d in all_dates if d >= start_dt]

        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            all_dates = [d for d in all_dates if d <= end_dt]

        return all_dates

    def _update_positions_high(self, positions, price_data, current_date):
        """更新持仓的最高价"""
        for code, pos in positions.items():
            if code in price_data and price_data[code] is not None:
                df = price_data[code]
                if current_date in df.index:
                    current_price = df.loc[current_date, 'close']
                    if current_price > pos['max_price']:
                        pos['max_price'] = current_price
        return positions

    def _check_stop_loss(self, positions, price_data, capital, current_date, date_str):
        """检查止损条件"""
        trades_today = []
        codes_to_remove = []

        for code, pos in positions.items():
            if code in price_data and price_data[code] is not None:
                df = price_data[code]
                if current_date in df.index:
                    current_price = df.loc[current_date, 'close']
                    highest_price = pos['max_price']

                    # 计算从最高点的回撤
                    drawdown = (highest_price - current_price) / highest_price

                    # 如果回撤超过止损比例，清仓
                    if drawdown >= self.stop_loss_pct:
                        # 计算卖出金额（考虑佣金）
                        sell_value = current_price * pos['shares']
                        commission = sell_value * self.commission_rate
                        net_proceeds = sell_value - commission

                        # 更新资金
                        capital += net_proceeds

                        # 计算盈亏
                        cost = pos['avg_price'] * pos['shares']
                        buy_commission = cost * self.commission_rate
                        total_cost = cost + buy_commission
                        pnl = net_proceeds - total_cost
                        pnl_pct = pnl / total_cost if total_cost > 0 else 0

                        # 记录交易
                        trade = {
                            'date': date_str,
                            'code': code,
                            'action': 'SELL',
                            'reason': f'止损（回撤{drawdown*100:.1f}%≥{self.stop_loss_pct*100}%）',
                            'price': current_price,
                            'shares': pos['shares'],
                            'amount': sell_value,
                            'commission': commission,
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'holding_days': (current_date - pos['buy_date']).days
                        }
                        trades_today.append(trade)

                        codes_to_remove.append(code)

        # 移除已清仓的股票
        for code in codes_to_remove:
            del positions[code]

        return positions, capital, trades_today

    def _execute_buy_signals(self, buy_signals, positions, price_data, capital, current_date, date_str):
        """执行买入信号"""
        trades_today = []

        for signal in buy_signals:
            code = signal['code']
            name = signal.get('name', '未知')

            # 如果已经持有该股票，跳过
            if code in positions:
                continue

            # 检查是否有价格数据
            if code not in price_data or price_data[code] is None:
                continue

            df = price_data[code]
            if current_date not in df.index:
                continue

            # 获取当日收盘价作为买入价
            buy_price = df.loc[current_date, 'close']

            # 计算可买入数量（每只股票分配1/N资金，N为信号数量）
            n_signals = len(buy_signals)
            allocation = capital / n_signals if n_signals > 0 else 0

            # 计算买入股数（取整百股）
            buy_value = min(allocation, capital * 0.2)  # 单只股票最多占用20%资金
            shares = int(buy_value // (buy_price * 100)) * 100  # 整百股

            if shares <= 0:
                continue

            # 计算买入金额和佣金
            cost = buy_price * shares
            commission = cost * self.commission_rate
            total_cost = cost + commission

            # 检查资金是否足够
            if total_cost > capital:
                continue

            # 更新资金
            capital -= total_cost

            # 记录持仓
            positions[code] = {
                'shares': shares,
                'avg_price': buy_price,
                'max_price': buy_price,  # 初始最高价为买入价
                'buy_date': current_date,
                'name': name
            }

            # 记录交易
            trade = {
                'date': date_str,
                'code': code,
                'name': name,
                'action': 'BUY',
                'reason': '选股信号',
                'price': buy_price,
                'shares': shares,
                'amount': cost,
                'commission': commission,
                'pnl': 0,
                'pnl_pct': 0,
                'holding_days': 0
            }
            trades_today.append(trade)

        return positions, capital, trades_today

    def _is_rebalance_day(self, date):
        """检查是否是调仓日"""
        # 0=Monday, 1=Tuesday, ..., 6=Sunday
        return date.weekday() == self.rebalance_day

    def _execute_weekly_rebalance(self, positions, price_data, capital, current_date, date_str, today_signals):
        """执行每周调仓"""
        trades_today = []

        if not positions:
            return positions, capital, trades_today

        print(f"  {date_str}: 执行每周调仓 (当前持仓{len(positions)}只股票)")

        # 1. 卖出所有持仓
        for code, pos in positions.items():
            if code in price_data and price_data[code] is not None:
                df = price_data[code]
                if current_date in df.index:
                    current_price = df.loc[current_date, 'close']

                    # 计算卖出金额（考虑佣金）
                    sell_value = current_price * pos['shares']
                    commission = sell_value * self.commission_rate
                    net_proceeds = sell_value - commission

                    # 更新资金
                    capital += net_proceeds

                    # 计算盈亏
                    cost = pos['avg_price'] * pos['shares']
                    buy_commission = cost * self.commission_rate
                    total_cost = cost + buy_commission
                    pnl = net_proceeds - total_cost
                    pnl_pct = pnl / total_cost if total_cost > 0 else 0

                    # 记录交易
                    trade = {
                        'date': date_str,
                        'code': code,
                        'action': 'SELL',
                        'reason': '每周调仓',
                        'price': current_price,
                        'shares': pos['shares'],
                        'amount': sell_value,
                        'commission': commission,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'holding_days': (current_date - pos['buy_date']).days
                    }
                    trades_today.append(trade)

        # 清空持仓
        positions = {}

        # 2. 重新买入今日的信号股票
        if today_signals:
            positions, capital, new_trades = self._execute_buy_signals(
                today_signals, positions, price_data, capital, current_date, date_str
            )
            trades_today.extend(new_trades)
            print(f"    重新买入{len(new_trades)}只股票")

        return positions, capital, trades_today

    def _calculate_portfolio_value(self, positions, price_data, capital, current_date):
        """计算当日持仓市值"""
        portfolio_value = capital

        for code, pos in positions.items():
            if code in price_data and price_data[code] is not None:
                df = price_data[code]
                if current_date in df.index:
                    current_price = df.loc[current_date, 'close']
                    market_value = current_price * pos['shares']
                    portfolio_value += market_value

        return portfolio_value

    def _record_daily_status(self, date_str, positions, capital, portfolio_value, trades_today):
        """记录当日状态"""
        # 记录投资组合历史
        daily_record = {
            'date': date_str,
            'cash': capital,
            'positions_count': len(positions),
            'portfolio_value': portfolio_value,
            'return': (portfolio_value / self.initial_capital - 1) * 100
        }
        self.portfolio_history.append(daily_record)

        # 记录交易历史
        self.trade_history.extend(trades_today)

    def _calculate_results(self, all_dates):
        """计算回测结果"""
        if not self.portfolio_history:
            return

        # 转换为DataFrame
        portfolio_df = pd.DataFrame(self.portfolio_history)
        portfolio_df['date'] = pd.to_datetime(portfolio_df['date'])
        portfolio_df.set_index('date', inplace=True)

        trades_df = pd.DataFrame(self.trade_history) if self.trade_history else pd.DataFrame()

        # 计算基本指标
        final_value = portfolio_df['portfolio_value'].iloc[-1]
        total_return = (final_value / self.initial_capital - 1) * 100

        # 计算年化收益率
        days = (all_dates[-1] - all_dates[0]).days
        years = days / 365.25
        annual_return = ((final_value / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

        # 计算最大回撤
        portfolio_df['cummax'] = portfolio_df['portfolio_value'].cummax()
        portfolio_df['drawdown'] = (portfolio_df['portfolio_value'] - portfolio_df['cummax']) / portfolio_df['cummax'] * 100
        max_drawdown = portfolio_df['drawdown'].min()

        # 计算夏普比率（假设无风险利率为3%）
        portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
        avg_daily_return = portfolio_df['daily_return'].mean() * 100
        std_daily_return = portfolio_df['daily_return'].std() * 100
        sharpe_ratio = (avg_daily_return - 3/252) / std_daily_return * np.sqrt(252) if std_daily_return > 0 else 0

        # 交易统计
        if not trades_df.empty:
            buy_trades = trades_df[trades_df['action'] == 'BUY']
            sell_trades = trades_df[trades_df['action'] == 'SELL']

            total_trades = len(buy_trades) + len(sell_trades)
            win_trades = sell_trades[sell_trades['pnl'] > 0]
            loss_trades = sell_trades[sell_trades['pnl'] <= 0]

            win_rate = len(win_trades) / len(sell_trades) * 100 if len(sell_trades) > 0 else 0
            avg_win = win_trades['pnl_pct'].mean() if len(win_trades) > 0 else 0
            avg_loss = loss_trades['pnl_pct'].mean() if len(loss_trades) > 0 else 0
            avg_holding_days = sell_trades['holding_days'].mean() if len(sell_trades) > 0 else 0
        else:
            total_trades = 0
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            avg_holding_days = 0

        # 保存结果
        self.results = {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return_pct': total_return,
            'annual_return_pct': annual_return,
            'max_drawdown_pct': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': total_trades,
            'win_rate_pct': win_rate,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'avg_holding_days': avg_holding_days,
            'portfolio_history': portfolio_df,
            'trade_history': trades_df
        }

    def print_results(self):
        """打印回测结果"""
        if not self.results:
            print("没有回测结果")
            return

        print("\n" + "="*60)
        print("回测结果汇总")
        print("="*60)

        r = self.results
        print(f"初始资金: {r['initial_capital']:,.2f}元")
        print(f"最终价值: {r['final_value']:,.2f}元")
        print(f"总收益率: {r['total_return_pct']:.2f}%")
        print(f"年化收益率: {r['annual_return_pct']:.2f}%")
        print(f"最大回撤: {r['max_drawdown_pct']:.2f}%")
        print(f"夏普比率: {r['sharpe_ratio']:.2f}")
        print(f"总交易次数: {r['total_trades']}次")
        print(f"胜率: {r['win_rate_pct']:.1f}%")
        print(f"平均盈利: {r['avg_win_pct']:.2f}%")
        print(f"平均亏损: {r['avg_loss_pct']:.2f}%")
        print(f"平均持仓天数: {r['avg_holding_days']:.1f}天")

        # 打印最近10笔交易
        if not r['trade_history'].empty:
            print(f"\n最近10笔交易:")
            recent_trades = r['trade_history'].tail(10)
            for _, trade in recent_trades.iterrows():
                action = "买入" if trade['action'] == 'BUY' else "卖出"
                pnl_str = f"+{trade['pnl']:.2f}" if trade['pnl'] > 0 else f"{trade['pnl']:.2f}"
                print(f"  {trade['date']} {action} {trade['code']} {trade.get('name', '')} "
                      f"价格:{trade['price']:.2f} 盈亏:{pnl_str}元({trade['pnl_pct']:.2f}%)")

        print("="*60)


def prepare_backtest_data(selected_stocks_history, start_date='2023-01-01', end_date=None):
    """
    准备回测数据

    Parameters:
    -----------
    selected_stocks_history : list
        选股历史记录，每个元素为(date, stocks_list)
    start_date : str
        开始日期
    end_date : str
        结束日期

    Returns:
    --------
    tuple : (signals_dict, price_data_dict)
    """
    print("准备回测数据...")

    # 1. 构建信号字典
    signals = {}
    for date_str, stocks in selected_stocks_history:
        signals[date_str] = stocks
        print(f"  {date_str}: {len(stocks)}只股票")

    # 2. 获取所有需要价格数据的股票代码
    all_codes = set()
    for stocks in signals.values():
        for stock in stocks:
            all_codes.add(stock['code'])

    print(f"需要获取{len(all_codes)}只股票的价格数据...")

    # 3. 获取价格数据（这里需要调用数据获取函数）
    # 注意：由于数据获取需要时间，这里简化处理
    # 实际使用时需要从main.py导入get_stock_data函数
    price_data = {}

    return signals, price_data


if __name__ == "__main__":
    # 示例用法
    print("回测模块测试")

    # 创建回测引擎（不带每周调仓）
    print("\n1. 测试不带每周调仓的策略:")
    backtest1 = BacktestEngine(
        initial_capital=1000000,
        stop_loss_pct=0.04,  # 4%止损
        commission_rate=0.0003  # 万分之三佣金
    )

    # 创建回测引擎（带每周调仓，每周一调仓）
    print("\n2. 测试带每周调仓的策略:")
    backtest2 = BacktestEngine(
        initial_capital=1000000,
        stop_loss_pct=0.04,  # 4%止损
        commission_rate=0.0003,  # 万分之三佣金
        rebalance_weekly=True,
        rebalance_day=0  # 周一调仓
    )

    # 这里需要实际的选股信号和价格数据
    # signals, price_data = prepare_backtest_data(selected_stocks_history)
    # results1 = backtest1.run_backtest(signals, price_data)
    # backtest1.print_results()
    # results2 = backtest2.run_backtest(signals, price_data)
    # backtest2.print_results()