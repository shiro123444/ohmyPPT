from types import SimpleNamespace

import pytest

from landppt.database.service import DatabaseService
from landppt.services.presentation.presentation_spec_service import PresentationSpecService


def _sample_outline():
    return {
        "title": "AI 战略汇报",
        "metadata": {"theme_config": {"primary": "#111111", "accent": "#ff6600"}},
        "slides": [
            {
                "page_number": 1,
                "title": "AI 战略汇报",
                "content_points": ["2026 规划", "经营委员会汇报"],
                "slide_type": "title",
            },
            {
                "page_number": 2,
                "title": "年度关键指标趋势",
                "content_points": ["收入增长 32%", "利润率提升 8%", "客户留存持续改善"],
                "slide_type": "content",
                "chart_config": {"type": "line", "series": [1, 2, 3]},
                "description": "突出核心增长指标和经营杠杆。",
            },
            {
                "page_number": 3,
                "title": "总结与下一步",
                "content_points": ["聚焦交付", "压缩试点周期"],
                "slide_type": "conclusion",
            },
        ],
    }


def test_presentation_spec_service_builds_phase1_spec():
    service = PresentationSpecService()
    project = SimpleNamespace(
        project_id="project-1",
        title="AI 战略汇报 - general",
        topic="AI 战略汇报",
        scenario="general",
        requirements="更偏董事会风格",
        project_metadata={
            "network_mode": True,
            "language": "zh",
            "template_mode": "global",
            "selected_global_template_id": 7,
            "presentation_mode": "professional",
        },
        confirmed_requirements={"ppt_style": "conference"},
        created_at=100.0,
        updated_at=120.0,
    )

    spec = service.build_for_project(project, _sample_outline())

    assert spec["schema_version"] == "1.0"
    assert spec["deck_meta"]["generation_mode"] == "professional"
    assert spec["theme_spec"]["template_mode"] == "global"
    assert spec["theme_spec"]["selected_template_id"] == 7
    assert spec["render_target"]["primary"] == "html"
    assert spec["render_target"]["pptx_compilation_ready"] is False
    assert spec["theme_spec"]["design_tokens"]["primary"] == "#111111"
    assert len(spec["slide_specs"]) == 3
    assert spec["slide_specs"][0]["visual_priority"] == "opening"
    assert spec["slide_specs"][1]["chart_policy"]["needs_chart"] is True
    assert spec["slide_specs"][1]["image_policy"]["source_preferences"] == ["local", "network", "ai_generated"]
    assert spec["outline_spec"]["slide_order"] == ["slide-01", "slide-02", "slide-03"]


def test_presentation_spec_service_preserves_top_level_theme_config():
    service = PresentationSpecService()
    project = SimpleNamespace(
        project_id="project-theme",
        title="AI 战略汇报 - general",
        topic="AI 战略汇报",
        scenario="general",
        requirements="更偏董事会风格",
        project_metadata={"network_mode": True, "language": "zh"},
        confirmed_requirements={"ppt_style": "conference"},
        created_at=100.0,
        updated_at=120.0,
    )
    outline = _sample_outline()
    outline["theme_config"] = {"surface": "paper", "primary": "#222222"}

    spec = service.build_for_project(project, outline)

    assert spec["theme_spec"]["design_tokens"]["surface"] == "paper"
    assert spec["theme_spec"]["design_tokens"]["primary"] == "#111111"
    assert spec["theme_spec"]["design_tokens"]["accent"] == "#ff6600"


def test_presentation_spec_service_resolves_render_plan():
    service = PresentationSpecService()
    project = SimpleNamespace(
        project_id="project-render",
        title="AI 战略汇报 - general",
        topic="AI 战略汇报",
        scenario="general",
        requirements="更偏董事会风格",
        project_metadata={"network_mode": True, "language": "zh"},
        confirmed_requirements={"ppt_style": "conference"},
        created_at=100.0,
        updated_at=120.0,
    )

    spec = service.build_for_project(project, _sample_outline())
    render_plan = PresentationSpecService.resolve_render_plan(
        presentation_spec=spec,
        slide_data={"page_number": 2, "title": "年度关键指标趋势"},
        page_number=2,
    )

    assert render_plan["slide_spec"]["page_number"] == 2
    assert render_plan["render_hints"]["layout_family"] == "content"
    assert render_plan["render_hints"]["needs_chart"] is True
    assert render_plan["render_hints"]["fallback_variant"] == "data-spotlight"
    assert "fallback 版式变体：data-spotlight" in render_plan["prompt_context"]


