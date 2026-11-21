# sql · 数仓参考 DDL

按 ODS → DWD → DWS → ADS 分层提供 SQLite 建表脚本，与运行时 `backend/app/core/database.py` 的表结构保持一致。

| 目录 | 文件 | 内容 |
|---|---|---|
| `ods/` | `schema.sql` | 六源贴源表、批次记录、原始行 JSON |
| `dim/` | `schema.sql` | 科室、病种、费别、日期、指标定义、质量规则 |
| `dwd/` | `schema.sql` | 标准化明细、统一就诊宽表、患者散列标识 |
| `dws/` | `schema.sql` | 八张主题日汇总、公共科室日汇总 |
| `ads/` | `schema.sql` | 指标结果表（日/周/月 × 科室）、质量告警表 |

运行时以 `database.py` 中常量与 `CREATE TABLE IF NOT EXISTS` 为准；本目录是阅读与评审用的参考实现。修改表结构时需同步两处并通过 `backend/tests/test_schema.py`。

## 各层主要表

| 层 | 代表表 | 说明 |
|---|---|---|
| ODS | `ods_his_outpatient` 等 6 张 | 贴源行、批次号、原始 JSON |
| DIM | `dim_department`、`dim_disease`、`dim_fee_type`、`dim_date` | 科室、病种、费别与日期维 |
| DWD | `dwd_outpatient_visit`、`dwd_inpatient_stay`、`dwd_charge_detail`、`dwd_emr_record`、`dwd_lis_report`、`dwd_finance_day` | 标准化明细与统一就诊宽表 |
| DWS | `dws_dept_day` 及 8 张主题表 | 门诊、住院、收入、药品、耗材、病种、资源、服务 |
| ADS | `ads_metric_result`、`quality_alert` | 40 项指标日/周/月结果、质量告警 |

`ads_metric_result` 的主键是「指标 × 粒度 × 统计日期 × 科室」，`dept_code='ALL'` 表示全院；回刷按完整日/周/月桶删除后重算。
