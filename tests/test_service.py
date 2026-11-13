import unittest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from chat_scout.rules import Rule
from chat_scout.service import TelegramService


class FakeClient:
    def __init__(self, messages):
        self.messages = messages

    async def iter_messages(self, entity, limit, offset_date):
        for msg in [m for m in self.messages if m.date < offset_date][:limit]:
            yield msg


class SearchTest(unittest.IsolatedAsyncioTestCase):
    async def test_period_limit_and_rules(self):
        now = datetime(2026, 11, 13, tzinfo=timezone.utc)
        messages = [SimpleNamespace(id=i + 1, date=now - timedelta(days=i), raw_text=text)
                    for i, text in enumerate(["Python удаленно", "Python стажировка", "Python удаленно", "Python удаленно"])]
        service = TelegramService()
        service.client = FakeClient(messages)
        found = []
        count = await service.search([(-100123, "Test", SimpleNamespace(username=None))],
                    Rule.parse("python", exclude="стажировка"), now - timedelta(days=2),
                    now + timedelta(days=1), 10, lambda row, live: found.append(row), lambda text: None)
        self.assertEqual(count, 3)
        self.assertEqual([r["message_id"] for r in found], [1, 3])
        found.clear()
        count = await service.search([(-100123, "Test", SimpleNamespace(username=None))],
                    Rule(), now - timedelta(days=10), now + timedelta(days=1), 1,
                    lambda row, live: found.append(row), lambda text: None)
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
