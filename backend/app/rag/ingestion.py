"""
Approved Evidence Ingestion Pipeline for SkillForge AI RAG Retrieval Layer.
Checkpoint C7-B.

Guarantees:
- Deterministic, idempotent document ingestion into existing RAG tables.
- Zero dynamic skill extraction via LLMs: foreign-key relationships to canonical skills are authoritative.
- Content safety: rejects raw database dumps, recruiter boilerplate, and secrets.
- Deterministic RFC 4122 UUID v5 document IDs derived from (source_type, source_reference).
- SHA-256 content hashing for duplicate avoidance and change detection.
- Clean re-indexing with stale-chunk removal via foreign key CASCADE.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid5, NAMESPACE_URL, NAMESPACE_DNS

from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    ApprovedProject,
    ApprovedResource,
    JobRole,
    MarketJob,
    MarketJobSkill,
    MarketSkillDemand,
    Skill,
    RAGDocument as DBRAGDocument,
)
from app.rag.provenance import (
    CANONICAL_SEED_PROJECT_HASHES,
    compute_canonical_project_fingerprint,
    is_canonical_project,
)
from app.rag.chunking import DeterministicChunker
from app.rag.embeddings import EmbeddingProvider, get_shared_embedding_provider
from app.rag.exceptions import RAGStorageError, RAGValidationError
from app.rag.models import (
    RAGChunk,
    RAGDocument,
    RAGDocumentMetadata,
    RAGSourceType,
)
from app.rag.repository import RAGRepository

logger = logging.getLogger(__name__)


def compute_document_content_hash(
    source_type: str,
    source_reference: str,
    title: str,
    content: str,
    skill_id: Optional[UUID] = None,
) -> str:
    """
    Computes a deterministic SHA-256 content hash over normalized document content and metadata.
    Used for idempotency checks and change detection.
    """
    st_norm = source_type.strip()
    sr_norm = source_reference.strip()
    sk_norm = str(skill_id) if skill_id else ""
    t_norm = title.strip()
    c_norm = content.strip()
    payload = f"{st_norm}|{sr_norm}|{sk_norm}|{t_norm}|{c_norm}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_resource_rag_document(
    resource: ApprovedResource,
    skill: Optional[Skill] = None,
) -> RAGDocument:
    """
    Deterministically transforms an approved learning resource into a typed RAGDocument.
    Enforces strict approval gating: is_approved must be True.
    """
    if not resource.is_approved:
        raise RAGValidationError(
            f"ApprovedResource '{resource.id}' is not approved (is_approved={resource.is_approved}). "
            "Only verified approved resources can enter RAG."
        )

    canonical_skill = skill or getattr(resource, "skill", None)
    if not canonical_skill or not resource.skill_id:
        raise RAGValidationError(
            f"ApprovedResource '{resource.id}' must be linked to a valid canonical skill."
        )

    title_clean = (resource.title or "").strip()
    url_clean = (resource.url or "").strip()
    provider_clean = (resource.provider or "Official").strip()
    rtype_clean = (resource.resource_type or "GUIDE").strip()
    diff_clean = (resource.difficulty or "ALL_LEVELS").strip()

    if not title_clean or not url_clean:
        raise RAGValidationError(
            f"ApprovedResource '{resource.id}' has missing or empty title/url."
        )

    source_type = RAGSourceType.APPROVED_RESOURCE
    source_reference = f"approved_resource:{resource.id}"
    doc_id = uuid5(NAMESPACE_URL, f"sf:rag:approved_resource:{resource.id}")
    doc_title = f"Learning Resource: {title_clean}"

    content_lines = [
        f"Learning Resource: {title_clean}",
        f"Provider: {provider_clean}",
        f"Type: {rtype_clean}",
        f"Difficulty: {diff_clean}",
        f"Duration: {resource.estimated_minutes or 'Self-paced'} minutes",
        f"Canonical Skill: {canonical_skill.name.strip()} (Category: {canonical_skill.category.strip() if canonical_skill.category else 'General'})",
        f"Official URL: {url_clean}",
    ]
    content = "\n".join(content_lines)

    content_hash = compute_document_content_hash(
        source_type=source_type.value,
        source_reference=source_reference,
        title=doc_title,
        content=content,
        skill_id=resource.skill_id,
    )

    observed_at = resource.updated_at or resource.created_at or datetime.now(timezone.utc)

    metadata = RAGDocumentMetadata(
        skill_id=resource.skill_id,
        skill_name=canonical_skill.name.strip(),
        source_reference=source_reference,
        observed_at=observed_at,
        confidence_score=1.0,
        approved_by="curated_learning_resource",
        content_hash=content_hash,
    )

    return RAGDocument(
        id=doc_id,
        source_type=source_type,
        source_reference=source_reference,
        title=doc_title,
        content=content,
        metadata=metadata,
        created_at=observed_at,
    )


def build_market_demand_rag_document(
    demand: MarketSkillDemand,
    skill: Optional[Skill] = None,
) -> RAGDocument:
    """
    Deterministically transforms a computed market demand record into a typed RAGDocument.
    Represents authoritative aggregate market statistics (no LLM, no raw job dumps).
    """
    canonical_skill = skill or getattr(demand, "skill", None)
    if not canonical_skill or not demand.skill_id:
        raise RAGValidationError(
            f"MarketSkillDemand '{demand.id}' must be linked to a valid canonical skill."
        )

    if demand.demand_score is None:
        raise RAGValidationError(
            f"MarketSkillDemand '{demand.id}' has null demand_score."
        )

    source_clean = (demand.source or "adzuna").strip()
    source_type = RAGSourceType.MARKET
    source_reference = f"market_demand:{source_clean}:{canonical_skill.slug.strip()}"
    doc_id = uuid5(NAMESPACE_URL, f"sf:rag:market_demand:{source_clean}:{canonical_skill.slug.strip()}")
    doc_title = f"Market Demand Intelligence: {canonical_skill.name.strip()}"

    computed_str = demand.computed_at.strftime("%Y-%m-%d") if demand.computed_at else "Unknown"

    content_lines = [
        f"Canonical Skill: {canonical_skill.name.strip()} (Category: {canonical_skill.category.strip() if canonical_skill.category else 'General'})",
        f"Market Source: {source_clean}",
        f"Demand Score: {round(float(demand.demand_score), 4)} (Normalized Scale: 0.0 to 1.0)",
        f"Demand Share: {round(float(demand.demand_share) * 100.0, 2)}% of analyzed market postings",
        f"Demanding Postings: {demand.job_count} out of {demand.sample_size} total postings",
        f"Observation Timestamp: {computed_str}",
    ]
    content = "\n".join(content_lines)

    content_hash = compute_document_content_hash(
        source_type=source_type.value,
        source_reference=source_reference,
        title=doc_title,
        content=content,
        skill_id=demand.skill_id,
    )

    observed_at = demand.computed_at or datetime.now(timezone.utc)

    metadata = RAGDocumentMetadata(
        skill_id=demand.skill_id,
        skill_name=canonical_skill.name.strip(),
        source_reference=source_reference,
        observed_at=observed_at,
        confidence_score=1.0,
        approved_by="market_demand_aggregation_pipeline",
        content_hash=content_hash,
    )

    return RAGDocument(
        id=doc_id,
        source_type=source_type,
        source_reference=source_reference,
        title=doc_title,
        content=content,
        metadata=metadata,
        created_at=observed_at,
    )


def build_market_job_rag_document(
    job: MarketJob,
    job_skill: MarketJobSkill,
    skill: Optional[Skill] = None,
) -> RAGDocument:
    """
    Deterministically transforms bounded job-posting evidence into a typed RAGDocument.
    Strictly excludes raw description dumps, recruiter boilerplate, and EEO legal boilerplate.
    Only bounded excerpt text and matched taxonomy metadata are retained.
    """
    if not job or not job.id:
        raise RAGValidationError("MarketJob record is missing or invalid.")
    if not job_skill or not job_skill.skill_id:
        raise RAGValidationError("MarketJobSkill record is missing or lacks skill_id.")
    if job_skill.market_job_id != job.id:
        raise RAGValidationError(
            f"MarketJobSkill '{job_skill.id}' does not belong to MarketJob '{job.id}'."
        )

    canonical_skill = skill or getattr(job_skill, "skill", None)
    if not canonical_skill or canonical_skill.id != job_skill.skill_id:
        raise RAGValidationError(
            f"MarketJobSkill '{job_skill.id}' must be linked to a matching canonical Skill."
        )

    source_type = RAGSourceType.MARKET
    source_reference = f"market_job:{job.id}:{canonical_skill.id}"
    doc_id = uuid5(NAMESPACE_URL, f"sf:rag:market_job:{job.id}:{canonical_skill.id}")

    job_title_clean = (job.title or "").strip()
    if not job_title_clean:
        raise RAGValidationError(f"MarketJob '{job.id}' has empty title.")

    doc_title = f"Market Requirement: {canonical_skill.name.strip()} ({job_title_clean})"

    company_clean = (job.company_name or "Industry Employer").strip()
    loc_clean = (job.location or "India / Remote").strip()
    cat_clean = (job.category or "Technology").strip()
    matched_alias = (job_skill.matched_alias or canonical_skill.name).strip()
    excerpt = (job_skill.evidence_text or job_title_clean).strip()
    job_source = (job.source or "market_feed").strip()

    content_lines = [
        f"Job Title: {job_title_clean}",
        f"Hiring Company: {company_clean}",
        f"Location: {loc_clean}",
        f"Job Category: {cat_clean}",
        f"Demanded Canonical Skill: {canonical_skill.name.strip()}",
        f"Matched Skill Keyword: {matched_alias}",
        f"Evidence Excerpt: {excerpt}",
        f"Provider Source: {job_source}",
    ]
    content = "\n".join(content_lines)

    content_hash = compute_document_content_hash(
        source_type=source_type.value,
        source_reference=source_reference,
        title=doc_title,
        content=content,
        skill_id=canonical_skill.id,
    )

    observed_at = job.ingested_at or job.created_at or datetime.now(timezone.utc)

    metadata = RAGDocumentMetadata(
        skill_id=canonical_skill.id,
        skill_name=canonical_skill.name.strip(),
        source_reference=source_reference,
        observed_at=observed_at,
        confidence_score=float(job_skill.confidence_score) if job_skill.confidence_score is not None else 1.0,
        approved_by="market_taxonomy_extraction",
        content_hash=content_hash,
    )

    return RAGDocument(
        id=doc_id,
        source_type=source_type,
        source_reference=source_reference,
        title=doc_title,
        content=content,
        metadata=metadata,
        created_at=observed_at,
    )


def build_project_rag_document(
    project: ApprovedProject,
    skill: Optional[Skill] = None,
    role: Optional[JobRole] = None,
) -> RAGDocument:
    """
    Deterministically transforms an approved practical project into a typed RAGDocument.
    Adheres strictly to the bounded C7-E project document format.
    Project evidence is curated context; it is NOT proof of candidate skill possession.
    """
    if not project or not getattr(project, "id", None):
        raise RAGValidationError("ApprovedProject record is missing or invalid.")

    canonical_skill = skill or getattr(project, "skill", None)
    if not canonical_skill or not getattr(project, "skill_id", None):
        raise RAGValidationError(
            f"ApprovedProject '{project.id}' must be linked to a valid canonical skill."
        )

    canonical_role = role or getattr(project, "role", None)
    role_name = (
        canonical_role.title.strip()
        if canonical_role and getattr(canonical_role, "title", None)
        else "General / Unspecified"
    )

    title_clean = (project.title or "").strip()
    if not title_clean:
        raise RAGValidationError(f"ApprovedProject '{project.id}' has missing or empty title.")

    desc_clean = (project.description or "").strip()
    diff_clean = (project.difficulty or "INTERMEDIATE").strip().upper()
    est_hours_str = str(project.estimated_hours) if project.estimated_hours is not None else "N/A"
    skill_name = canonical_skill.name.strip()

    # Normalize deliverables
    raw_deliverables = getattr(project, "deliverables", None) or []
    if isinstance(raw_deliverables, str):
        try:
            raw_deliverables = json.loads(raw_deliverables)
        except Exception:
            raw_deliverables = []
    deliverables = [str(d).strip() for d in raw_deliverables if str(d).strip()]
    if deliverables:
        deliverables_lines = "\n".join(f"- {d}" for d in deliverables)
    else:
        deliverables_lines = "- None specified"

    # Normalize verification criteria
    raw_criteria = getattr(project, "verification_criteria", None) or []
    if isinstance(raw_criteria, str):
        try:
            raw_criteria = json.loads(raw_criteria)
        except Exception:
            raw_criteria = []
    criteria = [str(c).strip() for c in raw_criteria if str(c).strip()]
    if criteria:
        criteria_lines = "\n".join(f"- {c}" for c in criteria)
    else:
        criteria_lines = "- None specified"

    source_type = RAGSourceType.APPROVED_PROJECT
    source_reference = f"approved_project:{project.id}"
    doc_id = uuid5(NAMESPACE_DNS, f"sf:rag:approved_project:{project.id}")
    doc_title = f"Approved Project: {title_clean}"

    content = (
        f"Approved Practical Project:\n"
        f"Title: {title_clean}\n"
        f"Target Skill: {skill_name}\n"
        f"Target Role: {role_name}\n"
        f"Difficulty: {diff_clean}\n"
        f"Estimated Hours: {est_hours_str}\n\n"
        f"Project Description:\n"
        f"{desc_clean}\n\n"
        f"Deliverables:\n"
        f"{deliverables_lines}\n\n"
        f"Verification Criteria:\n"
        f"{criteria_lines}\n\n"
        f"This is curated project evidence.\n"
        f"It is NOT proof that the candidate possesses the listed skills."
    )

    content_hash = compute_document_content_hash(
        source_type=source_type.value,
        source_reference=source_reference,
        title=doc_title,
        content=content,
        skill_id=project.skill_id,
    )

    observed_at = project.updated_at or project.created_at or datetime.now(timezone.utc)

    metadata = RAGDocumentMetadata(
        skill_id=project.skill_id,
        skill_name=skill_name,
        source_reference=source_reference,
        observed_at=observed_at,
        confidence_score=1.0,
        approved_by="curated_seed_0017",
        content_hash=content_hash,
    )

    return RAGDocument(
        id=doc_id,
        source_type=source_type,
        source_reference=source_reference,
        title=doc_title,
        content=content,
        metadata=metadata,
        created_at=observed_at,
    )


class EvidenceIngestionService:
    """
    Orchestrates deterministic, idempotent indexing of approved evidence into PostgreSQL/pgvector.
    Enforces atomic re-indexing, stale chunk purge, and zero duplicate documents or chunks.
    """

    def __init__(
        self,
        session: Session,
        embedding_provider: Optional[EmbeddingProvider] = None,
        chunker: Optional[DeterministicChunker] = None,
        repository: Optional[RAGRepository] = None,
    ):
        self.session = session
        self.embedding_provider = embedding_provider or get_shared_embedding_provider()
        self.chunker = chunker or DeterministicChunker()
        self.repository = repository or RAGRepository(session=self.session)

    def index_or_update_document(self, document: RAGDocument) -> str:
        """
        Idempotently indexes or updates a single approved RAGDocument.
        Returns:
            'skipped' : Document exists and content_hash is unchanged.
            'updated' : Document exists, content changed; old chunks purged via CASCADE, new chunks saved.
            'ingested': Document is new; document and chunks persisted.
        """
        if not isinstance(document, RAGDocument):
            raise RAGValidationError(f"Expected RAGDocument instance, got {type(document).__name__}")

        # Step 1: Idempotency check via deterministic reference lookup and PK lookup
        existing = self.repository.find_document_by_reference(
            source_type=document.source_type.value,
            source_reference=document.source_reference,
        )
        if not existing:
            existing = self.session.get(DBRAGDocument, document.id)

        target_hash = document.metadata.content_hash

        if existing:
            existing_hash = (existing.document_metadata or {}).get("content_hash")
            if existing_hash and existing_hash == target_hash:
                logger.debug(
                    "Skipping unchanged RAG document '%s' (%s)",
                    document.source_reference,
                    document.source_type.value,
                )
                return "skipped"

        # Step 2: Prepare chunks and embeddings in-memory BEFORE database mutations
        chunks = self.chunker.chunk_document(document)
        if not chunks:
            raise RAGValidationError(f"Chunker produced 0 chunks for document '{document.id}'.")

        chunk_texts = [c.content for c in chunks]
        embeddings = self.embedding_provider.embed_documents(chunk_texts)

        embedded_chunks: List[RAGChunk] = []
        for c, emb in zip(chunks, embeddings):
            embedded_chunks.append(
                RAGChunk(
                    id=c.id,
                    document_id=c.document_id,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    embedding=tuple(emb),
                    skill_id=c.skill_id,
                    source_type=c.source_type,
                    source_reference=c.source_reference,
                    metadata=c.metadata,
                    created_at=c.created_at,
                )
            )

        # Step 3: Atomic database persistence
        if existing:
            # Atomic replacement: delete existing document.
            # Foreign key CASCADE automatically purges all existing chunks in PostgreSQL.
            self.session.delete(existing)
            self.session.flush()

            self.repository.save_document(document)
            self.repository.save_chunks(embedded_chunks)
            self.session.commit()

            logger.info(
                "Updated changed RAG document '%s' (%s, %d chunks)",
                document.title,
                document.source_type.value,
                len(embedded_chunks),
            )
            return "updated"

        # New document insertion
        self.repository.save_document(document)
        self.repository.save_chunks(embedded_chunks)
        self.session.commit()

        logger.info(
            "Ingested new RAG document '%s' (%s, %d chunks)",
            document.title,
            document.source_type.value,
            len(embedded_chunks),
        )
        return "ingested"

    def ingest_approved_resources(self) -> Dict[str, Any]:
        """
        Scans approved_resources table and ingests all rows where is_approved == True.
        """
        resources = (
            self.session.query(ApprovedResource)
            .join(Skill, ApprovedResource.skill_id == Skill.id)
            .filter(ApprovedResource.is_approved == True)  # noqa: E712
            .all()
        )

        ingested = 0
        skipped = 0
        updated = 0
        failed = 0
        errors: List[Dict[str, str]] = []

        for r in resources:
            try:
                doc = build_resource_rag_document(resource=r, skill=r.skill)
                status = self.index_or_update_document(doc)
                if status == "ingested":
                    ingested += 1
                elif status == "skipped":
                    skipped += 1
                elif status == "updated":
                    updated += 1
            except Exception as exc:
                self.session.rollback()
                failed += 1
                ref = f"approved_resource:{r.id}"
                logger.error("Failed to ingest approved resource %s: %s", ref, str(exc))
                errors.append({"source_reference": ref, "error": str(exc)})

        return {
            "ingested": ingested,
            "skipped": skipped,
            "updated": updated,
            "failed": failed,
            "errors": errors,
        }

    def ingest_market_skill_demand(self) -> Dict[str, Any]:
        """
        Scans market_skill_demand table and ingests canonical aggregate demand evidence.
        """
        demands = (
            self.session.query(MarketSkillDemand)
            .join(Skill, MarketSkillDemand.skill_id == Skill.id)
            .filter(
                MarketSkillDemand.skill_id.isnot(None),
                MarketSkillDemand.demand_score.isnot(None),
            )
            .all()
        )

        ingested = 0
        skipped = 0
        updated = 0
        failed = 0
        errors: List[Dict[str, str]] = []

        for d in demands:
            try:
                doc = build_market_demand_rag_document(demand=d, skill=d.skill)
                status = self.index_or_update_document(doc)
                if status == "ingested":
                    ingested += 1
                elif status == "skipped":
                    skipped += 1
                elif status == "updated":
                    updated += 1
            except Exception as exc:
                self.session.rollback()
                failed += 1
                ref = f"market_demand:{d.source}:{getattr(d.skill, 'slug', 'unknown')}"
                logger.error("Failed to ingest market demand %s: %s", ref, str(exc))
                errors.append({"source_reference": ref, "error": str(exc)})

        return {
            "ingested": ingested,
            "skipped": skipped,
            "updated": updated,
            "failed": failed,
            "errors": errors,
        }

    def ingest_market_job_skills(self) -> Dict[str, Any]:
        """
        Scans market_job_skills joined with market_jobs and skills,
        ingesting bounded, structured concrete job requirement evidence.
        """
        records = (
            self.session.query(MarketJobSkill)
            .join(MarketJob, MarketJobSkill.market_job_id == MarketJob.id)
            .join(Skill, MarketJobSkill.skill_id == Skill.id)
            .filter(
                MarketJobSkill.skill_id.isnot(None),
                MarketJob.id.isnot(None),
            )
            .all()
        )

        ingested = 0
        skipped = 0
        updated = 0
        failed = 0
        errors: List[Dict[str, str]] = []

        for mjs in records:
            try:
                doc = build_market_job_rag_document(
                    job=mjs.market_job,
                    job_skill=mjs,
                    skill=mjs.skill,
                )
                status = self.index_or_update_document(doc)
                if status == "ingested":
                    ingested += 1
                elif status == "skipped":
                    skipped += 1
                elif status == "updated":
                    updated += 1
            except Exception as exc:
                self.session.rollback()
                failed += 1
                ref = f"market_job:{mjs.market_job_id}:{mjs.skill_id}"
                logger.error("Failed to ingest market job skill %s: %s", ref, str(exc))
                errors.append({"source_reference": ref, "error": str(exc)})

        return {
            "ingested": ingested,
            "skipped": skipped,
            "updated": updated,
            "failed": failed,
            "errors": errors,
        }

    def ingest_approved_projects(self) -> Dict[str, Any]:
        """
        Scans approved_projects table and ingests ONLY authoritative curated seed projects.
        Strict cryptographic provenance check: rejects all polluted fixture rows and modified copies.
        """
        projects = (
            self.session.query(ApprovedProject)
            .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
            .all()
        )

        ingested = 0
        skipped = 0
        updated = 0
        failed = 0
        errors: List[Dict[str, str]] = []

        for p in projects:
            if not is_canonical_project(p, p.skill, p.role):
                continue

            try:
                doc = build_project_rag_document(project=p, skill=p.skill, role=p.role)
                status = self.index_or_update_document(doc)
                if status == "ingested":
                    ingested += 1
                elif status == "skipped":
                    skipped += 1
                elif status == "updated":
                    updated += 1
            except Exception as exc:
                self.session.rollback()
                failed += 1
                ref = f"approved_project:{p.id}"
                logger.error("Failed to ingest approved project %s: %s", ref, str(exc))
                errors.append({"source_reference": ref, "error": str(exc)})

        return {
            "ingested": ingested,
            "skipped": skipped,
            "updated": updated,
            "failed": failed,
            "errors": errors,
        }

    def ingest_all_approved_evidence(self, include_projects: bool = True) -> Dict[str, Any]:
        """
        Runs the approved evidence ingestion pipeline across:
        1. approved_resources
        2. market_skill_demand
        3. market_job_skills + market_jobs bounded evidence
        4. approved_projects (if include_projects=True)
        """
        res_summary = self.ingest_approved_resources()
        demand_summary = self.ingest_market_skill_demand()
        jobs_summary = self.ingest_market_job_skills()
        projects_summary = (
            self.ingest_approved_projects()
            if include_projects
            else {"ingested": 0, "skipped": 0, "updated": 0, "failed": 0, "errors": []}
        )

        total_ingested = (
            res_summary["ingested"]
            + demand_summary["ingested"]
            + jobs_summary["ingested"]
            + projects_summary["ingested"]
        )
        total_skipped = (
            res_summary["skipped"]
            + demand_summary["skipped"]
            + jobs_summary["skipped"]
            + projects_summary["skipped"]
        )
        total_updated = (
            res_summary["updated"]
            + demand_summary["updated"]
            + jobs_summary["updated"]
            + projects_summary["updated"]
        )
        total_failed = (
            res_summary["failed"]
            + demand_summary["failed"]
            + jobs_summary["failed"]
            + projects_summary["failed"]
        )
        all_errors = (
            res_summary["errors"]
            + demand_summary["errors"]
            + jobs_summary["errors"]
            + projects_summary["errors"]
        )

        breakdown = {
            "approved_resources": res_summary,
            "market_skill_demand": demand_summary,
            "market_job_skills": jobs_summary,
        }
        if include_projects:
            breakdown["approved_projects"] = projects_summary

        return {
            "ingested": total_ingested,
            "skipped": total_skipped,
            "updated": total_updated,
            "failed": total_failed,
            "errors": all_errors,
            "breakdown": breakdown,
        }
