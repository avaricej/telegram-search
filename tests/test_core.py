import tempfile
import unittest
from pathlib import Path

from chat_scout.rules import Rule, message_link
from chat_scout.store import Store


class RulesTest(unittest.TestCase):
    def test_russian_and_or_exclusions(self):
        rule = Rule.parse("Python; аналитик", "удалённо; SQL", "стажировка; бесплатно")
        self.assertTrue(rule.matches("Нужен АНАЛИТИК, SQL, удаленно"))
        self.assertFalse(rule.matches("Python SQL удалённо: стажировка"))
        self.assertFalse(rule.matches("Python удалённо"))

    def test_whitespace_and_empty(self):
        self.assertTrue(Rule.parse("ищу   разработчика").matches("Ищу\nразработчика"))
        self.assertFalse(Rule().matches(""))
        self.assertTrue(Rule().matches("обычный текст"))

    def test_links(self):
        self.assertEqual(message_link(-10012345, 9), "https://t.me/c/12345/9")
        self.assertEqual(message_link(-10012345, 9, "example"), "https://t.me/example/9")
        self.assertEqual(message_link(-12345, 9), "")


class StoreTest(unittest.TestCase):
    def test_persistence_dedup_and_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.sqlite3"
            store = Store(path)
            row = dict(chat_id=-100123, message_id=1, title="Чат", date="2026-11-13T12:00:00+00:00",
                       text="текст", link="https://t.me/c/123/1")
            self.assertTrue(store.add(row))
            self.assertFalse(store.add(row))
            store.set("chats", [-100123])
            store.close()
            store = Store(path)
            self.assertEqual(store.results(), [row])
            self.assertEqual(store.get("chats"), [-100123])
            store.clear()
            self.assertEqual(store.results(), [])
            store.close()


if __name__ == "__main__":
    unittest.main()
