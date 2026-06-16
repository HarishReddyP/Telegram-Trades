"""Interactive helper to generate a Telethon StringSession.

Run once:  python -m app.services.telegram_session
Paste the printed string into TELEGRAM_SESSION in your .env.
"""
from app.core.config import settings


def main():
    try:
        from telethon.sync import TelegramClient
        from telethon.sessions import StringSession
    except ImportError:
        raise SystemExit("Install telethon first: pip install telethon")

    if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
        raise SystemExit("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env first.")

    with TelegramClient(StringSession(), settings.TELEGRAM_API_ID,
                        settings.TELEGRAM_API_HASH) as client:
        print("\n=== Your Telegram session string (keep it secret) ===\n")
        print(client.session.save())
        print("\nPaste it into TELEGRAM_SESSION in backend/.env\n")


if __name__ == "__main__":
    main()
