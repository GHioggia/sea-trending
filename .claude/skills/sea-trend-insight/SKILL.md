# sea-trend-insight

东南亚每日趋势抓取与游戏策划洞察报告生成。

## 何时使用

用户要求以下任一操作时触发：
- 生成东南亚趋势报告 / 抓取 SEA 趋势数据
- 菲律宾 / 印尼 / 泰国 玩家洞察、游戏市场趋势
- 发布趋势报告到 GitHub Pages
- 生成趋势播报文本（飞书/企微）

## 正确命令（必须使用）

```bash
# 模块入口（非 src/main.py）
python -m sea_trend_insight <subcommand> [options]
```

### 子命令

| 命令 | 说明 |
|------|------|
| `run` | 完整流程：fetch → classify → score → report → publish → broadcast |
| `report` | 只生成报告，不发布（等同于 run --dry-run） |
| `broadcast` | 基于已有 report.json 生成播报文本 |
| `publish` | 同步 docs/、git commit、可选 push |

### 常用组合

```bash
# 离线 sample 完整流程（不联网，写到 public/）
python -m sea_trend_insight run --date 2026-05-09 --sample

# 只生成报告，不写 public/
python -m sea_trend_insight run --date 2026-05-09 --sample --dry-run

# 查看发布计划（不改 git）
python -m sea_trend_insight publish --date 2026-05-09 --dry-run

# 提交到 docs/ 并推送
python -m sea_trend_insight publish --date 2026-05-09 --commit --push

# 实时抓取（需网络和代理）
python -m sea_trend_insight run --date 2026-05-09 --live
```

## 输出产物

| 产物 | 路径 |
|------|------|
| 原始数据 | `data/raw/{date}/{source}_{country}.json` |
| 规范化数据 | `data/normalized/{date}/items.json` |
| 报告 JSON | `reports/{date}/report.json` |
| 播报文本 | `reports/{date}/broadcast.md` |
| 发布日志 | `reports/{date}/publish-log.json` |
| HTML 报告（本地） | `public/{date}.html`, `public/index.html` |
| HTML 报告（Pages） | `docs/{date}.html`, `docs/index.html` |
| 旧页面备份 | `archive/index_{date}.html` |
| 运行日志 | `logs/{date}-run.log`, `logs/{date}-run.json` |

## 配置文件

`config/default.yaml`，关键字段：

```yaml
publish:
  mode: docs                # docs 目录模式（唯一支持的模式）
  pages_base_url: https://GHioggia.github.io/sea-trending/
  auto_push: false          # 必须 --push 才推送
  backup_before_publish: true
```

## Claude 执行步骤

1. 确认工作目录为项目根目录（含 `pyproject.toml`）
2. 依赖已安装：`.venv/bin/python` 或系统 `python -m sea_trend_insight`
3. 根据用户意图选命令执行
4. 执行后确认：
   - 播报文本已输出到 stdout
   - `reports/{date}/` 下有 `report.json` 和 `broadcast.md`
   - 如要发布：检查 `docs/` 已更新

## 强制约束

- **禁止绕过安全措施**：不得绕过登录、验证码，不使用代理池或指纹浏览器
- **单一代理**：proxy 参数是单个企业代理（非代理池），通过 `SEA_TREND_PROXY` 环境变量或 config 配置
- **降级而非中断**：provider 失败时跳过并记录，不中断流程
- **发布前备份**：publish 前自动备份旧 docs/index.html 到 archive/
- **默认 dry-run**：`publish` 不带 `--commit` 时只打印计划，不改 git
- **明确 push**：必须显式传 `--push`，绝不默认推送

## 验收命令

```bash
# 步骤 1：sample 完整流程
python -m sea_trend_insight run --date 2026-05-09 --sample

# 步骤 2：检查 publish 计划
python -m sea_trend_insight publish --date 2026-05-09 --dry-run

# 步骤 3：跑测试
python -m pytest tests/ -v
```

通过标准：41 tests passed，`reports/2026-05-09/broadcast.md` 存在，URL 无双斜杠。
