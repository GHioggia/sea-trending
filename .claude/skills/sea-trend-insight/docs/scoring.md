# 评分规则 — Scoring Rules

sea-trend-insight 对每条趋势数据计算 4 个维度的评分，所有分数范围 0.0 ~ 1.0。

## 1. relevance_score（相关性）

衡量该趋势在当地的影响力和数据源质量。

**计算公式**:
```
raw_normalized = min(raw_score / raw_score_max, 1.0)
source_mult = source_weights[source]
relevance = raw_normalized * 0.6 + source_mult * 0.4
```

**source_weights（数据源权重）**:

| 数据源 | 权重 | 理由 |
|--------|------|------|
| google_trends | 1.0 | 搜索量直接反映关注度 |
| google_news | 0.9 | 新闻覆盖面广 |
| gdelt | 0.8 | 全球事件数据库 |
| google_play | 0.8 | 应用商店排名 |
| trends24 | 0.7 | Twitter 趋势 |
| getdaytrends | 0.7 | 多平台趋势聚合 |
| appbrain | 0.7 | Android 生态 |
| appfigures | 0.7 | 应用商店数据 |
| kworb_youtube | 0.6 | YouTube 观看量 |
| sample | 0.5 | 离线测试数据 |

**raw_score_max**: 500,000（用于归一化原始分数）

## 2. virality_score（传播力）

衡量该趋势的病毒传播潜力。

**计算公式**:
```
base = platform_weight * 0.3
if viral_keyword_match: base += 0.3
if raw_score >= high_score_threshold: base += high_score_boost * ratio
if multi_source: base += 0.1 * min(source_count, 3)
```

**platform_weights**:
- tiktok: 1.0 | twitter: 0.9 | youtube: 0.8 | google: 0.6 | android: 0.4

**参数**:
- viral_keyword_boost: 0.3（匹配 challenge/meme/viral 等关键词）
- high_score_threshold: 100,000
- high_score_boost: 0.2

## 3. game_design_value_score（游戏设计价值）

衡量该趋势对游戏策划的参考价值。

**计算公式**:
```
base = 0.0
if category == "gaming": base += 0.6
if gaming_keyword_match: base += 0.2
if cultural_keyword_match: base += 0.15
if viral_mechanic_match: base += 0.1
```

**cultural_keywords**: festival, holiday, tradition, food, fashion, music, dance, cosplay, ramadan, eid, songkran, sinulog 等

**viral_mechanic_keywords**: challenge, meme, trend, viral, dance, mukbang, unboxing

## 4. risk_score（风险评分）

衡量在游戏中引用该趋势的风险。

**计算方式**:
- 匹配 sensitive_keywords（death, suicide, terror, drug 等）→ risk = 0.7
- 匹配 controversy_keywords（scandal, boycott, fraud 等）→ risk = 0.4
- 取最高值

## 综合排序分

用于 top items 排序的综合分：
```
composite = relevance * 0.3 + virality * 0.2 + game_design_value * 0.4 - risk * 0.1
```

## 分类规则

分类优先级（改进版）：

1. **来源直分类**：google_play / appbrain / appfigures → gaming
2. **强游戏关键词**：mlbb, genshin, valorant 等 → gaming（无论其他匹配）
3. **新闻源优先**：gdelt / google_news 来源的数据，优先匹配 news 关键词
4. **弱游戏关键词 + 无新闻上下文**：\bgame\b 等 → gaming
5. **新闻关键词**：typhoon, election 等 → news
6. **病毒关键词**：meme, viral 等 → viral
7. **兜底**：trending

## 去重规则

按优先级匹配：
1. URL 相同（去掉 query string 和 fragment 比较）
2. keyword 完全相同（大小写无关）
3. title 相似度 ≥ 0.7（SequenceMatcher）

去重时保留 score 最高的 item。

## Debug 字段

每个 ScoredItem 包含：
- `scores.debug`：四个维度的评分明细
- `classify_debug`：分类决策原因

所有评分权重可在 `config/default.yaml` 的 `scoring` 和 `analysis` 节点配置。
