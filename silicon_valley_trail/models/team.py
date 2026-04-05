from dataclasses import dataclass
from enum import Enum


class TeamRole(str, Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    PRODUCT = "product"


BURNOUT_LEAVE_DAYS = 2              # days a member is on leave after burnout
PERMANENT_LEAVE = -1                # sentinel: member was poached and will never return

PRODUCT_POACH_HYPE_THRESHOLD    = 70  # Leo gets poached above this hype level
FRONTEND_BURNOUT_THRESHOLD      = 10  # Hanna burns out at or below this morale
PRODUCT_BURNOUT_THRESHOLD       = 25  # Leo burns out at or below this morale
FRONTEND_BURNOUT_RISK_THRESHOLD = 20  # Hanna is at risk at or below this morale
PRODUCT_BURNOUT_RISK_THRESHOLD  = 30  # Leo is at risk at or below this morale


@dataclass
class TeamMember:
    name: str
    role: TeamRole
    specialty: str
    morale: int = 100
    is_active: bool = True
    inactive_days_remaining: int = 0

    # Role vulnerabilities:
    # BACKEND (Kay)    — protected: never targeted by poaching or burnout events
    # FRONTEND (Hanna) — poached by design studios and FAANG
    # PRODUCT (Leo)    — poached when hype > 70, burns out when morale < 25

    def can_be_poached(self, hype: int) -> bool:
        if self.role == TeamRole.BACKEND:
            return False
        if self.role == TeamRole.FRONTEND:
            return True
        if self.role == TeamRole.PRODUCT:
            return hype > PRODUCT_POACH_HYPE_THRESHOLD
        return False

    def should_burnout(self) -> bool:
        if self.role == TeamRole.BACKEND:
            return False
        if self.role == TeamRole.PRODUCT:
            return self.morale <= PRODUCT_BURNOUT_THRESHOLD
        return self.morale <= FRONTEND_BURNOUT_THRESHOLD

    def reduce_morale(self, amount: int) -> None:
        self.morale = max(0, self.morale - amount)
        if self.should_burnout() and self.is_active:
            self.is_active = False
            self.inactive_days_remaining = BURNOUT_LEAVE_DAYS

    def restore_morale(self, amount: int) -> None:
        self.morale = min(100, self.morale + amount)
        if self.morale > 0 and self.inactive_days_remaining == 0:
            self.is_active = True

    def is_burnout_risk(self) -> bool:
        if self.role == TeamRole.PRODUCT:
            return self.morale <= PRODUCT_BURNOUT_RISK_THRESHOLD
        if self.role == TeamRole.BACKEND:
            return False
        return self.morale <= FRONTEND_BURNOUT_RISK_THRESHOLD

    @property
    def has_left_permanently(self) -> bool:
        """True if this member was poached and will never return."""
        return not self.is_active and self.inactive_days_remaining == PERMANENT_LEAVE

    def apply_inactive_day(self) -> None:
        if self.has_left_permanently:
            return
        if self.inactive_days_remaining > 0:
            self.inactive_days_remaining -= 1
            if self.inactive_days_remaining == 0 and self.morale > 0:
                self.is_active = True

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
