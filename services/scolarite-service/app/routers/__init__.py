from .promotions import router as promotions_router
from .groupes import router as groupes_router
from .etudiants import router as etudiants_router
from .roles import router as roles_router

__all__ = ["promotions_router", "groupes_router", "etudiants_router", "roles_router"]
