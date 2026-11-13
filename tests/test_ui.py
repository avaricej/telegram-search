import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidgetItem
from chat_scout.app import Window
from chat_scout.store import Store


class UiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_result_display_and_chat_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "test.sqlite3")
            window = Window(store)
            window.chats = [(-100123, "Тестовый чат", object())]
            item = QListWidgetItem("Тестовый чат")
            item.setData(Qt.ItemDataRole.UserRole, -100123)
            item.setCheckState(Qt.CheckState.Checked)
            window.chat_list.addItem(item)
            self.assertEqual(window.selected_chats()[0][0], -100123)
            row = dict(chat_id=-100123, message_id=1, title="Тестовый чат",
                       date="2026-11-13T12:00:00+00:00", text="Python удалённо",
                       link="https://t.me/c/123/1")
            window.accept_result(row)
            window.accept_result(row)
            self.assertEqual(window.table.rowCount(), 1)
            self.assertEqual(window.table.item(0, 1).text(), "Тестовый чат")
            window.filter_chats("другой")
            self.assertTrue(item.isHidden())
            window.tray.hide()
            window.closing = True
            window.close()
            window.deleteLater()
            self.app.processEvents()
            store.close()


if __name__ == "__main__":
    unittest.main()
