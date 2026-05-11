# 验收标准

## 快速验收（Sample + Dry-run）

执行：
```bash
python src/main.py --sample --dry-run
```

### 必须通过

- [ ] 退出码为 0
- [ ] `output/raw/{date}/` 下有 sample 数据文件
- [ ] `output/normalized/{date}.json` 存在且为合法 JSON
- [ ] JSON 中包含 PH、ID、TH 三国数据
- [ ] 每条 TrendItem 有 keyword、country、source、category 字段
- [ ] category 值为 `gaming` / `news` / `viral` / `trending` 之一
- [ ] `output/reports/{date}.html` 存在且为合法 HTML
- [ ] `output/reports/index.html` 存在
- [ ] HTML 报告中按国家分区展示
- [ ] HTML 报告中按分类分组展示
- [ ] stdout 输出了播报文本
- [ ] `output/logs/{date}.log` 存在且记录了运行过程
- [ ] 未发起任何外部 HTTP 请求

### 报告内容检查

- [ ] 报告标题包含日期
- [ ] 每个国家至少有 3 条趋势数据
- [ ] 游戏相关分类下有数据（sample 数据中包含游戏关键词）
- [ ] 报告在浏览器中可正常打开和阅读
- [ ] 移动端视口下布局不溢出

### 播报文本检查

- [ ] 包含日期
- [ ] 包含各国热搜 Top 关键词
- [ ] 包含游戏相关趋势提示
- [ ] 文本可直接复制到聊天工具

## 完整验收（在线模式）

执行：
```bash
python src/main.py --dry-run
```

### 必须通过

- [ ] 至少 1 个在线 provider 成功返回数据
- [ ] 失败的 provider 在日志中有明确记录
- [ ] 生成的报告包含真实趋势数据
- [ ] 数据时效性：报告日期与数据日期一致

## 发布验收

执行：
```bash
python src/main.py --sample --publish
```

### 必须通过

- [ ] `docs/{date}.html` 存在
- [ ] `docs/index.html` 存在且指向当日报告
- [ ] 如果旧文件存在，`docs/archive/` 下有备份
- [ ] 发布后报告可通过 GitHub Pages URL 访问

## 降级场景验收

- [ ] 断网时 `--sample` 模式正常工作
- [ ] 单个 provider 超时（模拟）时其他 provider 不受影响
- [ ] 所有在线 provider 均失败时，报告明确错误信息并退出码 1
- [ ] provider 返回空数据时不会渲染出空白区块
