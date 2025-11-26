import json
import logging
import os
import time
from typing import Dict, List, Any, Set

import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
PENDLE_CHAIN_ID = int(os.getenv("PENDLE_CHAIN_ID", "1"))
STATE_FILE = os.getenv("STATE_FILE", "known_markets.json")

PENDLE_API_BASE = "https://api-v2.pendle.finance/core"
ACTIVE_MARKETS_PATH = "/v1/markets/active"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def send_telegram_message(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def fetch_active_markets(chain_id: int):
    url = f"{PENDLE_API_BASE}{ACTIVE_MARKETS_PATH}"
    params = {"chainId": chain_id}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    if isinstance(data, list):
        return data
    return []

def extract_market_id_and_name(m):
    mid = m.get("marketAddress") or m.get("address") or m.get("id") or m.get("lpAddress") or str(m)
    name = m.get("name") or m.get("symbol") or m.get("underlyingName") or m.get("underlyingSymbol") or "Unknown"
    return mid, name

def load_known_market_ids():
    if not os.path.exists(STATE_FILE):
        return set()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            arr = json.load(f)
            return set(arr) if isinstance(arr, list) else set()
    except:
        return set()

def save_known_market_ids(s):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(s)), f, indent=2, ensure_ascii=False)

def main():
    known = load_known_market_ids()
    first = len(known) == 0
    if first:
        mk = fetch_active_markets(PENDLE_CHAIN_ID)
        for m in mk:
            mid, _ = extract_market_id_and_name(m)
            known.add(mid)
        save_known_market_ids(known)

    while True:
        try:
            mk = fetch_active_markets(PENDLE_CHAIN_ID)
            new = []
            for m in mk:
                mid, name = extract_market_id_and_name(m)
                if mid not in known:
                    new.append(m)
                    known.add(mid)
            if new:
                txt = "<b>Новый проект на Pendle Finance!</b>\n\n"
                for m in new:
                    mid, name = extract_market_id_and_name(m)
                    txt += f"• <b>{name}</b>\nID: <code>{mid}</code>\n\n"
                send_telegram_message(txt)
                save_known_market_ids(known)
        except Exception as e:
            pass
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
