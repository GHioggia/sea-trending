# 发布流程

## 发布模式

### docs/ 目录模式（MVP 默认）

将生成的 HTML 报告复制到项目根目录下的 `docs/` 目录，GitHub Pages 直接从该目录提供服务。

```
docs/
├── index.html              # 指向最新报告
├── 2026-05-09.html         # 当日报告
├── 2026-05-08.html         # 历史报告
├── archive/                # 被覆盖的旧文件备份
│   ├── index_20260509.html
│   └── ...
└── assets/                 # 静态资源（CSS 等）
    └── style.css
```

### gh-pages 分支模式（后续）

将报告提交到独立的 `gh-pages` 分支，主分支不包含生成产物。

## 发布步骤

### 1. 检查前置条件
- `output/reports/{date}.html` 存在
- `output/reports/index.html` 存在

### 2. 备份旧文件
- 如果 `docs/index.html` 已存在，复制到 `docs/archive/index_{date}.html`
- 如果 `docs/{date}.html` 已存在，复制到 `docs/archive/{date}_{timestamp}.html`

### 3. 复制新文件
- 复制 `output/reports/{date}.html` → `docs/{date}.html`
- 复制 `output/reports/index.html` → `docs/index.html`
- 复制 `output/reports/assets/` → `docs/assets/`（如有）

### 4. Git 提交（可选）
- 仅在 `publish.auto_commit: true` 时执行
- 提交信息：`chore: update trend report {date}`
- 不自动 push（需用户确认）

## 注意事项

- 发布前**必须**备份旧文件，防止数据丢失
- `--dry-run` 模式下跳过整个发布流程
- `--publish` 需显式指定才执行发布
- 不指定 `--publish` 也不指定 `--dry-run` 时，只生成报告不发布
- Git 操作失败时报告警告但不中断（HTML 文件已在 docs/ 中）
