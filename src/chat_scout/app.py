import asyncio
import csv
import sys
import tempfile
from datetime import datetime, time, timedelta, timezone

import keyring
from platformdirs import user_data_path
from PySide6.QtCore import Qt, QDate, QLockFile, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem, QAbstractItemView,
    QDateEdit, QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QMessageBox, QInputDialog, QFileDialog, QSystemTrayIcon, QStyle, QCheckBox,
)
from qasync import QEventLoop
from telethon import errors

from .rules import Rule
from .service import TelegramService, SERVICE
from .store import Store


class Window(QMainWindow):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.service = TelegramService()
        self.task = None
        self.tasks = set()
        self.authorized = False
        self.closing = False
        self.chats = []
        self.rows = []
        self.setWindowTitle("Chat Scout · поиск в Telegram")
        self.resize(1200, 800)
        root = QWidget()
        layout = QVBoxLayout(root)
        self.setCentralWidget(root)
        title = QLabel("Chat Scout")
        title.setStyleSheet("font-size: 28px; font-weight: 700")
        layout.addWidget(title)
        layout.addWidget(QLabel("Локальный поиск в выбранных чатах · без ботов и LLM"))
        auth = QHBoxLayout()
        self.api_id = QLineEdit(str(store.get("api_id", "")))
        self.api_id.setPlaceholderText("API ID")
        self.api_hash = QLineEdit()
        self.api_hash.setPlaceholderText("API Hash (my.telegram.org)")
        self.api_hash.setEchoMode(QLineEdit.EchoMode.Password)
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("Телефон: +7…")
        self.login = QPushButton("Подключить / войти")
        self.login.clicked.connect(lambda: self.launch(self.connect_account()))
        self.logout_button = QPushButton("Выйти из аккаунта")
        self.logout_button.clicked.connect(self.ask_logout)
        for w in [self.api_id, self.api_hash, self.phone, self.login, self.logout_button]:
            auth.addWidget(w)
        layout.addLayout(auth)
        split = QSplitter()
        layout.addWidget(split, 1)
        left = QWidget()
        column = QVBoxLayout(left)
        reload_button = QPushButton("Обновить список чатов")
        reload_button.clicked.connect(lambda: self.launch(self.load_chats()))
        column.addWidget(reload_button)
        self.chat_filter = QLineEdit()
        self.chat_filter.setPlaceholderText("Фильтр списка чатов…")
        self.chat_filter.textChanged.connect(self.filter_chats)
        column.addWidget(self.chat_filter)
        column.addWidget(QLabel("Отметьте чаты для поиска:"))
        self.chat_list = QListWidget()
        column.addWidget(self.chat_list)
        split.addWidget(left)
        right = QWidget()
        panel = QVBoxLayout(right)
        form = QFormLayout()
        self.any_of = QLineEdit()
        self.all_of = QLineEdit()
        self.exclude = QLineEdit()
        for field, label, key in [(self.any_of, "Любая фраза", "any"),
                                  (self.all_of, "Все фразы", "all"),
                                  (self.exclude, "Исключить", "exclude")]:
            field.setText(store.get(key, ""))
            field.setPlaceholderText("Фразы через ; — без учёта регистра, ё = е")
            form.addRow(label, field)
        dates = QHBoxLayout()
        self.since = QDateEdit(QDate.currentDate().addDays(-7))
        self.until = QDateEdit(QDate.currentDate())
        for date in [self.since, self.until]:
            date.setCalendarPopup(True)
            date.setDisplayFormat("dd.MM.yyyy")
        dates.addWidget(self.since)
        dates.addWidget(QLabel("—"))
        dates.addWidget(self.until)
        form.addRow("Период (местное время)", dates)
        self.limit = QSpinBox()
        self.limit.setRange(100, 100000)
        self.limit.setValue(store.get("limit", 5000))
        self.limit.setSingleStep(1000)
        form.addRow("Максимум сообщений на чат", self.limit)
        panel.addLayout(form)
        hint = QLabel("Поиск проверяет последние N сообщений до конца периода.\n"
                      "Фразы ищутся как подстроки. Пустые условия означают весь текст.")
        hint.setWordWrap(True)
        panel.addWidget(hint)
        controls = QHBoxLayout()
        search = QPushButton("Найти в истории")
        search.clicked.connect(lambda: self.launch(self.search()))
        cancel = QPushButton("Отменить операцию")
        cancel.clicked.connect(self.cancel)
        self.watch = QPushButton("Начать мониторинг")
        self.watch.clicked.connect(self.toggle_monitor)
        for w in [search, cancel, self.watch]:
            controls.addWidget(w)
        panel.addLayout(controls)
        self.notifications = QCheckBox("Уведомлять о новых совпадениях (без текста сообщения)")
        self.notifications.setChecked(True)
        panel.addWidget(self.notifications)
        self.monitor_label = QLabel("Мониторинг выключен. Работает только при запущенном приложении.")
        self.monitor_label.setWordWrap(True)
        panel.addWidget(self.monitor_label)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Дата", "Чат", "Сообщение", "Ссылка"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(1, 170)
        self.table.cellDoubleClicked.connect(self.open_result)
        panel.addWidget(self.table, 1)
        foot = QHBoxLayout()
        export = QPushButton("Экспорт CSV…")
        export.clicked.connect(self.export)
        clear = QPushButton("Удалить результаты…")
        clear.clicked.connect(self.clear)
        foot.addWidget(export)
        foot.addWidget(clear)
        panel.addLayout(foot)
        split.addWidget(right)
        split.setSizes([280, 920])
        self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView), self)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        for row in store.results():
            self.append_row(row)
        self.statusBar().showMessage("Введите API ID / Hash и подключитесь. Двойной щелчок — открыть сообщение.")

    def launch(self, coro):
        if self.task and not self.task.done():
            coro.close()
            self.statusBar().showMessage("Дождитесь текущей операции или отмените её.")
            return
        self.task = asyncio.create_task(self.guarded(coro))
        self.tasks.add(self.task)
        self.task.add_done_callback(self.tasks.discard)

    async def guarded(self, coro):
        try:
            await coro
        except asyncio.CancelledError:
            self.statusBar().showMessage("Операция отменена. Полученные результаты сохранены.")
        except errors.FloodWaitError as exc:
            self.statusBar().showMessage(f"Telegram требует паузу {exc.seconds} сек. Повторите позже.")
        except Exception as exc:
            # Never display raw RPC arguments, session strings or authentication data.
            self.statusBar().showMessage(f"Операция не выполнена: {type(exc).__name__}")
            QMessageBox.warning(self, "Ошибка", f"Тип: {type(exc).__name__}\n"
                "Проверьте сеть, API ID / Hash, код входа и доступ к чату. Затем повторите операцию.")

    def cancel(self):
        if self.task and not self.task.done():
            self.task.cancel()

    def require_auth(self):
        if not self.authorized:
            raise ValueError("Not connected")

    async def prompt_secret(self, title, label, password=False):
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        if password:
            dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
        future = asyncio.get_running_loop().create_future()
        def finished(result):
            if not future.done():
                future.set_result(dialog.textValue() if result else None)
        dialog.finished.connect(finished)
        dialog.open()
        try:
            return await future
        finally:
            dialog.close()
            dialog.deleteLater()

    async def connect_account(self):
        self.authorized = False
        self.service.stop_monitor()
        self.monitor_stopped()
        api_id = int(self.api_id.text().strip())
        api_hash = self.api_hash.text().strip() or keyring.get_password(SERVICE, "api_hash")
        if api_id <= 0 or not api_hash or len(api_hash) != 32:
            raise ValueError("Invalid API credentials")
        self.statusBar().showMessage("Подключение к Telegram…")
        authorized = await self.service.connect(api_id, api_hash)
        if not authorized:
            phone = self.phone.text().strip()
            if not phone.startswith("+"):
                raise ValueError("Phone must include country code")
            await self.service.request_code(phone)
            code = await self.prompt_secret("Вход", "Код подтверждения из Telegram:", True)
            if code is None:
                return
            try:
                await self.service.sign_in(code=code.strip())
            except errors.SessionPasswordNeededError:
                password = await self.prompt_secret("Двухфакторная защита", "Пароль Telegram:", True)
                if password is None:
                    return
                await self.service.sign_in(password=password)
                password = None
        self.authorized = True
        keyring.set_password(SERVICE, "api_hash", api_hash)
        self.store.set("api_id", api_id)
        self.api_hash.clear()
        self.phone.clear()
        await self.load_chats()

    async def load_chats(self):
        self.require_auth()
        self.statusBar().showMessage("Загрузка чатов…")
        selected = {c[0] for c in self.selected_chats()} or set(self.store.get("chats", []))
        self.chats = await self.service.dialogs()
        self.chat_list.clear()
        for chat_id, title, _ in self.chats:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, chat_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if chat_id in selected else Qt.CheckState.Unchecked)
            self.chat_list.addItem(item)
        self.filter_chats(self.chat_filter.text())
        self.statusBar().showMessage(f"Подключено. Доступных чатов: {len(self.chats)}")

    def filter_chats(self, text):
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            item.setHidden(text.casefold() not in item.text().casefold())

    def selected_chats(self):
        ids = {self.chat_list.item(i).data(Qt.ItemDataRole.UserRole)
               for i in range(self.chat_list.count())
               if self.chat_list.item(i).checkState() == Qt.CheckState.Checked}
        return [chat for chat in self.chats if chat[0] in ids]

    def settings(self):
        self.require_auth()
        chats = self.selected_chats()
        if not chats:
            raise ValueError("Select chats")
        for key, value in [("any", self.any_of.text()), ("all", self.all_of.text()),
                           ("exclude", self.exclude.text()), ("limit", self.limit.value()),
                           ("chats", [c[0] for c in chats])]:
            self.store.set(key, value)
        return chats, Rule.parse(self.any_of.text(), self.all_of.text(), self.exclude.text())

    async def search(self):
        chats, rule = self.settings()
        since = datetime.combine(self.since.date().toPython(), time.min).astimezone(timezone.utc)
        until = datetime.combine(self.until.date().toPython() + timedelta(days=1), time.min).astimezone(timezone.utc)
        if since >= until:
            raise ValueError("Invalid date range")
        self.statusBar().showMessage("Поиск…")
        count = await self.service.search(chats, rule, since, until, self.limit.value(),
                                          self.accept_result, self.statusBar().showMessage)
        self.statusBar().showMessage(f"Готово: проверено {count} сообщений. Предел на чат: {self.limit.value()}.")

    def toggle_monitor(self):
        if self.service.handler:
            self.service.stop_monitor()
            self.monitor_stopped()
        else:
            self.launch(self.start_monitor())

    async def start_monitor(self):
        chats, rule = self.settings()
        self.service.monitor(chats, rule, self.accept_result)
        self.watch.setText("Остановить мониторинг")
        self.monitor_label.setText(f"Мониторинг включён: {len(chats)} чатов. Условия зафиксированы при запуске. "
                                   "После сна или отключения сети проверьте пропуски поиском по истории.")

    def monitor_stopped(self):
        self.watch.setText("Начать мониторинг")
        self.monitor_label.setText("Мониторинг выключен. Для работы приложение должно быть запущено.")

    def accept_result(self, result, live=False):
        if self.store.add(result):
            self.append_row(result, top=True)
            if live and self.notifications.isChecked() and self.tray.isVisible():
                self.tray.showMessage("Chat Scout", "Найдено новое совпадение. Откройте приложение.")

    def append_row(self, result, top=False):
        index = 0 if top else self.table.rowCount()
        self.rows.insert(index, result)
        self.table.insertRow(index)
        date = datetime.fromisoformat(result["date"]).astimezone().strftime("%d.%m.%Y %H:%M")
        for col, value in enumerate([date, result["title"], result["text"].replace("\n", " ")[:240], result["link"]]):
            item = QTableWidgetItem(value)
            item.setToolTip(result["text"] if col == 2 else value)
            self.table.setItem(index, col, item)
        if self.table.rowCount() > 2000:
            self.table.removeRow(2000)
            self.rows.pop()

    def open_result(self, row, col):
        result = self.rows[row]
        if result["link"]:
            QDesktopServices.openUrl(QUrl(result["link"]))
        else:
            QMessageBox.information(self, "Сообщение", result["text"])

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт результатов", "results.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["chat_id", "message_id", "title", "date", "text", "link"])
                writer.writeheader()
                for result in self.store.results(limit=1000000):
                    # Avoid spreadsheet formula injection in user-controlled chat text.
                    writer.writerow({k: ("'" + str(v) if str(v).lstrip().startswith(("=", "+", "-", "@")) else v)
                                     for k, v in result.items()})
            self.statusBar().showMessage("CSV сохранён. Файл содержит тексты сообщений.")
        except OSError:
            QMessageBox.warning(self, "Экспорт", "Не удалось записать файл.")

    def clear(self):
        if QMessageBox.question(self, "Удаление", "Удалить все сохранённые результаты с этого компьютера?") == QMessageBox.StandardButton.Yes:
            self.store.clear()
            self.rows.clear()
            self.table.setRowCount(0)

    def ask_logout(self):
        if QMessageBox.question(self, "Выход", "Завершить эту сессию Telegram? Результаты останутся; их можно удалить отдельно.") == QMessageBox.StandardButton.Yes:
            self.launch(self.logout())

    async def logout(self):
        await self.service.logout()
        self.authorized = False
        self.chats = []
        self.chat_list.clear()
        self.monitor_stopped()
        self.statusBar().showMessage("Сессия завершена.")

    def closeEvent(self, event):
        if self.closing:
            event.accept()
            return
        event.ignore()
        self.closing = True
        asyncio.create_task(self.shutdown())

    async def shutdown(self):
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*list(self.tasks), return_exceptions=True)
        try:
            await asyncio.wait_for(self.service.disconnect(), timeout=5)
        finally:
            self.store.close()
            self.tray.hide()
            self.close()


def main():
    smoke = "--smoke-test" in sys.argv
    temporary = tempfile.TemporaryDirectory(prefix="chat-scout-smoke-") if smoke else None
    app = QApplication(sys.argv)
    app.setApplicationName("ChatScout")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")
    from pathlib import Path
    path = Path(temporary.name) if temporary else user_data_path("ChatScout", appauthor=False)
    path.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(path / "app.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(None, "Chat Scout", "Приложение уже запущено.")
        return
    app.setStyleSheet("QLineEdit, QSpinBox, QDateEdit { padding: 6px; } QPushButton { padding: 7px 10px; }"
                      "QTableWidget { gridline-color: #dce2e8; } QMainWindow { background: #f5f7fa; }")
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = Window(Store(path / "results.sqlite3"))
    window.show()
    if smoke:
        QTimer.singleShot(500, window.close)
    with loop:
        loop.run_forever()
    lock.unlock()
    if temporary:
        temporary.cleanup()


if __name__ == "__main__":
    main()
