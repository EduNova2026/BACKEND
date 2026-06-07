from .assignments import router as assignments_router
from .promotions import router as promotions_router
from .groupes import router as groupes_router
from .etudiants import router as etudiants_router
from .roles import router as roles_router
from .notes import router as notes_router
from .utilisateurs import router as utilisateurs_router

__all__ = [
    "assignments_router",
    "promotions_router",
    "groupes_router",
    "etudiants_router",
    "roles_router",
    "notes_router",
    "utilisateurs_router",
]
