import pandas as pd
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QMessageBox, QHeaderView, 
                             QTabWidget, QFrame, QAbstractItemView, QGridLayout, QFileDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from core.database import DatabaseManager
from datetime import datetime

# ==========================================
# COMMON UI STYLESHEETS
# ==========================================
COMMON_INPUT_STYLE = """
    QLineEdit, QComboBox {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 6px 10px;
        background-color: #fdfdfd;
        selection-background-color: #3498db;
    }
    QLineEdit:focus, QComboBox:focus {
        border: 1px solid #3498db;
        background-color: #ffffff;
    }
    QComboBox::drop-down { border: none; }
"""

TABLE_STYLE = """
    QTableWidget {
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        background-color: #ffffff;
        alternate-background-color: #f9fbfd;
        gridline-color: #ecf0f1;
    }
    QHeaderView::section {
        background-color: #2c3e50;
        color: #ffffff;
        padding: 8px;
        font-weight: bold;
        border: none;
        border-right: 1px solid #34495e;
    }
    QTableWidget::item:selected {
        background-color: #d6eaf8;
        color: #2c3e50;
    }
"""

CARD_STYLE = """
    QFrame { 
        background: #ffffff; 
        border: 1px solid #e0e0e0; 
        border-radius: 8px; 
    }
    QLabel { 
        border: none; 
        font-weight: bold; 
        color: #34495e; 
    }
"""

# ==========================================
# CUSTOM FAST DATE INPUT
# ==========================================
class FastDateInput(QLineEdit):
    def __init__(self, default_date=None):
        super().__init__()
        self.setPlaceholderText("dd-mm-yyyy")
        self.setText(default_date if default_date else datetime.now().strftime("%d-%m-%Y"))
        self.editingFinished.connect(self.format_date)
        self.setStyleSheet(COMMON_INPUT_STYLE)

    def format_date(self):
        txt = self.text().strip().replace("/", "-").replace(".", "-")
        if not txt: return
        try:
            if "-" in txt:
                parts = txt.split("-")
                if len(parts) == 3:
                    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                    if y < 100: y += 2000
                    self.setText(f"{d:02d}-{m:02d}-{y}")
        except: pass

