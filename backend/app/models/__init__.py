"""SQLAlchemy models. Importing this package registers all tables on Base.metadata."""
from app.models.user import User, Role, AuditLog  # noqa: F401
from app.models.source import LogSource  # noqa: F401
from app.models.ingestion import ProcessingJob, RawLog  # noqa: F401
from app.models.event import NormalizedEvent  # noqa: F401
from app.models.security import SecurityAlert, SecurityRule, SecurityEvent  # noqa: F401
from app.models.parser import ParserPack, ParserVersion  # noqa: F401
from app.models.pipeline import PipelineRun  # noqa: F401
from app.models.privacy import PiiSetting  # noqa: F401
from app.models.template import Template, CompressionRecord  # noqa: F401

__all__ = [
    "User",
    "Role",
    "AuditLog",
    "LogSource",
    "ProcessingJob",
    "RawLog",
    "NormalizedEvent",
    "SecurityAlert",
    "SecurityRule",
    "SecurityEvent",
    "ParserPack",
    "ParserVersion",
    "PipelineRun",
    "PiiSetting",
    "Template",
    "CompressionRecord",
]
