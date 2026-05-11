# 完整工作流

## 流程总览

```
┌─────────┐    ┌───────────┐    ┌──────────┐    ┌────────┐    ┌─────────┐    ┌───────────┐
│  配置    │───>│  抓取     │───>│  规范化  │───>│  分类  │───>│  渲染   │───>│  发布     │
│  解析    │    │  Fetch    │    │  Normalize│   │Classify│    │  Report │    │  Publish  │
└─────────┘    └───────────┘    └──────────┘    └────────┘    └─────────┘    └───────────┘
                                                                                   │
                                                                              ┌────┴─────┐
                                                                              │  播报    │
                                                                              │Broadcast │
                                                                              └──────────┘
```

## 阶段详解

### 阶段 1：配置解析

- 解析命令行参数（`--date`, `--country`, `--sample`, `--dry-run`, `--publish`）
- 加载 `src/config.yaml`（如有）
- 确定启用的 provider 列表
- 初始化日志（写入 `output/logs/{date}.log`）
- 创建输出目录结构

### 阶段 2：数据抓取（Fetch）

- 遍历目标国家（PH, ID, TH）
- 对每个国家，遍历已启用的 provider
- 每个 provider 独立执行，单个失败不阻断
- `--sample` 模式下只调用 SampleProvider
- 保存原始响应到 `output/raw/{date}/{source}_{country}.json`
- 记录每个 provider 的成功/失败状态

### 阶段 3：数据规范化（Normalize）

- 将各 provider 的原始数据统一转换为 `TrendItem` 列表
- 去重（同一关键词来自多个源时合并）
- 保存到 `output/normalized/{date}.json`

### 阶段 4：分类（Classify）

- 对每个 TrendItem 执行分类，填充 `category` 字段
- 分类规则：
  1. `gaming` — 匹配游戏关键词库
  2. `news` — 匹配新闻/民生关键词或来自新闻源
  3. `viral` — 匹配热梗/传播关键词
  4. `trending` — 默认兜底分类
- 分类结果写回 normalized 数据

### 阶段 5：渲染（Report）

- 加载 Jinja2 模板 `templates/daily.html`
- 按国家 → 分类组织数据
- 渲染每日报告 `{date}.html`
- 渲染首页 `index.html`（指向最新报告）
- 保存到 `output/reports/`

### 阶段 6：发布（Publish）

- 仅在 `--publish` 模式下执行
- 备份旧文件到 `archive/`
- 复制报告到 `docs/` 目录
- 如配置了 git，自动 commit

### 阶段 7：播报（Broadcast）

- 从分类后的数据生成纯文本摘要
- 包含各国 Top 热搜、游戏相关高亮、报告链接
- 输出到 stdout
- 保存到 `output/broadcast/{date}.txt`

## 错误处理策略

| 场景 | 处理方式 |
|------|----------|
| 单个 provider HTTP 错误 | 记录日志，跳过该 provider，继续其他源 |
| 所有 provider 均失败 | 报告错误，退出码 1，不生成空报告 |
| HTML 模板渲染错误 | 报告错误，退出码 1 |
| 发布目录不存在 | 自动创建 |
| Git commit 失败 | 报告警告，HTML 已生成但未提交 |

## 幂等性

- 同一日期多次运行会覆盖当日产物
- 原始数据按 `{source}_{country}.json` 命名，同源同国覆盖
- 发布前备份确保旧数据不丢失
