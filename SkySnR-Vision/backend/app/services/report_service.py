"""PDF evidence reports built only from persisted records."""
from pathlib import Path
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

from ..config import get_settings

BALSAM = colors.HexColor("#65736E")
SAGE = colors.HexColor("#ADB9AD")


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M UTC") if dt else "Not recorded"


def _annotated(media_path: Path, boxes: list[dict], out: Path):
    if not media_path.exists():
        return None
    with Image.open(media_path) as im:
        im = im.convert("RGB")
        d = ImageDraw.Draw(im)
        for b in boxes:
            bb = b["bounding_box"]
            d.rectangle([bb["x"], bb["y"], bb["x"] + bb["width"], bb["y"] + bb["height"]],
                        outline="#B4785E", width=max(2, im.width // 300))
        im.thumbnail((1400, 1400))
        im.save(out, "JPEG", quality=85)
    return out


def build_report(path: Path, *, mission, detections, incidents, events_by_incident, users, generated_by) -> None:
    s = get_settings()
    styles = getSampleStyleSheet()
    h = styles["Heading2"]
    h.textColor = BALSAM
    body = styles["BodyText"]
    story = [Paragraph("SkySnR Vision — Evidence Report", styles["Title"]),
             Paragraph(f"Generated {_fmt(generated_by['at'])} by {generated_by['name']}", body),
             Paragraph("Decision-support record. AI predictions are unconfirmed unless marked as "
                       "manager-confirmed.", body),
             Spacer(1, 6 * mm), Paragraph("Mission", h)]
    rows = [["Mission", mission.get("mission_name", "")], ["Mission ID", str(mission["_id"])],
            ["Disaster type", mission.get("disaster_type", "Not recorded")],
            ["Terrain", mission.get("terrain_type", "Not recorded")],
            ["Location", mission.get("location_description") or "Not recorded"],
            ["Created", _fmt(mission.get("created_at"))], ["Status", mission.get("status", "")]]
    t = Table(rows, colWidths=[40 * mm, 120 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, SAGE), ("BACKGROUND", (0, 0), (0, -1), SAGE)]))
    story += [t, Spacer(1, 5 * mm),
              Paragraph("Evidence image (boxes drawn from stored model output)", h)]

    media = mission.get("media_reference")
    img = _annotated(s.media_dir / media, detections, path.with_suffix(".evidence.jpg")) if media else None
    if img:
        with Image.open(img) as im:
            ratio = im.height / im.width
        story.append(RLImage(str(img), width=160 * mm, height=160 * mm * ratio))
    else:
        story.append(Paragraph("Evidence image not available.", body))

    story += [Spacer(1, 5 * mm), Paragraph("Detections (AI model output)", h)]
    if detections:
        rows = [["Class", "Confidence", "Review", "Score", "Level"]]
        for d in detections:
            rows.append([d["object_class"], f"{d['confidence']:.2f}", d.get("review_status", "unreviewed"),
                         str(d.get("priority_score", "-")), d.get("priority_level", "-")])
        t = Table(rows, repeatRows=1)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, SAGE), ("BACKGROUND", (0, 0), (-1, 0), SAGE)]))
        story.append(t)
    else:
        story.append(Paragraph("No detections stored for this mission.", body))

    story += [Spacer(1, 5 * mm), Paragraph("Manager-confirmed incidents", h)]
    if not incidents:
        story.append(Paragraph("No incidents have been created from this mission.", body))
    for inc in incidents:
        member = users.get(str(inc.get("assigned_member_id")))
        story.append(Paragraph(f"Incident {inc['_id']}", styles["Heading3"]))
        rows = [["Priority", f"{inc.get('priority_score')} ({inc.get('priority_level')})"],
                ["Score explanation", Paragraph(inc.get("explanation", ""), body)],
                ["Manager notes", Paragraph(inc.get("manager_notes") or "None recorded", body)],
                ["Verification", inc.get("verification_status", "")],
                ["Assigned to", member["full_name"] if member else "Not assigned"],
                ["Status", inc.get("status", "")],
                ["Outcome", Paragraph(inc.get("outcome") or "Not recorded", body)]]
        t = Table(rows, colWidths=[40 * mm, 120 * mm])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, SAGE), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story += [t, Spacer(1, 2 * mm), Paragraph("Timeline", body)]
        ev = events_by_incident.get(str(inc["_id"]), [])
        rows = [["When", "Event", "By", "Notes"]] + [
            [_fmt(e["timestamp"]), e["event_type"],
             users.get(str(e["performed_by"]), {}).get("full_name", "Unknown"),
             Paragraph(e.get("notes") or "", body)] for e in ev]
        t = Table(rows, repeatRows=1, colWidths=[38 * mm, 32 * mm, 35 * mm, 55 * mm])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, SAGE), ("BACKGROUND", (0, 0), (-1, 0), SAGE),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story += [t, Spacer(1, 4 * mm)]
    SimpleDocTemplate(str(path), pagesize=A4, title="SkySnR Vision Report").build(story)
