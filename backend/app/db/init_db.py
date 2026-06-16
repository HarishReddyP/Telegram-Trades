"""Create tables and seed a default user + risk rule from settings.

Run:  python -m app.db.init_db
"""
from app.db.session import Base, engine, SessionLocal
from app.core.config import settings
from app.core.security import hash_password
from app.models.models import User, RiskRule, SettingKV  # noqa: F401  (register models)
import app.models.models  # noqa: F401


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).first():
            db.add(User(
                email="trader@example.com",
                hashed_password=hash_password("changeme"),
                role="admin",
            ))
        if not db.query(RiskRule).first():
            db.add(RiskRule(
                starting_capital=settings.STARTING_CAPITAL,
                max_risk_per_trade=settings.MAX_RISK_PER_TRADE,
                max_contracts_per_trade=settings.MAX_CONTRACTS_PER_TRADE,
                max_daily_loss=settings.MAX_DAILY_LOSS,
                max_open_trades=settings.MAX_OPEN_TRADES,
                allowed_tickers=settings.allowed_tickers,
                allowed_strategies=settings.allowed_strategies,
                no_trade_near_close=settings.NO_TRADE_NEAR_CLOSE,
                no_trade_minutes_before_close=settings.NO_TRADE_MINUTES_BEFORE_CLOSE,
                commission_per_contract=settings.COMMISSION_PER_CONTRACT,
            ))
        db.commit()
        print("DB initialized. Default login: trader@example.com / changeme")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
