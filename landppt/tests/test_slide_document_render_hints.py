from types import SimpleNamespace

from landppt.services.slide.slide_document_service import SlideDocumentService


def test_fallback_slide_html_uses_agenda_render_hints():
    service = SlideDocumentService(SimpleNamespace())

    html = service._generate_fallback_slide_html(
        {
            "title": "目录",
            "slide_type": "agenda",
            "content_points": ["市场背景", "战略路径", "执行计划", "风险控制"],
            "render_hints": {
                "layout_family": "toc",
                "fallback_variant": "toc-grid",
                "show_page_number": False,
            },
        },
        page_number=2,
        total_pages=10,
    )

    assert 'data-render-variant="toc-grid"' in html
    assert 'data-layout-family="toc"' in html
    assert "SECTION MAP" in html


def test_fallback_slide_html_uses_data_spotlight_render_hints():
    service = SlideDocumentService(SimpleNamespace())

    html = service._generate_fallback_slide_html(
        {
            "title": "年度关键指标趋势",
            "slide_type": "content",
            "content_points": ["收入增长 32%", "利润率提升 8%", "客户留存持续改善"],
            "render_hints": {
                "layout_family": "content",
                "fallback_variant": "data-spotlight",
                "chart_type": "line",
                "show_page_number": True,
            },
        },
        page_number=3,
        total_pages=10,
    )

    assert 'data-render-variant="data-spotlight"' in html
    assert "DATA SPOTLIGHT" in html
    assert "图表类型：line" in html
