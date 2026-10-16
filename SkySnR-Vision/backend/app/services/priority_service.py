"""Explainable review-priority score. An operational review aid only:
it is NOT a prediction of survival, injury or rescue success."""
import math

PERSON_POINTS = 20
OBSTACLE_POINTS = 15
OBSTACLE_CAP = 45
MULTI_PEOPLE_POINTS = 10
URGENT_POINTS = 25
MAX_SCORE = 100


def level_for(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _centre(b):
    return (b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)


def _is_near(person_box, other_box, factor: float) -> bool:
    """Image-space rule only: centres within `factor` x the person box diagonal.
    This does not establish physical distance."""
    diag = math.hypot(person_box["width"], person_box["height"])
    (px, py), (ox, oy) = _centre(person_box), _centre(other_box)
    return math.hypot(px - ox, py - oy) <= factor * diag


def compute_priority(person, all_detections, *, person_classes, obstacle_classes,
                     proximity_factor=3.0, urgent=False) -> dict:
    breakdown = []
    if (person.get("object_class") or "").lower() not in person_classes:
        return {"score": 0, "level": "low", "breakdown": [],
                "explanation": "Selected detection is not a person class, so no score factors apply."}

    score = PERSON_POINTS
    breakdown.append({"factor": "person_detected", "points": PERSON_POINTS,
                      "detail": "A person detection exists (model prediction, unconfirmed)."})

    others = [d for d in all_detections if str(d["_id"]) != str(person["_id"])]
    near_obstacles = []
    if obstacle_classes:
        near_obstacles = [d for d in others
                          if (d.get("object_class") or "").lower() in obstacle_classes
                          and _is_near(person["bounding_box"], d["bounding_box"], proximity_factor)]
    pts = min(len(near_obstacles) * OBSTACLE_POINTS, OBSTACLE_CAP)
    if pts:
        score += pts
        breakdown.append({"factor": "nearby_obstacles", "points": pts,
                          "detail": f"{len(near_obstacles)} obstacle detection(s) within the image-space "
                                    f"proximity rule (capped at +{OBSTACLE_CAP})."})

    near_people = [d for d in others
                   if (d.get("object_class") or "").lower() in person_classes
                   and _is_near(person["bounding_box"], d["bounding_box"], proximity_factor)]
    if near_people:
        score += MULTI_PEOPLE_POINTS
        breakdown.append({"factor": "multiple_people_nearby", "points": MULTI_PEOPLE_POINTS,
                          "detail": f"{len(near_people)} other person detection(s) within the proximity rule."})

    if urgent:
        score += URGENT_POINTS
        breakdown.append({"factor": "manager_urgent_flag", "points": URGENT_POINTS,
                          "detail": "Urgent flag entered by the manager."})

    score = min(score, MAX_SCORE)
    level = level_for(score)
    parts = "; ".join(f"{b['factor'].replace('_', ' ')} +{b['points']}" for b in breakdown)
    note = "" if obstacle_classes else " No obstacle classes are configured, so the obstacle factor was not applied."
    return {"score": score, "level": level, "breakdown": breakdown,
            "explanation": f"Score {score}/100 ({level}): {parts}.{note} Review aid only."}
