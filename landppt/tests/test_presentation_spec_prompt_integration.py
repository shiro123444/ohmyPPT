from landppt.services.prompts import design_prompts as prompts_module


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
