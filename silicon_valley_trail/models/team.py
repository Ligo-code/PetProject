from dataclasses import dataclass
from enum import Enum


class TeamRole(Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    PRODUCT = "product"


@dataclass
class TeamMember:
    name: str
    role: TeamRole
    specialty: str
    morale: int = 100
    is_active: bool = True
    inactive_days_remaining: int = 0  # counts down if temporarily inactive

    # Role vulnerabilities:
    # BACKEND (Kay)    — protected: never targeted by poaching or burnout events
    # FRONTEND (Hanna) — poached by design studios and FAANG
    # PRODUCT (Leo)    — poached when hype > 70, burns out when morale < 25

    def __str__(self) -> str:
        status = "" if self.is_active else " (on leave)"
        return f"{self.name} [{self.role.value}]{status}"


DEFAULT_TEAM: list[TeamMember] = [
    TeamMember(
        name="Kay",
        role=TeamRole.BACKEND,
        specialty="Keeps the backend solid and bugs at bay. Core founder — never leaves.",
    ),
    TeamMember(
        name="Hanna",
        role=TeamRole.FRONTEND,
        specialty="Designs and builds the face of the product. Makes everything look effortless.",
    ),
    TeamMember(
        name="Leo",
        role=TeamRole.PRODUCT,
        specialty="Full-stack visionary. Drives decisions, takes risks, ships fast.",
    ),
]
