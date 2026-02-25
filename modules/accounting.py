import os
import sys
import subprocess
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QMessageBox, QHeaderView, 
                             QTabWidget, QFrame, QAbstractItemView, QGridLayout, 
                             QCompleter, QFileDialog, QDialog, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from core.database import DatabaseManager
from core.utils import Utils

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER

# ==========================================
# CONSTANTS & HELPERS
# ==========================================
ACCOUNT_LABELS = [
    "REVENUE", 
    "DIRECT EXPENSES", 
    "INDIRECT REVENUE", 
    "INDIRECT EXPENSES", 
    "PERSONAL"
]

def parse_fin_year(year_str):
    if not year_str: return None, None
    try:
        parts = year_str.split('-')
        y1, y2 = int(parts[0]), int(parts[1])
        if y1 < 100: y1 += 2000
        if y2 < 100: y2 += 2000
        return datetime(y1, 4, 1).date(), datetime(y2, 3, 31).date()
    except:
        return None, None

def clean_date_to_iso(d_raw):
    if not d_raw: return ""
    parts = str(d_raw).strip().split('-')
    if len(parts) == 3:
        if len(parts[0]) == 4: return d_raw 
        return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    return d_raw

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
# 1. SUB ACCOUNT CREATION TAB
# ==========================================
class SubAccountTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_db()
        self.init_ui()
        self.load_data()

    def init_db(self):
        self.db.execute_query("CREATE TABLE IF NOT EXISTS acc_sub_accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, sub_account TEXT UNIQUE)")

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        frame = QFrame()
        frame.setStyleSheet(CARD_STYLE)
        grid = QGridLayout(frame)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(15)
        
        lbl_title = QLabel("📌 Create New Sub Account")
        lbl_title.setStyleSheet("font-size: 16px; color: #8e44ad; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px;")
        
        self.combo_label = QComboBox()
        self.combo_label.addItems(ACCOUNT_LABELS)
        self.combo_label.setStyleSheet(COMMON_INPUT_STYLE)
        
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Enter Sub Account Name...")
        self.txt_name.setStyleSheet(COMMON_INPUT_STYLE)
        
        btn_add = QPushButton("➕ Add Sub Account")
        btn_add.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self.add_sub_account)
        
        grid.addWidget(lbl_title, 0, 0, 1, 5)
        grid.addWidget(QLabel("Account Label:"), 1, 0)
        grid.addWidget(self.combo_label, 1, 1)
        grid.addWidget(QLabel("Sub Account Name:"), 1, 2)
        grid.addWidget(self.txt_name, 1, 3)
        grid.addWidget(btn_add, 1, 4)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Label", "Sub Account Name", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(TABLE_STYLE)
        
        layout.addWidget(frame)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_data(self):
        self.table.setRowCount(0)
        rows = self.db.fetch_all("SELECT id, label, sub_account FROM acc_sub_accounts ORDER BY label, sub_account")
        for r_idx, row in enumerate(rows):
            self.table.insertRow(r_idx)
            self.table.setItem(r_idx, 0, QTableWidgetItem(str(row[0])))
            self.table.setItem(r_idx, 1, QTableWidgetItem(row[1]))
            self.table.setItem(r_idx, 2, QTableWidgetItem(row[2]))
            
            btn_del = QPushButton("🗑️ Delete")
            btn_del.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border-radius: 3px; padding: 4px;} QPushButton:hover { background-color: #c0392b; }")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.clicked.connect(lambda checked, i=row[0]: self.delete_account(i))
            self.table.setCellWidget(r_idx, 3, btn_del)

    def add_sub_account(self):
        label = self.combo_label.currentText()
        name = self.txt_name.text().strip().upper()
        if not name: return QMessageBox.warning(self, "Error", "Name required!")
        try:
            self.db.execute_query("INSERT INTO acc_sub_accounts (label, sub_account) VALUES (?, ?)", (label, name))
            self.txt_name.clear()
            self.load_data()
        except: QMessageBox.warning(self, "Error", "Sub Account already exists!")

    def delete_account(self, acc_id):
        if QMessageBox.question(self, "Confirm", "Delete this Sub Account?") == QMessageBox.Yes:
            self.db.execute_query("DELETE FROM acc_sub_accounts WHERE id=?", (acc_id,))
            self.load_data()

# ==========================================
# 2. VOUCHER ENTRY TAB
# ==========================================
# ==========================================
# 2. VOUCHER ENTRY TAB
# ==========================================
class VoucherTab(QWidget):
    def __init__(self, db, get_active_year_func):
        super().__init__()
        self.db = db
        self.get_active_year = get_active_year_func 
        self.init_db()
        self.init_ui()
        self.load_dropdowns()
        self.load_data()

    def init_db(self):
        self.db.execute_query("CREATE TABLE IF NOT EXISTS acc_vouchers (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_date TEXT, amount REAL, label TEXT, sub_account TEXT, fin_year TEXT)")

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        frame = QFrame()
        frame.setStyleSheet(CARD_STYLE)
        grid = QGridLayout(frame)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(15)
        
        lbl_title = QLabel("📝 Record New Voucher")
        lbl_title.setStyleSheet("font-size: 16px; color: #2980b9; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px;")
        
        # 1. Date Input
        self.txt_date = QLineEdit()
        self.txt_date.setPlaceholderText("DD-MM-YYYY")
        self.txt_date.setStyleSheet(COMMON_INPUT_STYLE)
        
        # 2. Sub Account Input (No more Label Input!)
        self.combo_sub = QComboBox()
        self.combo_sub.setEditable(True)
        self.combo_sub.setPlaceholderText("Search Sub Account...")
        self.combo_sub.setStyleSheet(COMMON_INPUT_STYLE)
        
        # 3. Amount Input
        self.txt_amount = QLineEdit()
        self.txt_amount.setPlaceholderText("0.00")
        self.txt_amount.setStyleSheet(COMMON_INPUT_STYLE)
        
        btn_save = QPushButton("💾 Save Entry")
        btn_save.setStyleSheet("""
            QPushButton { background-color: #2980b9; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #3498db; }
        """)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self.save_voucher)
        
        # Reordered Grid Layout
        grid.addWidget(lbl_title, 0, 0, 1, 5)
        
        grid.addWidget(QLabel("Date:"), 1, 0)
        grid.addWidget(self.txt_date, 1, 1)
        grid.addWidget(QLabel("Sub Account:"), 1, 2)
        grid.addWidget(self.combo_sub, 1, 3)
        
        grid.addWidget(QLabel("Amount (₹):"), 2, 0)
        grid.addWidget(self.txt_amount, 2, 1)
        
        grid.addWidget(btn_save, 1, 4, 2, 1) # Span button across 2 rows on the right
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        # We keep "Label" in the table so you can see what the system auto-detected!
        self.table.setHorizontalHeaderLabels(["ID", "Date", "Auto-Detected Label", "Sub Account", "Amount (₹)", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(TABLE_STYLE)
        
        layout.addWidget(frame)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_dropdowns(self):
        self.combo_sub.clear()
        # Fetch ALL Sub Accounts directly, regardless of parent Label
        rows = self.db.fetch_all("SELECT sub_account FROM acc_sub_accounts ORDER BY sub_account")
        subs = [r[0] for r in rows]
        self.combo_sub.addItems(subs)
        
        comp_sub = QCompleter(subs)
        comp_sub.setCaseSensitivity(Qt.CaseInsensitive)
        comp_sub.setFilterMode(Qt.MatchContains)
        self.combo_sub.setCompleter(comp_sub)

    def load_data(self):
        self.table.setRowCount(0)
        active_year = self.get_active_year()
        rows = self.db.fetch_all("SELECT id, entry_date, label, sub_account, amount FROM acc_vouchers WHERE fin_year=? ORDER BY id DESC", (active_year,))
        for r_idx, row in enumerate(rows):
            self.table.insertRow(r_idx)
            for c in range(5):
                if c == 4:
                    item = QTableWidgetItem(f"{row[c]:,.2f}")
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setFont(QFont("", -1, QFont.Bold))
                    item.setForeground(QColor("#27ae60"))
                else:
                    item = QTableWidgetItem(str(row[c]))
                self.table.setItem(r_idx, c, item)
            
            btn_del = QPushButton("🗑️ Delete")
            btn_del.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border-radius: 3px; padding: 4px;} QPushButton:hover { background-color: #c0392b; }")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.clicked.connect(lambda checked, i=row[0]: self.delete_voucher(i))
            self.table.setCellWidget(r_idx, 5, btn_del)

    def save_voucher(self):
        active_year = self.get_active_year()
        start_dt, end_dt = parse_fin_year(active_year)
        if not start_dt: return QMessageBox.warning(self, "Error", "No valid Financial Year selected.")

        d_str = self.txt_date.text().strip()
        try:
            parts = d_str.replace('/','-').replace('.','-').split('-')
            y = int(parts[2])
            if y < 100: y += 2000
            m = int(parts[1])
            d = int(parts[0])
            
            # --- SMART CALENDAR CHECK ---
            try:
                entry_dt = datetime(y, m, d).date()
            except ValueError:
                return QMessageBox.warning(self, "Calendar Error", f"The date {d:02d}-{m:02d}-{y} does not exist!\n(Check the number of days in this month).")
            
            if not (start_dt <= entry_dt <= end_dt):
                return QMessageBox.warning(self, "Date Error", f"Date {d_str} not in active year ({active_year})!")
            
            clean_d = f"{d:02d}-{m:02d}-{y}"
            
        except Exception as e: 
            return QMessageBox.warning(self, "Error", "Invalid Date format. Please use DD-MM-YYYY.")

        try: 
            amt = float(self.txt_amount.text())
        except ValueError: 
            return QMessageBox.warning(self, "Error", "Invalid Amount.")

        sub = self.combo_sub.currentText().strip().upper()
        if not sub: 
            return QMessageBox.warning(self, "Error", "Sub Account required.")

        # --- AUTO-DETECT MAGIC ---
        # Look up the predefined Label linked to this Sub Account
        lbl_row = self.db.fetch_all("SELECT label FROM acc_sub_accounts WHERE sub_account=?", (sub,))
        
        if not lbl_row:
            return QMessageBox.warning(self, "Error", f"Sub Account '{sub}' does not exist!\nPlease create it in the 'Sub Accounts' tab first.")
        
        lbl = lbl_row[0][0] # Extracts the detected Label (e.g., 'REVENUE')

        self.db.execute_query("INSERT INTO acc_vouchers (entry_date, amount, label, sub_account, fin_year) VALUES (?, ?, ?, ?, ?)", (clean_d, amt, lbl, sub, active_year))
        
        self.txt_amount.clear()
        self.txt_amount.setFocus() # Put cursor back to amount for quick entry
        self.load_data()

    def delete_voucher(self, v_id):
        if QMessageBox.question(self, "Confirm", "Delete this Entry?") == QMessageBox.Yes:
            self.db.execute_query("DELETE FROM acc_vouchers WHERE id=?", (v_id,))
            self.load_data()

# ==========================================
# 3. P&L REPORT TAB
# ==========================================
class PnLReportTab(QWidget):
    def __init__(self, db, company_name, get_active_year_func):
        super().__init__()
        self.db = db
        self.company_name = company_name
        self.get_active_year = get_active_year_func
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        frame = QFrame()
        frame.setStyleSheet(CARD_STYLE)
        grid = QGridLayout(frame)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(15)
        
        lbl_title = QLabel("📊 Profit & Loss Statement")
        lbl_title.setStyleSheet("font-size: 16px; color: #d35400; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px;")
        
        self.txt_from = QLineEdit()
        self.txt_from.setPlaceholderText("From: DD-MM-YYYY")
        self.txt_from.setStyleSheet(COMMON_INPUT_STYLE)
        
        self.txt_to = QLineEdit()
        self.txt_to.setPlaceholderText("To: DD-MM-YYYY")
        self.txt_to.setStyleSheet(COMMON_INPUT_STYLE)
        
        btn_gen = QPushButton("🔄 Generate P&L")
        btn_gen.setStyleSheet("QPushButton { background-color: #8e44ad; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; } QPushButton:hover { background-color: #9b59b6; }")
        btn_gen.setCursor(Qt.PointingHandCursor)
        btn_gen.clicked.connect(self.generate_report)

        btn_pdf = QPushButton("📄 Export PDF")
        btn_pdf.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; } QPushButton:hover { background-color: #c0392b; }")
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.clicked.connect(self.export_pdf)

        btn_excel = QPushButton("📥 Import Excel")
        btn_excel.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; } QPushButton:hover { background-color: #2ecc71; }")
        btn_excel.setCursor(Qt.PointingHandCursor)
        btn_excel.clicked.connect(self.import_excel)

        # --- NEW: THE PERSONAL TOGGLE CHECKBOX ---
        self.chk_personal = QCheckBox("Include Personal (Owner's Cut)")
        self.chk_personal.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 5px;")
        self.chk_personal.setChecked(False) # Default to Formal P&L
        
        grid.addWidget(lbl_title, 0, 0, 1, 5)
        grid.addWidget(self.txt_from, 1, 0)
        grid.addWidget(self.txt_to, 1, 1)
        grid.addWidget(btn_gen, 1, 2)
        grid.addWidget(btn_pdf, 1, 3)
        grid.addWidget(btn_excel, 1, 4)
        
        # Add checkbox below the dates
        grid.addWidget(self.chk_personal, 2, 0, 1, 3) 
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Particulars", "Inner Amount (₹)", "Outer Amount (₹)"])

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) 
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(TABLE_STYLE + """
            QTableWidget::item { padding: 5px; }
        """)

        # --- THE SMART PERIOD LABEL ---
        self.lbl_period = QLabel("Report Period: [Not Generated Yet]")
        self.lbl_period.setStyleSheet("font-size: 13px; font-weight: bold; color: #7f8c8d; margin-top: 5px; margin-bottom: 5px;")
        self.lbl_period.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(frame)
        layout.addWidget(self.lbl_period)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.set_default_dates()

    def set_default_dates(self):
        active_year = self.get_active_year()
        if not active_year: return
        
        # This takes "24-25" and turns it into 01-04-2024 and 31-03-2025
        try:
            parts = active_year.split('-')
            start_year = 2000 + int(parts[0])
            end_year = 2000 + int(parts[1])
            
            self.txt_from.setText(f"01-04-{start_year}")
            self.txt_to.setText(f"31-03-{end_year}")
        except:
            pass

    def fetch_pnl_data(self):
        active_year = self.get_active_year()
        if not active_year: return {}

        # Fetch ALL vouchers for the year without relying on strict SQL filters
        query = "SELECT entry_date, label, sub_account, amount FROM acc_vouchers WHERE fin_year = ?"
        rows = self.db.fetch_all(query, (active_year,))

        # Smart Python Date Parser (Understands almost any format)
        def parse_date(d_str):
            txt = str(d_str).strip().replace('/', '-').replace('.', '-')
            if not txt: return None
            parts = txt.split('-')
            if len(parts) == 3:
                try:
                    y = int(parts[2])
                    if y < 100: y += 2000
                    return datetime(y, int(parts[1]), int(parts[0])).date()
                except: pass
            return None

        d_from = parse_date(self.txt_from.text())
        d_to = parse_date(self.txt_to.text())

        # Prepare empty data dictionary
        data = {lbl: {} for lbl in ACCOUNT_LABELS}
        
        for entry_date_str, lbl, sub, amt in rows:
            # 1. Smart Date Filter
            if d_from and d_to:
                row_date = parse_date(entry_date_str)
                if row_date:
                    if not (d_from <= row_date <= d_to):
                        continue # Skip this row if it's outside the date range

            # 2. Bulletproof Label Matching (Cleans hidden spaces and uppercase issues)
            lbl_clean = str(lbl).strip().upper()
            sub_clean = str(sub).strip().upper()
            
            if lbl_clean in data:
                try:
                    val = float(amt) if amt is not None else 0.0
                    # Add to existing sub-account amount, or create it if new
                    if sub_clean in data[lbl_clean]:
                        data[lbl_clean][sub_clean] += val
                    else:
                        data[lbl_clean][sub_clean] = val
                except Exception:
                    pass # Ignore rows with completely broken amounts

        return data

    def generate_report(self):
        # --- 1. STRICT DATE VALIDATION BOUNDARIES ---
        active_year = self.get_active_year()
        if not active_year: 
            return QMessageBox.warning(self, "Error", "No active Financial Year selected.")
        
        try:
            parts = active_year.split('-')
            start_year = 2000 + int(parts[0])
            end_year = 2000 + int(parts[1])
            # The strict boundary dates for the active year
            fy_start = datetime(start_year, 4, 1).date()
            fy_end = datetime(end_year, 3, 31).date()
        except:
            return QMessageBox.critical(self, "Error", "Invalid Financial Year format.")

        # Smart parser for whatever the user typed in the boxes
        def parse_date(d_str):
            txt = str(d_str).strip().replace('/', '-').replace('.', '-')
            if not txt: return None
            p = txt.split('-')
            if len(p) == 3:
                try:
                    y = int(p[2])
                    if y < 100: y += 2000
                    return datetime(y, int(p[1]), int(p[0])).date()
                except: pass
            return None

        d_from = parse_date(self.txt_from.text())
        d_to = parse_date(self.txt_to.text())

        # --- 2. OUT OF BOUNDS ERROR CATCHING ---
        if d_from:
            if d_from < fy_start:
                return QMessageBox.warning(self, "Date Error", f"The 'From' date ({d_from.strftime('%d-%m-%Y')}) cannot be before the start of the {active_year} financial year ({fy_start.strftime('%d-%m-%Y')}).")
            if d_from > fy_end:
                return QMessageBox.warning(self, "Date Error", f"The 'From' date ({d_from.strftime('%d-%m-%Y')}) cannot be after the end of the {active_year} financial year.")
                
        if d_to:
            if d_to > fy_end:
                return QMessageBox.warning(self, "Date Error", f"The 'To' date ({d_to.strftime('%d-%m-%Y')}) cannot exceed the end of the {active_year} financial year ({fy_end.strftime('%d-%m-%Y')}).")
            if d_to < fy_start:
                return QMessageBox.warning(self, "Date Error", f"The 'To' date ({d_to.strftime('%d-%m-%Y')}) cannot be before the start of the {active_year} financial year.")

        if d_from and d_to and d_from > d_to:
            return QMessageBox.warning(self, "Date Error", "The 'From' date cannot be after the 'To' date!")

        # --- 3. GENERATE THE REPORT ---
        disp_start = d_from.strftime('%d-%m-%Y') if d_from else fy_start.strftime('%d-%m-%Y')
        disp_end = d_to.strftime('%d-%m-%Y') if d_to else fy_end.strftime('%d-%m-%Y')
        
        include_personal = self.chk_personal.isChecked()
        mode_text = "(Owner's P&L - Includes Personal)" if include_personal else "(Formal P&L - Excludes Personal)"
        
        self.lbl_period.setText(f"📊 Showing Data For Period: {disp_start}   to   {disp_end}    |    {mode_text}")
        self.lbl_period.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; margin-top: 5px; margin-bottom: 5px;")

        try:
            self.table.setRowCount(0)
            data = self.fetch_pnl_data()
            
            if not data: return 

            bold_font = QFont(); bold_font.setBold(True)
            
            def add_row(col0, col1="", col2="", is_bold=False, bg_color=None, indent=False, text_color=None):
                r = self.table.rowCount()
                self.table.insertRow(r)
                
                p_text = f"      {col0}" if indent else col0 
                items = [QTableWidgetItem(str(p_text)), QTableWidgetItem(str(col1)), QTableWidgetItem(str(col2))]
                
                for i, item in enumerate(items):
                    if is_bold: item.setFont(bold_font)
                    if bg_color: item.setBackground(QColor(bg_color))
                    if text_color: item.setForeground(QColor(text_color))
                    if i > 0: item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.table.setItem(r, i, item)

            LABEL_BG = "#eaf2f8"

            tot_rev = sum(data.get("REVENUE", {}).values())
            tot_dir = sum(data.get("DIRECT EXPENSES", {}).values())
            
            for lbl in ["REVENUE", "DIRECT EXPENSES"]:
                tot = sum(data.get(lbl, {}).values())
                if tot > 0:
                    add_row(lbl, is_bold=True, bg_color=LABEL_BG, text_color="#2980b9")
                    for sub, amt in data.get(lbl, {}).items(): add_row(sub, f"{amt:,.2f}", indent=True)
                    add_row(f"Total {lbl}", "", f"{tot:,.2f}", is_bold=True, bg_color="#f8f9f9")
            
            gp = tot_rev - tot_dir
            gp_lbl = "⭐ GROSS PROFIT" if gp >= 0 else "🔻 GROSS LOSS"
            add_row(gp_lbl, "", f"{abs(gp):,.2f}", is_bold=True, bg_color="#d5f5e3" if gp>=0 else "#fadbd8", text_color="#1e8449" if gp>=0 else "#943126")

            tot_ind_rev = sum(data.get("INDIRECT REVENUE", {}).values())
            tot_ind_exp = sum(data.get("INDIRECT EXPENSES", {}).values())
            
            for lbl in ["INDIRECT REVENUE", "INDIRECT EXPENSES"]:
                tot = sum(data.get(lbl, {}).values())
                if tot > 0:
                    add_row(lbl, is_bold=True, bg_color=LABEL_BG, text_color="#2980b9")
                    for sub, amt in data.get(lbl, {}).items(): add_row(sub, f"{amt:,.2f}", indent=True)
                    add_row(f"Total {lbl}", "", f"{tot:,.2f}", is_bold=True, bg_color="#f8f9f9")

            np = gp + tot_ind_rev - tot_ind_exp
            np_lbl = "⭐⭐ NET PROFIT" if np >= 0 else "🔻🔻 NET LOSS"
            add_row(np_lbl, "", f"{abs(np):,.2f}", is_bold=True, bg_color="#abebc6" if np>=0 else "#f5b7b1", text_color="#145a32" if np>=0 else "#78281f")

            # --- THE CONDITIONAL PERSONAL LOGIC ---
            if include_personal:
                tot_pers = sum(data.get("PERSONAL", {}).values())
                if tot_pers > 0:
                    add_row("PERSONAL", is_bold=True, bg_color=LABEL_BG, text_color="#2980b9")
                    for sub, amt in data.get("PERSONAL", {}).items(): add_row(sub, f"{amt:,.2f}", indent=True)
                    add_row("Total PERSONAL", "", f"{tot_pers:,.2f}", is_bold=True, bg_color="#f8f9f9")

                fp = np - tot_pers
                fp_lbl = "🏆 FINAL PROFIT" if fp >= 0 else "💔 FINAL LOSS"
                add_row(fp_lbl, "", f"{abs(fp):,.2f}", is_bold=True, bg_color="#27ae60" if fp>=0 else "#c0392b", text_color="white")

        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"An error occurred while calculating the P&L report:\n\n{str(e)}\n\nPlease ensure your dates are correct.")

    def export_pdf(self):
        if self.table.rowCount() == 0: 
            return QMessageBox.warning(self, "Warning", "Generate report first.")
        
        reports_dir = os.path.join(Utils.get_company_path(self.company_name), "PDF_Reports")
        os.makedirs(reports_dir, exist_ok=True)
        path = os.path.join(reports_dir, f"PnL_Statement_{datetime.now().strftime('%H%M%S')}.pdf")
        
        try:
            from reportlab.lib.pagesizes import A4, portrait
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
            from reportlab.lib import colors

            doc = SimpleDocTemplate(path, pagesize=portrait(A4),
                                    rightMargin=30, leftMargin=30, topMargin=130, bottomMargin=50)
            elements = []
            
            # --- 1. TABLE DATA & STYLING ---
            # Changed to (INR) to prevent the black square Rupee symbol error
            pdf_data = [[" Particulars", "Amount (INR) "]]
            
            style_cmds = [
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                ('BACKGROUND', (0, 0), (1, 0), colors.Color(44/255, 62/255, 80/255)),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
                ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (1, 0), 8),
                ('TOPPADDING', (0, 0), (1, 0), 8),
            ]

            for r in range(self.table.rowCount()):
                raw_part_text = self.table.item(r, 0).text()
                is_bold = self.table.item(r, 0).font().bold()
                
                # Strip out UI emojis to prevent black squares
                part_text = raw_part_text.replace("⭐", "").replace("🔻", "").replace("🏆", "").replace("💔", "").strip()
                
                col1_text = self.table.item(r, 1).text().strip()
                col2_text = self.table.item(r, 2).text().strip()
                final_amt = col2_text if col2_text else col1_text
                
                if not is_bold:
                    pdf_data.append([f"      {part_text}", final_amt + " "])
                else:
                    if "TOTAL" not in part_text.upper() and "GROSS" not in part_text.upper() and "NET" not in part_text.upper() and "FINAL" not in part_text.upper():
                        pdf_data.append([f" {part_text}", ""]) 
                    else:
                        pdf_data.append([f" {part_text}", final_amt + " "])

                pdf_r = len(pdf_data) - 1 
                
                if is_bold:
                    # GROSS PROFIT / LOSS (Smart Green/Red Background)
                    if "GROSS" in part_text.upper():
                        bg_color = colors.HexColor("#27ae60") if "PROFIT" in part_text.upper() else colors.HexColor("#c0392b")
                        style_cmds.extend([
                            ('FONTNAME', (0, pdf_r), (1, pdf_r), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, pdf_r), (1, pdf_r), 11),
                            ('BACKGROUND', (0, pdf_r), (1, pdf_r), bg_color),
                            ('TEXTCOLOR', (0, pdf_r), (1, pdf_r), colors.white),
                            ('BOX', (0, pdf_r), (1, pdf_r), 0.5, colors.black), 
                            ('TOPPADDING', (0, pdf_r), (1, pdf_r), 10),
                            ('BOTTOMPADDING', (0, pdf_r), (1, pdf_r), 10),
                        ])
                    # NET / FINAL PROFIT (Smart Green/Red Background)
                    elif "NET" in part_text.upper() or "FINAL" in part_text.upper():
                        bg_color = colors.HexColor("#27ae60") if "PROFIT" in part_text.upper() else colors.HexColor("#c0392b")
                        style_cmds.extend([
                            ('FONTNAME', (0, pdf_r), (1, pdf_r), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, pdf_r), (1, pdf_r), 11),
                            ('BACKGROUND', (0, pdf_r), (1, pdf_r), bg_color),
                            ('TEXTCOLOR', (0, pdf_r), (1, pdf_r), colors.white),
                            ('BOX', (0, pdf_r), (1, pdf_r), 0.5, colors.black), 
                            ('TOPPADDING', (0, pdf_r), (1, pdf_r), 10),
                            ('BOTTOMPADDING', (0, pdf_r), (1, pdf_r), 10),
                        ])
                    # TOTALS (Italicized)
                    elif "TOTAL" in part_text.upper():
                        style_cmds.extend([
                            ('FONTNAME', (0, pdf_r), (1, pdf_r), 'Helvetica-BoldOblique'),
                            ('TOPPADDING', (0, pdf_r), (1, pdf_r), 6),
                            ('BOTTOMPADDING', (0, pdf_r), (1, pdf_r), 6),
                        ])
                    # CATEGORY HEADERS
                    else: 
                        style_cmds.extend([
                            ('FONTNAME', (0, pdf_r), (1, pdf_r), 'Helvetica-Bold'),
                            ('SPAN', (0, pdf_r), (1, pdf_r)),
                            ('TOPPADDING', (0, pdf_r), (1, pdf_r), 6),
                            ('BOTTOMPADDING', (0, pdf_r), (1, pdf_r), 6),
                        ])
                else:
                    # STANDARD ITEMS
                    style_cmds.extend([
                        ('FONTNAME', (0, pdf_r), (1, pdf_r), 'Helvetica'),
                        ('TOPPADDING', (0, pdf_r), (1, pdf_r), 4),
                        ('BOTTOMPADDING', (0, pdf_r), (1, pdf_r), 4),
                    ])

            t = Table(pdf_data, colWidths=[365, 170]) 
            t.setStyle(TableStyle(style_cmds))
            elements.append(t)
            
            # --- 2. THE HEADER & FOOTER CALLBACK ---
            def draw_header_footer(canvas, doc):
                canvas.saveState()
                
                # === THE EDGE-TO-EDGE DARK CHARCOAL HEADER ===
                canvas.setFillColor(colors.Color(44/255, 62/255, 80/255))
                canvas.rect(0, 842 - 110, 595.27, 110, fill=1, stroke=0) 
                
                canvas.setFillColor(colors.white)
                canvas.setFont("Helvetica-Bold", 24)
                canvas.drawCentredString(297.6, 842 - 35, self.company_name.upper())
                
                canvas.setFont("Helvetica-Bold", 12)
                canvas.drawCentredString(297.6, 842 - 60, "PROFIT & LOSS STATEMENT")
                
                raw_period = self.lbl_period.text()
                clean_period = raw_period.split("|")[0].replace("📊 Showing Data For Period:", "").strip()
                canvas.setFont("Helvetica", 10)
                canvas.drawCentredString(297.6, 842 - 75, f"Period: {clean_period}")
                
                canvas.setStrokeColor(colors.white)
                canvas.setLineWidth(1)
                canvas.line(170, 842 - 85, 425, 842 - 85)
                
                # === THE PARTY-WISE WATERMARK ===
                logo_path = os.path.join(Utils.get_company_path(self.company_name), "logo.png")
                if os.path.exists(logo_path):
                    from reportlab.lib.utils import ImageReader
                    try:
                        img = ImageReader(logo_path)
                        iw, ih = img.getSize()
                        aspect = iw / float(ih)
                        new_w = 400
                        new_h = 400 / aspect

                        canvas.translate(297.5, 420)
                        canvas.drawImage(logo_path, -new_w/2, -new_h/2, width=new_w, height=new_h, mask='auto')

                        canvas.setFillColor(colors.Color(1, 1, 1, alpha=0.85))
                        canvas.rect(-new_w/2, -new_h/2, new_w, new_h, fill=1, stroke=0)
                        canvas.translate(-297.5, -420) 
                    except Exception: pass
                else:
                    canvas.setFont('Helvetica-Bold', 60)
                    canvas.setFillColorRGB(0.85, 0.85, 0.85, alpha=0.25)
                    canvas.translate(297.5, 420)
                    canvas.rotate(45)
                    canvas.drawCentredString(0, 0, self.company_name.upper())
                    canvas.rotate(-45)
                    canvas.translate(-297.5, -420) 

                # === THE PARTY-WISE FOOTER ===
                page_num = canvas.getPageNumber()
                text = f"Page {page_num}  |  Profit & Loss Statement  |  Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
                canvas.setFont('Helvetica', 9)
                canvas.setFillColor(colors.dimgrey)
                canvas.setStrokeColor(colors.lightgrey)
                canvas.line(30, 30, 565, 30)
                canvas.drawRightString(565, 15, text)
                
                canvas.restoreState()

            doc.build(elements, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
            
            import sys, subprocess
            if sys.platform == "win32":
                os.startfile(path) 
            elif sys.platform == "darwin":
                subprocess.call(["open", path]) 
            else:
                subprocess.call(["xdg-open", path]) 
                
        except Exception as e: 
            QMessageBox.critical(self, "Error", f"PDF Export Failed: {str(e)}")


    def import_excel(self):
        active_year = self.get_active_year()
        if not active_year: return QMessageBox.warning(self, "Error", "No active Financial Year!")
        
        path, _ = QFileDialog.getOpenFileName(self, "Open Excel", "", "Excel (*.xlsx *.xls)")
        if not path: return
        
        try:
            df = pd.read_excel(path)
            required = ['DATE', 'AMOUNT', 'LABEL', 'SUB ACCOUNT']
            df.columns = [str(c).upper().strip() for c in df.columns]
            
            if not all(col in df.columns for col in required): return QMessageBox.warning(self, "Format Error", f"Excel must contain columns: {', '.join(required)}")
            
            count = 0
            for _, row in df.iterrows():
                try:
                    d_raw = pd.to_datetime(row['DATE']).strftime("%d-%m-%Y")
                    amt = float(row['AMOUNT'])
                    lbl = str(row['LABEL']).strip().upper()
                    sub = str(row['SUB ACCOUNT']).strip().upper()
                    
                    if lbl in ACCOUNT_LABELS:
                        try: self.db.execute_query("INSERT INTO acc_sub_accounts (label, sub_account) VALUES (?,?)", (lbl, sub))
                        except: pass
                        self.db.execute_query("INSERT INTO acc_vouchers (entry_date, amount, label, sub_account, fin_year) VALUES (?,?,?,?,?)", (d_raw, amt, lbl, sub, active_year))
                        count += 1
                except: continue
                
            QMessageBox.information(self, "Success", f"Imported {count} entries into {active_year}!")
            self.generate_report()
        except Exception as e: QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")


# ==========================================
# MAIN ACCOUNTING MODULE WRAPPER
# ==========================================
class AccountingModule(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.company_name = company_name
        self.db = DatabaseManager(company_name)
        self.active_year = None 
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        
        # Style the tabs to look colorful and modern
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
        
        get_year_func = lambda: self.active_year
        
        self.tab_sub = SubAccountTab(self.db)
        self.tab_vouchers = VoucherTab(self.db, get_year_func)
        self.tab_pnl = PnLReportTab(self.db, self.company_name, get_year_func)
        
        self.tabs.addTab(self.tab_sub, "📁 Sub Accounts")
        self.tabs.addTab(self.tab_vouchers, "✍️ Entry Vouchers")
        self.tabs.addTab(self.tab_pnl, "📈 P&L Statement")
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def set_active_year(self, year_str):
        self.active_year = year_str
        self.refresh_data()

    def refresh_data(self):
        self.tab_sub.load_data()
        self.tab_vouchers.load_dropdowns()
        self.tab_vouchers.load_data()
        self.tab_pnl.table.setRowCount(0) 

    def on_tab_changed(self):
        self.refresh_data()

PnLReportWidget = AccountingModule 

# ==========================================
# YEAR CREATION DIALOG
# ==========================================
class YearCreationDialog(QDialog):
    def __init__(self, company_name):
        super().__init__()
        self.company_name = company_name
        self.db = DatabaseManager(company_name)
        self.setWindowTitle("Create Financial Year")
        self.setFixedSize(300, 150)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setStyleSheet("background-color: white;")
        
        self.lbl_info = QLabel("Enter Financial Year (e.g., 24-25):")
        self.lbl_info.setStyleSheet("font-weight: bold; color: #2c3e50;")
        
        self.txt_year = QLineEdit()
        self.txt_year.setPlaceholderText("24-25")
        self.txt_year.setStyleSheet(COMMON_INPUT_STYLE)
        
        self.btn_save = QPushButton("Save Year")
        self.btn_save.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 8px; border-radius: 4px; } QPushButton:hover { background-color: #2ecc71; }")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_year)
        
        layout.addWidget(self.lbl_info)
        layout.addWidget(self.txt_year)
        layout.addWidget(self.btn_save)
        self.setLayout(layout)

    def save_year(self):
        year_name = self.txt_year.text().strip()
        if not year_name: return QMessageBox.warning(self, "Error", "Year name cannot be empty.")
        if "-" not in year_name: return QMessageBox.warning(self, "Format Error", "Please use the format 'YY-YY' (e.g. 24-25).")

        try:
            self.db.execute_query("CREATE TABLE IF NOT EXISTS years (id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
            self.db.execute_query("INSERT INTO years (name) VALUES (?)", (year_name,))
            QMessageBox.information(self, "Success", f"Financial Year '{year_name}' created successfully!")
            self.accept()
        except: QMessageBox.warning(self, "Error", "Failed to create year. It might already exist.")