# 医疗运营数据主题分析平台

基于 FastAPI、SQLite、Vue 3 与 ECharts 的医疗运营教学项目。平台将六份模拟 CSV 经 ODS/DWD/DWS/ADS 分层处理，提供运营看板、指标查询、多维报表、智能问数、数据质量与审计功能。

> **使用边界**：本项目仅用于课程教学与模拟数据分析，未达到生产验收标准。39项指标中30项可计算、9项因缺少源字段不可计算；床位与人力来自教学配置；DRG/DIP相关结果为估算，不是医保官方分组或绩效结论。本项目没有百万并发或生产级性能验证。

## 功能与技术栈

- 后端：FastAPI、Pydantic、PyJWT、SQLite（WAL模式）、httpx。
- ETL：CSV/XLSX/XLSM读取、字段与格式校验、批次记录、增量过滤、失败重试、幂等写入、质量规则、八张主题DWS集市和DWD统一明细宽表。
- 指标：39项目录、30项口径可算（当前可查29项，K25缺上年同期）；全部30项在ADS预计算日/周/月结果，支持按日期区间回刷。
- 前端：Vue 3、Vue Router、axios、ECharts、Vite；5个通用图表组件，支持科室下钻、日/周/月粒度、同比/环比。
- 智能分析：默认 DeepSeek，可切换 Kimi；受控指标问数、指标知识问答和安全只读NL2SQL接口，未配置Key时明确回退。
- 系统管理：用户、角色、数据源和ETL任务管理，支持新增、编辑、删除、连接测试和任务执行。
- 安全基础：PBKDF2密码散列、JWT、角色权限、科室数据范围、全量GET查询审计、Trace ID和SQL白名单校验。

## 目录

```text
backend/                 FastAPI、ETL、指标服务与后端测试
frontend/                Vue 3 + ECharts 前端与前端测试
data/mock_his/           五份HIS/EMR/LIS模拟CSV
data/files/              财务模拟CSV
data/init/               维度、指标与质量规则初始化快照
data/supplemental_12m/   12个月附加模拟数据与独立数仓（不进入默认主题）
data/derived/            默认SQLite与上传临时目录（运行时生成，不提交）
sql/                     SQLite五层参考DDL
deploy/                  前后端镜像、Nginx与Compose
scripts/                 Linux/macOS启动脚本
docs/                    项目、指标、部署、测试、进度与数据字典
```

## 快速启动

### 1. 准备环境

建议使用 Python 3.11+ 与 Node.js 20+。以下命令均从项目根目录开始，后端和前端需在两个终端分别运行。

### 2. 安装并执行ETL

**Linux / macOS / Git Bash（Linux风格虚拟环境）：**

```bash
python -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/python -m etl.jobs.pipeline
```

**Windows PowerShell：**

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m etl.jobs.pipeline
```

**Windows Git Bash（当前Windows虚拟环境布局）：**

```bash
PYTHONPATH=backend .venv/Scripts/python.exe -m etl.jobs.pipeline
```

ETL依次读取 `his_outpatient`、`his_inpatient`、`his_charge`、`emr_record`、`lis_report` 和 `finance_excel`，然后重建DWS与ADS。默认数据库为 `data/derived/medical_ops.db`；可通过 `MEDICAL_DB_PATH` 指定其他SQLite文件路径。重复导入以业务主键幂等替换，但源文件中已消失的历史记录不会被自动删除。

### 3. 启动后端

**Linux / macOS / Git Bash：**

```bash
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

**Windows PowerShell：**

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

也可在激活虚拟环境后进入 `backend/`，执行题目给定的等价命令：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Linux/macOS还可运行 `bash scripts/start_backend.sh`。

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Linux/macOS也可在根目录运行 `bash scripts/start_frontend.sh`。开发服务器默认代理 `/api` 到 `http://127.0.0.1:8765`。

### 5. 访问与账号

- 前端：http://127.0.0.1:5173
- 后端健康检查：http://127.0.0.1:8765/health
- Swagger API文档：http://127.0.0.1:8765/docs
- OpenAPI JSON：http://127.0.0.1:8765/openapi.json

| 用户名 | 密码 | 角色与范围 |
|---|---|---|
| `admin` | `admin123` | 管理员，全院数据与全量ETL等管理操作 |
| `analyst` | `analyst123` | 分析师，全院查询、导入、单任务ETL与质量执行 |
| `dept_hn` | `dept123` | 科室用户，仅呼吸内科（HN）数据 |

这些账号是首次建库时写入的演示凭据，不得直接用于共享或生产环境。

## API使用

业务接口统一位于 `/api/v1`，除登录外均需请求头 `Authorization: Bearer <token>`。正常响应 envelope 为 `{code, message, data, trace_id}`；响应头也带 `X-Trace-ID`。

```bash
curl -X POST http://127.0.0.1:8765/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'

curl 'http://127.0.0.1:8765/api/v1/dashboards/management' \
  -H 'Authorization: Bearer 替换为登录返回的token'
```

