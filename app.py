#!/usr/bin/env python3
"""
A股选股策略Web展示应用
"""

import os
import json
import datetime
import akshare as ak
from flask import Flask, render_template, jsonify, request
import pandas as pd

# 导入选股功能
try:
    from run_daily import main as run_daily_selection
    from run_daily import STRATEGY_PARAMS
    HAS_SELECTION = True
except ImportError as e:
    print(f"导入选股模块失败: {e}")
    print("将使用模拟数据")
    HAS_SELECTION = False

app = Flask(__name__)

# 数据文件路径
DATA_FILE = 'selected_stocks.json'
CACHE_FILE = 'cache/selected_stocks_cache.json'

def ensure_cache_dir():
    """确保缓存目录存在"""
    if not os.path.exists('cache'):
        os.makedirs('cache')

def get_today_date():
    """获取今日日期字符串"""
    return datetime.datetime.now().strftime('%Y-%m-%d')

def run_selection_and_save():
    """运行选股并保存结果"""
    if not HAS_SELECTION:
        print("警告：选股模块不可用")
        return None

    print("正在运行选股策略...")

    try:
        # 调用选股函数获取真实数据
        result = run_daily_selection(return_data=True)

        if result is None:
            print("选股返回空结果")
            return None

        print(f"选股完成，共选中 {len(result['stocks'])} 只股票")

        # 保存到缓存
        ensure_cache_dir()
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    except Exception as e:
        print(f"运行选股策略失败: {e}")
        return None


def load_cached_data():
    """加载缓存的数据"""
    ensure_cache_dir()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 检查是否是今天的数据
                if data.get('date') == get_today_date():
                    return data
                else:
                    print(f"缓存数据日期不匹配: {data.get('date')} != {get_today_date()}")
        except Exception as e:
            print(f"加载缓存数据失败: {e}")

    # 如果没有缓存或不是今天的数据，运行选股
    result = run_selection_and_save()
    if result is None:
        # 如果选股失败，返回空结果而不是模拟数据
        return {
            'date': get_today_date(),
            'stocks': [],
            'stats': {
                'total': 0,
                'by_sector': {},
                'by_trend': {'强': 0, '弱': 0}
            },
            'strategy_params': STRATEGY_PARAMS if HAS_SELECTION else {}
        }
    return result

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/api/stocks')
def get_stocks():
    """获取股票数据API"""
    data = load_cached_data()
    return jsonify(data)

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """刷新数据API"""
    data = run_selection_and_save()
    return jsonify({
        'success': True,
        'message': '数据刷新成功',
        'data': data
    })

@app.route('/api/stats')
def get_stats():
    """获取统计信息API"""
    data = load_cached_data()
    return jsonify(data['stats'])

@app.route('/api/filter')
def filter_stocks():
    """筛选股票API"""
    data = load_cached_data()
    stocks = data['stocks']

    # 获取筛选参数
    sector = request.args.get('sector', '').strip()
    search = request.args.get('search', '').strip().lower()
    trend = request.args.get('trend', '').strip()

    # 应用筛选
    filtered = []
    for stock in stocks:
        # 板块筛选
        if sector and stock['板块'] != sector:
            continue

        # 趋势强度筛选
        if trend and stock.get('趋势强度', '') != trend:
            continue

        # 搜索筛选（代码、名称）
        if search:
            if (search not in stock['代码'].lower() and
                search not in stock['名称'].lower()):
                continue

        filtered.append(stock)

    return jsonify({
        'stocks': filtered,
        'count': len(filtered),
        'filters': {
            'sector': sector,
            'search': search,
            'trend': trend
        }
    })

@app.route('/api/strategy')
def get_strategy():
    """获取策略参数API"""
    return jsonify({
        'strategy_params': STRATEGY_PARAMS if HAS_SELECTION else {},
        'has_selection': HAS_SELECTION
    })

@app.route('/stock/<stock_code>')
def stock_detail(stock_code):
    """股票详情页面"""
    return render_template('stock_detail.html', stock_code=stock_code)

@app.route('/api/stock/<stock_code>')
def get_stock_detail(stock_code):
    """获取股票详情数据API"""
    try:
        # 从缓存数据中查找股票
        data = load_cached_data()
        stocks = data['stocks']

        # 查找匹配的股票
        stock_info = None
        for stock in stocks:
            if stock['代码'] == stock_code:
                stock_info = stock
                break

        if not stock_info:
            return jsonify({
                'success': False,
                'message': f'未找到股票代码: {stock_code}'
            }), 404

        # 获取股票历史数据（从akshare获取真实数据）
        kline_data = get_stock_kline_data(stock_code)

        # 计算技术指标
        indicators = calculate_technical_indicators(kline_data)

        # 使用K线数据中的最新收盘价更新股票的最新价，确保数据一致性
        if kline_data and len(kline_data) > 0:
            latest_close = kline_data[-1]['close']
            stock_info['最新价'] = latest_close
            # 更新理由中的价格信息
            if '理由' in stock_info and '现价:' in stock_info['理由']:
                # 提取原理由中的回撤信息
                import re
                reason = stock_info['理由']
                pullback_match = re.search(r'回撤:([\d.]+)%', reason)
                if pullback_match:
                    pullback = pullback_match.group(1)
                    stock_info['理由'] = f'现价:{latest_close:.2f}, 回撤:{pullback}%'
                else:
                    stock_info['理由'] = f'现价:{latest_close:.2f}'

        return jsonify({
            'success': True,
            'stock': stock_info,
            'kline_data': kline_data,
            'indicators': indicators,
            'analysis': generate_stock_analysis(stock_info, indicators)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取股票数据失败: {str(e)}'
        }), 500

