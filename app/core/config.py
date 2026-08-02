from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central config, loaded from environment variables / .env.
    Equivalent to Laravel's config/*.php + .env combined.
    """

    APP_NAME: str = "Slipper Shop API"
    APP_DEBUG: bool = True

    DATABASE_URL: str = "mysql://root:@127.0.0.1:3306/laravel"

    TOKEN_SECRET: str = "change-this-to-a-long-random-string"
    TOKEN_EXPIRE_MINUTES: int = 0  # 0 = never expires

    GHASEDAK_API_KEY: str = ""
    SMS_IR_API_KEY: str = ""
    ZIBAL_MERCHANT: str = "zibal"  # "zibal" is Zibal's official test merchant id - swap for the real one in production
    PAYMENT_CALLBACK_URL: str = "http://localhost:3000/payment/verify"

    ANTHROPIC_API_KEY: str = ""
    AI_ASSISTANT_MODEL: str = "claude-sonnet-5"
    AI_ASSISTANT_MAX_TOKENS: int = 1024

    # AI_PROVIDER picks which one app/services/ai_assistant.py actually calls:
    # "anthropic" (direct Claude API) or "gapgpt" (api.gapgpt.app, an
    # OpenAI-compatible proxy - useful where direct access to the big
    # providers' APIs is unreliable). Only ANTHROPIC_API_KEY or only
    # GAPGPT_API_KEY needs to be set, matching whichever provider is active.
    AI_PROVIDER: str = "anthropic"
    GAPGPT_API_KEY: str = ""
    GAPGPT_MODEL: str = "gpt-4o-mini"

    CORS_ORIGINS: str = "https://slipperpaz.ir"

    # Absolute path where uploaded images/files are written. Leave empty to
    # default to <project_root>/storage (fine for local dev). In production
    # this MUST match the mount path of the persistent volume attached to
    # the service (currently mounted at /storage on Runflare), otherwise
    # uploads land in the container's ephemeral filesystem and vanish on
    # every redeploy.
    STORAGE_ROOT: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        # SQLAlchemy needs the mysqlclient dialect prefix
        url = self.DATABASE_URL
        if url.startswith("mysql://"):
            url = url.replace("mysql://", "mysql+mysqldb://", 1)
        return url


settings = Settings()