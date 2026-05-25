# 音乐推荐系统 (Music Recommendation System) v2.0

基于用户听歌历史和歌曲属性的混合音乐推荐系统，支持多模态特征、实时反馈、智能歌单生成。

## 技术栈

- **Python 3.9+**
- **FastAPI** - Web API框架
- **Surprise** - 协同过滤算法库
- **Scikit-learn** - 内容过滤/多模态特征处理
- **Redis** - 缓存层（可选，带内存回退）
- **Pandas/Numpy** - 数据处理

## 功能特性 v2.0

### 1. 混合推荐算法
- **协同过滤 (Collaborative Filtering)**: 基于SVD矩阵分解
- **内容过滤 (Content-based Filtering)**: 基于歌曲属性（风格、歌手、年份、流行度）的余弦相似度
- **动态权重**: 根据用户活跃度自动调整权重（新用户80%内容过滤，活跃用户80%协同过滤）

### 2. 多模态推荐 (Multimodal) ✨ NEW
- **专辑封面视觉特征**: 模拟CNN提取图像特征（色彩、风格、构图）
- **歌词文本特征**: TF-IDF向量化歌词主题（情感、主题词）
- **多模态融合**: 图像30% + 文本30% + 内容属性40%
- **推荐理由扩展**: 视觉风格匹配、歌词主题相似等

### 3. 实时反馈更新 ✨ NEW
- **5种动作类型**: like, play_complete, play_partial, skip, dislike
- **权重系统**: like(+2.0) > play_complete(+1.0) > play_partial(+0.3) > skip(-1.0) > dislike(-2.0)
- **跳过惩罚机制**: 累计跳过某风格会降低该风格推荐权重
- **实时生效**: 反馈后立即失效缓存，下次推荐自动调整

### 4. 智能歌单生成 ✨ NEW
- **8种预设主题**: Chill Vibes, Workout Hype, Late Night, Retro Classics, Party Mix, Focus Flow, Mood Booster, Discovery Mix
- **自动主题检测**: 根据推荐结果风格自动匹配歌单主题
- **歌单质量评估**: 多样性分数（风格/歌手/年代）、连贯性分数
- **Smart Mix**: 50%喜好 + 30%相似风格 + 20%新鲜发现
- **多样性优化**: 自动避免同一歌手/风格过于集中

### 5. Explore/Exploit 平衡
- **Epsilon-Greedy Bandit**: 以ε概率探索新音乐，1-ε概率利用已知偏好
- **探索率指数衰减**: 新用户10%探索率，活跃用户最低2%
- **Thompson Sampling**: Beta分布采样
- **UCB (Upper Confidence Bound)**: 置信区间上界算法
- **Contextual Bandit**: 上下文感知的多臂老虎机

### 6. 推荐理由生成
- 基于用户喜欢的歌手/风格/年代
- 基于相似用户行为
- 基于热门程度
- 基于多模态特征匹配
- 随机模板选择，避免重复

### 7. 缓存层
- Redis缓存（可选）
- 内存缓存回退
- 推荐结果、用户画像、Bandit状态缓存
- 反馈后自动失效缓存

## 项目结构

```
.
├── api/
│   ├── __init__.py
│   └── main.py              # FastAPI接口
├── data/
│   ├── __init__.py
│   ├── models.py            # 数据模型定义
│   └── data_generator.py    # 模拟数据生成器
├── recommenders/
│   ├── __init__.py
│   ├── collaborative_filtering.py  # 协同过滤
│   ├── content_filtering.py        # 内容过滤
│   ├── hybrid_recommender.py       # 混合推荐引擎
│   ├── bandit.py                   # Bandit算法
│   └── cache.py                    # 缓存层
├── config.py                # 配置文件
├── main.py                  # 启动入口
├── requirements.txt         # 依赖包
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

或使用uvicorn直接运行:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 访问API文档

打开浏览器访问: http://localhost:8000/docs

## API接口

### 推荐接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/recommendations/{user_id}` | 获取用户个性化推荐 |
| GET | `/api/recommendations/similar/{song_id}` | 获取相似歌曲推荐 |
| GET | `/api/recommendations/explore/{user_id}` | 获取探索性推荐 |
| POST | `/api/feedback/{user_id}/{song_id}` | 提交用户反馈 |

### 实时反馈接口 ✨ NEW

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/feedback/{user_id}/{song_id}?action={type}` | 提交用户行为反馈 |
| GET | `/api/users/{user_id}/skip-stats` | 获取用户跳过统计 |

**反馈类型 (action):**
- `like` - 收藏/喜欢 (+2.0)
- `play_complete` - 完整播放 (+1.0)
- `play_partial` - 部分播放 (+0.3)
- `skip` - 跳过 (-1.0)
- `dislike` - 不喜欢 (-2.0)

### 歌单接口 ✨ NEW

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/playlists/themes` | 获取所有歌单主题 |
| POST | `/api/playlists/generate/{user_id}` | 生成主题歌单 |
| POST | `/api/playlists/smart-mix/{user_id}` | 生成智能混合歌单 |

**歌单主题:**
- `chill_vibes` - 放松轻音乐
- `workout_hype` - 运动健身
- `late_night` - 深夜抒情
- `retro_classics` - 经典老歌
- `party_mix` - 派对狂欢
- `focus_flow` - 专注学习
- `mood_booster` - 心情提升
- `discovery` - 探索发现

