"""Tests for content management pipeline."""

from funnel_optimizer.models import Brief, Content
from funnel_optimizer.pipeline.content import (
    add_brief,
    add_content,
    approve_content,
    get_brief,
    get_content,
    list_briefs,
    list_content,
)


def test_add_and_get_brief(db):
    brief = Brief(name="Test Brief", project_type="Bathroom", geo="DFW", budget_cents=5000)
    brief_id = add_brief(brief, db)
    assert brief_id == 1

    result = get_brief(1, db)
    assert result is not None
    assert result.name == "Test Brief"
    assert result.project_type == "Bathroom"
    assert result.budget_cents == 5000
    assert result.status == "draft"


def test_list_briefs(db):
    add_brief(Brief(name="A", project_type="Bath", geo="DFW", budget_cents=0), db)
    add_brief(Brief(name="B", project_type="Kitchen", geo="Houston", budget_cents=0), db)

    briefs = list_briefs(db)
    assert len(briefs) == 2
    assert briefs[0].name == "A"
    assert briefs[1].name == "B"


def test_add_and_get_content(db):
    add_brief(Brief(name="B", project_type="Bath", geo="DFW", budget_cents=0), db)
    content = Content(brief_id=1, headline="Great Bathroom", primary_text="Get a quote")
    content_id = add_content(content, db)
    assert content_id == 1

    result = get_content(1, db)
    assert result is not None
    assert result.headline == "Great Bathroom"
    assert result.status == "draft"


def test_approve_content(db):
    add_brief(Brief(name="B", project_type="Bath", geo="DFW", budget_cents=0), db)
    add_content(Content(brief_id=1, headline="H", primary_text="P"), db)

    assert approve_content(1, db) is True
    result = get_content(1, db)
    assert result.status == "approved"


def test_approve_nonexistent_content(db):
    assert approve_content(999, db) is False


def test_list_content_filtered(db):
    add_brief(Brief(name="A", project_type="Bath", geo="DFW", budget_cents=0), db)
    add_brief(Brief(name="B", project_type="Kitchen", geo="DFW", budget_cents=0), db)
    add_content(Content(brief_id=1, headline="H1", primary_text="P1"), db)
    add_content(Content(brief_id=2, headline="H2", primary_text="P2"), db)

    all_content = list_content(conn=db)
    assert len(all_content) == 2

    filtered = list_content(brief_id=1, conn=db)
    assert len(filtered) == 1
    assert filtered[0].headline == "H1"
