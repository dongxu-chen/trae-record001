let trendChart, sentimentPieChart, aspectChart, wordcloudChart, negativeWordsChart, categoryChart, categorySentimentChart, targetWordsChart, opinionWordsChart, competitorChart, competitorAspectChart;
let currentProduct = '';
let currentComment = null;

document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    loadProducts();
    refreshData();
    loadAlerts();
    
    document.getElementById('startDate').addEventListener('change', refreshData);
    document.getElementById('endDate').addEventListener('change', refreshData);
    document.getElementById('categoryFilter').addEventListener('change', refreshData);
    
    window.addEventListener('resize', function() {
        trendChart && trendChart.resize();
        sentimentPieChart && sentimentPieChart.resize();
        aspectChart && aspectChart.resize();
        wordcloudChart && wordcloudChart.resize();
        negativeWordsChart && negativeWordsChart.resize();
        categoryChart && categoryChart.resize();
        categorySentimentChart && categorySentimentChart.resize();
        targetWordsChart && targetWordsChart.resize();
        opinionWordsChart && opinionWordsChart.resize();
        competitorChart && competitorChart.resize();
        competitorAspectChart && competitorAspectChart.resize();
    });
});

function initCharts() {
    trendChart = echarts.init(document.getElementById('trendChart'));
    sentimentPieChart = echarts.init(document.getElementById('sentimentPieChart'));
    aspectChart = echarts.init(document.getElementById('aspectChart'));
    wordcloudChart = echarts.init(document.getElementById('wordcloudChart'));
    negativeWordsChart = echarts.init(document.getElementById('negativeWordsChart'));
    categoryChart = echarts.init(document.getElementById('categoryChart'));
    categorySentimentChart = echarts.init(document.getElementById('categorySentimentChart'));
    targetWordsChart = echarts.init(document.getElementById('targetWordsChart'));
    opinionWordsChart = echarts.init(document.getElementById('opinionWordsChart'));
    competitorChart = echarts.init(document.getElementById('competitorChart'));
    competitorAspectChart = echarts.init(document.getElementById('competitorAspectChart'));
}

function getFilters() {
    return {
        start_date: document.getElementById('startDate').value,
        end_date: document.getElementById('endDate').value,
        category: document.getElementById('categoryFilter').value
    };
}

function refreshData() {
    const filters = getFilters();
    const queryString = new URLSearchParams(filters).toString();
    
    Promise.all([
        fetch(`/api/overview?${queryString}`).then(r => r.json()),
        fetch(`/api/trend?${queryString}`).then(r => r.json()),
        fetch(`/api/aspects?${queryString}`).then(r => r.json()),
        fetch(`/api/negative-words?${queryString}`).then(r => r.json()),
        fetch(`/api/opinion-pairs?${queryString}`).then(r => r.json()),
    ]).then(([overview, trend, aspects, negativeWords, opinionPairs]) => {
        updateStatistics(overview.statistics);
        updateTrendChart(trend.trend);
        updateSentimentPieChart(overview.statistics);
        updateAspectChart(aspects.aspects);
        updateNegativeWordsChart(negativeWords.negative_words);
        updateCategoryChart(overview.category_stats);
        updateCategorySentimentChart(overview.category_stats);
        updateTargetWordsChart(opinionPairs.top_targets);
        updateOpinionWordsChart(opinionPairs.top_opinions);
        updateWordcloud();
        loadComments(1);
    }).catch(error => {
        console.error('数据加载失败:', error);
    });
}

function updateStatistics(stats) {
    document.getElementById('totalComments').textContent = stats.total || 0;
    document.getElementById('positiveCount').textContent = stats.positive || 0;
    document.getElementById('neutralCount').textContent = stats.neutral || 0;
    document.getElementById('negativeCount').textContent = stats.negative || 0;
    document.getElementById('positiveRate').textContent = (stats.positive_rate || 0) + '%';
    document.getElementById('neutralRate').textContent = (100 - (stats.positive_rate || 0) - (stats.negative_rate || 0)).toFixed(2) + '%';
    document.getElementById('negativeRate').textContent = (stats.negative_rate || 0) + '%';
    document.getElementById('avgScore').textContent = stats.avg_score || 0;
    document.getElementById('avgRating').textContent = stats.avg_rating || 0;
}