### 数据接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/songs` | 获取歌曲列表 |
| GET | `/api/songs/{song_id}` | 获取歌曲详情 |
| GET | `/api/users` | 获取用户列表 |
| GET | `/api/users/{user_id}` | 获取用户详情 |
| GET | `/api/users/{user_id}/profile` | 用户画像（活跃度/权重） |
| GET | `/api/users/{user_id}/preferences` | 用户偏好分析 |
| GET | `/api/stats` | 获取系统统计信息 |

### 管理接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/refresh` | 重新训练所有模型 |

## 使用示例

### 获取推荐

```bash
curl "http://localhost:8000/api/recommendations/u_0001?top_n=10"
```

响应示例:
```json
{
  "user_id": "u_0001",
  "recommendations": [
    {
      "song_id": "s_0042",
      "title": "Midnight Dreams 42",
      "artist": "Taylor Swift",
      "genre": "pop",
      "year": 2020,
      "score": 0.89,
      "reason": "属于您喜欢的pop风格；与您兴趣相似的用户也喜欢这首歌",
      "source": "hybrid"
    }
  ],
  "timestamp": "2024-01-15T10:30:00"
}
```

### 提交反馈

```bash
curl -X POST "http://localhost:8000/api/feedback/u_0001/s_0042?reward=5"
```

## 配置说明

在 `config.py` 或 `.env` 文件中配置:

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `REDIS_HOST` | localhost | Redis主机 |
| `REDIS_PORT` | 6379 | Redis端口 |
| `CF_WEIGHT` | 0.5 | 协同过滤权重 |
| `CONTENT_WEIGHT` | 0.5 | 内容过滤权重（基准值，实际为动态调整） |
| `BANDIT_EPSILON` | 0.1 | Epsilon-Greedy探索概率（基准值，实际为指数衰减） |
| `CACHE_TTL` | 3600 | 缓存过期时间(秒) |
| `NUM_RECOMMENDATIONS` | 10 | 默认推荐数量 |

## 动态权重调整机制

### 活跃度分数计算
用户活跃度分数基于：
- 总播放次数（权重60%）
- 听过的不同歌曲数量（权重40%）

### 动态权重公式
```
activity_score = 0 ~ 1
cf_weight = 0.2 + activity_score * 0.6
content_weight = 0.8 - activity_score * 0.6
```

**效果：**
- 新用户（activity_score ≈ 0）: 20% 协同过滤 + 80% 内容过滤
- 中等用户（activity_score ≈ 0.5）: 50% 协同过滤 + 50% 内容过滤
- 活跃用户（activity_score ≈ 1）: 80% 协同过滤 + 20% 内容过滤

## 探索率指数衰减

### 衰减公式
```
epsilon = initial_epsilon * exp(-decay_rate * activity_score * 10)
epsilon = max(epsilon, 0.02)  # 最低2%探索率
```

**效果：**
- 新用户：10% 探索率
- 活跃用户：2% 探索率（保底）

## 多维度推荐理由模板

推荐理由从以下维度随机生成：

| 维度 | 触发条件 | 模板示例 |
|------|----------|----------|
| 风格匹配 | 歌曲风格在用户Top 3中 | "您喜爱的pop曲风", "属于您常听的rock类型" |
| 年代匹配 | 歌曲年代在用户偏好中 | "2000年代经典", "来自1990年代的好歌" |
| 歌手匹配 | 用户最爱的歌手（≥3首） | "您最爱的歌手Taylor Swift", "来自Coldplay" |
| 相似歌手 | 用户常听的相似歌手 | "与您喜爱的Ed Sheeran也很对味" |
| 协同过滤 | CF分数 > 0.75 | "与您兴趣相投的用户也在听", "同好用户的选择" |
| 热门度 | 流行度 > 0.85 | "近期热门", "排行榜热门歌曲" |
| 新歌 | 该歌手最新作品 | "Taylor Swift最新作品" |

## 算法说明

### 协同过滤 (Collaborative Filtering)

使用SVD (Singular Value Decomposition) 矩阵分解算法:
- 将用户-物品评分矩阵分解为用户因子和物品因子
- 通过因子点积预测评分
- 支持RMSE/MAE评估指标

### 内容过滤 (Content-based Filtering)

特征工程:
- 风格: One-Hot编码
- 歌手: TF-IDF向量化
- 年份: 标准化
- 流行度: 原始值

相似度计算:
- 余弦相似度 (Cosine Similarity)

### Bandit算法

**Epsilon-Greedy**:
- 以ε概率随机选择（探索）
- 以1-ε概率选择平均奖励最高的（利用）

**Thompson Sampling**:
- 每个臂维护Beta(alpha+successes, beta+failures)分布
- 采样后选择最大值

**UCB**:
- 选择均值 + C * sqrt(ln(N)/n) 最大的臂
- C为探索参数，N为总次数，n为臂被选择次数

## 推荐理由字段说明

- **source**: 推荐来源
  - `hybrid`: 混合推荐
  - `collaborative`: 协同过滤
  - `content`: 内容过滤
  - `explore`: 探索推荐

- **score**: 归一化推荐分数 [0, 1]

## 性能优化

1. **模型缓存**: 训练好的模型保存到磁盘
2. **推荐缓存**: Redis缓存用户推荐结果
3. **批量计算**: 相似度矩阵预计算
4. **增量更新**: Bandit算法支持在线学习

## 扩展建议

1. 添加深度学习推荐模型（Neural Collaborative Filtering）
2. 集成实时用户行为流（Kafka）
3. 添加A/B测试框架
4. 支持更多特征（音频特征、歌词分析）
5. 添加推荐解释可视化

## License

MIT
