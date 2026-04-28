"""
reportservice.py - Generate PDF analysis reports using ReportLab.
"""
import os
import json
from datetime import datetime
from typing import Dict, Any

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import REPORT_FOLDER

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ─── Color palette ─────────────────────────────────────────────────────────────
C_DARK   = colors.HexColor("#0f172a")
C_BLUE   = colors.HexColor("#6366f1")
C_GREEN  = colors.HexColor("#22c55e")
C_RED    = colors.HexColor("#ef4444")
C_AMBER  = colors.HexColor("#f59e0b")
C_GRAY   = colors.HexColor("#94a3b8")
C_LIGHT  = colors.HexColor("#f8fafc")
C_WHITE  = colors.white


def generate_report(analysis_data: Dict[str, Any], design_name: str) -> str:
    """
    Generate a PDF report from analysis data.
    Returns the absolute path of the generated PDF.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("ReportLab is not installed. Run: pip install reportlab")

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in design_name)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{safe_name}_{ts}.pdf"
    filepath = os.path.join(REPORT_FOLDER, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Normal"],
        fontSize=22, fontName="Helvetica-Bold",
        textColor=C_DARK, spaceAfter=4,
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Normal"],
        fontSize=13, fontName="Helvetica-Bold",
        textColor=C_BLUE, spaceBefore=12, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica",
        textColor=C_DARK, leading=14,
    )
    code_style = ParagraphStyle(
        "Code", parent=styles["Normal"],
        fontSize=8, fontName="Courier",
        textColor=C_DARK, leading=12,
    )

    story = []

    # ── Header ──
    story.append(Paragraph("⬡ SiliconMind FPGA Intelligence", title_style))
    story.append(Paragraph(f"Analysis Report — <b>{design_name}</b>", body_style))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", body_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE))
    story.append(Spacer(1, 0.3*cm))

    # ── Summary table ──
    features = analysis_data.get("features", {})
    ml = analysis_data.get("ml_result", {})
    health = ml.get("health_score", 0)
    status = ml.get("design_status", "N/A")
    bs = ml.get("bitstream_readiness", 0)

    status_color = C_GREEN if status == "OPTIMIZED" else (C_RED if status == "CRITICAL" else C_AMBER)

    story.append(Paragraph("Design Summary", h2_style))
    summary_data = [
        ["Metric", "Value"],
        ["Health Score", f"{health:.1f} / 100"],
        ["Design Status", status],
        ["Bitstream Readiness", f"{bs:.1f}%"],
        ["AI Confidence", f"{ml.get('confidence', 0)*100:.0f}%"],
        ["Model Used", ml.get("model_used", "rule_based")],
    ]
    t = Table(summary_data, colWidths=[6*cm, 11*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_BLUE),
        ("TEXTCOLOR",  (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_LIGHT, C_WHITE]),
        ("GRID",       (0, 0), (-1, -1), 0.5, C_GRAY),
        ("PADDING",    (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))

    # ── Power ──
    story.append(Paragraph("Power Analysis", h2_style))
    power = analysis_data.get("power", {})
    power_data = [
        ["Component", "Power (W)"],
        ["Total On-Chip", f"{features.get('total_power_w', 0):.3f}"],
        ["Dynamic", f"{features.get('dynamic_power_w', 0):.3f}"],
        ["Static", f"{features.get('static_power_w', 0):.3f}"],
    ]
    for bd in power.get("breakdown", []):
        power_data.append([f"  ↳ {bd['name']}", f"{bd['value']:.3f}"])
    t2 = Table(power_data, colWidths=[10*cm, 7*cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_DARK),
        ("TEXTCOLOR",  (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_LIGHT, C_WHITE]),
        ("GRID",       (0, 0), (-1, -1), 0.5, C_GRAY),
        ("PADDING",    (0, 0), (-1, -1), 5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 0.4*cm))

    # ── Timing ──
    story.append(Paragraph("Timing Analysis", h2_style))
    timing = analysis_data.get("timing", {})
    wns = features.get("worst_negative_slack_ns", 0)
    timing_status = "✓ PASS" if wns >= 0 else "✗ FAIL"
    timing_data_table = [
        ["Parameter", "Value"],
        ["Timing Status", timing_status],
        ["Worst Negative Slack", f"{wns:.3f} ns"],
        ["Target Frequency", f"{features.get('target_freq_mhz', 0):.0f} MHz"],
        ["Achieved Frequency", f"{features.get('achieved_freq_mhz', 0):.0f} MHz"],
    ]
    t3 = Table(timing_data_table, colWidths=[10*cm, 7*cm])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_DARK),
        ("TEXTCOLOR",  (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_LIGHT, C_WHITE]),
        ("GRID",       (0, 0), (-1, -1), 0.5, C_GRAY),
        ("PADDING",    (0, 0), (-1, -1), 5),
    ]))
    story.append(t3)
    story.append(Spacer(1, 0.4*cm))

    # ── AI Insights ──
    story.append(Paragraph("AI Insights", h2_style))
    ai = analysis_data.get("ai_result", {})
    insights = ai.get("insights", [])
    if isinstance(insights, str):
        insights = json.loads(insights)
    for ins in insights:
        icon = {"issue": "⚠", "opportunity": "💡", "warning": "⚡"}.get(ins.get("type", ""), "•")
        story.append(Paragraph(f"{icon} <b>{ins.get('title','')}</b>", body_style))
        story.append(Paragraph(ins.get("text", ""), code_style))
        story.append(Spacer(1, 0.15*cm))

    # ── Recommendations ──
    story.append(Paragraph("Recommendations", h2_style))
    recs = ai.get("recommendations", [])
    if recs:
        rec_data = [["Priority", "Action", "Impact", "Effort"]]
        for r in recs:
            rec_data.append([
                r.get("priority", "").upper(),
                Paragraph(r.get("title", ""), code_style),
                r.get("impact", ""),
                r.get("effort", ""),
            ])
        t4 = Table(rec_data, colWidths=[2*cm, 8*cm, 4*cm, 3*cm])
        t4.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_BLUE),
            ("TEXTCOLOR",  (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_LIGHT, C_WHITE]),
            ("GRID",       (0, 0), (-1, -1), 0.5, C_GRAY),
            ("PADDING",    (0, 0), (-1, -1), 5),
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t4)

    # ── Root Cause ──
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("Root Cause Analysis", h2_style))
    story.append(Paragraph(ai.get("root_cause", "N/A"), body_style))

    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_GRAY))
    story.append(Paragraph(
        f"Best Strategy: <b>{ai.get('best_strategy', 'N/A')}</b> · "
        f"Confidence: {ai.get('confidence', 0)*100:.0f}%",
        body_style,
    ))

    doc.build(story)
    return filepath
