from flask import Blueprint, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Analysis, SkinConcern, User
from datetime import datetime, timedelta
import io

report_bp = Blueprint('report', __name__)


def _this_week_analyses(user_id):
    since = datetime.utcnow() - timedelta(days=7)
    return (Analysis.query
            .filter_by(user_id=user_id)
            .filter(Analysis.created_at >= since)
            .order_by(Analysis.created_at.desc())
            .all())


def _build_concern_detail(concern):
    """Return a dict for a single SkinConcern row."""
    return {
        'concern_type':       concern.concern_type,
        'label':              concern.concern_type.replace('_', ' ').title(),
        'confidence':         round(concern.confidence, 3),
        'severity':           concern.severity,
        'notes':              concern.notes or '',
        'annotated_image_b64': concern.annotated_image_b64 or None,
    }


def _build_summary(analyses, user):
    if not analyses:
        return None

    from collections import Counter

    skin_types  = [a.skin_type for a in analyses]
    confidences = [a.confidence for a in analyses]
    avg_conf    = round(sum(confidences) / len(confidences), 1)
    dominant    = Counter(skin_types).most_common(1)[0][0]

    mid = len(analyses) // 2
    if mid > 0:
        trend = round(
            sum(confidences[:mid]) / mid
            - sum(confidences[mid:]) / max(len(analyses) - mid, 1),
            1
        )
    else:
        trend = None

    # Per-concern aggregation
    all_concerns: dict = {}
    for a in analyses:
        for c in SkinConcern.query.filter_by(analysis_id=a.id).all():
            if c.confidence > 0.15:
                all_concerns.setdefault(c.concern_type, []).append(c.confidence)

    concern_summary = dict(sorted({
        k: {
            'avg':   round(sum(v) / len(v), 3),
            'count': len(v),
            'label': k.replace('_', ' ').title(),
        }
        for k, v in all_concerns.items()
    }.items(), key=lambda x: -x[1]['avg']))

    # Per-analysis detail (includes face photo + concern zone images)
    analyses_detail = []
    for a in analyses:
        concerns_for_scan = SkinConcern.query.filter_by(analysis_id=a.id).all()
        analyses_detail.append({
            'id':                       a.id,
            'date':                     a.created_at.strftime('%b %d, %Y %H:%M'),
            'skin_type':                a.skin_type,
            'confidence':               round(a.confidence, 1),
            'normalized_image_b64':     a.normalized_image_b64 or None,
            'concerns': [
                _build_concern_detail(c)
                for c in concerns_for_scan
                if c.confidence > 0.15
            ],
        })

    # AI-generated narrative paragraph
    skin_narrative = _generate_narrative(
        user.username, dominant, avg_conf, trend, concern_summary,
        len(analyses),
        (datetime.utcnow() - timedelta(days=6)).strftime('%b %d'),
        datetime.utcnow().strftime('%b %d, %Y'),
    )

    return {
        'user':             user.username,
        'period':           f"{(datetime.utcnow()-timedelta(days=6)).strftime('%b %d')} - {datetime.utcnow().strftime('%b %d, %Y')}",
        'total_scans':      len(analyses),
        'avg_confidence':   avg_conf,
        'dominant_type':    dominant,
        'skin_types':       skin_types,
        'confidences':      confidences,
        'dates':            [a.created_at.strftime('%b %d') for a in analyses],
        'trend':            trend,
        'concerns':         concern_summary,
        'analyses':         analyses_detail,
        'skin_narrative':   skin_narrative,
    }


def _generate_narrative(username, dominant_type, avg_conf, trend, concerns, total_scans, start_date, end_date):
    """
    Generate a short AI paragraph summarising the week's skin health.
    Falls back to a static template if Groq is unavailable.
    """
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        from groq import Groq

        api_key = os.environ.get('GROQ_API_KEY', '').strip()
        if not api_key:
            raise ValueError('No GROQ_API_KEY')

        client = Groq(api_key=api_key)

        trend_str = (
            f"improving by {abs(trend)}% compared to earlier in the week"
            if trend and trend > 0
            else (f"declining by {abs(trend)}% compared to earlier" if trend and trend < 0 else "stable")
        )

        top_concerns = ', '.join(
            f"{v['label']} ({v['count']} scans, {'severe' if v['avg'] > 0.55 else 'moderate' if v['avg'] > 0.25 else 'mild'})"
            for v in list(concerns.values())[:3]
        ) if concerns else 'none detected'

        prompt = (
            f"Write a 3–4 sentence skin health summary paragraph for {username}. "
            f"This week ({start_date} to {end_date}): {total_scans} scans, "
            f"dominant skin type is {dominant_type}, average confidence {avg_conf}%, "
            f"confidence trend is {trend_str}. "
            f"Main concerns: {top_concerns}. "
            f"End with 1–2 specific actionable recommendations tailored to the skin type and concerns. "
            f"Write in second person (you/your), warm but professional tone. No bullet points."
        )

        resp = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=200,
            temperature=0.65,
        )
        return resp.choices[0].message.content.strip()

    except Exception:
        # Static fallback
        concern_list = ', '.join(v['label'] for v in list(concerns.values())[:3]) if concerns else 'no major concerns'
        trend_word   = 'improving' if (trend or 0) > 0 else ('declining slightly' if (trend or 0) < 0 else 'stable')
        return (
            f"Over the past week you completed {total_scans} skin scan{'s' if total_scans != 1 else ''}, "
            f"with your skin consistently showing as {dominant_type} at an average confidence of {avg_conf}%. "
            f"Your overall skin confidence is {trend_word} — keep up your current routine and stay consistent. "
            f"The main areas to watch are: {concern_list}. "
            f"Focus on hydration, sun protection, and a gentle cleanser suited to {dominant_type.lower()} skin."
        )


