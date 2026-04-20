"""
Builds a normalized presentation_spec payload from the current project state.

Phase 1 scope:
- keep HTML as the active renderer
- do not change export protocols
- persist presentation_spec inside project_metadata
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ContentBlockSpec(BaseModel):
    block_id: str
    block_type: Literal["title", "subtitle", "bullet_list", "paragraph", "chart", "image_hint", "note"]
    text: Optional[str] = None
    items: List[str] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)


class LayoutConstraintsSpec(BaseModel):
    density: Literal["low", "medium", "high"] = "medium"
    preferred_family: str = "content"
    emphasis: str = "message"


class ImagePolicySpec(BaseModel):
    usage: Literal["none", "supporting", "hero", "background"] = "supporting"
    image_slots: int = 1
    required: bool = False
    source_preferences: List[str] = Field(default_factory=list)


class ChartPolicySpec(BaseModel):
    needs_chart: bool = False
    preferred_chart_type: Optional[str] = None
    chart_config: Dict[str, Any] = Field(default_factory=dict)


class SlideSpec(BaseModel):
    slide_id: str
    page_number: int
    slide_type: str
    title: str
    content_blocks: List[ContentBlockSpec] = Field(default_factory=list)
    layout_constraints: LayoutConstraintsSpec
    visual_priority: Literal["opening", "navigation", "message", "data", "summary", "closure"] = "message"
    image_policy: ImagePolicySpec
    chart_policy: ChartPolicySpec
    notes: str = ""


class DeckMetaSpec(BaseModel):
    project_id: Optional[str] = None
    title: str
    topic: str
    scenario: Optional[str] = None
    language: str = "zh"
    generation_mode: Literal["creative", "professional"] = "creative"
    workflow_phase: Literal["phase1"] = "phase1"
    created_at: Optional[float] = None
    updated_at: Optional[float] = None


class ThemeSpec(BaseModel):
    template_mode: str = "default"
    selected_template_id: Optional[int] = None
    style_family: str = "general"
    style_prompt: Optional[str] = None
    design_tokens: Dict[str, Any] = Field(default_factory=dict)


class OutlineSpec(BaseModel):
    title: str
    total_slides: int
    slide_order: List[str] = Field(default_factory=list)
    sections: List[str] = Field(default_factory=list)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetPlanSpec(BaseModel):
    global_source_preferences: List[str] = Field(default_factory=list)
    slides: List[Dict[str, Any]] = Field(default_factory=list)


class SpeakerNotesSpec(BaseModel):
    strategy: Literal["empty", "description_seeded"] = "empty"
    notes_by_slide: Dict[str, str] = Field(default_factory=dict)


class RenderTargetSpec(BaseModel):
    primary: Literal["html", "pptx"] = "html"
    available: List[Literal["html", "pptx"]] = Field(default_factory=lambda: ["html"])
    planned: List[Literal["html", "pptx"]] = Field(default_factory=lambda: ["pptx"])
    html_preview_enabled: bool = True
    pptx_compilation_ready: bool = False


class PresentationSpec(BaseModel):
    schema_version: str = "1.0"
    generated_at: float
    deck_meta: DeckMetaSpec
    theme_spec: ThemeSpec
    outline_spec: OutlineSpec
    slide_specs: List[SlideSpec] = Field(default_factory=list)
    asset_plan: AssetPlanSpec
    speaker_notes: SpeakerNotesSpec
    render_target: RenderTargetSpec


class PresentationSpecService:
    """Build a unified presentation spec from a project and its normalized outline."""

    _SLIDE_LAYOUT_FAMILIES = {
        "title": "cover",
        "agenda": "toc",
        "content": "content",
        "conclusion": "summary",
        "thankyou": "closing",
    }

    _SLIDE_VISUAL_PRIORITIES = {
        "title": "opening",
        "agenda": "navigation",
        "content": "message",
        "conclusion": "summary",
        "thankyou": "closure",
    }

    _DATA_KEYWORDS = (
        "数据",
        "图表",
        "趋势",
        "占比",
        "增长",
        "chart",
        "trend",
        "metric",
        "kpi",
        "revenue",
    )

    def build_for_project(self, project: Any, outline: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        outline_data = self._normalize_outline(outline if outline is not None else getattr(project, "outline", None))
        metadata = self._safe_dict(getattr(project, "project_metadata", None))
        confirmed_requirements = self._safe_dict(getattr(project, "confirmed_requirements", None))
        global_source_preferences = self._build_source_preferences(metadata)

        slide_specs = [
            self._build_slide_spec(slide, index, global_source_preferences)
            for index, slide in enumerate(outline_data["slides"], start=1)
        ]
        slide_order = [slide.slide_id for slide in slide_specs]

        spec = PresentationSpec(
            generated_at=time.time(),
            deck_meta=self._build_deck_meta(project, outline_data, metadata),
            theme_spec=self._build_theme_spec(project, outline_data, metadata, confirmed_requirements),
            outline_spec=self._build_outline_spec(outline_data, slide_specs),
            slide_specs=slide_specs,
            asset_plan=self._build_asset_plan(slide_specs, global_source_preferences),
            speaker_notes=self._build_speaker_notes(slide_specs),
            render_target=RenderTargetSpec(),
        )

        payload = spec.model_dump(mode="json")
        payload["outline_spec"]["slide_order"] = slide_order
        return payload

    @classmethod
    def resolve_render_plan(
        cls,
        presentation_spec: Dict[str, Any],
        slide_data: Optional[Dict[str, Any]],
        page_number: int,
    ) -> Dict[str, Any]:
        if not isinstance(presentation_spec, dict):
            return {}

        slide_spec = cls.find_slide_spec(presentation_spec, slide_data, page_number)
        if not isinstance(slide_spec, dict):
            return {}

        render_hints = cls._build_render_hints(slide_spec)
        prompt_context = cls._build_prompt_context(
            deck_meta=cls._safe_dict(presentation_spec.get("deck_meta")),
            theme_spec=cls._safe_dict(presentation_spec.get("theme_spec")),
            slide_spec=slide_spec,
            render_hints=render_hints,
        )
        return {
            "slide_spec": slide_spec,
            "render_hints": render_hints,
            "prompt_context": prompt_context,
        }

    @classmethod
    def find_slide_spec(
        cls,
        presentation_spec: Dict[str, Any],
        slide_data: Optional[Dict[str, Any]],
        page_number: int,
    ) -> Optional[Dict[str, Any]]:
        slide_specs = presentation_spec.get("slide_specs")
        if not isinstance(slide_specs, list):
            return None

        slide_payload = slide_data if isinstance(slide_data, dict) else {}
        slide_id = slide_payload.get("slide_id")

        for candidate in slide_specs:
            if not isinstance(candidate, dict):
                continue
            if slide_id and candidate.get("slide_id") == slide_id:
                return candidate
            if candidate.get("page_number") == page_number:
                return candidate
        return None

    @staticmethod
    def _safe_dict(value: Any) -> Dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    @classmethod
    def _build_render_hints(cls, slide_spec: Dict[str, Any]) -> Dict[str, Any]:
        layout = cls._safe_dict(slide_spec.get("layout_constraints"))
        image_policy = cls._safe_dict(slide_spec.get("image_policy"))
        chart_policy = cls._safe_dict(slide_spec.get("chart_policy"))
        block_types = [
            block.get("block_type")
            for block in slide_spec.get("content_blocks", [])
            if isinstance(block, dict) and block.get("block_type")
        ]

        visual_priority = str(slide_spec.get("visual_priority") or "message")
        layout_family = str(layout.get("preferred_family") or "content")
        density = str(layout.get("density") or "medium")
        emphasis = str(layout.get("emphasis") or "message")
        needs_chart = bool(chart_policy.get("needs_chart"))

        fallback_variant = "balanced-bullets"
        if layout_family == "cover" or visual_priority == "opening":
            fallback_variant = "cover-hero"
        elif layout_family == "toc" or visual_priority == "navigation":
            fallback_variant = "toc-grid"
        elif visual_priority == "closure":
            fallback_variant = "closing-statement"
        elif visual_priority == "summary":
            fallback_variant = "summary-focus"
        elif needs_chart or emphasis == "data":
            fallback_variant = "data-spotlight"
        elif density == "high":
            fallback_variant = "dense-two-column"
        elif density == "low":
            fallback_variant = "spacious-bullets"

        show_page_number = visual_priority not in {"opening", "navigation", "closure"}
        return {
            "layout_family": layout_family,
            "visual_priority": visual_priority,
            "density": density,
            "emphasis": emphasis,
            "fallback_variant": fallback_variant,
            "show_page_number": show_page_number,
            "image_usage": image_policy.get("usage", "supporting"),
            "image_slots": int(image_policy.get("image_slots") or 0),
            "needs_chart": needs_chart,
            "chart_type": chart_policy.get("preferred_chart_type"),
            "block_types": block_types,
        }

    @staticmethod
    def _build_prompt_context(
        deck_meta: Dict[str, Any],
        theme_spec: Dict[str, Any],
        slide_spec: Dict[str, Any],
        render_hints: Dict[str, Any],
    ) -> str:
        lines = [
            "**Phase 1 Presentation Spec 约束**",
            f"- 模式：{deck_meta.get('generation_mode', 'creative')}",
            f"- 模板模式：{theme_spec.get('template_mode', 'default')}",
            f"- 风格家族：{theme_spec.get('style_family', 'general')}",
            f"- 当前页视觉角色：{render_hints.get('visual_priority', 'message')}",
            f"- 期望布局家族：{render_hints.get('layout_family', 'content')}",
            f"- 内容密度：{render_hints.get('density', 'medium')}",
            f"- 视觉强调点：{render_hints.get('emphasis', 'message')}",
            f"- fallback 版式变体：{render_hints.get('fallback_variant', 'balanced-bullets')}",
        ]
        block_types = render_hints.get("block_types") or []
        if block_types:
            lines.append(f"- 内容块类型：{', '.join(block_types)}")
        lines.append(
            f"- 图片策略：usage={render_hints.get('image_usage', 'supporting')}, slots={render_hints.get('image_slots', 0)}"
        )
        lines.append(
            f"- 图表策略：needs_chart={render_hints.get('needs_chart', False)}, type={render_hints.get('chart_type') or 'none'}"
        )
        if slide_spec.get("notes"):
            lines.append(f"- 备注提示：{slide_spec.get('notes')}")
        lines.append("- 要求：优先满足这些中间层约束，再决定最终 HTML 细节。")
        return "\n".join(lines)

    def _normalize_outline(self, outline: Any) -> Dict[str, Any]:
        if not isinstance(outline, dict):
            raise ValueError("outline must be a dict when building presentation_spec")
        slides = outline.get("slides")
        if not isinstance(slides, list) or not slides:
            raise ValueError("outline.slides must be a non-empty list")
        metadata = self._safe_dict(outline.get("metadata"))
        theme_config = self._safe_dict(outline.get("theme_config"))
        return {
            "title": str(outline.get("title") or "PPT大纲").strip() or "PPT大纲",
            "slides": slides,
            "metadata": metadata,
            "theme_config": theme_config,
        }

    def _build_deck_meta(self, project: Any, outline: Dict[str, Any], metadata: Dict[str, Any]) -> DeckMetaSpec:
        generation_mode = metadata.get("presentation_mode")
        if generation_mode not in {"creative", "professional"}:
            generation_mode = "creative"

        return DeckMetaSpec(
            project_id=getattr(project, "project_id", None),
            title=str(outline.get("title") or getattr(project, "title", "") or getattr(project, "topic", "PPT")).strip() or "PPT",
            topic=str(getattr(project, "topic", "") or outline.get("title") or "PPT").strip() or "PPT",
            scenario=getattr(project, "scenario", None),
            language=str(metadata.get("language") or "zh"),
            generation_mode=generation_mode,
            created_at=getattr(project, "created_at", None),
            updated_at=getattr(project, "updated_at", None),
        )

    def _build_theme_spec(
        self,
        project: Any,
        outline: Dict[str, Any],
        metadata: Dict[str, Any],
        confirmed_requirements: Dict[str, Any],
    ) -> ThemeSpec:
        template_mode = str(metadata.get("template_mode") or ("global" if metadata.get("selected_global_template_id") else "default"))
        style_prompt = (
            confirmed_requirements.get("custom_style_prompt")
            or metadata.get("free_template_prompt")
            or getattr(project, "requirements", None)
        )

        design_tokens = {}
        if isinstance(outline.get("theme_config"), dict):
            design_tokens.update(outline["theme_config"])
        raw_metadata = outline.get("metadata")
        if isinstance(raw_metadata, dict) and isinstance(raw_metadata.get("theme_config"), dict):
            design_tokens.update(raw_metadata["theme_config"])

        style_family = str(
            confirmed_requirements.get("ppt_style")
            or metadata.get("template_mode")
            or "general"
        )

        return ThemeSpec(
            template_mode=template_mode,
            selected_template_id=metadata.get("selected_global_template_id"),
            style_family=style_family,
            style_prompt=style_prompt,
            design_tokens=design_tokens,
        )

    def _build_outline_spec(self, outline: Dict[str, Any], slide_specs: List[SlideSpec]) -> OutlineSpec:
        agenda_sections: List[str] = []
        for slide in outline.get("slides", []):
            slide_type = str(slide.get("slide_type") or slide.get("type") or "content")
            if slide_type == "agenda":
                agenda_sections.extend(self._coerce_points(slide))

        if not agenda_sections:
            agenda_sections = [
                slide.title for slide in slide_specs if slide.slide_type == "content"
            ]

        return OutlineSpec(
            title=outline["title"],
            total_slides=len(slide_specs),
            slide_order=[slide.slide_id for slide in slide_specs],
            sections=agenda_sections,
            raw_metadata=self._safe_dict(outline.get("metadata")),
        )

    def _build_slide_spec(
        self,
        slide: Dict[str, Any],
        index: int,
        global_source_preferences: List[str],
    ) -> SlideSpec:
        slide_type = str(slide.get("slide_type") or slide.get("type") or "content")
        title = str(slide.get("title") or f"第{index}页").strip() or f"第{index}页"
        slide_id = str(slide.get("slide_id") or f"slide-{index:02d}")
        content_points = self._coerce_points(slide)
        description = str(slide.get("description") or "").strip()
        chart_config = self._safe_dict(slide.get("chart_config"))
        chart_needed = bool(chart_config) or self._looks_data_driven(title, content_points)

        content_blocks = [
            ContentBlockSpec(
                block_id=f"{slide_id}-title",
                block_type="title",
                text=title,
            )
        ]
        if description:
            content_blocks.append(
                ContentBlockSpec(
                    block_id=f"{slide_id}-description",
                    block_type="paragraph",
                    text=description,
                )
            )
        if content_points:
            content_blocks.append(
                ContentBlockSpec(
                    block_id=f"{slide_id}-bullets",
                    block_type="bullet_list",
                    items=content_points,
                )
            )
        if chart_needed:
            content_blocks.append(
                ContentBlockSpec(
                    block_id=f"{slide_id}-chart",
                    block_type="chart",
                    data=chart_config,
                )
            )
        if slide_type in {"title", "content", "conclusion"}:
            content_blocks.append(
                ContentBlockSpec(
                    block_id=f"{slide_id}-image-hint",
                    block_type="image_hint",
                    text=title,
                )
            )

        return SlideSpec(
            slide_id=slide_id,
            page_number=int(slide.get("page_number") or index),
            slide_type=slide_type,
            title=title,
            content_blocks=content_blocks,
            layout_constraints=LayoutConstraintsSpec(
                density=self._infer_density(slide_type, content_points),
                preferred_family=self._SLIDE_LAYOUT_FAMILIES.get(slide_type, "content"),
                emphasis="data" if chart_needed else "message",
            ),
            visual_priority=self._SLIDE_VISUAL_PRIORITIES.get(slide_type, "message"),
            image_policy=self._build_image_policy(slide_type, global_source_preferences),
            chart_policy=ChartPolicySpec(
                needs_chart=chart_needed,
                preferred_chart_type=self._infer_chart_type(chart_config),
                chart_config=chart_config,
            ),
            notes=description,
        )

    @staticmethod
    def _coerce_points(slide: Dict[str, Any]) -> List[str]:
        raw_points = slide.get("content_points")
        if raw_points is None:
            raw_points = slide.get("bullet_points")
        if raw_points is None:
            raw_points = slide.get("points")
        if isinstance(raw_points, str):
            raw_points = [raw_points]
        if not isinstance(raw_points, list):
            return []
        return [str(point).strip() for point in raw_points if str(point).strip()]

    def _build_source_preferences(self, metadata: Dict[str, Any]) -> List[str]:
        source_preferences = ["local"]
        if metadata.get("network_mode"):
            source_preferences.append("network")
        source_preferences.append("ai_generated")
        return source_preferences

    def _build_image_policy(self, slide_type: str, global_source_preferences: List[str]) -> ImagePolicySpec:
        if slide_type == "agenda":
            return ImagePolicySpec(
                usage="none",
                image_slots=0,
                required=False,
                source_preferences=[],
            )
        if slide_type == "title":
            return ImagePolicySpec(
                usage="hero",
                image_slots=1,
                required=False,
                source_preferences=list(global_source_preferences),
            )
        if slide_type == "thankyou":
            return ImagePolicySpec(
                usage="background",
                image_slots=1,
                required=False,
                source_preferences=list(global_source_preferences),
            )
        return ImagePolicySpec(
            usage="supporting",
            image_slots=1,
            required=False,
            source_preferences=list(global_source_preferences),
        )

    @staticmethod
    def _infer_density(slide_type: str, content_points: List[str]) -> Literal["low", "medium", "high"]:
        if slide_type in {"title", "thankyou"}:
            return "low"
        if len(content_points) >= 5:
            return "high"
        if len(content_points) <= 2:
            return "low"
        return "medium"

    def _looks_data_driven(self, title: str, content_points: List[str]) -> bool:
        joined = " ".join([title, *content_points]).lower()
        return any(keyword in joined for keyword in self._DATA_KEYWORDS)

    @staticmethod
    def _infer_chart_type(chart_config: Dict[str, Any]) -> Optional[str]:
        if not chart_config:
            return None
        if chart_config.get("type"):
            return str(chart_config["type"])
        if chart_config.get("series"):
            return "bar"
        return "custom"

    def _build_asset_plan(self, slide_specs: List[SlideSpec], global_source_preferences: List[str]) -> AssetPlanSpec:
        return AssetPlanSpec(
            global_source_preferences=list(global_source_preferences),
            slides=[
                {
                    "slide_id": slide.slide_id,
                    "image_usage": slide.image_policy.usage,
                    "image_slots": slide.image_policy.image_slots,
                    "needs_chart": slide.chart_policy.needs_chart,
                }
                for slide in slide_specs
            ],
        )

    @staticmethod
    def _build_speaker_notes(slide_specs: List[SlideSpec]) -> SpeakerNotesSpec:
        notes_by_slide = {
            slide.slide_id: slide.notes
            for slide in slide_specs
            if slide.notes
        }
        return SpeakerNotesSpec(
            strategy="description_seeded" if notes_by_slide else "empty",
            notes_by_slide=notes_by_slide,
        )