def add_market_prefix(stock_code):
    """为股票代码添加市场前缀"""
    if stock_code.startswith(('6', '5', '9')):
        return f"sh{stock_code}"
    elif stock_code.startswith(('0', '3', '2')):
        return f"sz{stock_code}"
    elif stock_code.startswith(('4', '8')):
        return f"bj{stock_code}"
    else:
        return stock_code

def get_stock_kline_data(stock_code):
    """获取股票K线数据（从akshare获取真实数据）"""
    try:
        # 为股票代码添加市场前缀
        market_code = add_market_prefix(stock_code)

        print(f"正在获取股票 {stock_code} ({market_code}) 的K线数据...")

        # 使用akshare获取股票历史数据
        # 获取最近60个交易日的数据
        df = ak.stock_zh_a_daily(
            symbol=market_code,
            start_date="20240101",  # 从2024年1月1日开始
            end_date=datetime.datetime.now().strftime("%Y%m%d"),
            adjust="qfq"  # 前复权
        )

        if df.empty:
            print(f"未获取到股票 {stock_code} 的数据")
            return []

        # 取最近60条数据
        df = df.tail(60)

        # 转换为需要的格式
        data = []
        for idx, row in df.iterrows():
            data.append({
                'date': row['date'],  # akshare返回的date列是字符串格式
                'open': float(row['open']),
                'close': float(row['close']),
                'high': float(row['high']),
                'low': float(row['low']),
                'volume': int(row['volume'])
            })

        print(f"成功获取股票 {stock_code} 的K线数据，共{len(data)}条")
        return data

    except Exception as e:
        print(f"获取股票 {stock_code} K线数据失败: {e}")
        # 如果获取真实数据失败，返回空列表
        return []


def calculate_technical_indicators(kline_data):
    """计算技术指标"""
    if not kline_data:
        return {}

    closes = [d['close'] for d in kline_data]
    volumes = [d['volume'] for d in kline_data]

    # 计算移动平均线
    ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else None
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else None

    # 计算最高价
    high_60d = max([d['high'] for d in kline_data[-60:]]) if len(kline_data) >= 60 else None

    # 计算成交量指标
    volume_today = volumes[-1] if volumes else None
    volume_ma5 = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else None
    volume_ratio = volume_today / volume_ma5 if volume_today and volume_ma5 else None

    return {
        'ma5': round(ma5, 2) if ma5 else None,
        'ma20': round(ma20, 2) if ma20 else None,
        'ma60': round(ma60, 2) if ma60 else None,
        'high_60d': round(high_60d, 2) if high_60d else None,
        'volume_today': volume_today,
        'volume_ma5': round(volume_ma5, 0) if volume_ma5 else None,
        'volume_ratio': round(volume_ratio, 2) if volume_ratio else None
    }

def generate_stock_analysis(stock_info, indicators):
    """生成股票分析"""
    analysis = {
        'strategy_points': [],
        'detailed_analysis': ''
    }

    # 策略匹配点
    if indicators.get('ma20') and indicators.get('ma60'):
        if indicators['ma20'] > indicators['ma60']:
            analysis['strategy_points'].append('✓ MA20 > MA60：满足双均线多头排列条件')
        else:
            analysis['strategy_points'].append('✗ MA20 ≤ MA60：不满足双均线多头排列条件')

    if indicators.get('high_60d') and stock_info.get('最新价'):
        current_price = stock_info['最新价']
        if current_price >= indicators['high_60d'] * 0.9:  # 接近60日高点
            analysis['strategy_points'].append('✓ 接近60日高点：满足屡创新高条件')
        else:
            analysis['strategy_points'].append('✗ 远离60日高点：不满足屡创新高条件')

    if '回撤' in stock_info.get('理由', ''):
        analysis['strategy_points'].append('✓ 经历回调：满足回调条件')

    if indicators.get('ma5') and stock_info.get('最新价'):
        if stock_info['最新价'] > indicators['ma5']:
            analysis['strategy_points'].append('✓ 站稳5日线：满足站稳5日线条件')
        else:
            analysis['strategy_points'].append('✗ 跌破5日线：不满足站稳5日线条件')

    # 详细分析
    trend_text = "强势" if stock_info.get('趋势强度') == '强' else "弱势"
    pullback_text = stock_info.get('理由', '').split('回撤:')[-1].split('%')[0] if '回撤:' in stock_info.get('理由', '') else "未知"

    analysis['detailed_analysis'] = f"""
    该股票当前处于{trend_text}趋势状态。根据选股策略分析：

    1. 价格表现：当前价格{stock_info.get('最新价', '未知')}元，相比60日高点回撤约{pullback_text}%。
    2. 均线系统：MA5={indicators.get('ma5', 'N/A')}，MA20={indicators.get('ma20', 'N/A')}，MA60={indicators.get('ma60', 'N/A')}。
    3. 成交量：今日成交量{indicators.get('volume_today', 'N/A')}手，量比{indicators.get('volume_ratio', 'N/A')}。

    综合来看，该股票符合选股策略的主要条件，建议关注。
    """

    return analysis

if __name__ == '__main__':
    import sys
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='A股选股策略Web应用')
    parser.add_argument('--port', type=int, default=5000, help='端口号 (默认: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='主机地址 (默认: 0.0.0.0)')
    args = parser.parse_args()

    # 确保缓存目录存在
    ensure_cache_dir()

    # 预加载数据
    print("初始化数据...")
    load_cached_data()

    print("启动Web应用...")
    print(f"访问地址: http://127.0.0.1:{args.port}")
    app.run(debug=True, host=args.host, port=args.port)