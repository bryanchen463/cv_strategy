/**
 * 股票详情页面 - JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // 全局变量
    let stockData = null;
    let klineChart = null;
    let stockCode = getStockCodeFromURL();

    // DOM元素
    const elements = {
        currentDate: document.getElementById('current-date'),
        stockInfo: document.getElementById('stock-info'),
        stockCode: document.getElementById('stock-code'),
        stockName: document.getElementById('stock-name'),
        stockSector: document.getElementById('stock-sector'),
        stockPrice: document.getElementById('stock-price'),
        stockTrend: document.getElementById('stock-trend'),
        stockPullback: document.getElementById('stock-pullback'),
        ma5Value: document.getElementById('ma5-value'),
        ma20Value: document.getElementById('ma20-value'),
        ma60Value: document.getElementById('ma60-value'),
        maCompare: document.getElementById('ma-compare'),
        high60d: document.getElementById('high-60d'),
        currentPullback: document.getElementById('current-pullback'),
        newHigh: document.getElementById('new-high'),
        volumeToday: document.getElementById('volume-today'),
        volumeMa5: document.getElementById('volume-ma5'),
        volumeRatio: document.getElementById('volume-ratio'),
        strategyPoints: document.getElementById('strategy-points'),
        detailedAnalysis: document.getElementById('detailed-analysis'),
        buyPrice: document.getElementById('buy-price'),
        stopLossPrice: document.getElementById('stop-loss-price'),
        dataUpdateTime: document.getElementById('data-update-time'),
        periodSelect: document.getElementById('period-select'),
        maSelect: document.getElementById('ma-select'),
        refreshChartBtn: document.getElementById('refresh-chart'),
        klineChart: document.getElementById('kline-chart')
    };

    // 初始化
    init();

    // 初始化函数
    function init() {
        // 设置当前日期
        const now = new Date();
        elements.currentDate.textContent = formatDate(now);

        // 绑定事件
        bindEvents();

        // 加载股票数据
        loadStockData();
    }

    // 绑定事件
    function bindEvents() {
        // 图表刷新
        elements.refreshChartBtn.addEventListener('click', refreshChart);

        // 周期选择
        elements.periodSelect.addEventListener('change', function() {
            if (stockData) {
                renderKlineChart(stockData.kline_data);
            }
        });

        // 均线选择
        elements.maSelect.addEventListener('change', function() {
            if (stockData) {
                renderKlineChart(stockData.kline_data);
            }
        });
    }

    // 从URL获取股票代码
    function getStockCodeFromURL() {
        const path = window.location.pathname;
        const parts = path.split('/');
        return parts[parts.length - 1];
    }

    // 加载股票数据
    async function loadStockData() {
        showLoading();

        try {
            const response = await fetch(`/api/stock/${stockCode}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                stockData = data;
                processStockData(data);
            } else {
                throw new Error(data.message || '加载股票数据失败');
            }
        } catch (error) {
            console.error('加载股票数据失败:', error);
            showError(`加载股票数据失败: ${error.message}`);
        }
    }

    // 处理股票数据
    function processStockData(data) {
        const stock = data.stock;
        const indicators = data.indicators;
        const analysis = data.analysis;

        // 更新股票基本信息
        elements.stockInfo.textContent = `${stock.名称} (${stock.代码})`;
        elements.stockCode.textContent = stock.代码;
        elements.stockName.textContent = stock.名称;
        elements.stockSector.textContent = stock.板块 || '-';
        elements.stockPrice.textContent = formatPrice(stock.最新价);

        // 趋势强度
        const trendClass = stock.趋势强度 === '强' ? 'trend-strong' : 'trend-weak';
        const trendText = stock.趋势强度 === '强' ? '强势' : '弱势';
        elements.stockTrend.innerHTML = `<span class="trend-tag ${trendClass}">${trendText}</span>`;

        // 回撤信息
        const pullbackMatch = stock.理由?.match(/回撤:([\d.]+)%/);
        if (pullbackMatch) {
            elements.stockPullback.textContent = `${pullbackMatch[1]}%`;
        }

        // 更新技术指标
        updateTechnicalIndicators(indicators, stock);

        // 更新分析内容
        updateAnalysisContent(analysis);

        // 更新交易建议
        updateTradingAdvice(stock, indicators);

        // 渲染K线图表
        renderKlineChart(data.kline_data);

        // 更新数据时间
        elements.dataUpdateTime.textContent = formatDateTime(new Date());

        // 隐藏加载状态
        hideLoading();
    }

    // 更新技术指标
    function updateTechnicalIndicators(indicators, stock) {
        // 移动平均线
        elements.ma5Value.textContent = formatPrice(indicators.ma5);
        elements.ma20Value.textContent = formatPrice(indicators.ma20);
        elements.ma60Value.textContent = formatPrice(indicators.ma60);

        // MA20 > MA60 判断
        if (indicators.ma20 && indicators.ma60) {
            const maCompare = indicators.ma20 > indicators.ma60;
            elements.maCompare.textContent = maCompare ? '是' : '否';
            elements.maCompare.style.color = maCompare ? 'var(--success-color)' : 'var(--danger-color)';
        }

        // 价格高点
        elements.high60d.textContent = formatPrice(indicators.high_60d);

        // 当前回撤
        if (indicators.high_60d && stock.最新价) {
            const pullback = ((indicators.high_60d - stock.最新价) / indicators.high_60d * 100).toFixed(1);
            elements.currentPullback.textContent = `${pullback}%`;
        }

        // 是否创新高
        if (indicators.high_60d && stock.最新价) {
            const isNewHigh = Math.abs(stock.最新价 - indicators.high_60d) / indicators.high_60d < 0.01;
            elements.newHigh.textContent = isNewHigh ? '是' : '否';
            elements.newHigh.style.color = isNewHigh ? 'var(--success-color)' : 'var(--danger-color)';
        }

        // 成交量
        elements.volumeToday.textContent = formatVolume(indicators.volume_today);
        elements.volumeMa5.textContent = formatVolume(indicators.volume_ma5);
        elements.volumeRatio.textContent = indicators.volume_ratio || '-';
    }

    // 更新分析内容
    function updateAnalysisContent(analysis) {
        // 策略匹配点
        elements.strategyPoints.innerHTML = '';
        if (analysis.strategy_points && analysis.strategy_points.length > 0) {
            analysis.strategy_points.forEach(point => {
                const li = document.createElement('li');
                li.textContent = point;
                elements.strategyPoints.appendChild(li);
            });
        }

        // 详细分析
        elements.detailedAnalysis.textContent = analysis.detailed_analysis || '';
    }

    // 更新交易建议
    function updateTradingAdvice(stock, indicators) {
        // 买入价格建议
        if (stock.最新价) {
            elements.buyPrice.textContent = `${formatPrice(stock.最新价)}元`;
        }

        // 止损价格建议
        if (stock.最新价) {
            const stopLossPrice = stock.最新价 * 0.96; // 回撤4%
            elements.stopLossPrice.textContent = `${formatPrice(stopLossPrice)}元`;
        }
    }

    // 渲染K线图表
    function renderKlineChart(klineData) {
        if (!klineData || klineData.length === 0) {
            console.warn('没有K线数据可渲染');
            return;
        }

        // 准备图表数据
        const dates = klineData.map(item => item.date);
        const values = klineData.map(item => [
            item.open,
            item.close,
            item.low,
            item.high
        ]);
        const volumes = klineData.map(item => item.volume);

        // 计算移动平均线
        const ma5 = calculateMA(5, klineData);
        const ma10 = calculateMA(10, klineData);
        const ma20 = calculateMA(20, klineData);
        const ma60 = calculateMA(60, klineData);

        // 销毁现有图表
        if (klineChart) {
            klineChart.dispose();
        }

        // 初始化图表
        klineChart = echarts.init(elements.klineChart);

        // 图表配置
        const option = {
            backgroundColor: '#fff',
            animation: true,
            legend: {
                bottom: 10,
                left: 'center',
                data: ['日K', 'MA5', 'MA10', 'MA20', 'MA60', '成交量']
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                },
                backgroundColor: 'rgba(245, 245, 245, 0.8)',
                borderWidth: 1,
                borderColor: '#ccc',
                textStyle: {
                    color: '#000'
                },
                formatter: function(params) {
                    let result = `${params[0].axisValue}<br/>`;
                    params.forEach(item => {
                        if (item.seriesName === '日K') {
                            const data = item.data;
                            result += `${item.seriesName}: ${data[0].toFixed(2)} / ${data[1].toFixed(2)} / ${data[2].toFixed(2)} / ${data[3].toFixed(2)}<br/>`;
                        } else if (item.seriesName === '成交量') {
                            result += `${item.seriesName}: ${formatVolume(item.data)}<br/>`;
                        } else {
                            result += `${item.seriesName}: ${item.data.toFixed(2)}<br/>`;
                        }
                    });
                    return result;
                }
            },
            axisPointer: {
                link: [{ xAxisIndex: 'all' }],
                label: {
                    backgroundColor: '#777'
                }
            },
            grid: [
                {
                    left: '10%',
                    right: '8%',
                    height: '50%'
                },
                {
                    left: '10%',
                    right: '8%',
                    top: '63%',
                    height: '16%'
                }
            ],
            xAxis: [
                {
                    type: 'category',
                    data: dates,
                    scale: true,
                    boundaryGap: false,
                    axisLine: { onZero: false },
                    splitLine: { show: false },
                    splitNumber: 20,
                    min: 'dataMin',
                    max: 'dataMax',
                    axisPointer: {
                        z: 100
                    }
                },
                {
                    type: 'category',
                    gridIndex: 1,
                    data: dates,
                    scale: true,
                    boundaryGap: false,
                    axisLine: { onZero: false },
                    axisTick: { show: false },
                    splitLine: { show: false },
                    axisLabel: { show: false },
                    splitNumber: 20,
                    min: 'dataMin',
                    max: 'dataMax'
                }
            ],
            yAxis: [
                {
                    scale: true,
                    splitArea: {
                        show: true
                    }
                },
                {
                    scale: true,
                    gridIndex: 1,
                    splitNumber: 2,
                    axisLabel: { show: false },
                    axisLine: { show: false },
                    axisTick: { show: false },
                    splitLine: { show: false }
                }
            ],
            dataZoom: [
                {
                    type: 'inside',
                    xAxisIndex: [0, 1],
                    start: 50,
                    end: 100
                },
                {
                    show: true,
                    xAxisIndex: [0, 1],
                    type: 'slider',
                    top: '85%',
                    start: 50,
                    end: 100
                }
            ],
            series: [
                {
                    name: '日K',
                    type: 'candlestick',
                    data: values,
                    itemStyle: {
                        color: '#ec0000',
                        color0: '#00da3c',
                        borderColor: '#8A0000',
                        borderColor0: '#008F28'
                    }
                },
                {
                    name: '成交量',
                    type: 'bar',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: volumes,
                    itemStyle: {
                        color: function(params) {
                            const colorList = values.map(item =>
                                item[1] >= item[0] ? '#ec0000' : '#00da3c'
                            );
                            return colorList[params.dataIndex];
                        }
                    }
                }
            ]
        };

        // 根据选择的均线添加数据
        const maSelect = elements.maSelect.value;
        if (maSelect === 'ma5' || maSelect === 'all') {
            option.series.push({
                name: 'MA5',
                type: 'line',
                data: ma5,
                smooth: true,
                lineStyle: {
                    opacity: 0.5,
                    width: 1
                }
            });
        }

        if (maSelect === 'ma10' || maSelect === 'all') {
            option.series.push({
                name: 'MA10',
                type: 'line',
                data: ma10,
                smooth: true,
                lineStyle: {
                    opacity: 0.5,
                    width: 1
                }
            });
        }

        if (maSelect === 'ma20' || maSelect === 'all') {
            option.series.push({
                name: 'MA20',
                type: 'line',
                data: ma20,
                smooth: true,
                lineStyle: {
                    opacity: 0.5,
                    width: 1
                }
            });
        }

        if (maSelect === 'ma60' || maSelect === 'all') {
            option.series.push({
                name: 'MA60',
                type: 'line',
                data: ma60,
                smooth: true,
                lineStyle: {
                    opacity: 0.5,
                    width: 1
                }
            });
        }

        // 设置图表选项
        klineChart.setOption(option);

        // 响应窗口大小变化
        window.addEventListener('resize', function() {
            klineChart.resize();
        });
    }

    // 计算移动平均线
    function calculateMA(dayCount, data) {
        const result = [];
        for (let i = 0, len = data.length; i < len; i++) {
            if (i < dayCount - 1) {
                result.push('-');
                continue;
            }
            let sum = 0;
            for (let j = 0; j < dayCount; j++) {
                sum += data[i - j].close;
            }
            result.push(sum / dayCount);
        }
        return result;
    }

    // 刷新图表
    function refreshChart() {
        if (stockData) {
            renderKlineChart(stockData.kline_data);
            showMessage('图表已刷新', 'success');
        }
    }

    // 显示加载状态
    function showLoading() {
        // 可以在页面中添加加载提示
        const loadingEl = document.createElement('div');
        loadingEl.className = 'loading';
        loadingEl.innerHTML = '<span class="loading-spinner"></span> 加载股票数据中...';
        loadingEl.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 30px;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            z-index: 1000;
        `;
        loadingEl.id = 'loading-overlay';
        document.body.appendChild(loadingEl);
    }

    // 隐藏加载状态
    function hideLoading() {
        const loadingEl = document.getElementById('loading-overlay');
        if (loadingEl) {
            loadingEl.remove();
        }
    }

    // 显示错误
    function showError(message) {
        const errorEl = document.createElement('div');
        errorEl.className = 'message message-error';
        errorEl.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            <span>${message}</span>
            <button class="message-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        document.body.appendChild(errorEl);

        // 5秒后自动移除
        setTimeout(() => {
            if (errorEl.parentElement) {
                errorEl.remove();
            }
        }, 5000);
    }

    // 显示消息
    function showMessage(message, type = 'info') {
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            <span>${message}</span>
            <button class="message-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        document.body.appendChild(messageEl);

        // 3秒后自动移除
        setTimeout(() => {
            if (messageEl.parentElement) {
                messageEl.remove();
            }
        }, 3000);
    }

    // 格式化日期
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}年${month}月${day}日`;
    }

    // 格式化日期时间
    function formatDateTime(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${year}-${month}-${day} ${hours}:${minutes}`;
    }

    // 格式化价格
    function formatPrice(price) {
        if (typeof price !== 'number') return '-';
        return price.toFixed(2);
    }

    // 格式化成交量
    function formatVolume(volume) {
        if (typeof volume !== 'number') return '-';
        if (volume >= 100000000) {
            return (volume / 100000000).toFixed(2) + '亿';
        } else if (volume >= 10000) {
            return (volume / 10000).toFixed(2) + '万';
        } else {
            return volume.toString();
        }
    }
});