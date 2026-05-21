from __future__ import annotations

class DefectPredictor:
    """Stub. Full implementation requires labeled bug-fix history (SZZ/DeepJIT)."""

    def predict(self, diff_content: str, commit_message: str) -> dict:
        return {"risk_score": None, "reason": "insufficient_history"}
