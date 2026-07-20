"""Seed a demo organization, owner user, and default agent on first startup.

Makes the platform usable immediately (no external services). Idempotent: it
does nothing if the demo org already exists.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.tools.registry import tool_names
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.org import Org
from app.models.role import Role
from app.models.user import User


def _slugify(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "demo"


def seed_demo_data() -> None:
    if not settings.SEED_DEMO_DATA:
        return
    db: Session = SessionLocal()
    try:
        slug = _slugify(settings.DEMO_ORG_NAME)
        if db.query(Org).filter(Org.slug == slug).first() is not None:
            return

        org = Org(name=settings.DEMO_ORG_NAME, slug=slug, plan="pro")
        db.add(org)
        db.flush()

        user = User(
            org_id=org.id,
            email=settings.DEMO_EMAIL,
            hashed_password=hash_password(settings.DEMO_PASSWORD),
            role=Role.OWNER.value,
        )
        db.add(user)

        agent = Agent(
            org_id=org.id,
            name="Workspace Assistant",
            description="A general-purpose assistant with calculator, notes, and time tools.",
            system_prompt="You are a helpful enterprise workspace assistant.",
        )
        agent.tools = tool_names()
        db.add(agent)

        db.commit()
    finally:
        db.close()
