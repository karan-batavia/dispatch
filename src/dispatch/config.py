import logging
import os
import base64
from urllib import parse
from typing import List

from starlette.config import Config
from starlette.datastructures import CommaSeparatedStrings

log = logging.getLogger(__name__)


def get_env_tags(tag_list: List[str]) -> dict:
    """Create dictionary of available env tags."""
    tags = {}
    for t in tag_list:
        tag_key, env_key = t.split(":")

        env_value = os.environ.get(env_key)

        if env_value:
            tags.update({tag_key: env_value})

    return tags


config = Config(".env")

SECRET_PROVIDER = config("SECRET_PROVIDER", default=None)
if SECRET_PROVIDER == "metatron-secret":
    import metatron.decrypt

    class Secret:
        """
        Holds a string value that should not be revealed in tracebacks etc.
        You should cast the value to `str` at the point it is required.
        """

        def __init__(self, value: str):
            self._value = value
            self._decrypted_value = (
                metatron.decrypt.MetatronDecryptor()
                .decryptBytes(base64.b64decode(self._value))
                .decode("utf-8")
            )

        def __repr__(self) -> str:
            class_name = self.__class__.__name__
            return f"{class_name}('**********')"

        def __str__(self) -> str:
            return self._decrypted_value


elif SECRET_PROVIDER == "kms-secret":
    import boto3

    class Secret:
        """
        Holds a string value that should not be revealed in tracebacks etc.
        You should cast the value to `str` at the point it is required.
        """

        def __init__(self, value: str):
            self._value = value
            self._decrypted_value = (
                boto3.client("kms")
                .decrypt(CiphertextBlob=base64.b64decode(value))["Plaintext"]
                .decode("utf-8")
            )

        def __repr__(self) -> str:
            class_name = self.__class__.__name__
            return f"{class_name}('**********')"

        def __str__(self) -> str:
            return self._decrypted_value


else:
    from starlette.datastructures import Secret


LOG_LEVEL = config("LOG_LEVEL", default=logging.WARNING)
ENV = config("ENV", default="local")

ENV_TAG_LIST = config("ENV_TAGS", cast=CommaSeparatedStrings, default="")
ENV_TAGS = get_env_tags(ENV_TAG_LIST)

DISPATCH_UI_URL = config("DISPATCH_UI_URL", default="http://localhost:8000 ")
DISPATCH_HELP_EMAIL = config("DISPATCH_HELP_EMAIL", default="help@example.com")

# authentication
DISPATCH_AUTHENTICATION_PROVIDER_SLUG = config(
    "DISPATCH_AUTHENTICATION_PROVIDER_SLUG", default="dispatch-auth-provider-basic"
)

MJML_PATH = config(
    "MJML_PATH",
    default=f"{os.path.dirname(os.path.realpath(__file__))}/static/dispatch/node_modules/.bin",
)

DISPATCH_JWT_AUDIENCE = config("DISPATCH_JWT_AUDIENCE", default=None)
DISPATCH_JWT_EMAIL_OVERRIDE = config("DISPATCH_JWT_EMAIL_OVERRIDE", default=None)

if DISPATCH_AUTHENTICATION_PROVIDER_SLUG == "dispatch-auth-provider-pkce":
    if not DISPATCH_JWT_AUDIENCE:
        log.warn("No JWT Audience specified. This is required for IdPs like Okta")
    if not DISPATCH_JWT_EMAIL_OVERRIDE:
        log.warn("No JWT Email Override specified. 'email' is expected in the idtoken.")

DISPATCH_JWT_SECRET = config("DISPATCH_JWT_SECRET", default=None)
DISPATCH_JWT_ALG = config("DISPATCH_JWT_ALG", default="HS256")
DISPATCH_JWT_EXP = config("DISPATCH_JWT_EXP", cast=int, default=86400)  # Seconds

if DISPATCH_AUTHENTICATION_PROVIDER_SLUG == "dispatch-auth-provider-basic":
    if not DISPATCH_JWT_SECRET:
        log.warn("No JWT secret specified, this is required if you are using basic authentication.")

DISPATCH_AUTHENTICATION_DEFAULT_USER = config(
    "DISPATCH_AUTHENTICATION_DEFAULT_USER", default="dispatch@example.com"
)

DISPATCH_AUTHENTICATION_PROVIDER_PKCE_JWKS = config(
    "DISPATCH_AUTHENTICATION_PROVIDER_PKCE_JWKS", default=None
)

DISPATCH_PKCE_DONT_VERIFY_AT_HASH = config("DISPATCH_PKCE_DONT_VERIFY_AT_HASH", default=False)

if DISPATCH_AUTHENTICATION_PROVIDER_SLUG == "dispatch-auth-provider-pkce":
    if not DISPATCH_AUTHENTICATION_PROVIDER_PKCE_JWKS:
        log.warn(
            "No PKCE JWKS url provided, this is required if you are using PKCE authentication."
        )

# sentry middleware
SENTRY_DSN = config("SENTRY_DSN", default="")

VUE_APP_DISPATCH_AUTHENTICATION_PROVIDER_SLUG = DISPATCH_AUTHENTICATION_PROVIDER_SLUG
VUE_APP_SENTRY_ENABLED = config("VUE_APP_SENTRY_ENABLED", default="")
VUE_APP_SENTRY_DSN = SENTRY_DSN
VUE_APP_SENTRY_APP_KEY = config("VUE_APP_SENTRY_APP_KEY", default="")

