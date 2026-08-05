class IngestionError(Exception):
    """Company-level fetch/normalize failure. Catchable so one bad board
    does not abort the rest of the run."""
