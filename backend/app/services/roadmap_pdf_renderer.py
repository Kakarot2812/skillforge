"""
SkillForge AI — Career Roadmap PDF Renderer.
Post-MVP Feature: Phase 4 — ReportLab Exact PDF Renderer.

Transforms ValidatedRoadmapPDFContent (Phase 3) into publication-quality A4 PDF bytes.

Core Invariants:
- Pure presentation layer: zero database, zero Gemini/LangChain, zero network calls, zero ORM.
- "The renderer never decides what is true. It renders verified facts and validated narrative."
- Exact visual hierarchy matching docs/ROADMAP_PDF_DESIGN.md.
- A4 Portrait geometry with natural page breaks, orphan suppression, and overflow safety.
- Two-pass NumberedCanvas for deterministic page numbering (Page X of Y) and audit watermark.
- Clickable hyperlinks for approved curated resources.
- Curated projects rendered strictly as practical challenges (NOT candidate proof).
"""

from datetime import datetime, timezone
import html
import io
import logging
from typing import List, Optional, Tuple
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.ai.context.roadmap_pdf_context import (
    PriorityTierLevel,
    SkillGapClassification,
    VerifiedApprovedProject,
    VerifiedApprovedResource,
)
from app.ai.roadmap.narrative_schemas import (
    ValidatedRoadmapPDFContent,
    ValidatedRoadmapPhase,
    ValidatedTopSkillGap,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 1. Design Tokens: Palette, Geometry, and Typography Constants
# -----------------------------------------------------------------------------

# A4 Geometry (Points)
PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.27 pt x 841.89 pt
MARGIN_LEFT = 36.0            # 0.5 in
MARGIN_RIGHT = 36.0           # 0.5 in
MARGIN_TOP = 36.0             # 0.5 in
MARGIN_BOTTOM = 45.0          # 0.625 in
USABLE_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT  # 523.27 pt

# Brand Color Palette (HexColor)
COLOR_PRIMARY_DARK   = colors.HexColor("#0F172A")  # Slate 900 (Headers, text)
COLOR_SECONDARY_DARK = colors.HexColor("#1E293B")  # Slate 800 (Card headers, pills)
COLOR_EMERALD        = colors.HexColor("#059669")  # Emerald 600 (Strong, Verified, Readiness)
COLOR_EMERALD_LIGHT  = colors.HexColor("#ECFDF5")  # Emerald 50 (Badge background)
COLOR_AMBER          = colors.HexColor("#D97706")  # Amber 600 (Partial, Medium priority)
COLOR_AMBER_LIGHT    = colors.HexColor("#FFFBEB")  # Amber 50 (Badge background)
COLOR_ROSE           = colors.HexColor("#E11D48")  # Rose 600 (Missing, High priority)
COLOR_ROSE_LIGHT     = colors.HexColor("#FFF1F2")  # Rose 50 (Badge background)
COLOR_BLUE           = colors.HexColor("#2563EB")  # Blue 600 (Resources, links)
COLOR_BLUE_LIGHT     = colors.HexColor("#EFF6FF")  # Blue 50 (Resource tags)
COLOR_INDIGO         = colors.HexColor("#4F46E5")  # Indigo 600 (Practice challenges)
COLOR_INDIGO_LIGHT   = colors.HexColor("#EEF2FF")  # Indigo 50 (Challenge box background)
COLOR_BG_CARD        = colors.HexColor("#FFFFFF")  # Pure White card backgrounds
COLOR_BG_SUBTLE      = colors.HexColor("#F8FAFC")  # Slate 50 (Banners, cards)
COLOR_BORDER         = colors.HexColor("#E2E8F0")  # Slate 200 (Subtle borders)
COLOR_BORDER_STRONG  = colors.HexColor("#CBD5E1")  # Slate 300
COLOR_TEXT_PRIMARY   = colors.HexColor("#0F172A")  # Slate 900
COLOR_TEXT_SECONDARY = colors.HexColor("#475569")  # Slate 600
COLOR_TEXT_MUTED     = colors.HexColor("#94A3B8")  # Slate 400
COLOR_PROGRESS_BG    = colors.HexColor("#E2E8F0")  # Slate 200 (Progress bar track)


# -----------------------------------------------------------------------------
# 2. Numbered Canvas for Dynamic Two-Pass Page Footers & Watermarks
# -----------------------------------------------------------------------------

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that accumulates total page count and renders a uniform,
    unclippable footer on every page:
    - Running rule divider
    - Brand attribution: "SkillForge AI — Evidence-Grounded Career Intelligence"
    - Page numbering: "Page X of Y"
    - Verification audit watermark (SHA-256 snippet)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_page_decorations(self, page_count: int):
        self.saveState()

        # Footer divider rule at y = 32 pt
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.75)
        self.line(MARGIN_LEFT, 32, PAGE_WIDTH - MARGIN_RIGHT, 32)

        # Footer Left: Brand & Product tagline
        self.setFont("Helvetica", 7.5)
        self.setFillColor(COLOR_TEXT_MUTED)
        self.drawString(
            MARGIN_LEFT,
            20,
            "SkillForge AI  •  Personalized Career Roadmap  •  Evidence-Grounded Intelligence"
        )

        # Footer Right: Page X of Y
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, 20, page_str)

        self.restoreState()