主要接口包括 `/meta`、`/dashboards/management`、`/analytics/{topic}`、`/metrics`、`/metrics/{code}/values`、`/reports/query`、`/reports/query/export`、`/ai/ask`、`/ai/knowledge`、`/ai/nl2sql`、`/reports/generate`、`/quality/latest`、`/etl/jobs`、`/etl/ads/refresh`、`/users`、`/roles`、`/data-sources` 和 `/audit/logs`。指标趋势和报表支持 `day/week/month`；非法粒度由后台代码校验并返回422。完整路径、角色与请求约束见 Swagger 和 [项目说明](docs/项目说明.md)。

### ADS区间回刷

管理员或分析师可调用 `POST /api/v1/etl/ads/refresh`：

```json
{"start":"2025-05-01","end":"2025-05-31","grains":["day","week","month"]}
```

也可在命令行执行：

```bash
PYTHONPATH=backend .venv/bin/python -m etl.jobs.ads_refresh --start 2025-05-01 --end 2025-05-31 --grains day,week,month
```

回刷会按完整日/周/月桶删除并重算指定区间，重复执行幂等；全部30项可算指标写入 `ads_metric_result`，K25在缺少上年数据时保留NULL。

### 12个月附加数据（不影响默认主题）

按用户要求另提供独立的12个月模拟数据集：前3个月为课程给定数据，后9个月按原始模板确定性扩展。

```bash
.venv/Scripts/python.exe scripts/build_supplemental_12m.py
```

输出：

- `data/supplemental_12m/`：六源CSV、manifest、summary、monthly_summary
- `data/supplemental_12m/derived/supplemental_12m.db`：独立SQLite数仓
- 日期范围：2025-04-01 至 2026-03-31
- 数据量：236,028行
- 验证：12个自然月、DWS 3,650科室日、30项ADS共141,900行

默认前端仍读取3个月主库。使用独立库启动后端时必须显式设置 `MEDICAL_DATA_DIR` 与 `MEDICAL_DB_PATH`，详见[附加数据说明](docs/附加材料-12个月模拟数据说明.md)。

## LLM环境变量

| 变量 | 默认值/说明 |
|---|---|
| `LLM_PROVIDER` | `deepseek`；设为 `kimi` 时切换Kimi，其他值按DeepSeek处理 |
| `DEEPSEEK_API_KEY` | 默认空；为空时使用 `local-rules` |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | `deepseek-chat` |
| `KIMI_API_KEY` | 默认空；为空时使用 `local-rules` |
| `KIMI_BASE_URL` | `https://api.moonshot.cn/v1` |
| `KIMI_MODEL` | `moonshot-v1-8k` |

本地Shell示例：

```bash
export LLM_PROVIDER=deepseek
export DEEPSEEK_API_KEY='你的Key'
# 或：export LLM_PROVIDER=kimi; export KIMI_API_KEY='你的Key'
```

外部调用超时为25秒，HTTP错误或响应结构异常时返回 `local-rules-fallback`。智能问数会把**用户问题与聚合指标上下文**发给所选供应商；报告摘要只发送聚合报告内容。不要在问题中输入患者信息或密钥。无Key时，指标解析、查询和固定模板回答仍可在本地完成。

后端只读取进程环境变量，**不会自动加载 `.env`**。本地运行需自行导出变量；根目录 `.env` 供下述Compose命令做变量替换。

## Docker Compose（演示部署）

```bash
cp .env.example .env
# 编辑 .env，至少替换 MEDICAL_SECRET_KEY；不使用外部LLM可留空Key。
docker compose -f deploy/docker-compose.yml build
docker compose -f deploy/docker-compose.yml up -d
```

后端容器启动时会先自动执行ETL再提供API；如需手动回刷，可另行执行 `docker compose -f deploy/docker-compose.yml run --rm backend python -m etl.jobs.pipeline`。Compose将前端映射到 `5173`、后端映射到 `8765`，SQLite持久化在命名卷 `medical-ops-analytics_medical_data`（实际名称以Compose输出为准）。前端容器通过Nginx反向代理 `/api`、`/health`、`/docs` 和 `/openapi.json`。详见[部署运维手册](docs/部署运维手册.md)。

## 指标与数据边界

