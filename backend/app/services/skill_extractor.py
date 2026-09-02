import re
from typing import Dict, List, Set, Tuple


# Delimiters frequently used in dedicated skill sections
SKILL_DELIMITERS_REGEX = re.compile(r"[,|\n•·;\t/]+")

# Obvious false positives to reject unless explicitly matched
FALSE_POSITIVES: Set[str] = {
    "team",
    "teams",
    "communication",
    "responsible",
    "worked",
    "project",
    "projects",
    "experience",
    "work",
    "development",
    "management",
    "leadership",
    "years",
    "year",
    "months",
    "month",
    "knowledge",
    "strong",
    "good",
    "skills",
    "software",
    "engineer",
    "developer",
    "architecture",
    "etc",
    "using",
    "used",
    "built",
    "designed",
    "implemented",
}


def clean_candidate_token(token: str) -> str:
    """Cleans punctuation from the edges of candidate skill tokens."""
    token = token.strip()
    # Strip markdown symbols and bullets
    token = re.sub(r"^[\s*#\-•·]+|[\s*#\-•·]+$", "", token).strip()
    # Remove leading/trailing quotes, colons, brackets
    token = token.strip("\"'`():[]{}")
    return token


def extract_candidate_mentions_from_skills_section(skills_text: str) -> List[str]:
    """
    Parses a dedicated skills section, splitting by common delimiters.
    Handles labels like 'Languages: Python, Go' or 'Databases: PostgreSQL'.
    """
    if not skills_text:
        return []

    candidates = []
    lines = skills_text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # If line starts with a category label like "Languages: Python, Java", strip the label or split
        if ":" in line and not line.lower().startswith("http"):
            parts = line.split(":", 1)
            content_part = parts[1].strip()
        else:
            content_part = line

        # Split on standard delimiters
        tokens = SKILL_DELIMITERS_REGEX.split(content_part)
        for tok in tokens:
            cleaned = clean_candidate_token(tok)
            if cleaned and len(cleaned) <= 50 and cleaned.lower() not in FALSE_POSITIVES:
                candidates.append(cleaned)

    return candidates


def extract_candidate_mentions(sections: Dict[str, str]) -> List[Tuple[str, str]]:
    """
    Extracts candidate skill strings across all parsed sections.
    Returns list of (candidate_mention, section_source) tuples.
    """
    candidates: List[Tuple[str, str]] = []
    seen: Set[str] = set()

    # 1. Dedicated Skills Section (Primary)
    skills_text = sections.get("skills", "")
    for mention in extract_candidate_mentions_from_skills_section(skills_text):
        norm = mention.lower()
        if norm not in seen:
            seen.add(norm)
            candidates.append((mention, "skills"))

    # 2. Secondary Sections (Projects & Experience)
    # Check lines and tokens from projects and experience
    for section_name in ["projects", "experience"]:
        section_text = sections.get(section_name, "")
        if not section_text:
            continue

        # Look for tokens in project bullet points
        lines = section_text.split("\n")
        for line in lines:
            # If line mentions "Tech Stack:", "Technologies:", or lists tools in parentheses
            bracketed = re.findall(r"\(([^)]+)\)", line)
            for group in bracketed:
                for tok in SKILL_DELIMITERS_REGEX.split(group):
                    cleaned = clean_candidate_token(tok)
                    if cleaned and len(cleaned) <= 40 and cleaned.lower() not in FALSE_POSITIVES:
                        norm = cleaned.lower()
                        if norm not in seen:
                            seen.add(norm)
                            candidates.append((cleaned, section_name))

    return candidates
