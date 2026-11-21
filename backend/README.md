# backend · 后端与数据工程

FastAPI 服务、六源 ETL、四层数仓建模、统一指标服务、数据质量与智能分析接口都在这里。

## 目录结构

```text
app/
  api/           登录、看板、主题分析、指标、报表、AI、质量、系统管理接口
  core/          配置、SQLite 连接与建表、JWT/RBAC、审计
  services/      指标计算（metrics.py）、主题分析（analytics.py）、报告、知识库
  llm/           DeepSeek / Kimi 客户端与本地规则回退
etl/
  jobs/          pipeline.py（六源接入与数仓重建）、ads_refresh.py
  quality/       质量规则与告警
  evaluation/    50 问受控问数评测
tests/           39 项后端测试
requirements.txt
```

## 本地启动

```bash
cd backend
PYTHONPATH=. python -m etl.jobs.pipeline
PYTHONPATH=. python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

首次启动前必须执行 ETL；数据库默认生成在 `data/derived/medical_ops.db`，数据库文件不入库。

接口文档：`http://127.0.0.1:8765/docs`。

## 设计要点

- **单一指标口径**：`app/services/analytics.py::metric_summary` 是所有页面、报表、问数和 ADS 的共同计算入口。
- **数仓分层**：ODS 保留原始行与批次，DWD 标准化并生成 `patient_key`，DWS 按科室日汇总，ADS 预落 40 项指标 × 日/周/月。
- **严格数据边界**：缺字段指标标记为不可算并返回明确错误，不用 0 或模型补造。
- **智能分析安全**：自然语言问数走指标白名单与参数化查询；LLM 只做意图解析与报告摘要，不直接执行任意 SQL。
- **审计与权限**：JWT + 角色 + 科室范围；登录、查询、导出、导入、回刷等关键操作写入审计表。

## 测试

```bash
PYTHONPATH=. python -m pytest
```

当前基线：39 项通过、覆盖率 87.51%。覆盖率报告写入运行时目录，不提交。

## 核心数据表

| 表 | 当前行数 | 说明 |
|---|---:|---|
| `dwd_outpatient_visit` | 9,000 | 门诊就诊明细，含号别、费用、科室与日期 |
| `dwd_inpatient_stay` | 1,500 | 住院就诊明细，含出入院、床日、病种与药耗 |
| `dwd_charge_detail` | 44,078 | 收费明细，支撑药/耗结构与费别分析 |
| `dwd_emr_record` | 1,500 | 病历记录，用于病历覆盖率与病种关联 |
| `dwd_lis_report` | 2,934 | 检验报告，用于异常率与检验覆盖率 |
| `dwd_finance_day` | 910 | 财务日汇总，用于质量校验 |
| `dws_dept_day` | 910 | 科室日汇总，公共指标的事实来源 |
| `ads_metric_result` | 47,520 | 40 项指标 × 日/周/月 × 科室 |

表结构变更必须同步 `sql/*/schema.sql`，并通过 `tests/test_schema.py` 的参考 DDL 一致性检查。
