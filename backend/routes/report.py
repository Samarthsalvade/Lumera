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
    return {
        'concern_type':        concern.concern_type,
        'label':               concern.concern_type.replace('_', ' ').title(),
        'confidence':          round(concern.confidence, 3),
        'severity':            concern.severity,
        'notes':               concern.notes or '',
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

    analyses_detail = []
    for a in analyses:
        concerns_for_scan = SkinConcern.query.filter_by(analysis_id=a.id).all()
        analyses_detail.append({
            'id':                   a.id,
            'date':                 a.created_at.strftime('%b %d, %Y %H:%M'),
            'skin_type':            a.skin_type,
            'confidence':           round(a.confidence, 1),
            'normalized_image_b64': a.normalized_image_b64 or None,
            'concerns': [
                _build_concern_detail(c)
                for c in concerns_for_scan
                if c.confidence > 0.15
            ],
        })

    skin_narrative = _generate_narrative(
        user.username, dominant, avg_conf, trend, concern_summary,
        len(analyses),
        (datetime.utcnow() - timedelta(days=6)).strftime('%b %d'),
        datetime.utcnow().strftime('%b %d, %Y'),
    )

    return {
        'user':           user.username,
        'period':         f"{(datetime.utcnow()-timedelta(days=6)).strftime('%b %d')} - {datetime.utcnow().strftime('%b %d, %Y')}",
        'total_scans':    len(analyses),
        'avg_confidence': avg_conf,
        'dominant_type':  dominant,
        'skin_types':     skin_types,
        'confidences':    confidences,
        'dates':          [a.created_at.strftime('%b %d') for a in analyses],
        'trend':          trend,
        'concerns':       concern_summary,
        'analyses':       analyses_detail,
        'skin_narrative': skin_narrative,
    }


def _generate_narrative(username, dominant_type, avg_conf, trend, concerns,
                         total_scans, start_date, end_date):
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
            else (f"declining by {abs(trend)}% compared to earlier"
                  if trend and trend < 0 else "stable")
        )

        top_concerns = ', '.join(
            f"{v['label']} ({v['count']} scans, "
            f"{'severe' if v['avg'] > 0.55 else 'moderate' if v['avg'] > 0.25 else 'mild'})"
            for v in list(concerns.values())[:3]
        ) if concerns else 'none detected'

        prompt = (
            f"Write a 3-4 sentence skin health summary paragraph for {username}. "
            f"This week ({start_date} to {end_date}): {total_scans} scans, "
            f"dominant skin type is {dominant_type}, average confidence {avg_conf}%, "
            f"confidence trend is {trend_str}. "
            f"Main concerns: {top_concerns}. "
            f"End with 1-2 specific actionable recommendations tailored to the skin type and concerns. "
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
        concern_list = ', '.join(
            v['label'] for v in list(concerns.values())[:3]
        ) if concerns else 'no major concerns'
        trend_word = ('improving' if (trend or 0) > 0
                      else ('declining slightly' if (trend or 0) < 0 else 'stable'))
        return (
            f"Over the past week you completed {total_scans} skin scan"
            f"{'s' if total_scans != 1 else ''}, with your skin consistently showing "
            f"as {dominant_type} at an average confidence of {avg_conf}%. "
            f"Your overall skin confidence is {trend_word} — keep up your current "
            f"routine and stay consistent. "
            f"The main areas to watch are: {concern_list}. "
            f"Focus on hydration, sun protection, and a gentle cleanser suited to "
            f"{dominant_type.lower()} skin."
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


# ─────────────────────────────────────────────────────────────────────────────
# PDF GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def _generate_pdf(s):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage, KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
    from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame
    from reportlab.pdfgen import canvas as rl_canvas
    import base64

    PAGE_W, PAGE_H = A4
    L_MAR = R_MAR = 20 * mm
    T_MAR = 22 * mm
    B_MAR = 20 * mm
    CONTENT_W = PAGE_W - L_MAR - R_MAR

    # ── Colour palette ────────────────────────────────────────────
    C_PURPLE     = colors.HexColor('#7C3AED')
    C_PURPLE_MID = colors.HexColor('#9333EA')
    C_INDIGO     = colors.HexColor('#4F46E5')
    C_PURPLE_LT  = colors.HexColor('#EDE9FE')   # very light purple bg
    C_PURPLE_XLT = colors.HexColor('#F5F3FF')   # even lighter
    C_WHITE      = colors.white
    C_DARK       = colors.HexColor('#111827')
    C_DARK_MID   = colors.HexColor('#374151')
    C_GRAY       = colors.HexColor('#6B7280')
    C_GRAY_LT    = colors.HexColor('#9CA3AF')
    C_BORDER     = colors.HexColor('#E5E7EB')
    C_GREEN      = colors.HexColor('#059669')
    C_GREEN_LT   = colors.HexColor('#D1FAE5')
    C_RED        = colors.HexColor('#DC2626')
    C_RED_LT     = colors.HexColor('#FEE2E2')
    C_AMBER      = colors.HexColor('#D97706')
    C_AMBER_LT   = colors.HexColor('#FEF3C7')

    SKIN_COLOR = {
        'Normal':      colors.HexColor('#22C55E'),
        'Oily':        colors.HexColor('#3B82F6'),
        'Dry':         colors.HexColor('#F97316'),
        'Combination': colors.HexColor('#A855F7'),
        'Sensitive':   colors.HexColor('#EF4444'),
    }
    SKIN_COLOR_LT = {
        'Normal':      colors.HexColor('#DCFCE7'),
        'Oily':        colors.HexColor('#DBEAFE'),
        'Dry':         colors.HexColor('#FFEDD5'),
        'Combination': colors.HexColor('#F3E8FF'),
        'Sensitive':   colors.HexColor('#FEE2E2'),
    }

    # ── Style helpers ─────────────────────────────────────────────
    _base = getSampleStyleSheet()['Normal']

    def S(name, **kw):
        return ParagraphStyle(name, parent=_base, **kw)

    # ── Canvas callback — adds page number + thin footer rule ─────
    def _add_page_number(canv, doc):
        canv.saveState()
        canv.setStrokeColor(C_BORDER)
        canv.setLineWidth(0.5)
        canv.line(L_MAR, B_MAR - 4 * mm, PAGE_W - R_MAR, B_MAR - 4 * mm)
        canv.setFont('Helvetica', 7)
        canv.setFillColor(C_GRAY)
        canv.drawString(
            L_MAR,
            B_MAR - 9 * mm,
            f'Lumera Skin Analysis  ·  {s["period"]}  ·  Confidential'
        )
        canv.drawRightString(
            PAGE_W - R_MAR,
            B_MAR - 9 * mm,
            f'Page {doc.page}'
        )
        canv.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=L_MAR, rightMargin=R_MAR,
        topMargin=T_MAR,  bottomMargin=B_MAR + 8 * mm,
        onPage=_add_page_number,
        onLaterPages=_add_page_number,
    )

    story = []

    # ─────────────────────────────────────────────────────────────
    # Helper: base64 → RLImage
    # ─────────────────────────────────────────────────────────────
    def b64_img(b64_str, w_mm, h_mm):
        try:
            raw  = base64.b64decode(b64_str)
            bio  = io.BytesIO(raw)
            img  = RLImage(bio, width=w_mm * mm, height=h_mm * mm)
            img.hAlign = 'CENTER'
            return img
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────────
    # SECTION 1 — HEADER BANNER
    # Two columns: branding left, report title + date right.
    # Rendered as a single-row Table with a purple background.
    # ─────────────────────────────────────────────────────────────
    header_left = [
        Paragraph(
            '<font color="white"><b>lumera</b></font>',
            S('HL', fontSize=22, fontName='Helvetica-Bold',
              leading=24, spaceAfter=2)
        ),
        Paragraph(
            '<font color="#C4B5FD">AI Skincare Analysis</font>',
            S('HL2', fontSize=8, leading=10)
        ),
    ]
    header_right = [
        Paragraph(
            '<font color="white"><b>Weekly Skin Report</b></font>',
            S('HR', fontSize=14, fontName='Helvetica-Bold',
              leading=16, alignment=TA_RIGHT)
        ),
        Paragraph(
            f'<font color="#C4B5FD">{s["period"]}</font>',
            S('HR2', fontSize=9, leading=12, alignment=TA_RIGHT)
        ),
        Paragraph(
            f'<font color="#C4B5FD">Prepared for <b><font color="white">'
            f'{s["user"]}</font></b></font>',
            S('HR3', fontSize=9, leading=12, alignment=TA_RIGHT)
        ),
    ]

    hdr_tbl = Table(
        [[header_left, header_right]],
        colWidths=[CONTENT_W * 0.45, CONTENT_W * 0.55],
    )
    hdr_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), C_PURPLE),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING',   (0, 0), (0, 0),   16),
        ('RIGHTPADDING',  (-1, 0), (-1, -1), 16),
        ('LEFTPADDING',   (1, 0), (1, 0),   8),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 14))

    # ─────────────────────────────────────────────────────────────
    # SECTION 2 — STATS CARDS (4 KPIs in a row)
    # Each card: light purple bg, metric label on top, big value below.
    # ─────────────────────────────────────────────────────────────
    trend_val  = s['trend'] or 0
    trend_str  = (f'+{s["trend"]}%' if trend_val >= 0 else f'{s["trend"]}%') \
                 if s['trend'] is not None else '—'
    trend_col  = C_GREEN if trend_val >= 0 else C_RED
    trend_bg   = C_GREEN_LT if trend_val >= 0 else C_RED_LT

    dominant   = s['dominant_type']
    dom_col    = SKIN_COLOR.get(dominant, C_PURPLE)
    dom_bg     = SKIN_COLOR_LT.get(dominant, C_PURPLE_LT)

    def _kpi_card(label, value, val_color, bg_color):
        inner = Table(
            [
                [Paragraph(label, S(f'kl_{label}', fontSize=7.5, textColor=C_GRAY,
                                    alignment=TA_CENTER, leading=10))],
                [Paragraph(f'<b>{value}</b>',
                           S(f'kv_{label}', fontSize=18, textColor=val_color,
                             fontName='Helvetica-Bold', alignment=TA_CENTER, leading=22))],
            ],
            colWidths=[CONTENT_W / 4 - 5 * mm],
        )
        inner.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), bg_color),
            ('TOPPADDING',    (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('ROUNDEDCORNERS', [4, 4, 4, 4]),
        ]))
        return inner

    kpi_cards = [
        _kpi_card('Total Scans',      str(s['total_scans']),       C_PURPLE,  C_PURPLE_LT),
        _kpi_card('Avg Confidence',   f'{s["avg_confidence"]}%',   C_GREEN,   C_GREEN_LT),
        _kpi_card('Primary Skin Type', dominant,                   dom_col,   dom_bg),
        _kpi_card('Confidence Trend',  trend_str,                  trend_col, trend_bg),
    ]

    kpi_row = Table(
        [kpi_cards],
        colWidths=[CONTENT_W / 4] * 4,
        hAlign='LEFT',
    )
    kpi_row.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(kpi_row)
    story.append(Spacer(1, 16))

    # ─────────────────────────────────────────────────────────────
    # SECTION 3 — AI SKIN HEALTH NARRATIVE
    # ─────────────────────────────────────────────────────────────
    if s.get('skin_narrative'):
        story.append(
            Paragraph(
                'Skin Health Summary',
                S('SH', fontSize=12, fontName='Helvetica-Bold',
                  textColor=C_DARK, spaceAfter=6, leading=15)
            )
        )

        narrative_tbl = Table(
            [[Paragraph(s['skin_narrative'],
                        S('NP', fontSize=9.5, textColor=C_DARK_MID,
                          leading=15, alignment=TA_JUSTIFY))]],
            colWidths=[CONTENT_W],
        )
        narrative_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), C_PURPLE_XLT),
            ('TOPPADDING',    (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING',   (0, 0), (-1, -1), 12),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
            ('LINEAFTER',     (0, 0), (0, -1),  3, C_PURPLE),   # left accent stripe
        ]))
        story.append(narrative_tbl)
        story.append(Spacer(1, 16))

    # ─────────────────────────────────────────────────────────────
    # SECTION 4 — SCAN HISTORY TABLE
    # Columns: thumbnail | date | skin type | confidence | concerns
    # ─────────────────────────────────────────────────────────────
    story.append(
        Paragraph(
            'Scan History',
            S('SH2', fontSize=12, fontName='Helvetica-Bold',
              textColor=C_DARK, spaceAfter=6, leading=15)
        )
    )

    COL_W = [14*mm, 38*mm, 32*mm, 28*mm, CONTENT_W - 14*mm - 38*mm - 32*mm - 28*mm]

    # Header row
    def _th(text):
        return Paragraph(
            f'<b>{text}</b>',
            S(f'th_{text}', fontSize=8, textColor=C_WHITE,
              fontName='Helvetica-Bold', alignment=TA_LEFT, leading=10)
        )

    scan_rows = [[_th('Photo'), _th('Date & Time'), _th('Skin Type'),
                  _th('Confidence'), _th('Concerns Detected')]]

    for idx, a in enumerate(s['analyses']):
        # Thumbnail
        thumb = ''
        if a.get('normalized_image_b64'):
            img = b64_img(a['normalized_image_b64'], 11, 11)
            if img:
                thumb = img

        # Skin type badge (coloured text)
        sk_col = SKIN_COLOR.get(a['skin_type'], C_PURPLE)
        skin_p = Paragraph(
            f'<b>{a["skin_type"]}</b>',
            S(f'sk_{idx}', fontSize=8.5, textColor=sk_col,
              fontName='Helvetica-Bold', leading=11)
        )

        # Confidence bar label
        conf_p = Paragraph(
            f'{a["confidence"]}%',
            S(f'cf_{idx}', fontSize=8.5, textColor=C_DARK_MID, leading=11)
        )

        # Concerns — comma-separated with severity colour
        if a['concerns']:
            concern_parts = []
            for c in a['concerns'][:4]:   # cap at 4 to prevent overflow
                sev = c['severity']
                col = ('#DC2626' if sev == 'severe'
                       else '#D97706' if sev == 'moderate'
                       else '#059669')
                concern_parts.append(
                    f'<font color="{col}">{c["label"]}</font>'
                )
            concerns_p = Paragraph(
                ' · '.join(concern_parts),
                S(f'cn_{idx}', fontSize=7.5, leading=11, textColor=C_DARK_MID)
            )
        else:
            concerns_p = Paragraph(
                '<font color="#9CA3AF">None detected</font>',
                S(f'cn_{idx}_none', fontSize=7.5, leading=11)
            )

        date_p = Paragraph(
            a['date'],
            S(f'dt_{idx}', fontSize=8, textColor=C_DARK_MID, leading=11)
        )

        row_bg = C_WHITE if idx % 2 == 0 else C_PURPLE_XLT
        scan_rows.append([thumb, date_p, skin_p, conf_p, concerns_p])

    scan_tbl = Table(scan_rows, colWidths=COL_W, repeatRows=1)
    # Build alternating row styles
    row_styles = [
        ('BACKGROUND',    (0, 0), (-1, 0),  C_PURPLE),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  C_WHITE),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  8),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 7),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 7),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',          (0, 0), (-1, -1), 0.25, C_BORDER),
        ('LINEBELOW',     (0, 0), (-1, 0),  1,    C_PURPLE_MID),
    ]
    for i in range(1, len(scan_rows)):
        bg = C_WHITE if i % 2 == 1 else C_PURPLE_XLT
        row_styles.append(('BACKGROUND', (0, i), (-1, i), bg))

    scan_tbl.setStyle(TableStyle(row_styles))
    story.append(scan_tbl)
    story.append(Spacer(1, 18))

    # ─────────────────────────────────────────────────────────────
    # SECTION 5 — DETECTED CONCERNS (with zone images)
    # One "card" per concern: header row + optional annotated images.
    # ─────────────────────────────────────────────────────────────
    if s['concerns']:
        story.append(
            Paragraph(
                'Detected Skin Concerns',
                S('SH3', fontSize=12, fontName='Helvetica-Bold',
                  textColor=C_DARK, spaceAfter=6, leading=15)
            )
        )

        for key, c in s['concerns'].items():
            avg = c['avg']
            sev = ('Severe' if avg > 0.55 else
                   'Moderate' if avg > 0.25 else 'Mild')
            sev_col    = C_RED   if sev == 'Severe'   else (C_AMBER   if sev == 'Moderate'   else C_GREEN)
            sev_bg     = C_RED_LT if sev == 'Severe'  else (C_AMBER_LT if sev == 'Moderate'  else C_GREEN_LT)

            # Collect up to 3 annotated zone images for this concern
            zone_imgs = []
            for analysis in s['analyses']:
                for cn in analysis.get('concerns', []):
                    if cn['concern_type'] == key and cn.get('annotated_image_b64'):
                        img = b64_img(cn['annotated_image_b64'], 28, 28)
                        if img:
                            zone_imgs.append(img)
                    if len(zone_imgs) >= 3:
                        break
                if len(zone_imgs) >= 3:
                    break

            # ── Concern header row ─────────────────────────────
            pct = round(avg * 100)
            header_cells = [
                # Concern name + scan count
                Paragraph(
                    f'<b>{c["label"]}</b>  '
                    f'<font color="#9CA3AF" size="8">({c["count"]} scan'
                    f'{"s" if c["count"] > 1 else ""})</font>',
                    S(f'clbl_{key}', fontSize=10.5, fontName='Helvetica-Bold',
                      textColor=C_DARK, leading=14)
                ),
                # Severity badge
                Paragraph(
                    f'<b>{sev}</b>',
                    S(f'csev_{key}', fontSize=9, fontName='Helvetica-Bold',
                      textColor=sev_col, alignment=TA_CENTER, leading=12)
                ),
                # Percentage
                Paragraph(
                    f'<b>{pct}%</b> avg confidence',
                    S(f'cpct_{key}', fontSize=9, textColor=C_DARK_MID,
                      alignment=TA_RIGHT, leading=12)
                ),
            ]
            c_hdr = Table(
                [header_cells],
                colWidths=[CONTENT_W * 0.50, CONTENT_W * 0.20, CONTENT_W * 0.30],
            )
            c_hdr.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), C_PURPLE_XLT),
                ('TOPPADDING',    (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING',   (0, 0), (0, 0),   10),
                ('LEFTPADDING',   (1, 0), (-1, -1), 6),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
                ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                # Left accent stripe in severity colour
                ('LINEAFTER',     (0, 0), (0, 0),   0,   C_PURPLE_XLT),
                ('LINEBEFORE',    (0, 0), (0, -1),  4,   sev_col),
            ]))

            concern_block = [c_hdr]

            # ── Zone images row ────────────────────────────────
            if zone_imgs:
                # Pad to 3 cells
                while len(zone_imgs) < 3:
                    zone_imgs.append('')
                img_row = Table(
                    [zone_imgs],
                    colWidths=[CONTENT_W / 3] * 3,
                )
                img_row.setStyle(TableStyle([
                    ('BACKGROUND',    (0, 0), (-1, -1), C_WHITE),
                    ('TOPPADDING',    (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                    ('LINEBEFORE',    (0, 0), (0, -1),  4, sev_col),
                    ('GRID',          (0, 0), (-1, -1), 0.25, C_BORDER),
                ]))
                concern_block.append(img_row)

            # ── Notes (from first matching concern) ───────────
            notes_text = ''
            for analysis in s['analyses']:
                for cn in analysis.get('concerns', []):
                    if cn['concern_type'] == key and cn.get('notes'):
                        notes_text = cn['notes']
                        break
                if notes_text:
                    break

            if notes_text:
                notes_tbl = Table(
                    [[Paragraph(
                        f'<font color="#6B7280"><b>Recommendation: </b></font>{notes_text}',
                        S(f'cnotes_{key}', fontSize=8.5, textColor=C_DARK_MID,
                          leading=13, alignment=TA_JUSTIFY)
                    )]],
                    colWidths=[CONTENT_W],
                )
                notes_tbl.setStyle(TableStyle([
                    ('BACKGROUND',    (0, 0), (-1, -1), C_WHITE),
                    ('TOPPADDING',    (0, 0), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
                    ('LINEBEFORE',    (0, 0), (0, -1),  4, sev_col),
                    ('GRID',          (0, 0), (-1, -1), 0.25, C_BORDER),
                ]))
                concern_block.append(notes_tbl)

            # Thin separator below each concern card
            concern_block.append(Spacer(1, 10))

            story.append(KeepTogether(concern_block))

        story.append(Spacer(1, 6))

    # ─────────────────────────────────────────────────────────────
    # SECTION 6 — FOOTER DISCLAIMER
    # ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f'Generated by Lumera on {datetime.utcnow().strftime("%B %d, %Y")}. '
            'This report is for informational purposes only and does not '
            'constitute medical advice. Consult a dermatologist for clinical '
            'evaluation.',
            S('disc', fontSize=7.5, textColor=C_GRAY_LT,
              alignment=TA_CENTER, leading=11)
        )
    )

    doc.build(story)
    return buf