def test_database_service_convert_db_project_exposes_presentation_spec():
    service = DatabaseService(None)
    db_project = SimpleNamespace(
        project_id="project-2",
        title="Title",
        scenario="general",
        topic="Topic",
        requirements=None,
        status="draft",
        outline={"slides": [{"title": "封面"}]},
        slides_html="",
        slides_data=None,
        confirmed_requirements=None,
        project_metadata={
            "presentation_spec": {
                "schema_version": "1.0",
                "deck_meta": {"title": "Topic"},
            }
        },
        todo_board=None,
        version=1,
        versions=[],
        slides=[],
        created_at=1.0,
        updated_at=2.0,
    )

    project = service._convert_db_project_to_api(db_project)

    assert project.presentation_spec == {
        "schema_version": "1.0",
        "deck_meta": {"title": "Topic"},
    }


@pytest.mark.asyncio
async def test_update_project_refreshes_presentation_spec_when_metadata_changes():
    outline = _sample_outline()
    project = SimpleNamespace(
        project_id="project-2b",
        title="AI 战略汇报",
        topic="AI 战略汇报",
        scenario="general",
        requirements="保留品牌感",
        outline=outline,
        confirmed_requirements={"ppt_style": "general"},
        project_metadata={
            "template_mode": "default",
            "language": "zh",
            "presentation_spec": {"stale": True},
        },
        created_at=1.0,
        updated_at=2.0,
    )
    service = DatabaseService(None)
    service.project_repo = _FakeProjectRepo(project)

    success = await service.update_project(
        "project-2b",
        {"project_metadata": {"template_mode": "global", "selected_global_template_id": 99}},
    )

    assert success is True
    spec = service.project_repo.updated_payload["project_metadata"]["presentation_spec"]
    assert spec["theme_spec"]["template_mode"] == "global"
    assert spec["theme_spec"]["selected_template_id"] == 99


class _FakeProjectRepo:
    def __init__(self, project):
        self.project = project
        self.updated_payload = None

    async def get_by_id(self, project_id, user_id=None):
        assert project_id == self.project.project_id
        return self.project

    async def update(self, project_id, update_data, user_id=None):
        assert project_id == self.project.project_id
        self.updated_payload = dict(update_data)
        for key, value in update_data.items():
            setattr(self.project, key, value)
        return self.project


@pytest.mark.asyncio
async def test_save_project_outline_merges_presentation_spec_into_project_metadata():
    outline = _sample_outline()
    project = SimpleNamespace(
        project_id="project-3",
        title="AI 战略汇报",
        topic="AI 战略汇报",
        scenario="general",
        requirements="保留品牌感",
        outline=None,
        confirmed_requirements={"ppt_style": "general"},
        project_metadata={"template_mode": "free", "free_template_status": "ready"},
        created_at=1.0,
        updated_at=2.0,
    )

    service = DatabaseService(None)
    service.project_repo = _FakeProjectRepo(project)

    success = await service.save_project_outline("project-3", outline)

    assert success is True
    assert service.project_repo.updated_payload is not None
    assert service.project_repo.updated_payload["outline"] == outline
    assert service.project_repo.updated_payload["project_metadata"]["template_mode"] == "free"
    assert service.project_repo.updated_payload["project_metadata"]["free_template_status"] == "ready"
    assert service.project_repo.updated_payload["project_metadata"]["presentation_spec"]["deck_meta"]["title"] == "AI 战略汇报"
    assert service.project_repo.updated_payload["project_metadata"]["presentation_spec_version"] == "1.0"
