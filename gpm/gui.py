"""
GPM Automation - GUI Application
Modern Qt-based interface for GPM automation tasks
"""
import sys
import asyncio
import threading
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QGroupBox, QGridLayout, QMessageBox,
    QFileDialog, QSplitter, QFrame, QLineEdit, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QTextCursor

# Import GPM modules
import config
from config import setup_logger
from excel import update_excel_column_a_with_cookie_files, read_excel
from services import create_profile, start_profile, close_profile, delete_profile
from runner import run_all_playwright
from utils import safe_print, menu_multi_select
from index import process_row


class OutputRedirector:
    """Redirect stdout/stderr to GUI terminal"""
    def __init__(self, text_widget, original_stream):
        self.text_widget = text_widget
        self.original_stream = original_stream

    def write(self, text):
        if text.strip():
            # Also write to original stream for debugging
            if self.original_stream:
                self.original_stream.write(text)

            # Write to GUI
            cursor = self.text_widget.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.text_widget.setTextCursor(cursor)
            self.text_widget.insertPlainText(text)
            self.text_widget.ensureCursorVisible()

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()


class TaskWorker(QThread):
    """Worker thread for running async tasks"""
    log_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, task_name, task_func):
        super().__init__()
        self.task_name = task_name
        self.task_func = task_func

    def run(self):
        try:
            self.log_signal.emit(f"\n{'='*70}\n🚀 Starting: {self.task_name}\n{'='*70}\n")

            # Run the task
            self.task_func()

            self.log_signal.emit(f"\n{'='*70}\n✅ Completed: {self.task_name}\n{'='*70}\n")
            self.finished_signal.emit(True, f"Task '{self.task_name}' completed!")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.log_signal.emit(f"\n{'='*70}\n❌ Failed: {self.task_name}\n{error_msg}\n{'='*70}\n")
            self.finished_signal.emit(False, error_msg)