function updateTrendChart(trendData) {
    const dates = trendData.map(item => item.date);
    const scores = trendData.map(item => item.avg_score);
    const counts = trendData.map(item => item.count);
    
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            formatter: function(params) {
                let result = params[0].name + '<br/>';
                params.forEach(param => {
                    result += param.marker + param.seriesName + ': ' + param.value + '<br/>';
                });
                return result;
            }
        },
        legend: {
            data: ['平均情感分', '评论数量'],
            top: 0
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: dates,
            axisLabel: { rotate: 45 }
        },
        yAxis: [
            {
                type: 'value',
                name: '情感分',
                min: 0,
                max: 1,
                position: 'left'
            },
            {
                type: 'value',
                name: '评论数',
                position: 'right'
            }
        ],
        series: [
            {
                name: '平均情感分',
                type: 'line',
                data: scores,
                smooth: true,
                lineStyle: { color: '#667eea', width: 3 },
                itemStyle: { color: '#667eea' },
                areaStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
                            { offset: 1, color: 'rgba(102, 126, 234, 0.05)' }
                        ]
                    }
                }
            },
            {
                name: '评论数量',
                type: 'bar',
                yAxisIndex: 1,
                data: counts,
                itemStyle: { color: '#764ba2' }
            }
        ]
    };
    
    trendChart.setOption(option);
}

function updateSentimentPieChart(stats) {
    const option = {
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'vertical',
            left: 'left'
        },
        series: [
            {
                name: '情感分布',
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 10,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: true,
                    formatter: '{b}: {d}%'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 16,
                        fontWeight: 'bold'
                    }
                },
                data: [
                    { value: stats.positive || 0, name: '正向', itemStyle: { color: '#10b981' } },
                    { value: stats.neutral || 0, name: '中性', itemStyle: { color: '#f59e0b' } },
                    { value: stats.negative || 0, name: '负向', itemStyle: { color: '#ef4444' } }
                ]
            }
        ]
    };
    
    sentimentPieChart.setOption(option);
}

function updateAspectChart(aspects) {
    const aspectNames = Object.keys(aspects);
    const positiveData = aspectNames.map(a => aspects[a].positive_rate || 0);
    const negativeData = aspectNames.map(a => 100 - (aspects[a].positive_rate || 0));
    const avgScores = aspectNames.map(a => aspects[a].avg_score || 0);
    
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        legend: {
            data: ['正向率', '平均情感分'],
            top: 0
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: aspectNames
        },
        yAxis: [
            {
                type: 'value',
                name: '正向率(%)',
                min: 0,
                max: 100,
                position: 'left'
            },
            {
                type: 'value',
                name: '情感分',
                min: 0,
                max: 1,
                position: 'right'
            }
        ],
        series: [
            {
                name: '正向率',
                type: 'bar',
                stack: 'total',
                data: positiveData,
                itemStyle: { color: '#10b981' },
                label: {
                    show: true,
                    position: 'inside',
                    formatter: '{c}%'
                }
            },
            {
                name: '负向率',
                type: 'bar',
                stack: 'total',
                data: negativeData,
                itemStyle: { color: '#ef4444' }
            },
            {
                name: '平均情感分',
                type: 'line',
                yAxisIndex: 1,
                data: avgScores,
                smooth: true,
                lineStyle: { color: '#667eea', width: 3 },
                itemStyle: { color: '#667eea' }
            }
        ]
    };
    
    aspectChart.setOption(option);
}

