"""Phase 15: PDF case dossier (ReportLab)."""
import io, math
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Circle, Line, String, Polygon
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

DISCLAIMER = "Automated analytical output for investigation support. This report does not establish criminal conduct and requires human review."
NAVY, ORANGE = colors.HexColor("#0b1b3a"), colors.HexColor("#f97316")


def _snapshot(inv):
    d = Drawing(480, 250)
    nodes = [a["account_id"] for a in inv["accounts"]]
    key, pos = inv["key_intermediary"], {}
    for i, a in enumerate(nodes):
        ang = 2 * math.pi * i / len(nodes)
        pos[a] = (240 + 170 * math.cos(ang), 125 + 95 * math.sin(ang))
    for t in inv["timeline"]:
        (x1, y1), (x2, y2) = pos[t["sender_account"]], pos[t["receiver_account"]]
        d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#64748b"), strokeWidth=1))
        ax, ay = x1 + (x2 - x1) * .8, y1 + (y2 - y1) * .8
        ang = math.atan2(y2 - y1, x2 - x1)
        d.add(Polygon([ax, ay, ax - 7 * math.cos(ang - .4), ay - 7 * math.sin(ang - .4),
                       ax - 7 * math.cos(ang + .4), ay - 7 * math.sin(ang + .4)], fillColor=colors.HexColor("#64748b"), strokeWidth=0))
    for a, (x, y) in pos.items():
        d.add(Circle(x, y, 7, fillColor=ORANGE if a == key else colors.HexColor("#2563eb"), strokeWidth=0))
        d.add(String(x, y - 17, a, fontSize=7, textAnchor="middle"))
    return d


def build_pdf(inv, explanation, whatif, account):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"TRACEFLOW {inv['case_id']}")
    ss = getSampleStyleSheet()
    H = ParagraphStyle("h", parent=ss["Heading2"], textColor=NAVY, spaceBefore=10)
    B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=13)
    inr = lambda n: f"INR {int(n):,}"

    def table(rows, widths=None, head=True):
        t = Table(rows, colWidths=widths, repeatRows=1 if head else 0)
        st = [("FONTSIZE", (0, 0), (-1, -1), 7.5), ("GRID", (0, 0), (-1, -1), .25, colors.lightgrey),
              ("VALIGN", (0, 0), (-1, -1), "TOP")]
        if head:
            st += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
        t.setStyle(TableStyle(st)); return t

    s = [Paragraph("<font color='#2563eb'>TRACE</font>FLOW", ParagraphStyle("t", fontSize=26, textColor=NAVY, fontName="Helvetica-Bold")),
         Paragraph("Temporal Graph Intelligence for Financial Crime Investigation", B), Spacer(1, 8),
         Paragraph(f"Case Dossier {inv['case_id']}", ss["Title"]),
         table([["Case ID", inv["case_id"]], ["Network ID", inv["id"]], ["Investigation date", datetime.now().strftime("%Y-%m-%d %H:%M")],
                ["Investigated account", account], ["Participating accounts", ", ".join(a["account_id"] for a in inv["accounts"])],
                ["Participating banks", ", ".join(inv["banks"])], ["Detected patterns", ", ".join(inv["pattern_types"])],
                ["Total amount", inr(inv["total_amount"])]], [45 * mm, 125 * mm], head=False),
         Paragraph("Investigation priority", H),
         Paragraph(f"<b>{inv['risk']['score']} / 100 - {inv['risk']['level']}</b> (priority indicator, not a probability of criminal activity)", B),
         table([["Factor", "Score", "Max"]] + [[f["name"], f["score"], f["max"]] for f in inv["risk"]["factors"]], [90 * mm, 30 * mm, 30 * mm]),
         Paragraph("Why flagged", H)] + [Paragraph("- " + e, B) for e in inv["evidence"]]
    d = inv["dna"]
    s += [Paragraph("Network DNA", H),
          table([["Accounts", d["accounts"], "Transactions", d["transactions"]],
                 ["Circularity", f"{d['circularity']}%", "Velocity", d["velocity"]],
                 ["Amount retention", f"{d['retention']}%" if d["retention"] is not None else "n/a", "Cross-bank", "YES" if d["cross_bank"] else "NO"],
                 ["Smurfing", "YES" if d["smurfing"] else "NO", "Mule-chain", "YES" if d["mule_chain"] else "NO"]], head=False),
          Paragraph("Explanation", H), Paragraph(explanation["text"], B), Paragraph("Graph snapshot", H), _snapshot(inv)]
    if whatif:
        a, b = whatif["after"], whatif["before"]
        s += [Paragraph("What-if simulation (hypothetical)", H),
              Paragraph(f"Removing <b>{whatif['removed_account']}</b>. {whatif['label']}.", B),
              table([["Metric", "Before", "After"], ["Network connectivity", "100%", f"{whatif['connectivity_after']}%"],
                     ["Reachable pairs", b["reachable_pairs"], a["reachable_pairs"]], ["Paths", b["paths"], a["paths"]],
                     ["Cycles", b["cycles"], a["cycles"]], ["Components", b["components"], a["components"]],
                     ["Transactions disrupted", "-", f"{whatif['disrupted_transactions']} of {whatif['total_transactions']}"]], [70 * mm, 40 * mm, 40 * mm])]
    s += [Paragraph("Transaction timeline / evidence", H),
          table([["Transaction", "Timestamp", "From", "To", "Banks", "Amount"]] +
                [[t["transaction_id"], t["timestamp"].replace("T", " "), t["sender_account"], t["receiver_account"],
                  f"{t['sender_bank']}>{t['receiver_bank']}", f"{int(t['amount']):,}"] for t in inv["timeline"][:60]],
                [24 * mm, 36 * mm, 20 * mm, 20 * mm, 40 * mm, 26 * mm]),
          Spacer(1, 12), Paragraph(f"<i>{DISCLAIMER}</i>", B)]
    doc.build(s)
    return buf.getvalue()