class ModernButton(QPushButton):
    """Styled button with modern look"""
    def __init__(self, text, icon="", color="#2196F3"):
        super().__init__()
        self.base_color = color
        display_text = f"{icon}  {text}" if icon else text
        self.setText(display_text)
        self.setMinimumHeight(35)
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setCursor(Qt.PointingHandCursor)
        self.update_style()

    def update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.base_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(self.base_color, 20)};
            }}
            QPushButton:pressed {{
                background-color: {self.lighten_color(self.base_color, -20)};
            }}
            QPushButton:disabled {{
                background-color: #424242;
                color: #757575;
            }}
        """)

    def lighten_color(self, hex_color, amount):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))
        return f"#{r:02x}{g:02x}{b:02x}"


class GPMMainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.current_worker = None
        self.logger = setup_logger()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("GPM Automation Suite")
        self.setMinimumSize(1200, 750)

        # Apply dark theme
        self.apply_dark_theme()

        # Main widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header
        layout.addWidget(self.create_header())

        # Main splitter
        splitter = QSplitter(Qt.Vertical)

        # Top section: Config + Tasks
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setSpacing(10)
        top_layout.addWidget(self.create_config_section(), 1)
        top_layout.addWidget(self.create_tasks_section(), 2)
        splitter.addWidget(top_widget)

        # Bottom section: Terminal
        splitter.addWidget(self.create_terminal_section())

        splitter.setSizes([280, 470])
        layout.addWidget(splitter)

        # Status bar
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background: #1a1a1a;
                color: #00ff00;
                border-top: 2px solid #2196F3;
                padding: 5px;
                font-weight: bold;
            }
        """)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0d0d0d;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial;
            }
            QGroupBox {
                background-color: #1a1a1a;
                border: 2px solid #2196F3;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                font-size: 10pt;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #2196F3;
            }
            QTextEdit {
                background-color: #000000;
                color: #00ff00;
                border: 2px solid #2196F3;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
                selection-background-color: #2196F3;
            }
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 6px;
                font-size: 9pt;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
            QSpinBox {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 4px;
                font-size: 9pt;
            }
            QSpinBox:focus {
                border: 1px solid #2196F3;
            }
            QCheckBox {
                spacing: 5px;
                color: #e0e0e0;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #2196F3;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
            }
            QLabel {
                color: #e0e0e0;
            }
            QSplitter::handle {
                background-color: #2196F3;
                height: 2px;
            }
        """)

    def create_header(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a237e, stop:1 #2196F3);
                border-radius: 8px;
                padding: 10px 15px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        title = QLabel("🚀 GPM Automation Suite")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: white;")

        subtitle = QLabel("TikTok Profile & Cookie Management")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: #bbdefb;")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        return frame

    def create_config_section(self):
        group = QGroupBox("⚙️ Configuration")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # Excel path with browse button
        layout.addWidget(QLabel("Excel File:"))
        excel_layout = QHBoxLayout()
        self.excel_path = QLineEdit(config.EXCEL_PATH)
        self.excel_path.setPlaceholderText("data/proxies.xlsx")
        excel_browse = QPushButton("📁")
        excel_browse.setMaximumWidth(30)
        excel_browse.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        excel_browse.clicked.connect(self.browse_excel)
        excel_layout.addWidget(self.excel_path)
        excel_layout.addWidget(excel_browse)
        layout.addLayout(excel_layout)

        # Cookies directory with browse button
        layout.addWidget(QLabel("Cookies Dir:"))
        cookies_layout = QHBoxLayout()
        self.cookies_dir = QLineEdit(config.COOKIES_DIR)
        self.cookies_dir.setPlaceholderText("data/cookies")
        cookies_browse = QPushButton("📁")
        cookies_browse.setMaximumWidth(30)
        cookies_browse.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        cookies_browse.clicked.connect(self.browse_cookies)
        cookies_layout.addWidget(self.cookies_dir)
        cookies_layout.addWidget(cookies_browse)
        layout.addLayout(cookies_layout)

        # Threads
        layout.addWidget(QLabel("Threads:"))
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 20)
        self.threads_spin.setValue(config.THREADS)
        layout.addWidget(self.threads_spin)

        # Start limit
        layout.addWidget(QLabel("Start Limit:"))
        self.start_limit = QSpinBox()
        self.start_limit.setRange(1, 50)
        self.start_limit.setValue(config.START_LIMIT)
        layout.addWidget(self.start_limit)

        layout.addStretch()

        # Apply button
        apply_btn = ModernButton("Apply Settings", "💾", "#4CAF50")
        apply_btn.clicked.connect(self.apply_config)
        layout.addWidget(apply_btn)

        group.setLayout(layout)
        return group

    def create_tasks_section(self):
        group = QGroupBox("📋 Automation Tasks")
        layout = QGridLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        tasks = [
            ("📝 Update Cookies to Excel", self.task_update_cookies, "#2196F3", 0, 0),
            ("➕ Create Profiles", self.task_create_profiles, "#4CAF50", 0, 1),
            ("▶️ Start Profiles", self.task_start_profiles, "#FF9800", 1, 0),
            ("📥 Import Cookies", self.task_import_cookies, "#9C27B0", 1, 1),
            ("🎬 Import & Start", self.task_import_and_start, "#E91E63", 2, 0),
            ("🤖 Run Automation", self.task_run_automation, "#00BCD4", 2, 1),
            ("🔄 Full Workflow", self.task_full_workflow, "#FF5722", 3, 0),
            ("🗑️ Close Profiles", self.task_close_profiles, "#F44336", 3, 1),
        ]

        for text, handler, color, row, col in tasks:
            icon, name = text.split(" ", 1)
            btn = ModernButton(name, icon, color)
            btn.clicked.connect(handler)
            layout.addWidget(btn, row, col)

        group.setLayout(layout)
        return group

    def create_terminal_section(self):
        group = QGroupBox("🖥️ Terminal Output")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Terminal
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("Consolas", 9))
        self.terminal.setFont(QFont("Consolas", 10))
        layout.addWidget(self.terminal)

        # Redirect stdout/stderr
        sys.stdout = OutputRedirector(self.terminal, sys.__stdout__)
        sys.stderr = OutputRedirector(self.terminal, sys.__stderr__)

        # Control buttons
        btn_layout = QHBoxLayout()

        clear_btn = ModernButton("Clear", "🗑️", "#616161")
        clear_btn.setMaximumWidth(100)
        clear_btn.clicked.connect(self.terminal.clear)

        save_btn = ModernButton("Save Log", "💾", "#455A64")
        save_btn.setMaximumWidth(100)
        save_btn.clicked.connect(self.save_log)

        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        group.setLayout(layout)
        return group

    @Slot()
    def browse_excel(self):
        """Browse for Excel file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File",
            config.EXCEL_PATH,
            "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.excel_path.setText(file_path)

    @Slot()
    def browse_cookies(self):
        """Browse for cookies directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Cookies Directory",
            config.COOKIES_DIR
        )
        if dir_path:
            self.cookies_dir.setText(dir_path)

    @Slot()
    def apply_config(self):
        config.EXCEL_PATH = self.excel_path.text()
        config.COOKIES_DIR = self.cookies_dir.text()
        config.THREADS = self.threads_spin.value()
        config.START_LIMIT = self.start_limit.value()

        self.log("✅ Configuration updated successfully")
        QMessageBox.information(self, "Success", "Configuration applied!")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.terminal.append(f"[{timestamp}] {message}")

    def run_task(self, name, func):
        if self.current_worker and self.current_worker.isRunning():
            QMessageBox.warning(self, "Task Running",
                "Another task is running. Please wait...")
            return

        self.current_worker = TaskWorker(name, func)
        self.current_worker.log_signal.connect(self.log)
        self.current_worker.finished_signal.connect(self.on_task_finished)
        self.current_worker.start()
        self.statusBar().showMessage(f"🔄 Running: {name}...")

    @Slot(bool, str)
    def on_task_finished(self, success, message):
        status = "✅ Success" if success else "❌ Failed"
        self.statusBar().showMessage(f"{status}: {message}")
        if not success:
            QMessageBox.critical(self, "Task Failed", message)

    # Task handlers
    def task_update_cookies(self):
        def run():
            n = update_excel_column_a_with_cookie_files(
                config.EXCEL_PATH,
                config.COOKIES_DIR
            )
            safe_print(f"✅ Updated {n} cookie paths")
        self.run_task("Update Cookies to Excel", run)

    def task_create_profiles(self):
        def run():
            rows = read_excel(config.EXCEL_PATH)
            for i, row in enumerate(rows, 1):
                name, cookie, proxy = row[:3]
                if name and proxy:
                    process_row(name, cookie, proxy, i, {
                        "handle_cookies": False,
                        "create": True,
                        "start": False,
                        "import": False,
                        "pw": False,
                        "close": False
                    })
        self.run_task("Create Profiles", run)

    def task_start_profiles(self):
        def run():
            rows = read_excel(config.EXCEL_PATH)
            for i, row in enumerate(rows, 1):
                name, cookie, proxy = row[:3]
                if name:
                    process_row(name, cookie, proxy, i, {
                        "handle_cookies": False,
                        "create": False,
                        "start": True,
                        "import": False,
                        "pw": False,
                        "close": False
                    })
        self.run_task("Start Profiles", run)

    def task_import_cookies(self):
        def run():
            rows = read_excel(config.EXCEL_PATH)

            # Process profiles
            for i, row in enumerate(rows, 1):
                name, cookie, proxy = row[:3]
                if name and cookie:
                    process_row(name, cookie, proxy, i, {
                        "handle_cookies": False,
                        "create": False,
                        "start": True,
                        "import": True,
                        "pw": True,
                        "close": False
                    })

            # Run playwright jobs
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            jobs = config.pw_jobs.copy()
            if jobs:
                loop.run_until_complete(
                    run_all_playwright(jobs, {"import": True, "start": False})
                )
            loop.close()

        self.run_task("Import Cookies", run)

    def task_import_and_start(self):
        def run():
            rows = read_excel(config.EXCEL_PATH)

            for i, row in enumerate(rows, 1):
                name, cookie, proxy = row[:3]
                if name and cookie:
                    process_row(name, cookie, proxy, i, {
                        "handle_cookies": False,
                        "create": False,
                        "start": True,
                        "import": True,
                        "pw": True,
                        "close": False
                    })

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            jobs = config.pw_jobs.copy()
            if jobs:
                loop.run_until_complete(
                    run_all_playwright(jobs, {"import": True, "start": True})
                )
            loop.close()

        self.run_task("Import & Start", run)

    def task_run_automation(self):
        def run():
            rows = read_excel(config.EXCEL_PATH)

            for i, row in enumerate(rows, 1):
                name, cookie, proxy = row[:3]
                if name:
                    process_row(name, cookie, proxy, i, {
                        "handle_cookies": False,
                        "create": False,
                        "start": True,
                        "import": False,
                        "pw": True,
                        "close": False
                    })

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            jobs = config.pw_jobs.copy()
            if jobs:
                loop.run_until_complete(
                    run_all_playwright(jobs, {"import": False, "start": True})
                )
            loop.close()

        self.run_task("Run Automation", run)

    def task_full_workflow(self):
        def run():
            # Update cookies
            n = update_excel_column_a_with_cookie_files(
                config.EXCEL_PATH,
                config.COOKIES_DIR
            )
            safe_print(f"✅ Updated {n} cookies")

            # Process all
            rows = read_excel(config.EXCEL_PATH)
            for i, row in enumerate(rows, 1):
                name, cookie, proxy = row[:3]
                if name and cookie and proxy:
                    process_row(name, cookie, proxy, i, {
                        "handle_cookies": False,
                        "create": True,
                        "start": True,
                        "import": True,
                        "pw": True,
                        "close": False
                    })

            # Run automation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            jobs = config.pw_jobs.copy()
            if jobs:
                loop.run_until_complete(
                    run_all_playwright(jobs, {"import": True, "start": True})
                )
            loop.close()

        self.run_task("Full Workflow", run)

    def task_close_profiles(self):
        def run():
            rows = read_excel(config.EXCEL_PATH)
            for i, row in enumerate(rows, 1):
                name, cookie, proxy = row[:3]
                if name:
                    process_row(name, cookie, proxy, i, {
                        "handle_cookies": False,
                        "create": False,
                        "start": False,
                        "import": False,
                        "pw": False,
                        "close": True
                    })
        self.run_task("Close Profiles", run)

    def save_log(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log",
            f"gpm_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.terminal.toPlainText())
            self.log(f"💾 Log saved: {file_path}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = GPMMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