- 39项指标定义中，**30项口径可计算、9项不可计算**：K03、K04、K05、K15、K30、K33、K34、K35、K36缺必要字段，不以0代替。30项中K25收入同比增长率缺上年同期数据，默认查询目录隐藏，页面实际可查29项；`/metrics?include_unavailable=true`可看30项，`?include_unsupported=true`保留完整39项目录供审计。每项指标带 `formula` 计算公式并在指标查询页展示。K37门诊患者人均就诊次数、K38住院患者人均住院次数、K39检验结果异常率由现有明细字段计算。
- 收入采用账单口径：门诊收入取 `dwd_outpatient_visit.fee_amount`，住院收入取 `dwd_inpatient_stay.total_fee`，两者合计为医疗总收入（课程数据集为 2,774.58 万元）。药品、耗材收入只有 `dwd_charge_detail` 提供费别字段，保留明细口径用于结构分析；两套金额在模拟数据中并不相等，页面与手册均标注口径。`finance_excel` 仅入仓和质量检查，不进入K16—K25。
- 八张主题DWS表为门诊、住院、收入、药品、耗材、病种、资源、患者服务日汇总；公共维表另有 `dim_date`。
- `dws_disease`、`dws_disease_day` 与病种分析来自住院记录，不是从EMR诊断文本做正式DRG分组。
- 床位、人力及科室映射状态为教学初始化配置；全院床位使用率按实际开放床位345张（编制375张，急诊科30张观察床不计入），K11—K14、K31、K32不能用于真实绩效。
- K26—K29是基于病种编码、费用和住院日的教学估算，不能称为官方DRG入组率或CMI。
- 原始模拟CSV含直接身份字段；DWD使用加盐散列的 `patient_key`，但 **ODS的 `payload_json` 仍保留原始行内容**。数据库、CSV、备份和日志均须按敏感文件限制访问，即使数据为模拟也不得替换为真实患者数据后直接对外使用。

完整公式与特殊口径见[指标口径手册](docs/指标口径手册.md)，字段级说明见[数据字典](docs/数据字典.md)。

## 测试状态

后端可在激活环境并进入 `backend/` 后用 `pytest`，或从根目录运行：

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests
.venv/bin/python scripts/check_reconciliation.py
.venv/bin/python scripts/security_check.py
cd frontend && npm test && npm run lint && npm run build && npm run e2e
```

执行E2E前需确保前端5173、后端8765均已启动。可先运行 `python scripts/load_test.py --workers 8 --requests 120` 做单机并发冒烟。

**本次交付已执行六源全量/增量ETL、DWD宽表（10,500行）、八张主题集市、30项三粒度ADS（35,640行）、后端36项测试（`backend/app`覆盖率86.80%）、前端19项单元测试、ESLint和734模块生产构建；50问受控问数评测为50/50、100%；浏览器E2E 20/20、HTTP安全冒烟13/13、源到ADS对账17/17通过；8并发120请求压测成功率100%。** Docker、真实第三方LLM调用、生产级渗透和容量测试仍未完成，不能据此宣称全部课程任务或生产部署已经通过。详见[测试计划与报告](docs/测试计划与报告.md)和[50问评测报告](docs/50问评测报告.md)。

## 安全说明

默认密钥、默认口令、本地Storage中的令牌、无TLS的HTTP、缺少登录限流/密码自助修改/密钥轮换等均属于教学实现边界。ODS原文、上传文件和SQLite备份需要文件系统权限保护。对外部LLM的调用是网络出向请求，应由部署方自行评估合规性。生产化前必须完成凭据治理、HTTPS、限流、备份恢复演练、安全测试和真实指标业务确认。

## 文档索引

### 需求与设计

- [需求规格说明书](docs/需求规格说明书.md)
- [概要设计说明书](docs/概要设计说明书.md)
- [详细设计说明书](docs/详细设计说明书.md)
- [项目说明](docs/项目说明.md)
- [指标口径手册](docs/指标口径手册.md)
- [数据字典](docs/数据字典.md)

### 开发与过程

- [开发流程](docs/开发流程.md)
- [培养目标](docs/培养目标.md)
- [开发计划与进度记录](docs/开发计划与进度记录.md)
- [代码评审记录](docs/代码评审记录.md)
- [测试用例与缺陷清单](docs/测试用例与缺陷清单.md)

### 测试与评测

- [测试计划与报告](docs/测试计划与报告.md)
- [测试用例与缺陷清单](docs/测试用例与缺陷清单.md)
- [50问智能问数评测报告](docs/50问评测报告.md)
- 对账证据：`data/derived/reconciliation_report.json`
- E2E证据：`data/derived/e2e_report.json`
- 安全冒烟证据：`data/derived/security_check_report.json`
- 压测证据：`data/derived/load_test_report.json`
- 查询计划与慢SQL优化证据：`data/derived/query_plan_report.json`

### 部署与使用

- [部署运维手册](docs/部署运维手册.md)
- [用户操作手册](docs/用户操作手册.md)
- [试运行与培训记录](docs/试运行与培训记录.md)

### 附加数据

- [12个月模拟数据说明](docs/附加材料-12个月模拟数据说明.md)

### 验收与归档

- [验收报告](docs/验收报告.md)
- [项目总结](docs/项目总结.md)
- [答辩材料（文字稿）](docs/答辩材料.md)
- [答辩演示文稿](docs/答辩材料/答辩材料.pptx)
- [运营看板截图说明](docs/screenshots/README.md)
- [成果物清单](docs/成果物清单.md)
