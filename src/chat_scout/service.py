import asyncio
from datetime import datetime

import keyring
from telethon import TelegramClient, events, errors
from telethon.sessions import StringSession
from telethon.utils import get_peer_id

from .rules import message_link

SERVICE = "ChatScout"


class TelegramService:
    def __init__(self):
        self.client = None
        self.phone = ""
        self.phone_hash = None
        self.handler = None

    async def connect(self, api_id, api_hash):
        await self.disconnect()
        saved = keyring.get_password(SERVICE, "session") or ""
        self.client = TelegramClient(StringSession(saved), api_id, api_hash,
                                     flood_sleep_threshold=0, request_retries=1)
        await self.client.connect()
        return await self.client.is_user_authorized()

    async def request_code(self, phone):
        self.phone = phone
        sent = await self.client.send_code_request(phone)
        self.phone_hash = sent.phone_code_hash

    async def sign_in(self, code=None, password=None):
        if password is not None:
            await self.client.sign_in(password=password)
        else:
            await self.client.sign_in(self.phone, code, phone_code_hash=self.phone_hash)
        keyring.set_password(SERVICE, "session", self.client.session.save())

    async def dialogs(self):
        return [(d.id, d.name, d.entity) async for d in self.client.iter_dialogs()
                if d.is_group or d.is_channel]

    @staticmethod
    def result(message, chat_id, title, entity):
        return dict(chat_id=chat_id, message_id=message.id, title=title,
                    date=message.date.isoformat(), text=message.raw_text or "",
                    link=message_link(chat_id, message.id, getattr(entity, "username", None)))

    async def search(self, chats, rule, since: datetime, until: datetime, limit, callback, progress):
        # Bounded history scan: unlike server search, local substring rules have
        # deterministic OR/AND semantics and normalize Russian ё/е.
        scanned = 0
        for chat_id, title, entity in chats:
            count = 0
            async for message in self.client.iter_messages(entity, limit=limit, offset_date=until):
                if message.date < since:
                    break
                count += 1
                scanned += 1
                if rule.matches(message.raw_text or ""):
                    callback(self.result(message, chat_id, title, entity), False)
                if count % 50 == 0:
                    progress(f"{title}: проверено {count}; всего {scanned}")
                    await asyncio.sleep(0)
            progress(f"{title}: проверено {count} (предел {limit})")
        return scanned

    def monitor(self, chats, rule, callback):
        self.stop_monitor()
        mapping = {c[0]: c for c in chats}

        async def handler(event):
            chat = mapping.get(event.chat_id)
            if chat and rule.matches(event.raw_text or ""):
                callback(self.result(event.message, chat[0], chat[1], chat[2]), True)

        self.handler = handler
        self.client.add_event_handler(handler, events.NewMessage(chats=[c[2] for c in chats]))

    def stop_monitor(self):
        if self.client and self.handler:
            self.client.remove_event_handler(self.handler)
        self.handler = None

    async def logout(self):
        self.stop_monitor()
        if self.client:
            await self.client.log_out()
        if keyring.get_password(SERVICE, "session"):
            keyring.delete_password(SERVICE, "session")
        self.client = None

    async def disconnect(self):
        self.stop_monitor()
        if self.client:
            await self.client.disconnect()
            self.client = None
