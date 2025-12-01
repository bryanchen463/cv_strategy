/**
 * A股选股策略系统 - 前端JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // 全局变量
    let allStocks = [];
    let filteredStocks = [];
    let sectors = new Set();
    let currentFilters = {
        sector: '',
        trend: '',
        search: ''
    };

    // DOM元素
    const elements = {
        currentDate: document.getElementById('current-date'),
        updateTime: document.getElementById('update-time'),
        totalStocks: document.getElementById('total-stocks'),
        totalSectors: document.getElementById('total-sectors'),
        strongTrend: document.getElementById('strong-trend'),
        filteredCount: document.getElementById('filtered-count'),
        totalCount: document.getElementById('total-count'),
        stocksTbody: document.getElementById('stocks-tbody'),
        sectorFilter: document.getElementById('sector-filter'),
        trendFilter: document.getElementById('trend-filter'),
        searchInput: document.getElementById('search-input'),
        searchBtn: document.getElementById('search-btn'),
        refreshBtn: document.getElementById('refresh-btn'),
        resetBtn: document.getElementById('reset-btn'),
        strategyParams: document.getElementById('strategy-params'),
        lastUpdate: document.getElementById('last-update')
    };

    // 初始化
    init();

    // 初始化函数
    function init() {
        // 设置当前日期
        const now = new Date();
        elements.currentDate.textContent = formatDate(now);
        elements.updateTime.textContent = formatTime(now);

        // 绑定事件
        bindEvents();

        // 加载数据
        loadData();

        // 加载策略参数
        loadStrategyParams();
    }

    // 绑定事件
    function bindEvents() {
        // 筛选器变化
        elements.sectorFilter.addEventListener('change', function() {
            currentFilters.sector = this.value;
            applyFilters();
        });

        elements.trendFilter.addEventListener('change', function() {
            currentFilters.trend = this.value;
            applyFilters();
        });

        // 搜索
        elements.searchBtn.addEventListener('click', performSearch);
        elements.searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });

        // 刷新数据
        elements.refreshBtn.addEventListener('click', refreshData);

        // 重置筛选
        elements.resetBtn.addEventListener('click', resetFilters);
    }

    // 加载数据
    async function loadData() {
        showLoading();

        try {
            const response = await fetch('/api/stocks');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            processData(data);
        } catch (error) {
            console.error('加载数据失败:', error);
            showError('加载数据失败，请刷新页面重试');
        }
    }

    // 处理数据
    function processData(data) {
        allStocks = data.stocks || [];
        filteredStocks = [...allStocks];

        // 更新统计信息
        updateStats(data.stats);

        // 提取板块
        extractSectors();

        // 更新板块筛选器
        updateSectorFilter();

        // 渲染表格
        renderTable();

        // 更新最后更新时间
        if (data.date) {
            elements.lastUpdate.textContent = data.date;
        }

        // 隐藏加载状态
        hideLoading();
    }

    // 更新统计信息
    function updateStats(stats) {
        if (!stats) return;

        elements.totalStocks.textContent = stats.total || 0;
        elements.totalCount.textContent = stats.total || 0;
        elements.filteredCount.textContent = stats.total || 0;

        // 计算板块数量
        const sectorCount = stats.by_sector ? Object.keys(stats.by_sector).length : 0;
        elements.totalSectors.textContent = sectorCount;

        // 强势趋势数量
        elements.strongTrend.textContent = stats.by_trend?.强 || 0;
    }

    // 提取板块
    function extractSectors() {
        sectors.clear();
        allStocks.forEach(stock => {
            if (stock.板块) {
                sectors.add(stock.板块);
            }
        });
    }

    // 更新板块筛选器
    function updateSectorFilter() {
        // 清空现有选项（保留"全部板块"）
        while (elements.sectorFilter.options.length > 1) {
            elements.sectorFilter.remove(1);
        }

        // 添加板块选项
        const sortedSectors = Array.from(sectors).sort();
        sortedSectors.forEach(sector => {
            const option = document.createElement('option');
            option.value = sector;
            option.textContent = sector;
            elements.sectorFilter.appendChild(option);
        });
    }

    // 渲染表格
    function renderTable() {
        const tbody = elements.stocksTbody;
        tbody.innerHTML = '';

        if (filteredStocks.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td colspan="8" class="loading">
                    没有找到符合条件的股票
                </td>
            `;
            tbody.appendChild(row);
            return;
        }

        filteredStocks.forEach((stock, index) => {
            const row = document.createElement('tr');
            row.className = 'fade-in';

            // 趋势强度标签
            const trendClass = stock.趋势强度 === '强' ? 'trend-strong' : 'trend-weak';
            const trendText = stock.趋势强度 === '强' ? '强势' : '弱势';

            row.innerHTML = `
                <td>${index + 1}</td>
                <td><span class="sector-badge">${stock.板块 || '-'}</span></td>
                <td><strong>${stock.代码 || '-'}</strong></td>
                <td>${stock.名称 || '-'}</td>
                <td class="price">${formatPrice(stock.最新价)}</td>
                <td><span class="trend-tag ${trendClass}">${trendText}</span></td>
                <td>${stock.理由 || '-'}</td>
                <td>
                    <a href="/stock/${stock.代码}" class="action-btn view-btn">
                        <i class="fas fa-eye"></i> 查看
                    </a>
                </td>
            `;

            tbody.appendChild(row);
        });

        // 更新筛选计数
        elements.filteredCount.textContent = filteredStocks.length;
    }

    // 应用筛选
    function applyFilters() {
        filteredStocks = allStocks.filter(stock => {
            // 板块筛选
            if (currentFilters.sector && stock.板块 !== currentFilters.sector) {
                return false;
            }

            // 趋势强度筛选
            if (currentFilters.trend && stock.趋势强度 !== currentFilters.trend) {
                return false;
            }

            // 搜索筛选
            if (currentFilters.search) {
                const searchLower = currentFilters.search.toLowerCase();
                const codeMatch = stock.代码?.toLowerCase().includes(searchLower) || false;
                const nameMatch = stock.名称?.toLowerCase().includes(searchLower) || false;
                if (!codeMatch && !nameMatch) {
                    return false;
                }
            }

            return true;
        });

        renderTable();
    }

    // 执行搜索
    function performSearch() {
        currentFilters.search = elements.searchInput.value.trim();
        applyFilters();
    }

    // 刷新数据
    async function refreshData() {
        // 显示加载状态
        const originalText = elements.refreshBtn.innerHTML;
        elements.refreshBtn.innerHTML = '<span class="loading-spinner"></span> 刷新中...';
        elements.refreshBtn.disabled = true;

        try {
            const response = await fetch('/api/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`刷新失败: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                // 更新数据
                processData(result.data);

                // 显示成功消息
                showMessage('数据刷新成功！', 'success');

                // 更新更新时间
                const now = new Date();
                elements.updateTime.textContent = formatTime(now);
                elements.lastUpdate.textContent = result.data.date || formatDate(now);
            } else {
                throw new Error(result.message || '刷新失败');
            }
        } catch (error) {
            console.error('刷新数据失败:', error);
            showMessage(`刷新失败: ${error.message}`, 'error');
        } finally {
            // 恢复按钮状态
            elements.refreshBtn.innerHTML = originalText;
            elements.refreshBtn.disabled = false;
        }
    }

    // 重置筛选
    function resetFilters() {
        elements.sectorFilter.value = '';
        elements.trendFilter.value = '';
        elements.searchInput.value = '';

        currentFilters = {
            sector: '',
            trend: '',
            search: ''
        };

        filteredStocks = [...allStocks];
        renderTable();
    }

    // 加载策略参数
    async function loadStrategyParams() {
        try {
            const response = await fetch('/api/strategy');
            if (!response.ok) return;

            const data = await response.json();
            if (data.strategy_params) {
                renderStrategyParams(data.strategy_params);
            }
        } catch (error) {
            console.error('加载策略参数失败:', error);
        }
    }

    // 渲染策略参数
    function renderStrategyParams(params) {
        const container = elements.strategyParams;
        container.innerHTML = '';

        const paramList = document.createElement('div');
        paramList.className = 'strategy-params-content';

        // 添加参数项
        const paramItems = [
            { name: '数据开始时间', value: params.start_date || '-' },
            { name: '短期均线', value: `${params.ma_short || '-'}日线` },
            { name: '中期均线', value: `${params.ma_mid || '-'}日线` },
            { name: '趋势均线', value: `${params.ma_trend || '-'}日线` },
            { name: '创新高窗口', value: `${params.high_window || '-'}日` },
            { name: '屡创新高考察期', value: `${params.recent_days || '-'}天` },
            { name: '回调考察窗口', value: `${params.pullback_lookback || '-'}天` }
        ];

        paramItems.forEach(item => {
            const div = document.createElement('div');
            div.className = 'param-item';
            div.innerHTML = `
                <span class="param-name">${item.name}</span>
                <span class="param-value">${item.value}</span>
            `;
            paramList.appendChild(div);
        });

        container.appendChild(paramList);
    }

    // 显示加载状态
    function showLoading() {
        const tbody = elements.stocksTbody;
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="loading">
                    <span class="loading-spinner"></span> 加载数据中...
                </td>
            </tr>
        `;
    }

    // 隐藏加载状态
    function hideLoading() {
        // 加载状态会在renderTable中被替换
    }

    // 显示错误
    function showError(message) {
        const tbody = elements.stocksTbody;
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="loading" style="color: var(--danger-color);">
                    <i class="fas fa-exclamation-circle"></i> ${message}
                </td>
            </tr>
        `;
    }

    // 显示消息
    function showMessage(message, type = 'info') {
        // 创建消息元素
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            <span>${message}</span>
            <button class="message-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

        // 添加样式
        messageEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? 'var(--success-color)' : 'var(--danger-color)'};
            color: white;
            padding: 15px 20px;
            border-radius: var(--border-radius);
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: var(--shadow);
            z-index: 1000;
            animation: fadeIn 0.3s ease;
        `;

        // 添加到页面
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

    // 格式化时间
    function formatTime(date) {
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    }

    // 格式化价格
    function formatPrice(price) {
        if (typeof price !== 'number') return '-';
        return price.toFixed(2);
    }

    // 查看股票详情函数（已替换为页面跳转）
});