@report_bp.route('/summary', methods=['GET'])
@jwt_required()
def weekly_summary():
    try:
        user_id  = int(get_jwt_identity())
        user     = User.query.get(user_id)
        analyses = _this_week_analyses(user_id)
        summary  = _build_summary(analyses, user)
        if not summary:
            return jsonify({'summary': None, 'message': 'No scans this week.'}), 200
        return jsonify({'summary': summary}), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@report_bp.route('/weekly', methods=['GET'])
@jwt_required()
def weekly_pdf():
    try:
        user_id  = int(get_jwt_identity())
        user     = User.query.get(user_id)
        analyses = _this_week_analyses(user_id)
        if not analyses:
            return jsonify({'error': 'No scans found for this week.'}), 404
        summary = _build_summary(analyses, user)
        pdf_buf = _generate_pdf(summary)
        pdf_buf.seek(0)
        return send_file(
            pdf_buf, mimetype='application/pdf', as_attachment=True,
            download_name=f"lumera_report_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _generate_pdf(s):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable, Image as RLImage)
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    import base64

    buf = io.BytesIO()
    W   = A4[0] - 40 * mm
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=18*mm, bottomMargin=18*mm)

    PURPLE   = colors.HexColor('#7C3AED')
    INDIGO   = colors.HexColor('#4F46E5')
    LIGHT_BG = colors.HexColor('#F5F3FF')
    GRAY     = colors.HexColor('#6B7280')
    DARK     = colors.HexColor('#111827')
    GREEN    = colors.HexColor('#059669')
    RED      = colors.HexColor('#DC2626')
    AMBER    = colors.HexColor('#D97706')
    SKIN_COL = {
        'Normal':      colors.HexColor('#22c55e'),
        'Oily':        colors.HexColor('#3b82f6'),
        'Dry':         colors.HexColor('#f97316'),
        'Combination': colors.HexColor('#a855f7'),
        'Sensitive':   colors.HexColor('#ef4444'),
    }

    base_sty = getSampleStyleSheet()['Normal']
    def sty(name, **kw):
        return ParagraphStyle(name, parent=base_sty, **kw)

    def b64_to_rl_image(b64_str, width_mm, height_mm):
        """Convert a base64 PNG string to a ReportLab Image flowable."""
        try:
            raw  = base64.b64decode(b64_str)
            buf_ = io.BytesIO(raw)
            return RLImage(buf_, width=width_mm * mm, height=height_mm * mm)
        except Exception:
            return None

    story = []

    # ── Header ──────────────────────────────────────────────────
    hdr = Table([[
        Paragraph('<b>Lumera</b>', sty('h', fontSize=18, textColor=colors.white)),
        Paragraph(
            f'<b>Weekly Skin Report</b><br/><font size="9">{s["period"]}</font>',
            sty('h2', fontSize=12, textColor=colors.white, alignment=TA_RIGHT)
        ),
    ]], colWidths=[W * 0.5, W * 0.5])
    hdr.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), PURPLE),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
    ]))
    story += [
        hdr,
        Spacer(1, 8),
        Paragraph(f'Prepared for: <b>{s["user"]}</b>', sty('b', fontSize=10, textColor=DARK)),
        Spacer(1, 6),
        HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#E5E7EB')),
        Spacer(1, 8),
    ]

    # ── Stats row ───────────────────────────────────────────────
    trend_val = s['trend'] or 0
    trend_str = (f"+{s['trend']}%" if trend_val >= 0 else f"{s['trend']}%") if s['trend'] is not None else '--'
    trend_col = GREEN if trend_val >= 0 else RED
    stats = [
        ('Total Scans',      str(s['total_scans']),      PURPLE),
        ('Avg Confidence',   f"{s['avg_confidence']}%",  GREEN),
        ('Primary Type',     s['dominant_type'],          SKIN_COL.get(s['dominant_type'], PURPLE)),
        ('Confidence Trend', trend_str,                   trend_col),
    ]
    stat_cells = [
        Table([[
            Paragraph(lbl, sty(f'sl{i}', fontSize=8,  textColor=GRAY,  alignment=TA_CENTER)),
            Paragraph(val, sty(f'sv{i}', fontSize=15, fontName='Helvetica-Bold', textColor=col, alignment=TA_CENTER)),
        ]], colWidths=[W / 4 - 4])
        for i, (lbl, val, col) in enumerate(stats)
    ]
    st = Table([stat_cells], colWidths=[W / 4] * 4)
    st.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), LIGHT_BG),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story += [st, Spacer(1, 12)]

    # ── AI Narrative ────────────────────────────────────────────
    if s.get('skin_narrative'):
        story += [
            Paragraph('Skin Health Summary', sty('nh', fontSize=13, fontName='Helvetica-Bold',
                                                  textColor=PURPLE, spaceAfter=4)),
            Paragraph(s['skin_narrative'], sty('np', fontSize=10, textColor=DARK,
                                               leading=15, spaceAfter=8)),
            HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#E5E7EB')),
            Spacer(1, 10),
        ]

    # ── Scan History with face photos ───────────────────────────
    story.append(Paragraph('Scan History', sty('h3', fontSize=13, fontName='Helvetica-Bold',
                                                textColor=DARK, spaceBefore=6, spaceAfter=4)))
    rows = [['Photo', 'Date', 'Skin Type', 'Confidence']]
    for a in s['analyses']:
        img_cell = ''
        if a.get('normalized_image_b64'):
            img = b64_to_rl_image(a['normalized_image_b64'], 12, 12)
            img_cell = img if img else ''

        rows.append([
            img_cell,
            Paragraph(a['date'],               sty('rd',  fontSize=9,  textColor=DARK)),
            Paragraph(f"<b>{a['skin_type']}</b>",
                      sty('rs',  fontSize=9,  fontName='Helvetica-Bold',
                          textColor=SKIN_COL.get(a['skin_type'], PURPLE))),
            Paragraph(f"{a['confidence']}%",   sty('rc',  fontSize=9,  textColor=DARK)),
        ])

    t = Table(rows, colWidths=[W * 0.12, W * 0.38, W * 0.28, W * 0.22])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  PURPLE),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  9),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ('GRID',          (0, 0), (-1, -1), 0.3, colors.HexColor('#E5E7EB')),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
    ]))
    story += [t, Spacer(1, 12)]

    # ── Concerns with annotated zone images ─────────────────────
    if s['concerns']:
        story += [
            HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#E5E7EB')),
            Spacer(1, 8),
            Paragraph('Detected Concerns', sty('h4', fontSize=13, fontName='Helvetica-Bold',
                                               textColor=DARK, spaceAfter=4)),
        ]

        for key, c in s['concerns'].items():
            avg  = c['avg']
            sev  = 'Severe' if avg > 0.55 else ('Moderate' if avg > 0.25 else 'Mild')
            sc   = RED if sev == 'Severe' else (AMBER if sev == 'Moderate' else GREEN)

            # Collect up to 2 annotated zone images for this concern
            zone_imgs = []
            for analysis in s['analyses']:
                for cn in analysis.get('concerns', []):
                    if cn['concern_type'] == key and cn.get('annotated_image_b64'):
                        img = b64_to_rl_image(cn['annotated_image_b64'], 20, 20)
                        if img:
                            zone_imgs.append(img)
                        if len(zone_imgs) >= 2:
                            break
                if len(zone_imgs) >= 2:
                    break

            # Concern header row
            concern_row = Table([[
                Paragraph(f"<b>{c['label']}</b>",
                          sty(f'cl{key}', fontSize=11, fontName='Helvetica-Bold', textColor=DARK)),
                Paragraph(f"<b>{sev}</b>",
                          sty(f'cs{key}', fontSize=10, fontName='Helvetica-Bold', textColor=sc, alignment=TA_RIGHT)),
                Paragraph(f"{c['count']} scan{'s' if c['count'] > 1 else ''} · {round(avg * 100)}% avg",
                          sty(f'ca{key}', fontSize=9, textColor=GRAY, alignment=TA_RIGHT)),
            ]], colWidths=[W * 0.40, W * 0.25, W * 0.35])
            concern_row.setStyle(TableStyle([
                ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING',    (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('BACKGROUND',    (0, 0), (-1, -1), LIGHT_BG),
                ('LEFTPADDING',   (0, 0), (0, 0),   8),
            ]))
            story.append(concern_row)

            # Zone images row (if any)
            if zone_imgs:
                img_cells = zone_imgs + ([''] * (2 - len(zone_imgs)))
                img_row = Table([img_cells], colWidths=[W * 0.22, W * 0.22, W * 0.56])
                img_row.setStyle(TableStyle([
                    ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
                    ('TOPPADDING',    (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 4),
                ]))
                story.append(img_row)

            story.append(Spacer(1, 6))

        story.append(Spacer(1, 6))

    # ── Footer ──────────────────────────────────────────────────
    story += [
        HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#E5E7EB')),
        Spacer(1, 6),
        Paragraph(
            f"Generated by Lumera on {datetime.utcnow().strftime('%B %d, %Y')}. For informational purposes only.",
            sty('ft', fontSize=8, textColor=GRAY, alignment=TA_CENTER)
        ),
    ]

    doc.build(story)
    return buf