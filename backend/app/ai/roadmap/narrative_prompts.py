"""
Prompt construction for AI Roadmap PDF Narrative Generation.
Post-MVP Career Roadmap PDF Feature (Phase 3).

Enforces:
- Authoritative ground truth of the supplied VerifiedRoadmapPDFContext.
- Strict prohibition against inventing skills, inventing URLs, fabricating scores, or re-ordering milestones.
- Privacy protection: candidate email and internal identifiers are omitted from the prompt.
- Curated projects are described as practical recommendations, NOT candidate proof.
- weekly_hours_recommendation must NOT be invented.
"""

from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from app.ai.context.roadmap_pdf_context import VerifiedRoadmapPDFContext

ROADMAP_NARRATIVE_SYSTEM_PROMPT = (
    "You are the Executive Career Strategist for SkillForge AI.\n"
    "Your objective is to generate an evidence-grounded, professional narrative for a candidate's "
    "Personalized Career Roadmap PDF based SOLELY on the supplied authoritative context.\n\n"
    "INVIOLABLE ARCHITECTURAL RULES:\n"
    "1. The supplied context contains absolute ground truth deterministically calculated by SkillForge.\n"
    "2. NEVER invent, modify, or contradict any verified fact: readiness percentage, skill classifications, "
    "demand scores, growth rates, priority scores, priority tiers, or milestone sequences.\n"
    "3. NEVER invent new learning resources, external links, or URLs. Refer only to the approved materials provided.\n"
    "4. NEVER invent new skills, certifications, or technologies not present in the supplied context.\n"
    "5. Curated projects are recommended practical engineering challenges, NOT proof of candidate skill possession. "
    "Do NOT state that the candidate has completed them.\n"
    "6. Do NOT fabricate study schedules, weekly study hours, completion dates, or salary expectations.\n"
    "7. For every milestone phase, you MUST use the exact skill_id provided in the context.\n"
    "8. For top skill gap explanations, you MUST use the exact skill_id provided in the top gaps section.\n"
    "9. Tone: Professional, empowering, rigorous, and engineering-focused. Avoid hype, fluff, or false assurances."
)


def build_roadmap_narrative_messages(context: VerifiedRoadmapPDFContext) -> List[BaseMessage]:
    """
    Serializes a VerifiedRoadmapPDFContext into a bounded, privacy-safe LangChain message list.
    Candidate email and secret identifiers are excluded.
    """
    candidate = context.candidate
    readiness = context.readiness
    roadmap = context.roadmap

    # Candidate profile lines (excluding email for privacy)
    profile_lines = [
        f"Candidate Name: {candidate.name or 'SkillForge Candidate'}",
        f"Target Career Role: {roadmap.target_role_title}",
        f"Hiring Market: {roadmap.location}",
    ]
    if candidate.college:
        profile_lines.append(f"College/University: {candidate.college}")
    if candidate.degree:
        profile_lines.append(f"Degree: {candidate.degree}")
    if candidate.branch:
        profile_lines.append(f"Major/Branch: {candidate.branch}")
    if candidate.semester:
        profile_lines.append(f"Current Semester: {candidate.semester}")
    if candidate.experience_level:
        profile_lines.append(f"Experience Level: {candidate.experience_level}")

    # Readiness metrics lines
    readiness_lines = [
        f"Readiness Score: {readiness.readiness_percentage}%",
        f"Total Demanded Competencies: {readiness.total_required_skills}",
        f"Strongly Demonstrated Skills: {readiness.strong_count}",
        f"Partially Demonstrated/Claimed Skills: {readiness.partial_count}",
        f"Missing Skills: {readiness.missing_count}",
        f"Resume Analyzed: {'Yes' if readiness.has_resume else 'No'}",
        f"GitHub Analyzed: {'Yes' if readiness.has_github else 'No'}",
    ]

    # Top prioritized gaps lines
    gap_lines = []
    for g in context.prioritized_gaps.top_gaps:
        p_str = f"{g.priority_level.value} (score {g.priority_score})" if g.priority_level else "Prioritized"
        d_str = f"{round((g.demand_score or 0.0) * 100)}%"
        growth_str = f"{round((g.growth_rate or 0.0) * 100)}% YoY"
        gap_lines.append(
            f"- Skill: {g.skill_name} (skill_id: {g.skill_id})\n"
            f"  Status: {g.gap_status.value} | Priority: {p_str}\n"
            f"  Market Demand: {d_str} | Growth: {growth_str}\n"
            f"  Reason: {g.deterministic_explanation or 'Demanded competency for target role.'}"
        )

    # Sequenced roadmap milestones lines
    milestone_lines = []
    for m in roadmap.milestones:
        prereqs = [p.skill_name for p in m.prerequisites]
        prereq_str = ", ".join(prereqs) if prereqs else "None (Foundational)"
        
        res_titles = [f"'{r.title}' ({r.provider})" for r in m.resources[:2]]
        res_str = "; ".join(res_titles) if res_titles else "Curated official documentation"

        proj_str = f"'{m.project.title}' ({m.project.difficulty} Challenge)" if m.project else "Hands-on implementation"

        milestone_lines.append(
            f"Phase #{m.order_index}: {m.skill_name} (skill_id: {m.skill_id})\n"
            f"  - Category: {m.category or 'Core'}\n"
            f"  - Gap Status: {m.gap_status.value}\n"
            f"  - Priority Tier: {m.priority_level.value if m.priority_level else 'Foundational Prerequisite'}\n"
            f"  - Prerequisite Ordering: {prereq_str}\n"
            f"  - Deterministic Reason: {m.deterministic_reason}\n"
            f"  - Curated Resources: {res_str}\n"
            f"  - Engineering Project Challenge: {proj_str}"
        )

    user_content = (
        "=== CANDIDATE PROFILE ===\n"
        + "\n".join(profile_lines)
        + "\n\n=== DETERMINISTIC READINESS BENCHMARK ===\n"
        + "\n".join(readiness_lines)
        + "\n\n=== HIGH PRIORITY ACTIONABLE SKILL GAPS ===\n"
        + ("\n".join(gap_lines) if gap_lines else "None (All required competencies satisfied)")
        + "\n\n=== SEQUENCED ROADMAP PHASES (TOPOLOGICAL DAG) ===\n"
        + "\n".join(milestone_lines)
        + "\n\n=== TASK ===\n"
        + "Generate a cohesive, personalized narrative conforming strictly to the requested schema.\n"
        + "Remember: Every phase must correspond to the exact order and skill_id in the sequenced roadmap."
    )

    return [
        SystemMessage(content=ROADMAP_NARRATIVE_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]
