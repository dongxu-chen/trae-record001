class LiveDashboard {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectInterval = 3000;
        this.wsUrl = 'ws://localhost:8765';

        this.charts = {};
        this.trendData = {
            timestamps: [],
            viewers: [],
            likes: [],
            transactions: [],
            amount: [],
        };
        this.maxTrendPoints = 30;

        this.init();
    }

    init() {
        this.initCharts();
        this.updateCurrentTime();
        setInterval(() => this.updateCurrentTime(), 1000);
        this.connect();
    }

    updateCurrentTime() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { hour12: false });
        document.getElementById('currentTime').textContent = timeStr;
    }

    initCharts() {
        this.charts.trend = echarts.init(document.getElementById('trendChart'));
        this.charts.hotword = echarts.init(document.getElementById('hotwordChart'));
        this.charts.sentiment = echarts.init(document.getElementById('sentimentChart'));
        this.charts.products = echarts.init(document.getElementById('productsChart'));

        this.updateTrendChart();
        this.updateHotwordChart([]);
        this.updateSentimentChart({ positive_count: 0, neutral_count: 0, negative_count: 0 });
        this.updateProductsChart([]);

        window.addEventListener('resize', () => {
            Object.values(this.charts).forEach(chart => chart.resize());
        });
    }

    connect() {
        this.setConnectionStatus('connecting');

        try {
            this.ws = new WebSocket(this.wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket连接成功');
                this.setConnectionStatus('connected');
                this.reconnectAttempts = 0;
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleData(data);
                } catch (e) {
                    console.error('解析数据失败:', e);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket错误:', error);
            };

            this.ws.onclose = () => {
                console.log('WebSocket连接断开');
                this.setConnectionStatus('disconnected');
                this.reconnect();
            };
        } catch (e) {
            console.error('创建WebSocket连接失败:', e);
            this.reconnect();
        }
    }

    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('达到最大重连次数，停止重连');
            this.setConnectionStatus('failed');
            return;
        }

        this.reconnectAttempts++;
        console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        this.setConnectionStatus('connecting');

        setTimeout(() => {
            this.connect();
        }, this.reconnectInterval);
    }

    setConnectionStatus(status) {
        const dot = document.querySelector('.conn-dot');
        const text = document.getElementById('connText');

        dot.className = 'conn-dot';
        switch (status) {
            case 'connected':
                dot.classList.add('connected');
                text.textContent = '已连接';
                break;
            case 'connecting':
                dot.classList.add('connecting');
                text.textContent = '连接中...';
                break;
            case 'disconnected':
                text.textContent = '已断开';
                break;
            case 'failed':
                text.textContent = '连接失败';
                break;
        }
    }

    handleData(data) {
        if (data.type !== 'metrics_update') return;

        const { metrics, sentiment, hotwords, trend, top_products, latest_danmu, suggestion, watermark, incremental_info } = data;

        this.updateMetrics(metrics);
        this.updateTrendData(trend);
        this.updateHotwordChart(hotwords);
        this.updateSentimentChart(sentiment);
        this.updateProductsChart(top_products);
        this.updateDanmuList(latest_danmu);
        this.updateSentimentStats(sentiment);
        this.updateEventTimeInfo(watermark, metrics);
        this.updateIncrementalStats(suggestion, incremental_info);

        if (suggestion) {
            this.updateSuggestion(suggestion);
        }
    }

    formatNumber(num) {
        if (num >= 100000000) {
            return (num / 100000000).toFixed(2) + '亿';
        } else if (num >= 10000) {
            return (num / 10000).toFixed(1) + '万';
        }
        return Math.floor(num).toLocaleString();
    }

    animateValue(elementId, newValue, duration = 500) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const startValue = parseFloat(element.textContent.replace(/[^\d.]/g, '')) || 0;
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            const currentValue = startValue + (newValue - startValue) * easeProgress;
            element.textContent = this.formatNumber(currentValue);

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }

    updateMetrics(metrics) {
        this.animateValue('totalViewers', metrics.total_viewers);
        this.animateValue('currentOnline', metrics.current_online);
        this.animateValue('totalLikes', metrics.total_likes);
        this.animateValue('totalAmount', metrics.total_amount);
        this.animateValue('conversionRate', metrics.conversion_rate * 100);
        this.animateValue('totalOrders', metrics.total_transactions);
        this.animateValue('totalClicks', metrics.total_product_clicks);

        document.getElementById('viewersPerMin').textContent = `+${metrics.viewers_per_minute}`;
        document.getElementById('viewersPerSec').textContent = metrics.viewers_per_second;
        document.getElementById('likesPerSec').textContent = metrics.likes_per_second;
        document.getElementById('ordersPerMin').textContent = metrics.transactions_per_minute;
        document.getElementById('amountPerMin').textContent = this.formatNumber(metrics.amount_per_minute);
    }

    updateTrendData(trend) {
        if (trend && trend.timestamps && trend.timestamps.length > 0) {
            this.trendData = trend;
        } else {
            const now = Date.now() / 1000;
            this.trendData.timestamps.push(now);
            this.trendData.viewers.push(0);
            this.trendData.likes.push(0);
            this.trendData.transactions.push(0);
            this.trendData.amount.push(0);

            if (this.trendData.timestamps.length > this.maxTrendPoints) {
                this.trendData.timestamps.shift();
                this.trendData.viewers.shift();
                this.trendData.likes.shift();
                this.trendData.transactions.shift();
                this.trendData.amount.shift();
            }
        }
        this.updateTrendChart();
    }

    updateTrendChart() {
        const times = this.trendData.timestamps.map(ts => {
            const date = new Date(ts * 1000);
            return date.toLocaleTimeString('zh-CN', { hour12: false });
        });

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                borderColor: 'rgba(0, 255, 255, 0.3)',
                textStyle: { color: '#fff' },
            },
            legend: {
                show: false,
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                top: '10%',
                containLabel: true,
            },
            xAxis: {
                type: 'category',
                data: times,
                axisLine: { lineStyle: { color: 'rgba(0, 255, 255, 0.3)' } },
                axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
                splitLine: { show: false },
            },
            yAxis: [
                {
                    type: 'value',
                    name: '人数/次数',
                    axisLine: { lineStyle: { color: 'rgba(0, 255, 255, 0.3)' } },
                    axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
                    splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
                },
                {
                    type: 'value',
                    name: '金额(元)',
                    position: 'right',
                    axisLine: { lineStyle: { color: 'rgba(255, 170, 0, 0.3)' } },
                    axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
                    splitLine: { show: false },
                },
            ],
            series: [
                {
                    name: '在线增量',
                    type: 'line',
                    smooth: true,
                    data: this.trendData.viewers,
                    lineStyle: { color: '#00ff88', width: 2 },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(0, 255, 136, 0.3)' },
                            { offset: 1, color: 'rgba(0, 255, 136, 0)' },
                        ]),
                    },
                    symbol: 'none',
                },
                {
                    name: '点赞',
                    type: 'line',
                    smooth: true,
                    data: this.trendData.likes,
                    lineStyle: { color: '#ff4466', width: 2 },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(255, 68, 102, 0.3)' },
                            { offset: 1, color: 'rgba(255, 68, 102, 0)' },
                        ]),
                    },
                    symbol: 'none',
                },
                {
                    name: '订单',
                    type: 'bar',
                    data: this.trendData.transactions,
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(255, 170, 0, 0.8)' },
                            { offset: 1, color: 'rgba(255, 170, 0, 0.2)' },
                        ]),
                        borderRadius: [4, 4, 0, 0],
                    },
                    barWidth: '30%',
                },
                {
                    name: '成交额',
                    type: 'line',
                    smooth: true,
                    yAxisIndex: 1,
                    data: this.trendData.amount,
                    lineStyle: { color: '#ffaa00', width: 2, type: 'dashed' },
                    symbol: 'circle',
                    symbolSize: 6,
                    itemStyle: { color: '#ffaa00' },
                },
            ],
        };

        this.charts.trend.setOption(option);
    }

    updateHotwordChart(hotwords) {
        const data = hotwords.map(hw => ({
            name: hw.word,
            value: hw.count * 10,
        }));

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                show: true,
                formatter: (params) => `${params.name}: ${Math.floor(params.value / 10)}次`,
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                borderColor: 'rgba(0, 255, 255, 0.3)',
                textStyle: { color: '#fff' },
            },
            series: [{
                type: 'wordCloud',
                shape: 'circle',
                left: 'center',
                top: 'center',
                width: '90%',
                height: '90%',
                sizeRange: [12, 40],
                rotationRange: [-30, 30],
                rotationStep: 15,
                gridSize: 8,
                drawOutOfBound: false,
                textStyle: {
                    fontWeight: 'bold',
                    color: () => {
                        const colors = ['#00ffff', '#ff00ff', '#00ff88', '#ffaa00', '#ff4466', '#44aaff'];
                        return colors[Math.floor(Math.random() * colors.length)];
                    },
                },
                emphasis: {
                    textStyle: {
                        shadowBlur: 10,
                        shadowColor: '#00ffff',
                    },
                },
                data: data.length > 0 ? data : [
                    { name: '等待', value: 10 },
                    { name: '数据', value: 8 },
                    { name: '热词', value: 6 },
                ],
            }],
        };

        this.charts.hotword.setOption(option);
    }

    updateSentimentChart(sentiment) {
        const data = [
            { value: sentiment.positive_count || 0, name: '正面', itemStyle: { color: '#00ff88' } },
            { value: sentiment.neutral_count || 0, name: '中性', itemStyle: { color: '#aaaaaa' } },
            { value: sentiment.negative_count || 0, name: '负面', itemStyle: { color: '#ff4466' } },
        ];

        const total = data.reduce((sum, d) => sum + d.value, 0) || 1;

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c} ({d}%)',
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                borderColor: 'rgba(0, 255, 255, 0.3)',
                textStyle: { color: '#fff' },
            },
            legend: {
                orient: 'vertical',
                right: '5%',
                top: 'center',
                textStyle: { color: 'rgba(255, 255, 255, 0.7)', fontSize: 12 },
            },
            series: [{
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['35%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: 'rgba(0, 0, 0, 0.3)',
                    borderWidth: 2,
                },
                label: {
                    show: false,
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 14,
                        fontWeight: 'bold',
                        color: '#fff',
                    },
                },
                data: data,
            }],
        };

        this.charts.sentiment.setOption(option);
    }

    updateProductsChart(products) {
        const productNames = products.map(p => p.product_id || '未知');
        const amounts = products.map(p => p.amount || 0);
        const conversions = products.map(p => (p.conversion_rate || 0) * 100);

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                borderColor: 'rgba(0, 255, 255, 0.3)',
                textStyle: { color: '#fff' },
                axisPointer: {
                    type: 'shadow',
                },
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                top: '10%',
                containLabel: true,
            },
            xAxis: {
                type: 'category',
                data: productNames.length > 0 ? productNames : ['暂无数据'],
                axisLine: { lineStyle: { color: 'rgba(0, 255, 255, 0.3)' } },
                axisLabel: {
                    color: 'rgba(255, 255, 255, 0.7)',
                    fontSize: 10,
                    rotate: 30,
                },
            },
            yAxis: [
                {
                    type: 'value',
                    name: '销售额(元)',
                    axisLine: { lineStyle: { color: 'rgba(0, 255, 255, 0.3)' } },
                    axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
                    splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
                },
                {
                    type: 'value',
                    name: '转化率(%)',
                    position: 'right',
                    axisLine: { lineStyle: { color: 'rgba(170, 68, 255, 0.3)' } },
                    axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
                    splitLine: { show: false },
                    max: 30,
                },
            ],
            series: [
                {
                    name: '销售额',
                    type: 'bar',
                    data: amounts.length > 0 ? amounts : [0],
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(0, 255, 255, 0.8)' },
                            { offset: 1, color: 'rgba(0, 255, 255, 0.2)' },
                        ]),
                        borderRadius: [4, 4, 0, 0],
                    },
                    barWidth: '40%',
                },
                {
                    name: '转化率',
                    type: 'line',
                    yAxisIndex: 1,
                    smooth: true,
                    data: conversions.length > 0 ? conversions : [0],
                    lineStyle: { color: '#aa44ff', width: 2 },
                    symbol: 'circle',
                    symbolSize: 8,
                    itemStyle: { color: '#aa44ff' },
                },
            ],
        };

        this.charts.products.setOption(option);
    }

    updateDanmuList(danmuList) {
        if (!danmuList || danmuList.length === 0) return;

        const container = document.getElementById('danmuList');
        const hasEmpty = container.querySelector('.danmu-empty');
        if (hasEmpty) {
            container.innerHTML = '';
        }

        const existingIds = new Set(
            Array.from(container.querySelectorAll('.danmu-item')).map(el => el.dataset.key)
        );

        danmuList.forEach((danmu, index) => {
            const key = `${danmu.timestamp}-${index}`;
            if (existingIds.has(key)) return;

            const sentiment = danmu.sentiment || {};
            const item = document.createElement('div');
            item.className = `danmu-item sentiment-${sentiment.label || 'neutral'}`;
            item.dataset.key = key;

            const scoreClass = sentiment.score >= 0.6 ? 'positive' :
                             sentiment.score <= 0.4 ? 'negative' : 'neutral';

            item.innerHTML = `
                <div class="danmu-header">
                    <span class="danmu-user ${danmu.is_vip ? 'vip' : ''}">
                        ${danmu.is_vip ? '👑 ' : ''}${danmu.user_name}
                    </span>
                    <span class="danmu-score ${scoreClass}">
                        ${sentiment.score ? sentiment.score.toFixed(2) : '0.50'}
                    </span>
                </div>
                <div class="danmu-content">${this.escapeHtml(danmu.content)}</div>
            `;

            container.insertBefore(item, container.firstChild);

            while (container.children.length > 50) {
                container.removeChild(container.lastChild);
            }
        });
    }

    updateSentimentStats(sentiment) {
        document.getElementById('sentimentPositive').textContent =
            `${((sentiment.positive_rate || 0) * 100).toFixed(1)}%`;
        document.getElementById('sentimentNeutral').textContent =
            `${((sentiment.neutral_count ? sentiment.neutral_count / (sentiment.positive_count + sentiment.neutral_count + sentiment.negative_count || 1) : 0) * 100).toFixed(1)}%`;
        document.getElementById('sentimentNegative').textContent =
            `${((sentiment.negative_rate || 0) * 100).toFixed(1)}%`;
    }

    updateEventTimeInfo(watermark, metrics) {
        if (!watermark && !metrics) return;

        const eventTime = metrics?.event_time || (watermark ? watermark.max_event_time : 0);
        const watermarkTime = watermark?.current_watermark || 0;
        const lag = watermark?.lag || 0;

        if (eventTime > 0) {
            const eventDate = new Date(eventTime * 1000);
            document.getElementById('eventTime').textContent =
                eventDate.toLocaleTimeString('zh-CN', { hour12: false });
        }

        if (watermarkTime > 0) {
            const watermarkDate = new Date(watermarkTime * 1000);
            document.getElementById('watermark').textContent =
                watermarkDate.toLocaleTimeString('zh-CN', { hour12: false });
        }

        const lagElement = document.getElementById('lag');
        if (lagElement) {
            lagElement.textContent = `${lag.toFixed(1)}s`;
            lagElement.className = 'lag-indicator';
            if (lag > 5) {
                lagElement.classList.add('lag-high');
            } else if (lag > 2) {
                lagElement.classList.add('lag-medium');
            } else {
                lagElement.classList.add('lag-low');
            }
        }

        if (watermark) {
            document.getElementById('eventTimeInfo').style.display = 'flex';
        }
    }

    updateIncrementalStats(suggestion, incrementalInfo) {
        if (suggestion && suggestion.incremental) {
            const inc = suggestion.incremental;
            document.getElementById('processedDanmu').textContent = inc.total_danmu_processed || 0;
            document.getElementById('windowAge').textContent = inc.window_age || 0;
        } else if (suggestion && suggestion.state) {
            const state = suggestion.state;
            document.getElementById('processedDanmu').textContent = state.total_danmu || 0;
            document.getElementById('windowAge').textContent = state.window_age || 0;
        } else if (incrementalInfo) {
            document.getElementById('processedDanmu').textContent = incrementalInfo.total_danmu_in_window || 0;
        }
    }

    updateSuggestion(suggestion) {
        const container = document.getElementById('suggestionContent');
        if (!suggestion.current) return;

        const s = suggestion.current;
        const levelLabels = {
            success: '优秀',
            info: '提示',
            warning: '警告',
            danger: '危险',
        };
        const categoryLabels = {
            interaction: '互动',
            sentiment: '情感',
            conversion: '转化',
            hotwords: '热词',
            online: '流量',
            products: '商品',
        };

        const card = document.createElement('div');
        card.className = `suggestion-card level-${s.level}`;
        card.innerHTML = `
            <div class="suggestion-header">
                <span class="suggestion-level">${levelLabels[s.level] || s.level}</span>
                <span class="suggestion-category">${categoryLabels[s.category] || s.category}</span>
            </div>
            <div class="suggestion-message">${this.escapeHtml(s.message)}</div>
            <div class="suggestion-action">💡 ${this.escapeHtml(s.action)}</div>
        `;

        container.innerHTML = '';
        container.appendChild(card);

        if (suggestion.history && suggestion.history.length > 1) {
            suggestion.history.slice(0, -1).reverse().forEach(historyItem => {
                const historyCard = document.createElement('div');
                historyCard.className = `suggestion-card level-${historyItem.level}`;
                historyCard.style.opacity = '0.6';
                historyCard.style.transform = 'scale(0.98)';
                historyCard.innerHTML = `
                    <div class="suggestion-header">
                        <span class="suggestion-level">${levelLabels[historyItem.level] || historyItem.level}</span>
                        <span class="suggestion-category">${categoryLabels[historyItem.category] || historyItem.category}</span>
                    </div>
                    <div class="suggestion-message">${this.escapeHtml(historyItem.message)}</div>
                `;
                container.appendChild(historyCard);
            });
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new LiveDashboard();
});