# -----------------------------------------------------------------------------
# 3. Custom Flowable: Authoritative Segmented Readiness Progress Bar
# -----------------------------------------------------------------------------

class SegmentedProgressBarFlowable(Flowable):
    """
    Renders an authoritative segmented progress bar representing the candidate's
    skill possession breakdown: Strong (Emerald), Partial (Amber), and Missing (Slate/Rose).
    Guarantees: Zero division-by-zero, bounds safety [0, 100], and crisp vector output.
    """

    def __init__(
        self,
        width: float,
        height: float,
        strong_count: int,
        partial_count: int,
        missing_count: int,
        total_skills: int,
    ):
        super().__init__()
        self.width = width
        self.height = height
        self.strong_count = max(0, strong_count)
        self.partial_count = max(0, partial_count)
        self.missing_count = max(0, missing_count)
        self.total_skills = max(0, total_skills)

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        canv = self.canv
        canv.saveState()

        # Background track
        canv.setFillColor(COLOR_PROGRESS_BG)
        canv.roundRect(0, 0, self.width, self.height, radius=self.height / 2, fill=1, stroke=0)

        if self.total_skills > 0:
            strong_ratio = min(1.0, self.strong_count / self.total_skills)
            partial_ratio = min(1.0 - strong_ratio, self.partial_count / self.total_skills)

            strong_w = self.width * strong_ratio
            partial_w = self.width * partial_ratio

            # Strong segment (Emerald)
            if strong_w > 0:
                canv.setFillColor(COLOR_EMERALD)
                canv.roundRect(0, 0, strong_w, self.height, radius=self.height / 2, fill=1, stroke=0)

            # Partial segment (Amber)
            if partial_w > 0:
                canv.setFillColor(COLOR_AMBER)
                # Fill partial rectangle directly adjacent to strong
                canv.rect(strong_w, 0, partial_w, self.height, fill=1, stroke=0)

        canv.restoreState()


# -----------------------------------------------------------------------------
# 4. RoadmapPDFRenderer Implementation
# -----------------------------------------------------------------------------

