from app.db.database import SessionLocal
from app.db.models import User, Skill


def test_create_and_query_user():
    """Verify creating and retrieving a user model in PostgreSQL."""
    db = SessionLocal()
    try:
        user = User(
            email="developer@example.com",
            full_name="Alex River",
            target_role="Backend Engineer",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.email == "developer@example.com"
        assert user.created_at is not None

        # Clean up
        db.delete(user)
        db.commit()
    finally:
        db.close()


def test_create_and_query_skill():
    """Verify creating and retrieving a skill model in PostgreSQL."""
    db = SessionLocal()
    try:
        skill = Skill(
            name="GraphQL",
            slug="graphql",
            category="API Query Languages",
            description="Query language for APIs and runtime for fulfilling those queries.",
        )
        db.add(skill)
        db.commit()
        db.refresh(skill)

        assert skill.id is not None
        assert skill.name == "GraphQL"
        assert skill.slug == "graphql"

        # Clean up
        db.delete(skill)
        db.commit()
    finally:
        db.close()
