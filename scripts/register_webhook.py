"""
Quick utility to manually register / check / delete the Telegram webhook.

Usage:
    python scripts/register_webhook.py           ← auto-detect ngrok and register
    python scripts/register_webhook.py info      ← show current webhook info
    python scripts/register_webhook.py delete    ← remove webhook
    python scripts/register_webhook.py <url>     ← register a specific URL
"""
import sys
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BASE  = f"https://api.telegram.org/bot{TOKEN}"


def get_ngrok_url() -> str | None:
    try:
        resp = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        for tunnel in resp.json().get("tunnels", []):
            url = tunnel.get("public_url", "")
            if url.startswith("https://"):
                return url
    except Exception as e:
        print(f"  Could not reach ngrok API: {e}")
    return None


def register(webhook_url: str):
    full_url = f"{webhook_url}/webhook/telegram"
    print(f"  Registering: {full_url}")
    resp = requests.post(f"{BASE}/setWebhook", json={
        "url": full_url,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": True,
    })
    result = resp.json()
    if result.get("ok"):
        print("  ✅ Webhook registered successfully!")
    else:
        print(f"  ❌ Failed: {result}")


def info():
    resp = requests.get(f"{BASE}/getWebhookInfo")
    info = resp.json().get("result", {})
    print("\n  📋 Current webhook info:")
    print(f"  URL        : {info.get('url', 'not set')}")
    print(f"  Pending    : {info.get('pending_update_count', 0)} updates")
    print(f"  Last error : {info.get('last_error_message', 'none')}")


def delete():
    resp = requests.post(f"{BASE}/deleteWebhook")
    result = resp.json()
    if result.get("ok"):
        print("  ✅ Webhook deleted.")
    else:
        print(f"  ❌ Failed: {result}")


if __name__ == "__main__":
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        sys.exit(1)

    arg = sys.argv[1] if len(sys.argv) > 1 else ""

    if arg == "info":
        info()
    elif arg == "delete":
        delete()
    elif arg.startswith("https://"):
        register(arg)
    else:
        print("🔍 Looking for ngrok tunnel...")
        url = get_ngrok_url()
        if url:
            print(f"🌐 Found: {url}")
            register(url)
            print()
            info()
        else:
            print("⚠️  ngrok not running or no HTTPS tunnel found.")
            print("   Start ngrok first:  ngrok http 8000")
