
import asyncio
import logging
from typing import Optional, Tuple, List, Union, Dict, Any

import aiosqlite
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import DB_NAME

log = logging.getLogger(__name__)

def _markup_from_layout(layout: Optional[list]) -> Optional[InlineKeyboardMarkup]:
    if not layout:
        return None
    rows = []
    for row in layout:
        btns = []
        for btn in row:
            text = str(btn.get("text", ""))[:64]
            url = str(btn.get("url", ""))
            if not (text and url and (url.startswith("http://") or url.startswith("https://"))):
                continue
            btns.append(InlineKeyboardButton(text=text, url=url))
        if btns:
            rows.append(btns)
    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def get_audience_user_ids(audience: str) -> List[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        if audience == "buyers":
            query = "SELECT DISTINCT user_id FROM orders WHERE status IN ('completed','success','paid')"
        else:
            query = "SELECT user_id FROM users"
        async with db.execute(query) as cur:
            rows = await cur.fetchall()
            return [int(r[0]) for r in rows]

async def send_broadcast(
    bot: Bot,
    audience: str,
    text: str,
    parse_mode: Optional[str],
    keyboard_layout_or_payload: Optional[Union[list, Dict[str, Any]]],
    progress_cb=None,
    batch: int = 35,
    pause_ms: int = 80,
) -> Tuple[int, int, int]:
    log.info(f"send_broadcast started: audience={audience}, batch={batch}, pause_ms={pause_ms}")
    layout = None
    media = None
    if isinstance(keyboard_layout_or_payload, list):
        layout = keyboard_layout_or_payload
    elif isinstance(keyboard_layout_or_payload, dict):
        layout = keyboard_layout_or_payload.get("buttons")
        media = keyboard_layout_or_payload.get("media")
    markup = _markup_from_layout(layout)

    log.info("Getting audience user IDs...")
    user_ids = await get_audience_user_ids(audience)
    total = len(user_ids)
    log.info(f"Found {total} users to send to")
    ok = 0
    failed = 0

    for i in range(0, total, batch):
        chunk = user_ids[i:i+batch]
        tasks = []
        for uid in chunk:
            tasks.append(_send_one(bot, uid, text, parse_mode, markup, media))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                failed += 1
            elif res is True:
                ok += 1
            else:
                failed += 1
        
        # Логируем каждые 10 батчей
        batch_num = i // batch + 1
        if batch_num % 10 == 0 or i + batch >= total:
            log.info(f"Batch {batch_num}: sent {i + len(chunk)}/{total}, ok={ok}, failed={failed}")
        
        if progress_cb:
            try:
                await progress_cb(i + len(chunk), total, ok, failed)
            except Exception:
                pass
        await asyncio.sleep(pause_ms / 1000.0)
    
    log.info(f"send_broadcast completed: total={total}, ok={ok}, failed={failed}")
    return total, ok, failed

async def _send_one(bot: Bot, uid: int, text: str, parse_mode: Optional[str], markup: Optional[InlineKeyboardMarkup], media: Optional[dict]) -> bool:
    try:
        if media and media.get("type") == "photo" and media.get("file_id"):
            caption = (media.get("caption") or text or "")[:1024]
            pm = (media.get("parse_mode") or parse_mode or "HTML")
            await bot.send_photo(chat_id=uid, photo=media["file_id"], caption=caption, parse_mode=pm, reply_markup=markup)
        else:
            await bot.send_message(chat_id=uid, text=text, parse_mode=parse_mode or "HTML", reply_markup=markup, disable_web_page_preview=True)
        return True
    except TelegramRetryAfter as e:
        await asyncio.sleep(float(e.retry_after))
        try:
            if media and media.get("type") == "photo" and media.get("file_id"):
                caption = (media.get("caption") or text or "")[:1024]
                pm = (media.get("parse_mode") or parse_mode or "HTML")
                await bot.send_photo(chat_id=uid, photo=media["file_id"], caption=caption, parse_mode=pm, reply_markup=markup)
            else:
                await bot.send_message(chat_id=uid, text=text, parse_mode=parse_mode or "HTML", reply_markup=markup, disable_web_page_preview=True)
            return True
        except Exception:
            return False
    except (TelegramForbiddenError, TelegramBadRequest):
        return False
    except Exception as e:
        log.debug("send_one error for %s: %s", uid, e)
        return False
