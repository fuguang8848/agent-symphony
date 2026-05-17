---
name: search
version: 1.0.0
family: agent-symphony
role: information-retrieval
description: 搜索技能 - 多引擎搜索、爬虫、过滤、排序
---

# search 搜索技能

> Agent Symphony 技能交响乐的信息获取中心

## 角色定位

search 是技能交响乐的**信息获取中心**，负责：
- 多引擎搜索
- 深度爬虫
- 智能过滤
- 结果排序
- 自动缓存

## 支持的搜索引擎

| 引擎 | 特点 | 适用场景 |
|------|------|----------|
| **Tavily** | AI 原生，结果 LLM-ready | 通用搜索 |
| **Firecrawl** | 权威来源，全内容爬取 | 深度内容 |
| **Brave** | 独立索引，无 SEO 垃圾 | 干净结果 |
| **Exa** | 语义搜索，理解意图 | 概念搜索 |
| **Perplexity** | LLM 答案 + 引用 | 直接答案 |

## 核心能力

| 能力 | 说明 |
|------|------|
| `search.execute` | 执行搜索 |
| `search.crawl` | 深度爬取 |
| `search.filter` | 过滤结果 |
| `search.rank` | 排序结果 |
| `search.cache` | 缓存管理 |

## 搜索流程

```
用户/思考技能发起查询
    ↓
[预处理] 理解查询意图
    ↓
[引擎选择] Tavily? Brave? Exa?
    ↓
[执行搜索] 并行多引擎
    ↓
[过滤] 去重 → 质量 → 相关性 → 安全
    ↓
[提取] 正文提取，去除噪音
    ↓
[排序] 多维评分
    ↓
[缓存] 存入缓存
    ↓
[存储] 有价值结果存入 memory
```

## 过滤器

| 过滤器 | 说明 |
|--------|------|
| `relevance` | 相关性阈值 (0-1) |
| `freshness` | 时效性要求 |
| `authority` | 权威性阈值 (0-1) |
| `languages` | 语言过滤 |

## 排序权重

| 维度 | 默认权重 |
|------|----------|
| 相关性 | 40% |
| 时效性 | 30% |
| 权威性 | 20% |
| 综合评分 | 10% |

## 标准接口

```python
from agent_symphony.skills.search import get_skill_instance

# 获取技能实例
search = get_skill_instance()

# 执行搜索
search.execute("search", {
    "query": "最新的 AI Agent 框架",
    "engines": ["tavily", "exa"],
    "max_results": 10,
    "filters": {
        "relevance": 0.7,
        "freshness": "30d",
        "languages": ["zh", "en"]
    }
})

# 深度爬取
search.execute("crawl", {
    "url": "https://example.com/article"
})

# 过滤结果
search.query("search.filter", {
    "results": [...],
    "filters": {"relevance": 0.8}
})

# 排序结果
search.query("search.rank", {
    "results": [...],
    "criteria": {
        "relevance_weight": 0.5,
        "freshness_weight": 0.3,
        "authority_weight": 0.2
    }
})

# 获取缓存
search.query("search.cache", {
    "query": "AI Agent"
})
```

## 与其他技能的联动

- `thinking` 调用 `search.execute()` 获取信息
- `search` 自动将结果存入 `memory`
- `search` 利用 `context` 共享上下文

---

_Agent Symphony 技能交响乐_