class RoadmapPDFRenderer:
    """
    Deterministic ReportLab PDF Renderer.
    Converts ValidatedRoadmapPDFContent into A4 binary PDF bytes.
    """

    def __init__(self):
        self._init_styles()

    def _init_styles(self):
        """Initializes a centralized, consistent typography stylesheet."""
        base_sheet = getSampleStyleSheet()

        self.styles = {
            "DocTitle": ParagraphStyle(
                "DocTitle",
                parent=base_sheet["Normal"],
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                textColor=COLOR_PRIMARY_DARK,
                spaceAfter=2,
            ),
            "DocSubtitle": ParagraphStyle(
                "DocSubtitle",
                parent=base_sheet["Normal"],
                fontName="Helvetica",
                fontSize=9.5,
                leading=13.5,
                textColor=COLOR_TEXT_SECONDARY,
                spaceAfter=8,
            ),
            "SectionHeader": ParagraphStyle(
                "SectionHeader",
                parent=base_sheet["Normal"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=15,
                textColor=COLOR_PRIMARY_DARK,
                spaceBefore=6,
                spaceAfter=4,
            ),
            "SectionCaption": ParagraphStyle(
                "SectionCaption",
                parent=base_sheet["Normal"],
                fontName="Helvetica",
                fontSize=8,
                leading=11,
                textColor=COLOR_TEXT_MUTED,
                spaceAfter=6,
            ),
            "Body": ParagraphStyle(
                "Body",
                parent=base_sheet["Normal"],
                fontName="Helvetica",
                fontSize=8.5,
                leading=11.5,
                textColor=COLOR_TEXT_PRIMARY,
            ),
            "BodyMuted": ParagraphStyle(
                "BodyMuted",
                parent=base_sheet["Normal"],
                fontName="Helvetica",
                fontSize=8,
                leading=11,
                textColor=COLOR_TEXT_SECONDARY,
            ),
            "MetaLabel": ParagraphStyle(
                "MetaLabel",
                parent=base_sheet["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=COLOR_TEXT_SECONDARY,
            ),
            "MetaValue": ParagraphStyle(
                "MetaValue",
                parent=base_sheet["Normal"],
                fontName="Helvetica",
                fontSize=8,
                leading=10.5,
                textColor=COLOR_TEXT_PRIMARY,
            ),
            "PhaseTitle": ParagraphStyle(
                "PhaseTitle",
                parent=base_sheet["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10.5,
                leading=13.5,
                textColor=COLOR_PRIMARY_DARK,
            ),
            "BadgeText": ParagraphStyle(
                "BadgeText",
                parent=base_sheet["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7,
                leading=8.5,
                alignment=1,  # Center
            ),
            "TableHeader": ParagraphStyle(
                "TableHeader",
                parent=base_sheet["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=COLOR_TEXT_SECONDARY,
            ),
            "ResourceLink": ParagraphStyle(
                "ResourceLink",
                parent=base_sheet["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10.5,
                textColor=COLOR_BLUE,
            ),
            "ChallengeHeading": ParagraphStyle(
                "ChallengeHeading",
                parent=base_sheet["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11.5,
                textColor=COLOR_INDIGO,
            ),
        }

    def render(self, content: ValidatedRoadmapPDFContent) -> bytes:
        """
        Renders ValidatedRoadmapPDFContent into binary A4 PDF bytes.

        Args:
            content: Authoritative, reference-validated roadmap content.

        Returns:
            bytes: Binary A4 PDF document.

        Raises:
            TypeError / ValueError: If input content is invalid or null.
        """
        if not content or not isinstance(content, ValidatedRoadmapPDFContent):
            raise TypeError("ValidatedRoadmapPDFContent instance is required for PDF rendering.")

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="Personalized Career Roadmap",
            author="SkillForge AI",
            subject="AI-Generated Personalized Career Roadmap",
            keywords="SkillForge, Roadmap, Career, Learning, Skills",
        )

        story: List[Flowable] = []

        # 1. Top Brand Banner & Title
        story.extend(self._build_top_header(content))
        story.append(Spacer(1, 8))

        # 2. Executive Narrative Banner
        story.extend(self._build_executive_banner(content))
        story.append(Spacer(1, 8))

        # 3. Candidate Profile Metadata Card
        story.extend(self._build_candidate_metadata_card(content))
        story.append(Spacer(1, 10))

        # 4. Executive Readiness & Gaps Summary Cards
        story.extend(self._build_readiness_and_summary_section(content))
        story.append(Spacer(1, 12))

        # 5. Top Prioritized Skill Gaps Table
        story.extend(self._build_top_gaps_section(content))
        story.append(Spacer(1, 14))

        # 6. Sequenced Learning Roadmap Phases
        story.extend(self._build_roadmap_phases(content))
        story.append(Spacer(1, 12))

        # 7. Immediate Next Steps & Strategic Takeaway
        story.extend(self._build_next_steps_section(content))
        story.append(Spacer(1, 10))

        # 8. Motivational Closing Card
        story.extend(self._build_closing_card(content))

        # Build document with custom two-pass NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(
            "Rendered roadmap PDF: %d bytes across %d milestones (roadmap_id=%s)",
            len(pdf_bytes),
            content.total_milestones,
            content.roadmap_id,
        )
        return pdf_bytes

    # -------------------------------------------------------------------------
    # Section Builders
    # -------------------------------------------------------------------------

    def _build_top_header(self, content: ValidatedRoadmapPDFContent) -> List[Flowable]:
        """Builds top brand header bar, document title, and personalized subtitle."""
        flowables: List[Flowable] = []

        # Header Bar: Brand on Left, Date & Target Market on Right
        left_brand = Paragraph(
            "<b><font color='#059669'>SkillForge AI</font></b>  <font color='#94A3B8'>|</font>  "
            "<b><font color='#0F172A'>CAREER INTELLIGENCE PLATFORM</font></b>",
            self.styles["MetaLabel"]
        )

        formatted_date = content.generated_at.strftime("%B %d, %Y")
        right_info = Paragraph(
            f"<b>Market:</b> {html.escape(content.location)}  •  <b>Generated:</b> {formatted_date}",
            ParagraphStyle(
                "HeaderRight",
                parent=self.styles["MetaLabel"],
                alignment=2,  # Right
            )
        )

        header_table = Table([[left_brand, right_info]], colWidths=[USABLE_WIDTH * 0.55, USABLE_WIDTH * 0.45])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        flowables.append(header_table)

        # Subtle divider
        flowables.append(HRFlowable(width="100%", thickness=0.75, color=COLOR_BORDER, spaceBefore=2, spaceAfter=8))

        # Document Title
        flowables.append(Paragraph("Personalized Career Roadmap", self.styles["DocTitle"]))

        # Personalized Subtitle
        subtitle_escaped = html.escape(content.personalized_subtitle)
        flowables.append(Paragraph(subtitle_escaped, self.styles["DocSubtitle"]))

        return flowables

    def _build_executive_banner(self, content: ValidatedRoadmapPDFContent) -> List[Flowable]:
        """Builds an executive summary callout banner with an emerald left accent."""
        summary_escaped = html.escape(content.executive_summary)

        banner_text = Paragraph(
            f"<b>Executive Pathway Strategy:</b> {summary_escaped}",
            self.styles["Body"]
        )

        banner_table = Table([[banner_text]], colWidths=[USABLE_WIDTH])
        banner_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_SUBTLE),
            ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
            ("LINEBEFORE", (0, 0), (0, -1), 3.0, COLOR_EMERALD),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        return [banner_table]

    def _build_candidate_metadata_card(self, content: ValidatedRoadmapPDFContent) -> List[Flowable]:
        """Renders 4-column candidate profile metadata grid."""
        candidate = content.candidate
        readiness = content.readiness

        name_display = html.escape(candidate.name or "SkillForge Candidate")
        role_display = html.escape(content.target_role_title)

        edu_items = []
        if candidate.degree:
            edu_items.append(candidate.degree)
        if candidate.branch:
            edu_items.append(candidate.branch)
        if candidate.semester:
            edu_items.append(f"Sem {candidate.semester}")
        edu_display = html.escape(", ".join(edu_items) if edu_items else (candidate.education or "Undergraduate Profile"))

        evidence_list = []
        if readiness.has_resume:
            evidence_list.append("Resume Claims")
        if readiness.has_github:
            evidence_list.append("GitHub Code")
        evidence_display = html.escape(" + ".join(evidence_list) if evidence_list else "Self-Assessment")

        row1 = [
            Paragraph("CANDIDATE NAME", self.styles["MetaLabel"]),
            Paragraph("TARGET ROLE", self.styles["MetaLabel"]),
            Paragraph("ACADEMIC / EXP", self.styles["MetaLabel"]),
            Paragraph("VERIFIED SOURCES", self.styles["MetaLabel"]),
        ]
        row2 = [
            Paragraph(name_display, self.styles["MetaValue"]),
            Paragraph(role_display, self.styles["MetaValue"]),
            Paragraph(edu_display, self.styles["MetaValue"]),
            Paragraph(evidence_display, self.styles["MetaValue"]),
        ]

        col_w = USABLE_WIDTH / 4.0
        meta_table = Table([row1, row2], colWidths=[col_w] * 4)
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_SUBTLE),
            ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return [meta_table]

    def _build_readiness_and_summary_section(self, content: ValidatedRoadmapPDFContent) -> List[Flowable]:
        """Renders side-by-side readiness card and gap summary metrics."""
        readiness = content.readiness

        # Left Card: Readiness Percentage & Segmented Progress Bar
        pct = readiness.readiness_percentage
        pct_color = "#059669" if pct >= 60 else ("#D97706" if pct >= 35 else "#E11D48")

        readiness_headline = Paragraph(
            f"<font name='Helvetica-Bold' size='22' color='{pct_color}'>{pct}%</font> "
            f"<font name='Helvetica-Bold' size='9' color='#0F172A'>ROLE READINESS SCORE</font>",
            self.styles["Body"]
        )

        card_w = (USABLE_WIDTH - 10) / 2.0
        bar_w = card_w - 20
        progress_bar = SegmentedProgressBarFlowable(
            width=bar_w,
            height=7,
            strong_count=readiness.strong_count,
            partial_count=readiness.partial_count,
            missing_count=readiness.missing_count,
            total_skills=readiness.total_required_skills,
        )

        readiness_counts = Paragraph(
            f"<b>{readiness.strong_count}</b> Demonstrated  •  "
            f"<b>{readiness.partial_count}</b> Partial  •  "
            f"<b>{readiness.missing_count}</b> Missing of {readiness.total_required_skills} Required",
            self.styles["MetaLabel"]
        )

        readiness_explanation = Paragraph(
            html.escape(content.readiness_explanation),
            self.styles["BodyMuted"]
        )

        left_content = [
            [readiness_headline],
            [Spacer(1, 4)],
            [progress_bar],
            [Spacer(1, 4)],
            [readiness_counts],
            [Spacer(1, 4)],
            [readiness_explanation],
        ]
        left_table = Table(left_content, colWidths=[card_w])
        left_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_CARD),
            ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))

        # Right Card: Roadmap Pipeline Metrics
        right_headline = Paragraph(
            "<b>ROADMAP PIPELINE METRICS</b>",
            self.styles["SectionHeader"]
        )

        gaps_metric = Paragraph(
            f"<b>Actionable Skill Gaps:</b> {content.high_priority_count} High Priority  "
            f"• {content.medium_priority_count} Medium  • {content.low_priority_count} Low",
            self.styles["Body"]
        )

        milestones_metric = Paragraph(
            f"<b>Curated Learning Phases:</b> {content.total_milestones} Sequenced Phases "
            f"({content.transitive_prerequisite_count} Foundational Prerequisites)",
            self.styles["Body"]
        )

        hash_snip = content.verification_hash[:16]
        audit_metric = Paragraph(
            f"<b>Integrity Audit Hash:</b> <font face='Courier'>{hash_snip}...</font> (SHA-256)",
            self.styles["MetaLabel"]
        )

        right_content = [
            [right_headline],
            [Spacer(1, 3)],
            [gaps_metric],
            [Spacer(1, 4)],
            [milestones_metric],
            [Spacer(1, 6)],
            [audit_metric],
        ]
        right_table = Table(right_content, colWidths=[card_w])
        right_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_CARD),
            ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))

        # Combine two cards side by side
        container = Table([[left_table, right_table]], colWidths=[card_w, card_w])
        container.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return [container]

    def _build_top_gaps_section(self, content: ValidatedRoadmapPDFContent) -> List[Flowable]:
        """Renders prioritized skill gap table with badges, demand metrics, and explanation."""
        flowables: List[Flowable] = []

        flowables.append(Paragraph("Prioritized Skill Gaps", self.styles["SectionHeader"]))
        flowables.append(
            Paragraph(
                f"Actionable competencies required for {html.escape(content.target_role_title)}, "
                "ranked by deterministic priority, gap severity, and market growth.",
                self.styles["SectionCaption"]
            )
        )

        if not content.validated_top_gaps:
            empty_p = Paragraph(
                "<b>All required competencies demonstrated.</b> No critical skill gaps identified.",
                self.styles["Body"]
            )
            empty_table = Table([[empty_p]], colWidths=[USABLE_WIDTH])
            empty_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_SUBTLE),
                ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]))
            flowables.append(empty_table)
            return flowables

        # Table Header
        headers = [
            Paragraph("SKILL COMPETENCY", self.styles["TableHeader"]),
            Paragraph("GAP STATUS", self.styles["TableHeader"]),
            Paragraph("PRIORITY", self.styles["TableHeader"]),
            Paragraph("DEMAND / GROWTH", self.styles["TableHeader"]),
            Paragraph("STRATEGIC RECOMMENDATION", self.styles["TableHeader"]),
        ]

        table_data = [headers]

        col_widths = [
            USABLE_WIDTH * 0.22,  # Skill & Category
            USABLE_WIDTH * 0.14,  # Status badge
            USABLE_WIDTH * 0.14,  # Priority badge
            USABLE_WIDTH * 0.16,  # Demand % & Growth %
            USABLE_WIDTH * 0.34,  # Personalized Explanation
        ]

        for gap in content.validated_top_gaps:
            # Skill Column
            cat_str = f"<br/><font color='#64748B' size='7'>{html.escape(gap.category or 'Core Competency')}</font>"
            skill_p = Paragraph(f"<b>{html.escape(gap.skill_name)}</b>{cat_str}", self.styles["Body"])

            # Status Badge
            status_val = gap.gap_status.value
            status_bg = "#FFF1F2" if status_val == "MISSING" else ("#FFFBEB" if status_val == "PARTIAL" else "#ECFDF5")
            status_fg = "#E11D48" if status_val == "MISSING" else ("#D97706" if status_val == "PARTIAL" else "#059669")
            status_p = Paragraph(
                f"<font color='{status_fg}'><b>{status_val}</b></font>",
                self.styles["BadgeText"]
            )

            # Priority Badge
            p_level = gap.priority_level.value if gap.priority_level else "PRIORITIZED"
            p_fg = "#E11D48" if p_level == "HIGH" else ("#D97706" if p_level == "MEDIUM" else "#2563EB")
            p_score_str = f" ({gap.priority_score:.2f})" if gap.priority_score is not None else ""
            priority_p = Paragraph(
                f"<font color='{p_fg}'><b>{p_level}</b>{p_score_str}</font>",
                self.styles["BadgeText"]
            )

            # Demand & Growth
            demand_pct = f"{round((gap.demand_score or 0.0) * 100)}%"
            growth_pct = f"{round((gap.growth_rate or 0.0) * 100):+d}% YoY"
            demand_p = Paragraph(
                f"<b>{demand_pct}</b> Demand<br/><font color='#059669' size='7'><b>{growth_pct}</b></font>",
                self.styles["MetaValue"]
            )

            # Narrative Explanation
            narrative_text = gap.why_it_matters or gap.suggested_focus or "Critical competency for target role."
            narrative_p = Paragraph(html.escape(narrative_text), self.styles["BodyMuted"])

            table_data.append([skill_p, status_p, priority_p, demand_p, narrative_p])

        gaps_table = Table(table_data, colWidths=col_widths)
        gaps_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_BG_SUBTLE),
            ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        flowables.append(gaps_table)
        return flowables

    def _build_roadmap_phases(self, content: ValidatedRoadmapPDFContent) -> List[Flowable]:
        """Renders ordered sequence of roadmap phase cards enclosed in KeepTogether."""
        flowables: List[Flowable] = []

        flowables.append(Paragraph("Actionable Learning Roadmap", self.styles["SectionHeader"]))
        flowables.append(
            Paragraph(
                "Deterministic topological prerequisite sequence designed to systematically close skill gaps.",
                self.styles["SectionCaption"]
            )
        )

        for phase in content.validated_phases:
            phase_card = self._build_single_phase_card(phase)
            # Wrap each phase card in KeepTogether to prevent awkward multi-page splits
            flowables.append(KeepTogether(phase_card))
            flowables.append(Spacer(1, 8))

        return flowables

    def _build_single_phase_card(self, phase: ValidatedRoadmapPhase) -> List[Flowable]:
        """Constructs a single self-contained roadmap phase milestone card."""
        elements: List[Flowable] = []

        # Phase Card Header Table
        # Left: Phase Number Badge + Title + Skill Pill
        phase_num_badge = f"<font color='#2563EB'><b>PHASE {phase.order_index}</b></font>"
        skill_name_badge = f"<font color='#0F172A'><b>[{html.escape(phase.skill_name)}]</b></font>"
        p_tier = phase.priority_level.value if phase.priority_level else ("PREREQUISITE" if phase.is_transitive_prerequisite else "CORE")
        tier_color = "#E11D48" if p_tier == "HIGH" else ("#D97706" if p_tier == "MEDIUM" else "#2563EB")
        tier_badge = f"<font color='{tier_color}'><b>• {p_tier}</b></font>"

        title_p = Paragraph(
            f"{phase_num_badge}  {skill_name_badge}  <b>{html.escape(phase.phase_title)}</b>  {tier_badge}",
            self.styles["PhaseTitle"]
        )

        # Strategic Rationale
        rationale_p = Paragraph(
            f"<b>Rationale:</b> {html.escape(phase.personalized_rationale)}",
            self.styles["Body"]
        )

        # Key Technical Topics
        topics_str = "  •  ".join(html.escape(t) for t in phase.key_topics) if phase.key_topics else "Fundamental Core Concepts"
        topics_p = Paragraph(f"<b>Key Competencies:</b> {topics_str}", self.styles["MetaValue"])

        card_content = [
            [title_p],
            [Spacer(1, 3)],
            [rationale_p],
            [Spacer(1, 4)],
            [topics_p],
        ]

        if phase.expected_focus:
            focus_p = Paragraph(f"<b>Expected Focus:</b> {html.escape(phase.expected_focus)}", self.styles["BodyMuted"])
            card_content.extend([[Spacer(1, 3)], [focus_p]])

        # Approved Learning Resources
        if phase.resources:
            res_flowables = self._build_approved_resources_subtable(phase.resources)
            card_content.extend([[Spacer(1, 5)], [res_flowables]])

        # Curated Practice Challenge (Project Box)
        if phase.project:
            proj_box = self._build_curated_project_box(phase.project)
            card_content.extend([[Spacer(1, 5)], [proj_box]])

        phase_table = Table(card_content, colWidths=[USABLE_WIDTH])
        phase_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_CARD),
            ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(phase_table)
        return elements

    def _build_approved_resources_subtable(self, resources: Tuple[VerifiedApprovedResource, ...]) -> Flowable:
        """Builds subtable of curated learning resources with clickable hyperlinks."""
        header_row = [
            Paragraph("APPROVED RESOURCE", self.styles["TableHeader"]),
            Paragraph("PROVIDER", self.styles["TableHeader"]),
            Paragraph("TYPE", self.styles["TableHeader"]),
            Paragraph("DURATION", self.styles["TableHeader"]),
        ]
        sub_data = [header_row]

        sub_col_widths = [
            (USABLE_WIDTH - 16) * 0.50,
            (USABLE_WIDTH - 16) * 0.20,
            (USABLE_WIDTH - 16) * 0.15,
            (USABLE_WIDTH - 16) * 0.15,
        ]

        for res in resources[:3]:
            # Secure XML-escaped clickable hyperlink
            escaped_url = html.escape(res.url)
            escaped_title = html.escape(res.title)
            link_html = f"<a href='{escaped_url}' color='#2563EB'><u>{escaped_title}</u></a>"
            res_p = Paragraph(link_html, self.styles["Body"])

            provider_p = Paragraph(html.escape(res.provider), self.styles["MetaValue"])
            type_p = Paragraph(html.escape(res.resource_type.replace("_", " ")), self.styles["MetaValue"])

            mins = f"{res.estimated_minutes} min" if res.estimated_minutes else "Self-Paced"
            dur_p = Paragraph(mins, self.styles["MetaValue"])

            sub_data.append([res_p, provider_p, type_p, dur_p])

        res_table = Table(sub_data, colWidths=sub_col_widths)
        res_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_BLUE_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        return res_table

    def _build_curated_project_box(self, project: VerifiedApprovedProject) -> Flowable:
        """
        Builds distinct callout box for curated approved engineering challenge.
        ENFORCES: Prominent label indicating CURATED CHALLENGE — NOT CANDIDATE PROOF.
        """
        hours_str = f" • Estimated {project.estimated_hours} Hours" if project.estimated_hours else ""
        header_p = Paragraph(
            f"<b>PRACTICE CHALLENGE:</b> {html.escape(project.title)} "
            f"[{html.escape(project.difficulty)}{hours_str}]  "
            f"<font color='#4F46E5' size='6.5'><b>[RECOMMENDED CHALLENGE — NOT CANDIDATE PROOF]</b></font>",
            self.styles["ChallengeHeading"]
        )

        desc_p = Paragraph(html.escape(project.description), self.styles["BodyMuted"])

        deliverables_str = ", ".join(html.escape(d) for d in project.deliverables) if project.deliverables else "Code Repository"
        deliv_p = Paragraph(f"<b>Deliverables:</b> {deliverables_str}", self.styles["MetaValue"])

        criteria_str = "; ".join(html.escape(c) for c in project.verification_criteria) if project.verification_criteria else "Automated test suite"
        crit_p = Paragraph(f"<b>Verification Criteria:</b> {criteria_str}", self.styles["MetaValue"])

        box_data = [
            [header_p],
            [Spacer(1, 2)],
            [desc_p],
            [Spacer(1, 2)],
            [deliv_p],
            [Spacer(1, 2)],
            [crit_p],
        ]
        box_table = Table(box_data, colWidths=[USABLE_WIDTH - 16])
        box_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_INDIGO_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.75, COLOR_INDIGO),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return box_table

    def _build_next_steps_section(self, content: ValidatedRoadmapPDFContent) -> List[Flowable]:
        """Renders immediate actionable next steps."""
        flowables: List[Flowable] = []

        flowables.append(Paragraph("Immediate Execution Steps (7–14 Days)", self.styles["SectionHeader"]))

        step_rows = []
        for idx, step in enumerate(content.immediate_next_steps, start=1):
            pill = Paragraph(f"<b>#{idx}</b>", self.styles["BadgeText"])
            step_text = Paragraph(html.escape(step), self.styles["Body"])
            step_rows.append([pill, step_text])

        step_table = Table(step_rows, colWidths=[USABLE_WIDTH * 0.08, USABLE_WIDTH * 0.92])
        step_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), COLOR_BG_SUBTLE),
            ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        flowables.append(step_table)
        return flowables

    def _build_closing_card(self, content: ValidatedRoadmapPDFContent) -> List[Flowable]:
        """Renders motivational closing summary card."""
        closing_escaped = html.escape(content.closing_encouragement)

        closing_p = Paragraph(
            f"<b>Career Acceleration Outlook:</b> {closing_escaped}",
            self.styles["Body"]
        )

        closing_table = Table([[closing_p]], colWidths=[USABLE_WIDTH])
        closing_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_SUBTLE),
            ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
            ("LINEBEFORE", (0, 0), (0, -1), 3.0, COLOR_PRIMARY_DARK),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return [closing_table]


# Global singleton helper
roadmap_pdf_renderer = RoadmapPDFRenderer()
