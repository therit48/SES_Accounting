import pandas as pd
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QMessageBox, QHeaderView, 
                             QTabWidget, QFrame, QAbstractItemView, QGridLayout)
from PyQt5.QtCore import Qt
from core.database import DatabaseManager
import re

# ==========================================
# 1. SCHEDULE MASTER TAB (With Migration)
# ==========================================
class ScheduleTab(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.db = DatabaseManager(company_name)
        self.init_db()
        self.init_ui()
        self.load_data()

    def init_db(self):
        self.db.execute_query("CREATE TABLE IF NOT EXISTS schedules (code TEXT PRIMARY KEY, name TEXT)")
        # Check for legacy table structure if necessary, though code is usually the PK here.

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame { background-color: #ecf0f1; border: 1px solid #bdc3c7; border-radius: 4px; }
            QLabel { font-weight: bold; color: #2c3e50; font-size: 14px; }
        """)
        grid = QGridLayout(form_frame)
        grid.setContentsMargins(15, 15, 15, 15)
        grid.setSpacing(15)

        lbl_title = QLabel("Create New Schedule")
        lbl_title.setStyleSheet("color: #2980b9; font-size: 15px; text-decoration: underline;")
        
        self.input_code = QLineEdit()
        self.input_code.setPlaceholderText("e.g. 35")
        self.input_code.setFixedWidth(100)
        
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("e.g. Sundry Creditor")

        btn_add = QPushButton("Save Schedule")
        btn_add.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold;")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self.add_entry)

        grid.addWidget(lbl_title, 0, 0, 1, 4)
        grid.addWidget(QLabel("Code:"), 1, 0)
        grid.addWidget(self.input_code, 1, 1)
        grid.addWidget(QLabel("Name:"), 1, 2)
        grid.addWidget(self.input_name, 1, 3)
        grid.addWidget(btn_add, 1, 4)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Code", "Schedule Name", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        layout.addWidget(form_frame)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def add_entry(self):
        code = self.input_code.text().strip()
        name = self.input_name.text().strip()
        if not code or not name:
            QMessageBox.warning(self, "Error", "Fill both fields")
            return

        if self.db.execute_query("INSERT INTO schedules (code, name) VALUES (?, ?)", (code, name)):
            self.input_code.clear(); self.input_name.clear()
            self.load_data()
        else:
            QMessageBox.warning(self, "Error", "Code already exists")

    def load_data(self):
        self.table.setRowCount(0)
        rows = self.db.fetch_all("SELECT code, name FROM schedules ORDER BY code ASC")
        for r, (code, name) in enumerate(rows):
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(code)))
            self.table.setItem(r, 1, QTableWidgetItem(name))
            btn = QPushButton("Delete")
            btn.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 3px;")
            btn.clicked.connect(lambda ch, c=code: self.delete_entry(c))
            self.table.setCellWidget(r, 2, btn)

    def delete_entry(self, code):
        check = self.db.fetch_all("SELECT count(*) FROM accounts WHERE schedule_code=?", (code,))
        if check and check[0][0] > 0:
            QMessageBox.warning(self, "Error", "Schedule is in use by accounts.")
            return
        if QMessageBox.question(self, "Confirm", "Delete Schedule?") == QMessageBox.Yes:
            self.db.execute_query("DELETE FROM schedules WHERE code=?", (code,))
            self.load_data()

# ==========================================
# 2. ACCOUNT MASTER TAB
# ==========================================
class AccountTab(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.db = DatabaseManager(company_name)
        self.init_db()
        self.init_ui()
        self.load_schedules()
        self.load_data()

    def init_db(self):
        self.db.execute_query("""
            CREATE TABLE IF NOT EXISTS accounts (
                party_code TEXT PRIMARY KEY, 
                party_name TEXT, 
                schedule_code TEXT
            )
        """)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        form_frame = QFrame()
        form_frame.setStyleSheet("background-color: #ecf0f1; border: 1px solid #bdc3c7; border-radius: 4px;")
        grid = QGridLayout(form_frame)
        
        self.combo_schedule = QComboBox()
        self.input_party = QLineEdit()
        btn_create = QPushButton("Save Party")
        btn_create.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold;")
        btn_create.clicked.connect(self.create_party)

        grid.addWidget(QLabel("Select Schedule:"), 0, 0)
        grid.addWidget(self.combo_schedule, 0, 1)
        grid.addWidget(QLabel("Party Name:"), 0, 2)
        grid.addWidget(self.input_party, 0, 3)
        grid.addWidget(btn_create, 0, 4)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Code", "Party Name", "Schedule", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(form_frame)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_schedules(self):
        self.combo_schedule.clear()
        rows = self.db.fetch_all("SELECT code, name FROM schedules")
        for code, name in rows: self.combo_schedule.addItem(f"{code} - {name}", code)

    def create_party(self):
        name = self.input_party.text().strip()
        sched_code = self.combo_schedule.currentData()
        if not name or not sched_code: return

        clean_name = re.sub(r'[^a-zA-Z]', '', name)
        prefix = f"{sched_code}{clean_name[:2].upper() if len(clean_name)>=2 else 'XX'}"
        existing = self.db.fetch_all("SELECT party_code FROM accounts WHERE party_code LIKE ?", (f"{prefix}%",))
        max_num = 0
        for (code,) in existing:
            try:
                num = int(code[-3:])
                if num > max_num: max_num = num
            except: pass
        
        final_code = f"{prefix}{max_num + 1:03d}"
        if self.db.execute_query("INSERT INTO accounts (party_code, party_name, schedule_code) VALUES (?, ?, ?)", 
                                 (final_code, name, sched_code)):
            self.input_party.clear()
            self.load_data()

    def load_data(self):
        self.table.setRowCount(0)
        rows = self.db.fetch_all("SELECT party_code, party_name, schedule_code FROM accounts ORDER BY party_code DESC")
        for r, (code, name, sched) in enumerate(rows):
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(code))
            self.table.setItem(r, 1, QTableWidgetItem(name))
            self.table.setItem(r, 2, QTableWidgetItem(sched))
            btn = QPushButton("Delete")
            btn.setStyleSheet("background-color: #e74c3c; color: white;")
            btn.clicked.connect(lambda ch, c=code: self.delete_party(c))
            self.table.setCellWidget(r, 3, btn)

    def delete_party(self, code):
        if QMessageBox.question(self, "Confirm", "Delete Party?") == QMessageBox.Yes:
            self.db.execute_query("DELETE FROM accounts WHERE party_code=?", (code,))
            self.load_data()

# ==========================================
# 3. ITEM MASTER TAB (With Automated Migration)
# ==========================================
class ItemTab(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.db = DatabaseManager(company_name)
        self.init_db() # migration logic inside here
        self.init_ui()
        self.load_data()

    def init_db(self):
        # 1. Ensure table exists
        self.db.execute_query("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
        
        # 2. MIGRATION CHECK: Check if 'id' column exists by attempting to select it
        try:
            self.db.fetch_all("SELECT id FROM items LIMIT 1")
        except Exception:
            # If selection fails, column 'id' is missing. Move data to new structure.
            print("MIGRATING ITEM MASTER: Adding ID column...")
            self.db.execute_query("ALTER TABLE items RENAME TO items_old")
            self.db.execute_query("CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
            self.db.execute_query("INSERT INTO items (name) SELECT name FROM items_old")
            self.db.execute_query("DROP TABLE items_old")

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        form_frame = QFrame()
        form_frame.setStyleSheet("background-color: #ecf0f1; border: 1px solid #bdc3c7; border-radius: 4px;")
        grid = QGridLayout(form_frame)
        
        self.input_item = QLineEdit()
        btn_add = QPushButton("Save Item")
        btn_add.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold;")
        btn_add.clicked.connect(self.add_item)

        grid.addWidget(QLabel("Item Name:"), 0, 0)
        grid.addWidget(self.input_item, 0, 1)
        grid.addWidget(btn_add, 0, 2)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Item Name", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(form_frame)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def add_item(self):
        name = self.input_item.text().strip().upper()
        if name and self.db.execute_query("INSERT INTO items (name) VALUES (?)", (name,)):
            self.input_item.clear()
            self.load_data()

    def load_data(self):
        self.table.setRowCount(0)
        rows = self.db.fetch_all("SELECT id, name FROM items ORDER BY name ASC")
        for r, (id_val, name) in enumerate(rows):
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(id_val)))
            self.table.setItem(r, 1, QTableWidgetItem(name))
            btn = QPushButton("Delete")
            btn.setStyleSheet("background-color: #e74c3c; color: white;")
            btn.clicked.connect(lambda ch, i=id_val: self.delete_item(i))
            self.table.setCellWidget(r, 2, btn)

    def delete_item(self, id_val):
        if QMessageBox.question(self, "Confirm", "Delete Item?") == QMessageBox.Yes:
            self.db.execute_query("DELETE FROM items WHERE id=?", (id_val,))
            self.load_data()

# ==========================================
# MAIN MASTER CONTAINER
# ==========================================
class AccountMaster(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.company_name = company_name
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.addTab(ScheduleTab(self.company_name), "Schedule Master")
        self.tabs.addTab(AccountTab(self.company_name), "Account Master")
        self.tabs.addTab(ItemTab(self.company_name), "Item Master")
        
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #bdc3c7; background: white; margin-top: -1px; }
            QTabBar::tab {
                background: #e0e0e0; color: #333; padding: 12px 20px;
                border: 1px solid #ccc; border-bottom: none;
                border-top-left-radius: 4px; border-top-right-radius: 4px;
                min-width: 150px; font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #3498db; color: white; border-bottom: 2px solid #3498db;
            }
        """)

        layout.addWidget(QLabel("<h2>Master Data Management</h2>"))
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        
    def refresh_data(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'load_data'): tab.load_data()
            if hasattr(tab, 'load_schedules'): tab.load_schedules()