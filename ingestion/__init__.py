"""ATS ingestion: fetch public job boards and normalize into one schema."""

from .runner import ingest_companies
from .schema import JobPosting

__all__ = ["JobPosting", "ingest_companies"]
