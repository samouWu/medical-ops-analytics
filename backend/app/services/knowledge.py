from app.services.metrics import METRIC_MAP, METRICS

TOPICS = {
    "权限": "平台使用JWT和RBAC：admin可管理全院与系统配置，analyst可做全院分析与导入，department只允许授权科室。科室范围在服务端scope()强制校验，前端筛选不能绕过。",
    "角色": "当前包含admin、analyst、department和预留engineer角色。权限以服务端依赖为准，科室用户只能访问dept_codes_json中的科室。",
    "数据源": "当前接入HIS门诊、HIS住院、HIS收费、EMR、LIS和财务六类文件源，共59,922行。数据库/API连接器当前只是登记配置，未实现采集。",
    "dws": "DWS是主题汇总层，当前有门诊、住院、收入、药品、耗材、病种、资源效率和患者服务八张日集市，另有公共dws_dept_day和dws_disease。",
    "ads": "ADS保存核心指标的日/周/月结果，主库当前预计算全部30项可算指标；区间回刷按完整时间桶删除后重算，重复执行幂等。",
    "drg": "K26—K29是基于病种、费用和住院日的教学估算，不是医保官方DRG/DIP分组，也不是正式CMI或绩效结论。",
    "数据质量": "当前有10项质量规则，覆盖完整性、唯一性、日期逻辑、金额值域、科室/病种映射、LIS结果值域和财务非负，并输出质量分数和批次记录。",
    "模型": "平台默认DeepSeek、可切换Kimi，不接GPT。模型只接收问题和聚合指标上下文，不接收患者明细；无Key或调用失败时明确返回local-rules或local-rules-fallback。",
    "隐私": "DWD不保存姓名、身份证和手机号，使用加盐patient_key。ODS仍保留原始行，必须作为敏感文件保护。",
}


def answer(question: str):
    text = question.strip().lower()
    candidates = []
    for code, metric in METRIC_MAP.items():
        names = [code.lower(), metric["name"].lower()]
        if any(name in text for name in names):
            candidates.append((max(len(name) for name in names if name in text), code))
    if candidates:
        code = max(candidates)[1]
        metric = METRIC_MAP[code]
        status = "可计算" if metric["supported"] else "不可计算，原因是缺少源字段"
        answer_text = (
            f"{code} {metric['name']}，主题为{metric['topic']}，单位为{metric['unit']}，当前状态：{status}。"
            f"口径：{metric['description']}。比率先汇总分子分母再相除，零分母返回空值；科室用户只计算授权科室。"
        )
        return {
            "answer": answer_text,
            "intent": "knowledge",
            "topic": "metric",
            "metric_code": code,
            "sources": [f"docs/指标口径手册.md#{code}", "backend/app/services/metrics.py"],
            "provider": "local-knowledge",
        }

    for keyword, answer_text in TOPICS.items():
        if keyword.lower() in text:
            return {
                "answer": answer_text,
                "intent": "knowledge",
                "topic": keyword,
                "metric_code": None,
                "sources": ["docs/需求规格说明书.md", "docs/指标口径手册.md", "docs/详细设计说明书.md"],
                "provider": "local-knowledge",
            }

    examples = "、".join(f"{row[0]} {row[1]}" for row in METRICS[:6])
    return {
        "answer": f"暂未匹配到明确的知识条目。可以询问指标口径、权限角色、数据源、DWS/ADS、DRG边界、质量规则或模型隐私，例如：{examples}。",
        "intent": "knowledge-fallback",
        "topic": None,
        "metric_code": None,
        "sources": ["docs/指标口径手册.md"],
        "provider": "local-knowledge",
    }