# ==========================================
# 1. YARN ENTRY TAB
# ==========================================
class YarnEntryTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # --- Input Form ---
        form_frame = QFrame()
        form_frame.setStyleSheet(CARD_STYLE)
        grid = QGridLayout(form_frame)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(15)

        lbl_title = QLabel("📦 Record Yarn Stock Entry")
        lbl_title.setStyleSheet("font-size: 16px; color: #2980b9; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px;")

        self.combo_item = QComboBox()
        self.combo_item.setStyleSheet(COMMON_INPUT_STYLE)
        
        self.date_entry = FastDateInput()
        
        self.input_inv = QLineEdit()
        self.input_inv.setPlaceholderText("Invoice No.")
        self.input_inv.setStyleSheet(COMMON_INPUT_STYLE)
        
        self.input_weight = QLineEdit()
        self.input_weight.setPlaceholderText("0.00")
        self.input_weight.setStyleSheet(COMMON_INPUT_STYLE)
        
        self.input_rate = QLineEdit()
        self.input_rate.setPlaceholderText("0.00")
        self.input_rate.setStyleSheet(COMMON_INPUT_STYLE)
        
        self.input_broker = QLineEdit()
        self.input_broker.setPlaceholderText("Broker Name")
        self.input_broker.setStyleSheet(COMMON_INPUT_STYLE)
        
        self.input_main_company = QLineEdit()
        self.input_main_company.setPlaceholderText("Company Name")
        self.input_main_company.setStyleSheet(COMMON_INPUT_STYLE)
        
        self.input_del_company = QLineEdit()
        self.input_del_company.setPlaceholderText("Delivery Company")
        self.input_del_company.setStyleSheet(COMMON_INPUT_STYLE)
        
        self.date_del = FastDateInput()
        
        self.input_remark = QLineEdit()
        self.input_remark.setPlaceholderText("Optional Remarks...")
        self.input_remark.setStyleSheet(COMMON_INPUT_STYLE)

        btn_save = QPushButton("💾 Save Yarn Entry")
        btn_save.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 10px; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self.save_data)

        # Grid Placements
        grid.addWidget(lbl_title, 0, 0, 1, 5)
        grid.addWidget(QLabel("Item Name:"), 1, 0); grid.addWidget(self.combo_item, 1, 1)
        grid.addWidget(QLabel("Entry Date:"), 1, 2); grid.addWidget(self.date_entry, 1, 3)
        grid.addWidget(QLabel("Invoice:"), 2, 0); grid.addWidget(self.input_inv, 2, 1)
        grid.addWidget(QLabel("Weight (Kg):"), 2, 2); grid.addWidget(self.input_weight, 2, 3)
        grid.addWidget(QLabel("Rate (₹):"), 3, 0); grid.addWidget(self.input_rate, 3, 1)
        grid.addWidget(QLabel("Broker:"), 3, 2); grid.addWidget(self.input_broker, 3, 3)
        grid.addWidget(QLabel("Company:"), 4, 0); grid.addWidget(self.input_main_company, 4, 1)
        grid.addWidget(QLabel("Del. Company:"), 4, 2); grid.addWidget(self.input_del_company, 4, 3)
        grid.addWidget(QLabel("Del. Date:"), 5, 0); grid.addWidget(self.date_del, 5, 1)
        grid.addWidget(QLabel("Remark:"), 5, 2); grid.addWidget(self.input_remark, 5, 3)
        grid.addWidget(btn_save, 1, 4, 5, 1) # Span button across 5 rows on the far right

        # --- Action Buttons & Search ---
        action_layout = QHBoxLayout()
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search Invoice, Broker, or Company...")
        self.search_bar.setStyleSheet("""
            QLineEdit { padding: 8px 15px; border: 1px solid #3498db; border-radius: 18px; min-width: 350px; background: white; }
            QLineEdit:focus { border: 2px solid #2980b9; }
        """)
        self.search_bar.textChanged.connect(self.filter_table)
        
        btn_import = QPushButton("📥 Import Excel")
        btn_import.setStyleSheet("QPushButton { background-color: #2980b9; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; } QPushButton:hover { background-color: #3498db; }")
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.clicked.connect(self.import_excel)

        btn_clear_all = QPushButton("🗑️ Clear Displayed")
        btn_clear_all.setStyleSheet("QPushButton { background-color: #c0392b; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; } QPushButton:hover { background-color: #e74c3c; }")
        btn_clear_all.setCursor(Qt.PointingHandCursor)
        btn_clear_all.clicked.connect(self.delete_bulk)

        action_layout.addWidget(self.search_bar)
        action_layout.addStretch()
        action_layout.addWidget(btn_import)
        action_layout.addWidget(btn_clear_all)

        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(12) 
        self.table.setHorizontalHeaderLabels([
            "ID", "Item", "Date", "Invoice", "Weight", "Rate", 
            "Broker", "Company", "Del. Company", "Del. Date", "Remark", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch) # Stretch company
        self.table.setColumnHidden(0, True) 
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(TABLE_STYLE + "QTableWidget::item { padding: 5px; }")

        layout.addWidget(form_frame)
        layout.addLayout(action_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_dropdowns(self):
        self.combo_item.clear()
        items = self.db.fetch_all("SELECT name FROM items ORDER BY name ASC")
        for (name,) in items: self.combo_item.addItem(name)

    def save_data(self):
        data = (
            self.combo_item.currentText(), self.date_entry.text(), self.input_inv.text(),
            self.input_weight.text(), self.input_rate.text(), self.input_broker.text(),
            self.input_main_company.text(), self.input_del_company.text(), 
            self.date_del.text(), self.input_remark.text()
        )
        query = """INSERT INTO yarn_entries 
                   (item_name, entry_date, invoice, weight, rate, broker, 
                    company, delivery_company, delivery_date, remark) 
                   VALUES (?,?,?,?,?,?,?,?,?,?)"""
        if self.db.execute_query(query, data):
            self.input_inv.clear(); self.input_weight.clear(); self.input_rate.clear()
            self.input_main_company.clear(); self.input_remark.clear(); self.input_broker.clear()
            self.load_entries()
            self.input_inv.setFocus() # Auto focus back to invoice for fast entry

    def load_entries(self, search_term=""):
        self.table.setRowCount(0)
        
        # 1. Smart Query: Search in the database, and ALWAYS limit to the latest 25 rows
        query = """SELECT id, item_name, entry_date, invoice, weight, rate, 
                          broker, company, delivery_company, delivery_date, remark 
                   FROM yarn_entries """
        params = ()
        
        if search_term:
            query += "WHERE invoice LIKE ? OR broker LIKE ? OR company LIKE ? OR remark LIKE ? COLLATE NOCASE "
            s = f"%{search_term}%"
            params = (s, s, s, s)
            
        # CHANGED TO 25 FOR MAXIMUM SPEED
        query += "ORDER BY id DESC LIMIT 25"
        
        rows = self.db.fetch_all(query, params)
        
        from PyQt5.QtGui import QColor, QFont
        bold_font = QFont()
        bold_font.setBold(True)
        
        for r, row in enumerate(rows):
            self.table.insertRow(r)
            for c, val in enumerate(row):
                # Format Weight (4) and Rate (5)
                if c in [4, 5]:
                    try:
                        num_val = float(val or 0)
                        item = QTableWidgetItem(f"{num_val:,.2f}")
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        item.setFont(bold_font)
                        item.setForeground(QColor("#27ae60") if c == 4 else QColor("#2980b9"))
                    except:
                        item = QTableWidgetItem("0.00")
                else:
                    item = QTableWidgetItem(str(val if val is not None else ""))
                
                self.table.setItem(r, c, item)
            
            btn = QPushButton("🗑️ Delete")
            btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border-radius: 3px; padding: 4px;} QPushButton:hover { background-color: #c0392b; }")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda ch, i=row[0]: self.delete_entry(i))
            self.table.setCellWidget(r, 11, btn)

    def filter_table(self):
        # 2. Upgraded Search: Hits the database directly instead of hiding UI rows
        search_text = self.search_bar.text().strip()
        self.load_entries(search_text)

    def delete_entry(self, entry_id):
        if QMessageBox.question(self, "Confirm", "Delete this entry?") == QMessageBox.Yes:
            self.db.execute_query("DELETE FROM yarn_entries WHERE id=?", (entry_id,))
            self.load_entries()

    def delete_bulk(self):
        visible_rows = []
        for r in range(self.table.rowCount()):
            if not self.table.isRowHidden(r):
                visible_rows.append(self.table.item(r, 0).text())
        
        if not visible_rows: return
        
        msg = f"⚠️ Permanently delete ALL {len(visible_rows)} visible entries?"
        if QMessageBox.question(self, "Bulk Delete", msg, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            for eid in visible_rows:
                self.db.execute_query("DELETE FROM yarn_entries WHERE id=?", (eid,))
            self.load_entries()

    def import_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Excel", "", "Excel Files (*.xlsx *.xls)")
        if not path: return
        try:
            df = pd.read_excel(path, header=None)
            first_row = [str(x).strip().upper() for x in df.iloc[0].tolist()]
            has_header = any(x in ["DATE", "INVOICE", "WEIGHT"] for x in first_row)
            start_idx = 1 if has_header else 0
            
            item_name = self.combo_item.currentText()
            count = 0
            for i in range(start_idx, len(df)):
                row = df.iloc[i].tolist()
                def get_safe(idx): return str(row[idx]) if len(row) > idx and not pd.isna(row[idx]) else ""

                data = (
                    item_name, get_safe(0), get_safe(1), 
                    row[2] if len(row) > 2 else 0, row[3] if len(row) > 3 else 0, 
                    get_safe(4), get_safe(5), get_safe(6), get_safe(7), get_safe(8)
                )
                query = """INSERT INTO yarn_entries 
                           (item_name, entry_date, invoice, weight, rate, broker, 
                            company, delivery_company, delivery_date, remark) 
                           VALUES (?,?,?,?,?,?,?,?,?,?)"""
                if self.db.execute_query(query, data): count += 1
            
            QMessageBox.information(self, "Success", f"Imported {count} entries.")
            self.load_entries()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import: {str(e)}")

# ==========================================
# MAIN MODULE
# ==========================================
class InventoryModule(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.db = DatabaseManager(company_name)
        self.init_db()
        self.init_ui()

    def init_db(self):
        # 1. Create the base table if it doesn't exist
        self.db.execute_query("""
            CREATE TABLE IF NOT EXISTS yarn_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT, entry_date TEXT, invoice TEXT,
                weight REAL, rate REAL, broker TEXT,
                delivery_company TEXT, delivery_date TEXT
            )
        """)
        
        # 2. Silently check existing columns to avoid console spam
        try:
            columns_info = self.db.fetch_all("PRAGMA table_info(yarn_entries)")
            existing_columns = [col[1] for col in columns_info]
            
            if "company" not in existing_columns:
                self.db.execute_query("ALTER TABLE yarn_entries ADD COLUMN company TEXT")
            if "remark" not in existing_columns:
                self.db.execute_query("ALTER TABLE yarn_entries ADD COLUMN remark TEXT")
        except:
            pass

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        self.tab_entry = YarnEntryTab(self.db)
        self.tabs.addTab(self.tab_entry, "🧵 Yarn Stock Entry")
        
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #bdc3c7; background: #ffffff; border-radius: 4px; }
            QTabBar::tab {
                background: #ecf0f1; color: #7f8c8d; padding: 12px 25px;
                border: 1px solid #dcdcdc; border-bottom: none;
                border-top-left-radius: 6px; border-top-right-radius: 6px;
                min-width: 150px; font-weight: bold; font-size: 13px;
                margin-right: 2px;
            }
            QTabBar::tab:hover { background: #d6eaf8; color: #2980b9; }
            QTabBar::tab:selected {
                background: #2980b9; color: white; border: 1px solid #2980b9;
            }
        """)

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def refresh_data(self):
        self.tab_entry.load_dropdowns()
        self.tab_entry.load_entries()