VUE_APP_DISPATCH_AUTHENTICATION_PROVIDER_PKCE_OPEN_ID_CONNECT_URL = config(
    "VUE_APP_DISPATCH_AUTHENTICATION_PROVIDER_PKCE_OPEN_ID_CONNECT_URL", default=""
)
VUE_APP_DISPATCH_AUTHENTICATION_PROVIDER_PKCE_CLIENT_ID = config(
    "VUE_APP_DISPATCH_AUTHENTICATION_PROVIDER_PKCE_CLIENT_ID", default=""
)
VUE_APP_DISPATCH_AUTHENTICATION_PROVIDER_USE_ID_TOKEN = config(
    "VUE_APP_DISPATCH_AUTHENTICATION_PROVIDER_USE_ID_TOKEN", default=""
)

# static files
DEFAULT_STATIC_DIR = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), os.path.join("static", "dispatch", "dist")
)
STATIC_DIR = config("STATIC_DIR", default=DEFAULT_STATIC_DIR)

# metrics
METRIC_PROVIDERS = config("METRIC_PROVIDERS", cast=CommaSeparatedStrings, default="")

# database
DATABASE_HOSTNAME = config("DATABASE_HOSTNAME")
DATABASE_CREDENTIALS = config("DATABASE_CREDENTIALS", cast=Secret)
# this will support special chars for credentials
_DATABASE_CREDENTIAL_USER, _DATABASE_CREDENTIAL_PASSWORD = str(DATABASE_CREDENTIALS).split(":")
_QUOTED_DATABASE_PASSWORD = parse.quote(str(_DATABASE_CREDENTIAL_PASSWORD))
DATABASE_NAME = config("DATABASE_NAME", default="dispatch")
DATABASE_PORT = config("DATABASE_PORT", default="5432")
SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{_DATABASE_CREDENTIAL_USER}:{_QUOTED_DATABASE_PASSWORD}@{DATABASE_HOSTNAME}:{DATABASE_PORT}/{DATABASE_NAME}"

ALEMBIC_CORE_REVISION_PATH = config(
    "ALEMBIC_CORE_REVISION_PATH",
    default=f"{os.path.dirname(os.path.realpath(__file__))}/database/revisions/core",
)
ALEMBIC_TENANT_REVISION_PATH = config(
    "ALEMBIC_TENANT_REVISION_PATH",
    default=f"{os.path.dirname(os.path.realpath(__file__))}/database/revisions/tenant",
)
ALEMBIC_INI_PATH = config(
    "ALEMBIC_INI_PATH",
    default=f"{os.path.dirname(os.path.realpath(__file__))}/alembic.ini",
)
ALEMBIC_MULTI_TENANT_MIGRATION_PATH = config(
    "ALEMBIC_MULTI_TENANT_MIGRATION_PATH",
    default=f"{os.path.dirname(os.path.realpath(__file__))}/database/revisions/multi-tenant-migration.sql",
)

# incident resources
INCIDENT_STORAGE_FOLDER_ID = config("INCIDENT_STORAGE_FOLDER_ID", default=None)

INCIDENT_STORAGE_OPEN_ON_CLOSE = config("INCIDENT_STORAGE_OPEN_ON_CLOSE", default=True)

INCIDENT_RESPONSE_TEAM_EMAIL = config("INCIDENT_RESPONSE_TEAM_EMAIL", default="")

INCIDENT_ONCALL_SERVICE_ID = config("INCIDENT_ONCALL_SERVICE_ID", default=None)
if not INCIDENT_ONCALL_SERVICE_ID:
    INCIDENT_DAILY_SUMMARY_ONCALL_SERVICE_ID = config(
        "INCIDENT_DAILY_SUMMARY_ONCALL_SERVICE_ID", default=None
    )
    if INCIDENT_DAILY_SUMMARY_ONCALL_SERVICE_ID:
        log.warn(
            "INCIDENT_DAILY_SUMMARY_ONCALL_SERVICE_ID has been deprecated. Please use INCIDENT_ONCALL_SERVICE_ID instead."
        )
        INCIDENT_ONCALL_SERVICE_ID = INCIDENT_DAILY_SUMMARY_ONCALL_SERVICE_ID

INCIDENT_RESOURCE_TACTICAL_GROUP = config(
    "INCIDENT_RESOURCE_TACTICAL_GROUP", default="google-group-participant-tactical-group"
)
INCIDENT_RESOURCE_NOTIFICATIONS_GROUP = config(
    "INCIDENT_RESOURCE_NOTIFICATIONS_GROUP", default="google-group-participant-notifications-group"
)
INCIDENT_RESOURCE_INCIDENT_TASK = config(
    "INCIDENT_RESOURCE_INCIDENT_TASK", default="google-docs-incident-task"
)

# Incident Cost Configuration
ANNUAL_COST_EMPLOYEE = config("ANNUAL_COST_EMPLOYEE", cast=int, default="650000")
BUSINESS_HOURS_YEAR = config("BUSINESS_HOURS_YEAR", cast=int, default="2080")
