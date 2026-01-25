from typing import Any, Dict

from app.extensions import db
from app.models.wizard_session import WizardSession
from app.jobs.wizard_tree import WizardTree

class WizardSessionService:
    def __init__(self, tree: WizardTree):
        self.tree = tree

    def create(self) -> WizardSession:
        ws = WizardSession(path=[], inputs={}, status="draft")
        db.session.add(ws)
        db.session.commit()
        return ws

    def get(self, session_id: int) -> WizardSession:
        return WizardSession.query.get_or_404(session_id)

    def set_choice(self, ws, choice: str):
        """
        Move the session one step by selecting `choice`.
        If the newly selected node resolves to a profile, set ws.profile immediately.
        """
        node = get_node_for_path(ws.path)
        options = node.get("options") or {}
        if choice not in options:
            raise ValueError(f"Invalid choice: {choice}")

        # advance path
        ws.path = list(ws.path or []) + [choice]

        # resolve node at new path
        new_node = get_node_for_path(ws.path)
        profile = new_node.get("profile")
        if profile:
            # set profile immediately when a profile is present on the selected node
            ws.profile = profile

        # Clear any previously computed status that depends on path/inputs
        ws.status = None

        # persist the session (the service should provide save/update)
        try:
            self.save(ws)
        except AttributeError:
            # service may manage persistence differently; fallback to update() if available
            if hasattr(self, "update"):
                self.update(ws)
        return ws

    def back(self, ws: WizardSession) -> WizardSession:
        if ws.path:
            ws.path = ws.path[:-1]
        profile, normalized_path = self.tree.resolve_profile(ws.path or [])
        ws.path = normalized_path
        ws.profile = profile
        ws.status = "ready" if ws.profile else "draft"
        db.session.commit()
        return ws

    def set_inputs(self, ws: WizardSession, inputs: Dict[str, Any]) -> WizardSession:
        merged = dict(ws.inputs or {})
        merged.update(inputs or {})
        ws.inputs = merged
        db.session.commit()
        return ws

    def state(self, ws: WizardSession) -> Dict[str, Any]:
        return {
            "id": ws.id,
            "path": [p for p in (session.path or []) if p != "options"],
            "profile": ws.profile,
            "status": ws.status,
            "inputs": ws.inputs,
            "options": self.tree.options(ws.path or []),
            "is_leaf": bool(ws.profile),
        }