from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    DATABASE_URL: str = "postgresql+psycopg://trader:traderpass@db:5432/trades"
    REDIS_URL: str = "redis://redis:6379/0"
    JWT_SECRET: str = "change-me"
    JWT_EXPIRE_MINUTES: int = 1440

    # Safety gates
    TRADING_MODE: str = "paper"          # paper | live
    MANUAL_APPROVAL: bool = True
    LIVE_TRADING_ENABLED: bool = False
    KILL_SWITCH: bool = False

    # Account / default risk
    STARTING_CAPITAL: float = 25000
    MAX_RISK_PER_TRADE: float = 500
    MAX_CONTRACTS_PER_TRADE: int = 5
    MAX_DAILY_LOSS: float = 1000
    MAX_OPEN_TRADES: int = 5
    ALLOWED_TICKERS: str = "SPX,SPY,QQQ,IWM"
    ALLOWED_STRATEGIES: str = (
        "BULL_PUT_SPREAD,BEAR_CALL_SPREAD,IRON_CONDOR,IRON_FLY,BUTTERFLY,SINGLE_LEG"
    )
    NO_TRADE_NEAR_CLOSE: bool = True
    NO_TRADE_MINUTES_BEFORE_CLOSE: int = 15
    COMMISSION_PER_CONTRACT: float = 0.65

    # Telegram
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_SESSION: str = ""
    TELEGRAM_CHANNEL: str = ""

    # Anthropic (Claude Vision for image-based alerts)
    ANTHROPIC_API_KEY: str = ""

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "alerts@example.com"
    REPORT_RECIPIENT: str = ""

    # Market session
    MARKET_TZ: str = "America/New_York"
    MARKET_CLOSE: str = "16:00"

    # Live quotes (Tradier market data)
    QUOTE_PROVIDER: str = "none"          # none | tradier
    TRADIER_TOKEN: str = ""
    TRADIER_BASE_URL: str = "https://sandbox.tradier.com"
    FILL_PRICE_MODE: str = "mid"          # mid | conservative

    @property
    def allowed_tickers(self) -> List[str]:
        return [t.strip().upper() for t in self.ALLOWED_TICKERS.split(",") if t.strip()]

    @property
    def allowed_strategies(self) -> List[str]:
        return [s.strip().upper() for s in self.ALLOWED_STRATEGIES.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