function updateWordcloud() {
    const filters = getFilters();
    const sentiment = document.getElementById('wordcloudSentiment').value;
    const queryString = new URLSearchParams({ ...filters, sentiment }).toString();
    
    fetch(`/api/wordcloud?${queryString}`)
        .then(r => r.json())
        .then(data => {
            const words = data.words.map(item => ({
                name: item.word,
                value: item.count,
                textStyle: {
                    color: getRandomColor()
                }
            }));
            
            const option = {
                tooltip: {
                    show: true,
                    formatter: function(params) {
                        return params.name + ': ' + params.value;
                    }
                },
                series: [{
                    type: 'wordCloud',
                    gridSize: 2,
                    sizeRange: [12, 50],
                    rotationRange: [-45, 45],
                    shape: 'circle',
                    drawOutOfBound: false,
                    data: words
                }]
            };
            
            wordcloudChart.setOption(option);
        });
}

function getRandomColor() {
    const colors = ['#667eea', '#764ba2', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];
    return colors[Math.floor(Math.random() * colors.length)];
}

function updateNegativeWordsChart(negativeWords) {
    const words = negativeWords.map(item => item.word).reverse();
    const counts = negativeWords.map(item => item.count).reverse();
    
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'value',
            name: '出现次数'
        },
        yAxis: {
            type: 'category',
            data: words
        },
        series: [
            {
                name: '出现次数',
                type: 'bar',
                data: counts,
                itemStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 1, y2: 0,
                        colorStops: [
                            { offset: 0, color: '#ef4444' },
                            { offset: 1, color: '#f87171' }
                        ]
                    }
                },
                label: {
                    show: true,
                    position: 'right'
                }
            }
        ]
    };
    
    negativeWordsChart.setOption(option);
}

function updateCategoryChart(categoryStats) {
    const categories = categoryStats.map(item => item.category);
    const counts = categoryStats.map(item => item.count);
    
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: categories,
            axisLabel: { rotate: 30 }
        },
        yAxis: {
            type: 'value',
            name: '评论数'
        },
        series: [
            {
                name: '评论数',
                type: 'bar',
                data: counts,
                itemStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: '#667eea' },
                            { offset: 1, color: '#764ba2' }
                        ]
                    }
                },
                label: {
                    show: true,
                    position: 'top'
                }
            }
        ]
    };
    
    categoryChart.setOption(option);
}

function updateCategorySentimentChart(categoryStats) {
    const categories = categoryStats.map(item => item.category);
    const scores = categoryStats.map(item => item.avg_sentiment_score);
    const ratings = categoryStats.map(item => item.avg_rating);
    
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' }
        },
        legend: {
            data: ['平均情感分', '平均评分'],
            top: 0
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: categories,
            axisLabel: { rotate: 30 }
        },
        yAxis: [
            {
                type: 'value',
                name: '情感分',
                min: 0,
                max: 1,
                position: 'left'
            },
            {
                type: 'value',
                name: '评分',
                min: 0,
                max: 5,
                position: 'right'
            }
        ],
        series: [
            {
                name: '平均情感分',
                type: 'bar',
                data: scores,
                itemStyle: { color: '#10b981' },
                label: {
                    show: true,
                    position: 'top',
                    formatter: '{c}'
                }
            },
            {
                name: '平均评分',
                type: 'line',
                yAxisIndex: 1,
                data: ratings,
                smooth: true,
                lineStyle: { color: '#f59e0b', width: 3 },
                itemStyle: { color: '#f59e0b' }
            }
        ]
    };
    
    categorySentimentChart.setOption(option);
}

function updateTargetWordsChart(targetWords) {
    const words = targetWords.map(item => item.word).reverse();
    const counts = targetWords.map(item => item.count).reverse();
    
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'value',
            name: '出现次数'
        },
        yAxis: {
            type: 'category',
            data: words
        },
        series: [
            {
                name: '出现次数',
                type: 'bar',
                data: counts,
                itemStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 1, y2: 0,
                        colorStops: [
                            { offset: 0, color: '#667eea' },
                            { offset: 1, color: '#764ba2' }
                        ]
                    }
                },
                label: {
                    show: true,
                    position: 'right'
                }
            }
        ]
    };
    
    targetWordsChart.setOption(option);
}

