import base64
import logging
import tempfile
import urllib.parse
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from ...api.models import SlideContent


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .slide_html_service import SlideHtmlService


class SlideDocumentService:
    """Extracted document/fallback rendering logic for SlideHtmlService."""

    def __init__(self, service: "SlideHtmlService"):
        self._service = service

    def __getattr__(self, name: str):
        return getattr(self._service, name)

    @staticmethod
    def _get_render_hints(slide_data: Dict[str, Any]) -> Dict[str, Any]:
        hints = slide_data.get("render_hints")
        return dict(hints) if isinstance(hints, dict) else {}

    @staticmethod
    def _build_page_number_html(page_number: int, total_pages: int, dark: bool = False) -> str:
        color = "rgba(255,255,255,0.8)" if dark else "#95a5a6"
        background = "rgba(0,0,0,0.2)" if dark else "rgba(255,255,255,0.8)"
        return (
            f'<div style="position: absolute; bottom: 15px; right: 20px; color: {color}; '
            f'font-size: clamp(10px, 1.5vw, 14px); font-weight: 500; background: {background}; '
            'padding: 6px 12px; border-radius: 20px; z-index: 10;">'
            f'第{page_number}页 / 共{total_pages}页</div>'
        )

    @staticmethod
    def _render_content_points(content_points: List[str], item_style: str) -> str:
        return "".join(
            f"<li style=\"{item_style}\">{point}</li>"
            for point in content_points
        )

    def _generate_title_fallback(self, title: str, page_number: int, total_pages: int) -> str:
        return f"""
                <div data-render-variant="cover-hero" data-layout-family="cover" style="
                    text-align: center;
                    width: 100%;
                    aspect-ratio: 16/9;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    margin: 0 auto;
                    box-sizing: border-box;
                    position: relative;
                    max-width: 1200px;
                    padding: 3% 5%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
                    overflow: hidden;
                ">
                    <div style="
                        position: absolute;
                        top: -50%;
                        left: -50%;
                        width: 200%;
                        height: 200%;
                        background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
                        background-size: 50px 50px;
                        animation: float 20s ease-in-out infinite;
                        z-index: 1;
                    "></div>
                    <div style="
                        position: absolute;
                        top: 20%;
                        right: 10%;
                        width: 200px;
                        height: 200px;
                        background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%);
                        border-radius: 50%;
                        z-index: 1;
                    "></div>
                    <div style="
                        position: absolute;
                        bottom: 30%;
                        left: 15%;
                        width: 150px;
                        height: 150px;
                        background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
                        border-radius: 50%;
                        z-index: 1;
                    "></div>
                    <div style="position: relative; z-index: 2;">
                        <h1 style="
                            font-size: clamp(2rem, 5vw, 4rem);
                            color: #ffffff;
                            margin-bottom: clamp(30px, 4vh, 50px);
                            line-height: 1.2;
                            text-shadow: 0 4px 8px rgba(0,0,0,0.3);
                            font-weight: 700;
                            letter-spacing: 1px;
                            background: linear-gradient(45deg, #ffffff, #f8f9fa);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                            background-clip: text;
                        ">{title}</h1>
                        <div style="
                            width: 80px;
                            height: 4px;
                            background: linear-gradient(90deg, #ff6b6b, #4ecdc4, #45b7d1);
                            margin: 0 auto clamp(20px, 3vh, 30px) auto;
                            border-radius: 2px;
                        "></div>
                        <p style="
                            font-size: clamp(1.2rem, 3vw, 2rem);
                            color: rgba(255,255,255,0.9);
                            line-height: 1.4;
                            font-weight: 300;
                            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        ">专业演示文稿</p>
                    </div>
                    {self._build_page_number_html(page_number, total_pages, dark=True)}
                    <style>
                        @keyframes float {{
                            0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
                            50% {{ transform: translateY(-20px) rotate(180deg); }}
                        }}
                    </style>
                </div>
                """

    def _generate_closing_fallback(
        self,
        title: str,
        page_number: int,
        total_pages: int,
        render_hints: Dict[str, Any],
    ) -> str:
        page_number_html = ""
        if render_hints.get("show_page_number", True):
            page_number_html = self._build_page_number_html(page_number, total_pages, dark=True)

        return f"""
                <div data-render-variant="{render_hints.get('fallback_variant', 'closing-statement')}" data-layout-family="{render_hints.get('layout_family', 'closing')}" style="
                    text-align: center;
                    width: 100%;
                    aspect-ratio: 16/9;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    margin: 0 auto;
                    box-sizing: border-box;
                    position: relative;
                    max-width: 1200px;
                    padding: 3% 5%;
                    background: linear-gradient(135deg, #2c3e50 0%, #3498db 50%, #9b59b6 100%);
                    overflow: hidden;
                ">
                    <div style="
                        position: absolute;
                        inset: 0;
                        background-image:
                            radial-gradient(2px 2px at 20px 30px, rgba(255,255,255,0.8), transparent),
                            radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.6), transparent),
                            radial-gradient(1px 1px at 90px 40px, rgba(255,255,255,0.9), transparent);
                        background-repeat: repeat;
                        background-size: 200px 100px;
                        animation: sparkle 3s ease-in-out infinite;
                        z-index: 1;
                    "></div>
                    <div style="position: relative; z-index: 2;">
                        <h1 style="
                            font-size: clamp(2.5rem, 6vw, 4.5rem);
                            color: #ffffff;
                            margin-bottom: clamp(20px, 3vh, 30px);
                            line-height: 1.2;
                            text-shadow: 0 4px 12px rgba(0,0,0,0.4);
                            font-weight: 700;
                            letter-spacing: 2px;
                            background: linear-gradient(45deg, #ffffff, #f39c12, #e74c3c);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                            background-clip: text;
                        ">{title}</h1>
                        <p style="
                            font-size: clamp(1.2rem, 3vw, 1.8rem);
                            color: rgba(255,255,255,0.9);
                            line-height: 1.4;
                            font-weight: 300;
                            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
                            margin-bottom: clamp(30px, 4vh, 40px);
                        ">感谢您的聆听</p>
                    </div>
                    {page_number_html}
                    <style>
                        @keyframes sparkle {{
                            0%, 100% {{ opacity: 0.8; }}
                            50% {{ opacity: 1; }}
                        }}
                    </style>
                </div>
                """

    def _generate_agenda_fallback(
        self,
        title: str,
        content_points: List[str],
        page_number: int,
        total_pages: int,
        render_hints: Dict[str, Any],
    ) -> str:
        cards_html = "".join(
            (
                '<div style="background: rgba(255,255,255,0.88); border: 1px solid rgba(52,152,219,0.18); '
                'border-radius: 18px; padding: 20px 22px; min-height: 110px; display: flex; flex-direction: column; '
                'justify-content: space-between; box-shadow: 0 18px 40px rgba(31, 78, 121, 0.08);">'
                f'<div style="font-size: 0.82rem; font-weight: 700; letter-spacing: 0.14em; color: #2980b9;">{idx:02d}</div>'
                f'<div style="font-size: clamp(1rem, 2vw, 1.25rem); line-height: 1.45; color: #1f2d3d; font-weight: 600;">{point}</div>'
                '</div>'
            )
            for idx, point in enumerate(content_points, start=1)
        )

        page_number_html = ""
        if render_hints.get("show_page_number", False):
            page_number_html = self._build_page_number_html(page_number, total_pages)

        return f"""
                <div data-render-variant="{render_hints.get('fallback_variant', 'toc-grid')}" data-layout-family="{render_hints.get('layout_family', 'toc')}" style="
                    padding: 3% 5%;
                    width: 100%;
                    aspect-ratio: 16/9;
                    box-sizing: border-box;
                    margin: 0 auto;
                    position: relative;
                    max-width: 1200px;
                    background: linear-gradient(160deg, #f7fbff 0%, #eef6ff 100%);
                    overflow: hidden;
                ">
                    <div style="position: absolute; inset: 0; background:
                        radial-gradient(circle at top right, rgba(52,152,219,0.12), transparent 32%),
                        radial-gradient(circle at bottom left, rgba(26,188,156,0.10), transparent 28%);
                    "></div>
                    <div style="position: relative; z-index: 1;">
                        <div style="font-size: 0.9rem; letter-spacing: 0.18em; font-weight: 700; color: #2980b9; margin-bottom: 12px;">SECTION MAP</div>
                        <h1 style="font-size: clamp(1.7rem, 4vw, 3rem); color: #12324a; margin: 0 0 26px 0; line-height: 1.18;">{title}</h1>
                        <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px;">
                            {cards_html}
                        </div>
                    </div>
                    {page_number_html}
                </div>
                """

    def _generate_content_fallback(
        self,
        title: str,
        content_points: List[str],
        page_number: int,
        total_pages: int,
        render_hints: Dict[str, Any],
    ) -> str:
        variant = render_hints.get("fallback_variant", "balanced-bullets")
        page_number_html = ""
        if render_hints.get("show_page_number", True):
            page_number_html = self._build_page_number_html(page_number, total_pages)

        if variant == "data-spotlight":
            lead = content_points[0] if content_points else "核心指标"
            cards_html = "".join(
                f'<div style="padding: 16px 18px; border-radius: 16px; background: #ffffff; border: 1px solid rgba(52,152,219,0.16); box-shadow: 0 14px 30px rgba(15,76,129,0.08); font-size: clamp(0.92rem, 1.8vw, 1.05rem); line-height: 1.45; color: #26435d;">{point}</div>'
                for point in (content_points[1:] or content_points[:1])
            )
            body_html = f"""
                    <div style="display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(260px, 0.85fr); gap: 24px; align-items: stretch; min-height: 70%;">
                        <div style="padding: 24px 26px; border-radius: 24px; background: linear-gradient(135deg, #12324a, #2d6b96); color: white; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 24px 60px rgba(17, 50, 74, 0.22);">
                            <div style="font-size: 0.82rem; letter-spacing: 0.16em; font-weight: 700; opacity: 0.75;">DATA SPOTLIGHT</div>
                            <div style="font-size: clamp(1.35rem, 3vw, 2rem); line-height: 1.3; font-weight: 700;">{lead}</div>
                            <div style="font-size: 0.95rem; opacity: 0.8;">图表类型：{render_hints.get('chart_type') or 'custom'}</div>
                        </div>
                        <div style="display: grid; gap: 14px;">{cards_html}</div>
                    </div>
            """
        elif variant == "dense-two-column":
            points_html = "".join(
                f'<div style="break-inside: avoid; margin-bottom: 12px; padding: 12px 14px; border-radius: 14px; background: rgba(255,255,255,0.78); border: 1px solid rgba(52,152,219,0.14); font-size: clamp(0.88rem, 1.7vw, 1rem); line-height: 1.45;">{point}</div>'
                for point in content_points
            )
            body_html = f'<div style="column-count: 2; column-gap: 22px; padding-right: 10px;">{points_html}</div>'
        else:
            font_size = "clamp(1rem, 2vw, 1.2rem)" if variant == "spacious-bullets" else "clamp(0.92rem, 1.9vw, 1.08rem)"
            spacing = "1.05em" if variant == "spacious-bullets" else "0.78em"
            points_html = self._render_content_points(
                content_points=content_points,
                item_style=f"margin-bottom: {spacing}; word-wrap: break-word;",
            )
            body_html = f"<div style='max-height: 60vh; overflow-y: auto; padding-right: 10px;'><ul style='font-size: {font_size}; line-height: 1.5; margin: 0; padding-left: 1.5em;'>{points_html}</ul></div>"

        return f"""
                <div data-render-variant="{variant}" data-layout-family="{render_hints.get('layout_family', 'content')}" style="
                    padding: 3% 5%;
                    width: 100%;
                    aspect-ratio: 16/9;
                    box-sizing: border-box;
                    margin: 0 auto;
                    position: relative;
                    max-width: 1200px;
                    display: flex;
                    flex-direction: column;
                    background: linear-gradient(180deg, #fbfdff 0%, #f4f8fc 100%);
                ">
                    <h1 style="font-size: clamp(1.5rem, 4vw, 3rem); color: #2c3e50; margin-bottom: clamp(15px, 2vh, 25px); border-bottom: 3px solid #3498db; padding-bottom: 10px; line-height: 1.2; flex-shrink: 0;">{title}</h1>
                    <div style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">
                        {body_html}
                    </div>
                    {page_number_html}
                </div>
                """

    def _generate_fallback_slide_html(self, slide_data: Dict[str, Any], page_number: int, total_pages: int) -> str:
        """Generate fallback HTML with render-hint aware variants."""
        title = slide_data.get("title", f"第{page_number}页")
        content_points = slide_data.get("content_points", [])
        slide_type = slide_data.get("slide_type", "content")
        render_hints = self._get_render_hints(slide_data)

        if slide_type == "title":
            content_html = self._generate_title_fallback(title, page_number, total_pages)
        elif slide_type in {"thankyou", "conclusion"}:
            content_html = self._generate_closing_fallback(title, page_number, total_pages, render_hints)
        elif slide_type == "agenda" or render_hints.get("layout_family") == "toc":
            content_html = self._generate_agenda_fallback(title, content_points, page_number, total_pages, render_hints)
        else:
            content_html = self._generate_content_fallback(title, content_points, page_number, total_pages, render_hints)

        return f"""
    <!DOCTYPE html>
    <html lang="zh-CN" style="height: 100%; display: flex; align-items: center; justify-content: center;">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #2c3e50;
                width: 1280px;
                height: 720px;
                position: relative;
                overflow: hidden;
            }}
        </style>
    </head>
    <body>
        {content_html}
    </body>
    </html>
            """

    def _combine_slides_to_full_html(self, slides_data: List[Dict[str, Any]], title: str) -> str:
        """Combine individual slides into a full presentation HTML and save to temp files."""
        try:
            if not slides_data:
                logger.warning("No slides data provided for combining")
                return self._generate_empty_presentation_html(title)
            if not title:
                title = "未命名演示"

            presentation_id = f"presentation_{uuid.uuid4().hex[:8]}"
            temp_dir = Path(tempfile.gettempdir()) / "landppt" / presentation_id
            temp_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Combining %s slides into full HTML presentation", len(slides_data))

            for i, slide in enumerate(slides_data):
                page_number = slide.get("page_number", i + 1)
                slide_filename = f"slide_{page_number}.html"
                slide_path = temp_dir / slide_filename
                html_content = slide.get("html_content", "<div>空内容</div>")
                with open(slide_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

            slides_html = ""
            for i, slide in enumerate(slides_data):
                page_number = slide.get("page_number", i + 1)
                html_content = slide.get("html_content", "<div>空内容</div>")
                encoded_html = self._encode_html_to_base64(html_content)
                data_url = f"data:text/html;charset=utf-8;base64,{encoded_html}"
                slides_html += (
                    f'\n<div class="slide" id="slide-{page_number}" style="display: {"block" if i == 0 else "none"};">'
                    f'\n    <iframe src="{data_url}" style="width: 100%; height: 100%; border: none;"></iframe>'
                    "\n</div>\n"
                )

            return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: #000;
            }}
            .slide {{
                width: 100%;
                max-width: 1200px;
                aspect-ratio: 16/9;
                position: relative;
                margin: 0 auto;
            }}
            .navigation {{
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 1000;
                background: rgba(0,0,0,0.7);
                padding: 10px 20px;
                border-radius: 25px;
            }}
            .nav-btn {{
                background: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                margin: 0 5px;
                border-radius: 5px;
                cursor: pointer;
            }}
            .nav-btn:hover {{
                background: #2980b9;
            }}
            .nav-btn:disabled {{
                background: #95a5a6;
                cursor: not-allowed;
            }}
            .slide-counter {{
                color: white;
                margin: 0 15px;
            }}
        </style>
    </head>
    <body>
        {slides_html}

        <div class="navigation">
            <button class="nav-btn" onclick="previousSlide()">⬅️ 上一页</button>
            <span class="slide-counter" id="slideCounter">1 / {len(slides_data)}</span>
            <button class="nav-btn" onclick="nextSlide()">下一页 ➡️</button>
        </div>

        <script>
            let currentSlide = 0;
            const totalSlides = {len(slides_data)};

            function showSlide(index) {{
                document.querySelectorAll('.slide').forEach(slide => slide.style.display = 'none');
                const targetSlide = document.getElementById('slide-' + (index + 1));
                if (targetSlide) {{
                    targetSlide.style.display = 'block';
                }}
                document.getElementById('slideCounter').textContent = (index + 1) + ' / ' + totalSlides;
            }}

            function nextSlide() {{
                if (currentSlide < totalSlides - 1) {{
                    currentSlide++;
                    showSlide(currentSlide);
                }}
            }}

            function previousSlide() {{
                if (currentSlide > 0) {{
                    currentSlide--;
                    showSlide(currentSlide);
                }}
            }}

            document.addEventListener('keydown', function(e) {{
                if (e.key === 'ArrowRight') nextSlide();
                if (e.key === 'ArrowLeft') previousSlide();
            }});

            document.addEventListener('DOMContentLoaded', function() {{
                showSlide(0);
            }});
        </script>
    </body>
    </html>
                """
        except Exception as e:
            logger.error("Error combining slides to full HTML: %s", e)
            import traceback
            traceback.print_exc()
            return self._generate_empty_presentation_html(title)

    def _generate_empty_presentation_html(self, title: str) -> str:
        """Generate empty presentation HTML as fallback."""
        return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: #f0f0f0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }}
            .empty-message {{
                text-align: center;
                color: #666;
                font-size: 24px;
            }}
        </style>
    </head>
    <body>
        <div class="empty-message">
            <h1>暂无幻灯片内容</h1>
            <p>请先生成幻灯片内容</p>
        </div>
    </body>
    </html>
            """

    def _encode_html_for_iframe(self, html_content: str) -> str:
        """Encode HTML content for iframe src."""
        return urllib.parse.quote(html_content)

    def _encode_html_to_base64(self, html_content: str) -> str:
        """Encode HTML content to base64 for safe JavaScript transmission."""
        return base64.b64encode(html_content.encode("utf-8")).decode("ascii")

    def _generate_basic_html(self, slides: List[SlideContent], theme_config: Dict[str, Any]) -> str:
        """Generate basic HTML as fallback."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>PPT Presentation</title>",
            "<style>",
            "body { margin: 0; padding: 0; font-family: " + theme_config.get("font_family", "Arial, sans-serif") + "; }",
            ".presentation-container { width: 1280px; height: 720px; margin: 0 auto; position: relative; }",
            ".slide { width: 1280px; height: 720px; background: " + theme_config.get("background", "#f0f0f0") + "; padding: 40px; box-sizing: border-box; position: relative; }",
            ".title { color: " + theme_config.get("primary_color", "#333") + "; font-size: 2em; margin-bottom: 20px; }",
            ".content { color: " + theme_config.get("secondary_color", "#666") + "; font-size: 1.2em; line-height: 1.6; }",
            ".page-number { position: absolute; bottom: 20px; right: 20px; color: #999; font-size: 0.9em; }",
            "@media (max-width: 1280px) { .presentation-container, .slide { width: 100vw; height: 56.25vw; max-height: 100vh; } }",
            "</style>",
            "</head>",
            "<body>",
            "<div class='presentation-container'>",
        ]
        for i, slide in enumerate(slides):
            html_parts.extend(
                [
                    f"<div class='slide' id='slide-{i + 1}'>",
                    f"<h1 class='title'>{slide.title}</h1>",
                    f"<div class='content'>{slide.content or ''}</div>",
                    f"<div class='page-number'>{i + 1}</div>",
                    "</div>",
                ]
            )
        html_parts.extend(["</div>", "</body>", "</html>"])
        return "\n".join(html_parts)
