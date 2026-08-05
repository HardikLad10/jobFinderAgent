from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class JobPosting:
    """Normalized job shape shared across ATS sources."""

    title: str
    company: str
    location: str
    posted_date: str
    url: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