function updateOpinionWordsChart(opinionWords) {
    const words = opinionWords.map(item => item.word).reverse();
    const counts = opinionWords.map(item => item.count).reverse();
    
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'value',
            name: '出现次数'
        },
        yAxis: {
            type: 'category',
            data: words
        },
        series: [
            {
                name: '出现次数',
                type: 'bar',
                data: counts,
                itemStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 1, y2: 0,
                        colorStops: [
                            { offset: 0, color: '#10b981' },
                            { offset: 1, color: '#34d399' }
                        ]
                    }
                },
                label: {
                    show: true,
                    position: 'right'
                }
            }
        ]
    };
    
    opinionWordsChart.setOption(option);
}

function loadComments(page) {
    const filters = getFilters();
    const sentiment = document.getElementById('commentSentiment').value;
    const queryString = new URLSearchParams({ ...filters, sentiment, page, page_size: 20 }).toString();
    
    fetch(`/api/comments?${queryString}`)
        .then(r => r.json())
        .then(data => {
            renderComments(data.comments);
            renderPagination(page, Math.ceil(data.total / data.page_size));
        });
}

function renderComments(comments) {
    const container = document.getElementById('commentsList');
    
    if (comments.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">暂无评论数据</div>';
        return;
    }
    
    container.innerHTML = comments.map(comment => {
        const sentimentClass = comment.sentiment_label;
        const aspects = comment.aspects ? comment.aspects.split(',').filter(a => a) : [];
        
        let opinionPairsHtml = '';
        if (comment.opinion_pairs) {
            try {
                const pairs = typeof comment.opinion_pairs === 'string' 
                    ? JSON.parse(comment.opinion_pairs.replace(/'/g, '"')) 
                    : comment.opinion_pairs;
                
                if (pairs && pairs.length > 0) {
                    opinionPairsHtml = `
                        <div class="opinion-pairs">
                            ${pairs.map(p => `
                                <span class="opinion-pair-tag">
                                    <span class="target-word">${p.target}</span>
                                    <span class="pair-arrow">→</span>
                                    <span class="opinion-word ${p.sentiment}">${p.opinion}</span>
                                </span>
                            `).join('')}
                        </div>
                    `;
                }
            } catch (e) {
                console.error('解析观点对失败:', e);
            }
        }
        
        return `
            <div class="comment-item">
                <div class="comment-header">
                    <span class="comment-user">${comment.user_name}</span>
                    <div class="comment-meta">
                        <span>${comment.product_name}</span>
                        <span>${comment.comment_time}</span>
                        <span>评分: ${comment.rating}</span>
                        <span class="sentiment-tag ${sentimentClass}">${comment.sentiment_label_cn} (${comment.sentiment_score})</span>
                    </div>
                </div>
                <div class="comment-text">${comment.comment_text}</div>
                ${aspects.length > 0 ? `
                    <div class="comment-aspects">
                        ${aspects.map(a => `<span class="aspect-tag">${a}</span>`).join('')}
                    </div>
                ` : ''}
                ${opinionPairsHtml}
                ${comment.sentiment_label === 'negative' ? `
                    <div style="margin-top: 8px;">
                        <button class="reply-btn" onclick="event.stopPropagation(); openReplyModal(${JSON.stringify(comment).replace(/"/g, '&quot;')})">智能回复</button>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

function renderPagination(currentPage, totalPages) {
    const container = document.getElementById('pagination');
    let html = '';
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    for (let i = 1; i <= Math.min(totalPages, 10); i++) {
        const active = i === currentPage ? 'active' : '';
        html += `<button class="${active}" onclick="loadComments(${i})">${i}</button>`;
    }
    
    if (totalPages > 10) {
        html += '<span>...</span>';
        html += `<button onclick="loadComments(${totalPages})">${totalPages}</button>`;
    }
    
    container.innerHTML = html;
}

function analyzeText() {
    const text = document.getElementById('analyzeInput').value.trim();
    
    if (!text) {
        alert('请输入要分析的评论内容');
        return;
    }
    
    fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
    })
    .then(r => r.json())
    .then(result => {
        const resultDiv = document.getElementById('analyzeResult');
        resultDiv.classList.add('show');
        
        let progressClass = result.label;
        let aspectsHtml = '';
        
        if (result.aspects && result.aspects.length > 0) {
            aspectsHtml = `
                <div class="result-item">
                    <div class="result-label">涉及方面:</div>
                    <div class="result-value">
                        ${result.aspects.map(a => `<span class="aspect-tag">${a}</span>`).join(' ')}
                    </div>
                </div>
            `;
        }
        
        resultDiv.innerHTML = `
            <div class="result-item">
                <div class="result-label">情感分类:</div>
                <div class="result-value">
                    <span class="sentiment-tag ${result.label}">${result.label_cn}</span>
                </div>
            </div>
            <div class="result-item">
                <div class="result-label">情感得分:</div>
                <div class="result-value">${result.score}</div>
                <div class="progress-bar">
                    <div class="progress-fill ${progressClass}" style="width: ${result.score * 100}%"></div>
                </div>
            </div>
            ${aspectsHtml}
        `;
    });
}

