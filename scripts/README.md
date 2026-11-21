# scripts · 数据构建与验证脚本

所有脚本均从项目根目录运行，默认使用 `.venv` 与项目内 `data/` 路径。

| 脚本 | 用途 |
|---|---|
| `build_supplemental_12m.py` | 生成 12 个自然月独立模拟数据并完成 ETL/DWS/ADS 与验证 |
| `check_reconciliation.py` | 源文件 → DWD → DWS → ADS 全链路对账（26 项） |
| `check_deliverables.py` | 交付物完整性、指标数量、图表与测试证据检查 |
| `check_query_plans.py` | 查询计划与慢 SQL 检查 |
| `security_check.py` | HTTP 安全冒烟（鉴权、越权、输入校验等 13 项） |
| `load_test.py` | 单机并发冒烟（默认 8 并发 120 请求） |
| `export_init_data.py` | 从代码常量导出 `data/init/` 快照与 manifest |
| `start_backend.sh` | Linux/macOS 启动后端 |
| `start_frontend.sh` | Linux/macOS 启动前端 |

## 常用命令

```bash
.venv/Scripts/python.exe scripts/check_reconciliation.py
.venv/Scripts/python.exe scripts/check_deliverables.py
.venv/Scripts/python.exe scripts/security_check.py
.venv/Scripts/python.exe scripts/load_test.py --workers 8 --requests 120
```

对账、安全、压测与查询计划报告写入 `data/derived/`，该目录不提交；脚本本身可复现实验。

## 推荐执行顺序

1. `build_supplemental_12m.py`（仅在需要 12 个月独立库时）
2. `export_init_data.py`（修改科室、指标或规则后重算快照）
3. `check_reconciliation.py`（确认源到 ADS 数值一致）
4. `security_check.py`（确认鉴权、越权与输入校验）
5. `check_query_plans.py`（检查慢 SQL 与索引使用）
6. `load_test.py`（单机并发冒烟）
7. `check_deliverables.py`（交付物、文档链接与测试证据总检）

第 3—7 步依赖后端已完成 ETL；压测与 E2E 还需要后端 8765、前端 5173 已启动。

所有报告写入 `data/derived/`，重复执行会覆盖同名文件。
