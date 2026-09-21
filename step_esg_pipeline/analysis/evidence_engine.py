import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


@dataclass
class EvidenceItem:
    type: str  # technical, browser, document, authority, currentness, applicability, candidate
    finding: str

    @property
    def detail(self) -> str:
        return self.finding

    def to_dict(self) -> Dict[str, str]:
        return {"type": self.type, "finding": self.finding}


class EvidenceTrail:
    """Manages structured, category-tagged evidence points justifying every pipeline decision."""

    def __init__(self, initial_items: Optional[List[Dict[str, str]]] = None):
        self.items: List[EvidenceItem] = []
        if initial_items:
            for it in initial_items:
                if isinstance(it, dict) and "type" in it and "finding" in it:
                    self.items.append(EvidenceItem(type=it["type"], finding=it["finding"]))
                elif isinstance(it, str):
                    self.items.append(EvidenceItem(type="general", finding=it))

    def add(
        self,
        ev_type: str = "general",
        finding: str = "",
        category: str = "",
        claim: str = "",
        status: str = "",
        confidence: float = 1.0,
        source: str = "",
        detail: str = "",
        **kwargs,
    ) -> "EvidenceTrail":
        t = category or ev_type or "general"
        f = claim or finding or detail or ""
        if detail and claim and detail != claim:
            f = f"{claim} ({detail})"
        elif not f and status:
            f = f"Status: {status}"

        if f:
            clean = f.strip()
            if not any(item.type == t and item.finding == clean for item in self.items):
                self.items.append(EvidenceItem(type=t, finding=clean))
        return self

    def to_list(self) -> List[Dict[str, str]]:
        return [it.to_dict() for it in self.items]

    def to_json(self) -> str:
        return json.dumps(self.to_list(), ensure_ascii=False)

    def to_text_bullets(self) -> str:
        return "\n".join(f"• [{it.type.upper()}] {it.finding}" for it in self.items)

    def summary(self, decision: str = "") -> str:
        return self.summarize_why(decision)

    def summarize_why(self, decision: str = "") -> str:
        """Generates a clear human-readable explanation of Why this decision was made."""
        if not self.items:
            return f"Decision {decision or 'MANUAL_REVIEW'} based on standard regulatory screening."

        why_lines = [f"Why was this marked {decision or 'MANUAL_REVIEW'}?"]
        for idx, it in enumerate(self.items, 1):
            why_lines.append(f"{idx}. ({it.type.capitalize()}): {it.finding}")

        return "\n".join(why_lines)

    @classmethod
    def from_raw(cls, raw: Any) -> "EvidenceTrail":
        if isinstance(raw, EvidenceTrail):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return cls(parsed)
            except Exception:
                pass
            return cls([{"type": "general", "finding": raw}]) if raw else cls()
        if isinstance(raw, list):
            return cls(raw)
        return cls()