function generateNewData() {
    if (confirm('确定要生成新的评论数据吗？这将覆盖现有数据。')) {
        fetch('/api/refresh-data')
            .then(r => r.json())
            .then(result => {
                if (result.success) {
                    alert('数据生成成功！');
                    refreshData();
                    loadAlerts();
                } else {
                    alert('数据生成失败: ' + result.message);
                }
            });
    }
}

function loadProducts() {
    fetch('/api/products')
        .then(r => r.json())
        .then(data => {
            const select = document.getElementById('competitorProduct');
            select.innerHTML = data.products.map(p => `<option value="${p}">${p}</option>`).join('');
            if (data.products.length > 0) {
                currentProduct = data.products[0];
                updateCompetitorComparison();
            }
        });
}

function updateCompetitorComparison() {
    const product = document.getElementById('competitorProduct').value;
    if (!product) return;
    
    const filters = getFilters();
    const queryString = new URLSearchParams({ product, ...filters }).toString();
    
    fetch(`/api/competitor-comparison?${queryString}')
        .then(r => r.json())
        .then(data => {
            updateCompetitorChart(data.comparison);
            updateCompetitorAspectChart(data.aspect_comparison);
        });
}

function updateCompetitorChart(comparison) {
    const products = Object.keys(comparison.products);
    const positiveRates = products.map(p => comparison.products[p].positive_rate);
    const avgScores = products.map(p => comparison.products[p].avg_score);
    
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' }
        },
        legend: {
            data: ['正向率(%)', '平均情感分'],
            top: 0
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: products,
            axisLabel: { rotate: 30 }
        },
        yAxis: [
            {
                type: 'value',
                name: '正向率(%)',
                min: 0,
                max: 100,
                position: 'left'
            },
            {
                type: 'value',
                name: '情感分',
                min: 0,
                max: 1,
                position: 'right'
            }
        ],
        series: [
            {
                name: '正向率(%)',
                type: 'bar',
                data: positiveRates,
                itemStyle: {
                    color: function(params) {
                        return params.dataIndex === 0 ? '#667eea' : '#a5b4fc';
                    }
                },
                label: {
                    show: true,
                    position: 'top',
                    formatter: '{c}%'
                }
            },
            {
                name: '平均情感分',
                type: 'line',
                yAxisIndex: 1,
                data: avgScores,
                smooth: true,
                lineStyle: { color: '#ef4444', width: 3 },
                itemStyle: { color: '#ef4444' }
            }
        ]
    };
    
    competitorChart.setOption(option);
}

function updateCompetitorAspectChart(aspectComparison) {
    const products = new Set();
    for (const aspect in aspectComparison) {
        for (const product in aspectComparison[aspect]) {
            products.add(product);
        }
    }
    
    const productList = Array.from(products);
    const aspectList = ['价格', '质量', '物流', '服务'];
    
    const series = productList.map((product, index) => ({
        name: product,
        type: 'bar',
        data: aspectList.map(aspect => {
            if (aspectComparison[aspect] && aspectComparison[aspect][product]) {
                return aspectComparison[aspect][product].positive_rate;
            }
            return 0;
        }),
        itemStyle: {
            color: ['#667eea', '#764ba2', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'][index]
        }
    }));
    
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        legend: {
            top: 0,
            type: 'scroll'
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: aspectList
        },
        yAxis: {
            type: 'value',
            name: '正向率(%)',
            min: 0,
            max: 100
        },
        series: series
    };
    
    competitorAspectChart.setOption(option);
}

function loadAlerts() {
    fetch('/api/alerts?unread_only=false&limit=20')
        .then(r => r.json())
        .then(data => {
            document.getElementById('alertCount').textContent = data.summary.unread;
            if (data.summary.unread > 0) {
                document.getElementById('alertBadge').classList.add('has-alerts');
            } else {
                document.getElementById('alertBadge').classList.remove('has-alerts');
            }
            renderAlerts(data.alerts);
        });
}

function checkAlerts() {
    fetch('/api/alerts/check', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.new_alerts.length > 0) {
                alert(`检测到 ${data.new_alerts.length} 条新预警！`);
            } else {
                alert('未检测到新预警');
            }
            loadAlerts();
        });
}

function renderAlerts(alerts) {
    const container = document.getElementById('alertList');
    
    if (alerts.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">暂无预警信息</div>';
        return;
    }
    
    container.innerHTML = alerts.map(alert => `
        <div class="alert-item ${alert.severity} ${alert.read ? '' : 'unread'}" onclick="markAlertRead('${alert.id}')">
            <div class="alert-item-header">
                <span class="alert-type">${alert.type_name}</span>
                <span class="alert-severity ${alert.severity}">${alert.severity === 'high' ? '高危' : alert.severity === 'medium' ? '中危' : '低危'}</span>
            </div>
            <div class="alert-message">${alert.message}</div>
            <div class="alert-time">${alert.timestamp}</div>
        </div>
    `).join('');
}

function toggleAlertPanel() {
    const panel = document.getElementById('alertPanel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

function markAlertRead(alertId) {
    fetch('/api/alerts/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_id: alertId })
    }).then(() => loadAlerts());
}

function markAllAlertsRead() {
    fetch('/api/alerts/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mark_all: true })
    }).then(() => loadAlerts());
}

function openReplyModal(comment) {
    currentComment = comment;
    document.getElementById('replyCommentText').textContent = comment.comment_text;
    document.getElementById('replyModal').style.display = 'flex';
    
    generateReplies();
}

function closeReplyModal() {
    document.getElementById('replyModal').style.display = 'none';
    currentComment = null;
}

function generateReplies() {
    if (!currentComment) return;
    
    fetch('/api/generate-reply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment: currentComment })
    }).then(r => r.json())
      .then(data => {
          renderReplyOptions(data.replies);
      });
}

function renderReplyOptions(replies) {
    const container = document.getElementById('replyOptions');
    
    container.innerHTML = replies.map((reply, index) => `
        <div class="reply-option">
            <div class="reply-option-header">
                <span class="reply-style-tag">${reply.style_name}</span>
            </div>
            <div class="reply-content">${reply.content}</div>
            <div class="reply-option-actions">
                <button class="copy-btn" onclick="copyReply('${reply.content.replace(/'/g, "\\'")}')">复制</button>
            </div>
        </div>
    `).join('');
}

function copyReply(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('回复已复制到剪贴板！');
    });
}
