import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from app.api.common import ok, trace_context
from app.core.database import audit
from app.core.security import current_user, require_roles
from app.llm.nl2sql import NL2SQLError, ask_sql
from app.llm.semantic import ask
from app.schemas import AskRequest, ReportRequest
from app.services.knowledge import answer as knowledge_answer
from app.services.reports import generate_report

router = APIRouter(tags=["智能分析"])


@router.post("/ai/ask")
def ai_ask(payload: AskRequest, user: dict = Depends(current_user)):
    try:
        result = ask(payload.question, user, payload.start, payload.end, payload.dept_code)
        audit(user["username"], "AI_ASK", "metric", payload.question, trace_context.get())
        return ok(result)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@router.post("/ai/nl2sql")
def ai_nl2sql(payload: AskRequest, user: dict = Depends(require_roles("admin", "analyst"))):
    try:
        result = ask_sql(payload.question)
        audit(user["username"], "AI_NL2SQL", "readonly_sql", payload.question[:120], trace_context.get())
        return ok(result)
    except NL2SQLError as exc:
        status = 503 if "未配置" in str(exc) else 422
        raise HTTPException(status, str(exc)) from None


@router.post("/ai/knowledge")
def ai_knowledge(payload: AskRequest, user: dict = Depends(current_user)):
    result = knowledge_answer(payload.question)
    audit(user["username"], "AI_KNOWLEDGE", "knowledge", payload.question[:120], trace_context.get())
    return ok(result)


@router.post("/reports/generate")
def report(payload: ReportRequest, user: dict = Depends(current_user)):
    try:
        result = generate_report(payload.period, payload.date, user, payload.dept_code)
        audit(user["username"], "GENERATE", "report", payload.period, trace_context.get())
        return ok(result)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@router.post("/reports/export/pdf")
def report_pdf(payload: ReportRequest, user: dict = Depends(current_user)):
    data = generate_report(payload.period, payload.date, user, payload.dept_code)
    output = io.BytesIO()
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    pdf.setFont("STSong-Light", 18)
    pdf.drawString(50, height-55, data["title"])
    y = height-90
    for section in data["sections"]:
        pdf.setFont("STSong-Light", 13)
        pdf.drawString(50, y, section["title"])
        y -= 23
        pdf.setFont("STSong-Light", 10)
        text = section["content"]
        lines = [text[i:i+43] for i in range(0, len(text), 43)]
        for line in lines:
            pdf.drawString(50, y, line)
            y -= 17
        y -= 12
        if y < 70:
            pdf.showPage()
            y = height-55
            pdf.setFont("STSong-Light", 10)
    pdf.setFont("STSong-Light", 8)
    pdf.drawString(50, 35, "教学课程项目；DRG、床位和人力假设不构成真实医疗或绩效结论")
    pdf.save()
    output.seek(0)
    audit(user["username"], "EXPORT", "report_pdf", data["title"], trace_context.get())
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="medical-report.pdf"'})
