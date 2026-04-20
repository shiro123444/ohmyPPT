from types import SimpleNamespace

import pytest

from landppt.services.prompts import design_prompts as prompts_module
from landppt.services.slide.creative_design_service import CreativeDesignService


def test_single_slide_html_prompt_includes_presentation_spec_context(monkeypatch):
    monkeypatch.setattr(prompts_module, "_is_image_service_enabled", lambda: False)

    prompt = prompts_module.DesignPrompts.get_single_slide_html_prompt(
        slide_data={"title": "增长机会", "slide_type": "content", "content_points": ["渠道扩张", "品牌升级"]},
        confirmed_requirements={"topic": "年度复盘"},
        page_number=2,
        total_pages=8,
        context_info="普通内容页",
        style_genes="色彩克制，强调对比。",
        presentation_spec_context="**Phase 1 Presentation Spec 约束**\n- 期望布局家族：content\n- 内容密度：medium",
    )

    assert "Phase 1 Presentation Spec 约束" in prompt
    assert "期望布局家族：content" in prompt
    assert "内容密度：medium" in prompt


@pytest.mark.asyncio
async def test_creative_template_context_includes_presentation_spec_context(monkeypatch):
    monkeypatch.setattr(prompts_module, "_is_image_service_enabled", lambda: False)

    presentation_spec = {
        "deck_meta": {"generation_mode": "professional"},
        "theme_spec": {"template_mode": "global", "style_family": "conference"},
        "slide_specs": [
            {
                "slide_id": "slide-02",
                "page_number": 2,
                "title": "增长机会",
                "visual_priority": "message",
                "layout_constraints": {
                    "preferred_family": "content",
                    "density": "medium",
                    "emphasis": "message",
                },
                "image_policy": {"usage": "supporting", "image_slots": 1},
                "chart_policy": {"needs_chart": False, "preferred_chart_type": None},
                "content_blocks": [
                    {"block_type": "title"},
                    {"block_type": "bullet_list"},
                ],
                "notes": "突出渠道扩张与品牌升级。",
            }
        ],
    }

    class _FakeProjectManager:
        async def get_project(self, project_id, user_id=None):
            assert project_id == "project-1"
            return SimpleNamespace(
                presentation_spec=presentation_spec,
                project_metadata={"presentation_spec": presentation_spec},
            )

    owner = SimpleNamespace(
        project_manager=_FakeProjectManager(),
        user_id=None,
    )

    async def _noop_ensure(*args, **kwargs):
        return None

    async def _no_images(*args, **kwargs):
        return None

    owner._ensure_slide_images_context = _noop_ensure
    owner._process_slide_image = _no_images
    owner._build_slide_context = lambda *args, **kwargs: "普通内容页"

    service = CreativeDesignService(owner)
    service._get_creative_design_inputs = _noop_design_inputs = _make_design_inputs_stub()
    service._ensure_slide_images_context = _noop_ensure
    service._process_slide_image = _no_images
    slide_data = {
        "title": "增长机会",
        "slide_type": "content",
        "content_points": ["渠道扩张", "品牌升级"],
    }

    prompt = await service._build_creative_template_context(
        slide_data=slide_data,
        template_html="<main>{{ page_content }}</main>",
        template_name="模板A",
        page_number=2,
        total_pages=8,
        confirmed_requirements={"topic": "年度复盘"},
        project_id="project-1",
    )

    assert "Phase 1 Presentation Spec 约束" in prompt
    assert "模板模式：global" in prompt
    assert "期望布局家族：content" in prompt
    assert slide_data["render_hints"]["layout_family"] == "content"
    assert slide_data["presentation_spec_slide_spec"]["page_number"] == 2


def _make_design_inputs_stub():
    async def _design_inputs(*args, **kwargs):
        return ("色彩克制，强调对比。", "", "")

    return _design_inputs
