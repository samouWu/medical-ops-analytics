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
