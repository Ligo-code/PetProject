from dataclasses import dataclass, field


@dataclass
class Location:
    name: str
    description: str
    lat: float
    lon: float
    event_pool: list[str] = field(default_factory=list)


LOCATIONS: list[Location] = [
    Location(
        name="San Jose",
        description="Your startup's humble garage HQ",
        lat=37.3382, lon=-121.8863,
        event_pool=["vc_pitch", "coffee_shortage", "recruiter_dm"],
    ),
    Location(
        name="Santa Clara",
        description="Home of tech giants",
        lat=37.3541, lon=-121.9552,
        event_pool=["vc_pitch", "server_bill", "hackathon", "recruiter_dm", "team_conflict"],
    ),
    Location(
        name="Sunnyvale",
        description="Where ideas become products",
        lat=37.3688, lon=-122.0363,
        event_pool=["press_coverage", "tech_debt_crisis", "coffee_shortage", "team_conflict"],
    ),
    Location(
        name="Mountain View",
        description="Googleplex territory — recruiters everywhere",
        lat=37.3861, lon=-122.0839,
        event_pool=["recruiter_dm", "key_dev_poached", "hackathon", "angel_investor", "team_conflict"],
    ),
    Location(
        name="Palo Alto",
        description="Stanford and Sand Hill Road VC row",
        lat=37.4419, lon=-122.1430,
        event_pool=["vc_pitch", "angel_investor", "idea_leaked", "press_coverage"],
    ),
    Location(
        name="Menlo Park",
        description="Where big tech grows bigger",
        lat=37.4529, lon=-122.1817,
        event_pool=["server_bill", "idea_leaked", "recruiter_dm", "key_dev_poached"],
    ),
    Location(
        name="Redwood City",
        description="The halfway point hustle",
        lat=37.4852, lon=-122.2364,
        event_pool=["coffee_shortage", "tech_debt_crisis", "press_coverage"],
    ),
    Location(
        name="San Mateo",
        description="Bridge city between two worlds",
        lat=37.5630, lon=-122.3255,
        event_pool=["angel_investor", "server_bill", "hackathon"],
    ),
    Location(
        name="Burlingame",
        description="Airport energy, always moving",
        lat=37.5841, lon=-122.3661,
        event_pool=["aircraft_supply_drop", "recruiter_dm", "press_coverage"],
    ),
    Location(
        name="South San Francisco",
        description="Biotech and startup corridor",
        lat=37.6547, lon=-122.4077,
        event_pool=["vc_pitch", "idea_leaked", "coffee_shortage"],
    ),
    Location(
        name="Daly City",
        description="The final stretch — SF is right there",
        lat=37.6879, lon=-122.4702,
        event_pool=["burnout_warning", "tech_debt_crisis", "angel_investor"],
    ),
    Location(
        name="San Francisco",
        description="The dream. Series A awaits.",
        lat=37.7749, lon=-122.4194,
        event_pool=[],  # final destination — no random events
    ),
]
