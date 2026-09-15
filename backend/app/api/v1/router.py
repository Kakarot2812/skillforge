from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.skills import router as skills_router
from app.api.v1.github import router as github_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.roles import router as roles_router
from app.api.v1.demand import router as demand_router
from app.api.v1.demand_intelligence import router as intelligence_router
from app.api.v1.gaps import router as gaps_router
from app.api.v1.ai import router as ai_router
from app.api.v1.roadmap import router as roadmap_router
from app.api.v1.roadmaps import router as roadmaps_router, user_progress_router
from app.api.v1.users import router as users_router
from app.api.v1.profile import router as profile_router
from app.api.v1.conversations import router as conversations_router

api_router = APIRouter()

# Mount health routes under /api/v1 as well as root
api_router.include_router(health_router)

# Mount user identity routes under /api/v1/users
api_router.include_router(users_router)

# Mount resume intelligence routes under /api/v1/resumes
api_router.include_router(resumes_router)

# Mount skills intelligence routes under /api/v1/skills
api_router.include_router(skills_router)

# Mount GitHub intelligence routes under /api/v1/github
api_router.include_router(github_router)

# Mount Project Evidence routes under /api/v1/evidence
api_router.include_router(evidence_router)

# Mount canonical Job Roles routes under /api/v1/roles
api_router.include_router(roles_router, prefix="/roles")

# Mount Industry Skill Demand routes under /api/v1/demand
api_router.include_router(demand_router, prefix="/demand")

# Mount Demand Intelligence routes under /api/v1/intelligence
api_router.include_router(intelligence_router, prefix="/intelligence")

# Mount Skill Gap Foundation routes under /api/v1/gaps
api_router.include_router(gaps_router, prefix="/gaps")

# Mount Evidence-Grounded AI Career Intelligence routes under /api/v1/ai
api_router.include_router(ai_router, prefix="/ai")

# Mount Personalized Career Roadmap routes under /api/v1/roadmap
api_router.include_router(roadmap_router, prefix="/roadmap")

# Mount Candidate User Profile routes under /api/v1/profile
api_router.include_router(profile_router)

# Mount Persistent AI Chat History routes under /api/v1/conversations
api_router.include_router(conversations_router, prefix="/conversations")

# Mount Static Skill Roadmaps routes under /api/v1/roadmaps
api_router.include_router(roadmaps_router, prefix="/roadmaps")

# Mount Static User Roadmap Progress routes under /api/v1/users/me/roadmap-progress
api_router.include_router(user_progress_router)



