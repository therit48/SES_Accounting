from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QMessageBox, QHeaderView, 
                             QTabWidget, QFrame, QAbstractItemView, QGridLayout, QCompleter)
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
        self.setStyleSheet(COMMON_INPUT_STYLE)
        if default_date: self.setText(default_date)
        else: self.setText(datetime.now().strftime("%d-%m-%Y"))
        self.editingFinished.connect(self.format_date)

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
            elif len(txt) == 6 and txt.isdigit():
                d, m, y = int(txt[:2]), int(txt[2:4]), int(txt[4:]) + 2000
                self.setText(f"{d:02d}-{m:02d}-{y}")
            elif len(txt) == 8 and txt.isdigit():
                d, m, y = int(txt[:2]), int(txt[2:4]), int(txt[4:])
                self.setText(f"{d:02d}-{m:02d}-{y}")
        except ValueError: pass

    def date_obj(self):
        try: return datetime.strptime(self.text(), "%d-%m-%Y").date()
        except: return datetime.now().date()

# ==========================================
# 1. RECEIPT VOUCHER TAB 
# ==========================================
class ReceiptTab(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.db = DatabaseManager(company_name)
        self.init_db()
        self.init_ui()
        self.load_accounts()
        self.generate_voucher_no()
        self.load_recent_entries()

    def init_db(self):
        self.db.execute_query("""
            CREATE TABLE IF NOT EXISTS receipts (
                voucher_no INTEGER PRIMARY KEY,
                date TEXT,
                account_code TEXT,
                amount REAL,
                remark TEXT,
                invoice_no TEXT
            )
        """)
        
        try:
            existing_cols = self.db.fetch_all("PRAGMA table_info(receipts)")
            col_names = [col[1] for col in existing_cols]
            if 'amount' not in col_names: self.db.execute_query("ALTER TABLE receipts ADD COLUMN amount REAL DEFAULT 0.0")
            if 'invoice_no' not in col_names: self.db.execute_query("ALTER TABLE receipts ADD COLUMN invoice_no TEXT DEFAULT ''")
        except: pass

    def init_ui(self):
        # --- NEW: Import Shortcuts locally ---
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        form_frame = QFrame()
        form_frame.setStyleSheet(CARD_STYLE)
        grid = QGridLayout(form_frame)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(15)

        lbl_title = QLabel("💵 Record Receipt Voucher")
        lbl_title.setStyleSheet("color: #27ae60; font-size: 16px; font-weight: bold; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px;")

        self.input_voucher = QLineEdit()
        self.input_voucher.setReadOnly(True)
        self.input_voucher.setStyleSheet("background-color: #f2f4f4; color: #7f8c8d; font-weight: bold; border: 1px solid #bdc3c7; border-radius: 4px; padding: 6px;")
        self.input_voucher.setAlignment(Qt.AlignCenter)
        
        self.date_picker = FastDateInput()

        self.combo_account = QComboBox()
        self.combo_account.setEditable(True) 
        self.combo_account.setInsertPolicy(QComboBox.NoInsert)
        self.combo_account.setPlaceholderText("Search Party Name...")
        self.combo_account.setStyleSheet(COMMON_INPUT_STYLE)

        self.input_inv_no = QLineEdit()
        self.input_inv_no.setPlaceholderText("Invoice / Ref No")
        self.input_inv_no.setStyleSheet(COMMON_INPUT_STYLE)

        self.input_amount = QLineEdit()
        self.input_amount.setPlaceholderText("0.00")
        self.input_amount.setAlignment(Qt.AlignRight)
        self.input_amount.setStyleSheet("font-size: 15px; font-weight: bold; color: #27ae60; background-color: #eaeded; border: 2px solid #2ecc71; border-radius: 4px; padding: 6px;")

        self.input_remark = QLineEdit()
        self.input_remark.setPlaceholderText("Enter Remarks / Narration")
        self.input_remark.setStyleSheet(COMMON_INPUT_STYLE)

        btn_save = QPushButton("💾 Save Receipt")
        btn_save.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 10px; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        btn_save.setMinimumWidth(150)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self.save_receipt)

        grid.addWidget(lbl_title, 0, 0, 1, 4)

        grid.addWidget(QLabel("Voucher No:"), 1, 0)
        grid.addWidget(self.input_voucher, 1, 1)
        grid.addWidget(QLabel("Date:"), 1, 2)
        grid.addWidget(self.date_picker, 1, 3)

        grid.addWidget(QLabel("Account:"), 2, 0)
        grid.addWidget(self.combo_account, 2, 1)
        grid.addWidget(QLabel("Inv/Ref No:"), 2, 2)
        grid.addWidget(self.input_inv_no, 2, 3)

        grid.addWidget(QLabel("Amount (₹):"), 3, 0)
        grid.addWidget(self.input_amount, 3, 1)
        grid.addWidget(QLabel("Remark:"), 3, 2)
        grid.addWidget(self.input_remark, 3, 3) 

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        grid.addLayout(btn_layout, 4, 0, 1, 4)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Voucher", "Date", "Account", "Inv/Ref", "Amount (₹)", "Remark", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(TABLE_STYLE + "QTableWidget::item { padding: 5px; }")

        layout.addWidget(form_frame)
        
        lbl_recent = QLabel("📋 Recent Receipt Entries")
        lbl_recent.setStyleSheet("font-weight: bold; color: #34495e; font-size: 14px;")
        layout.addWidget(lbl_recent)
        
        layout.addWidget(self.table)
        self.setLayout(layout)

        # --- NEW: KEYBOARD SHORTCUTS FOR 'ENTER' ---
        self.shortcut_enter = QShortcut(QKeySequence("Return"), self)
        self.shortcut_enter.activated.connect(self.save_receipt)
        
        self.shortcut_numpad = QShortcut(QKeySequence("Enter"), self)
        self.shortcut_numpad.activated.connect(self.save_receipt)

    def load_accounts(self):
        self.combo_account.clear()
        rows = self.db.fetch_all("SELECT party_code, party_name FROM accounts")
        for code, name in rows:
            self.combo_account.addItem(f"{name} ({code})", code)
        
        completer = QCompleter([f"{name} ({code})" for code, name in rows])
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.combo_account.setCompleter(completer)

    def generate_voucher_no(self):
        rows = self.db.fetch_all("SELECT MAX(voucher_no) FROM receipts")
        max_id = rows[0][0] if rows and rows[0][0] else 0
        self.input_voucher.setText(str(max_id + 1))

    def save_receipt(self):
        # --- NEW: INSTANT EMPTY FIELD CHECKS ---
        v_no = self.input_voucher.text()
        date = self.date_picker.text().strip()
        acc_text = self.combo_account.currentText().strip()
        amt_str = self.input_amount.text().strip()
        inv_no = self.input_inv_no.text()
        remark = self.input_remark.text()

        if not date:
            self.date_picker.setFocus()
            return QMessageBox.warning(self, "Missing Data", "Please enter the Date.")
        
        if not acc_text:
            self.combo_account.setFocus()
            return QMessageBox.warning(self, "Missing Data", "Please select an Account.")
            
        if not amt_str:
            self.input_amount.setFocus()
            return QMessageBox.warning(self, "Missing Data", "Please enter the Amount.")

        acc_data = self.combo_account.currentData()
        if not acc_data:
            if "(" in acc_text and ")" in acc_text: 
                acc_data = acc_text.split("(")[-1].strip(")")
        
        if not acc_data: 
            self.combo_account.setFocus()
            return QMessageBox.warning(self, "Error", "Please select a valid Account from the list.")

        try: 
            amt = float(amt_str)
        except ValueError: 
            self.input_amount.setFocus()
            self.input_amount.selectAll()
            return QMessageBox.warning(self, "Error", "Please enter a valid Amount.")

        if self.db.execute_query("INSERT INTO receipts (voucher_no, date, account_code, amount, remark, invoice_no) VALUES (?, ?, ?, ?, ?, ?)", 
                                 (v_no, date, acc_data, amt, remark, inv_no)):
            
            # --- NEW: RESET AND TELEPORT FOCUS ---
            self.input_amount.clear()
            self.input_remark.clear()
            self.input_inv_no.clear()
            self.combo_account.setCurrentText("")
            
            self.generate_voucher_no()
            self.load_recent_entries()
            
            # Teleport cursor back to the Date field!
            self.date_picker.setFocus()
            self.date_picker.selectAll()
            
        else: 
            QMessageBox.critical(self, "Error", "Database Error")

    def load_recent_entries(self):
        self.table.setRowCount(0)
        query = """
            SELECT r.voucher_no, r.date, a.party_name, r.invoice_no, r.amount, r.remark 
            FROM receipts r
            LEFT JOIN accounts a ON r.account_code = a.party_code
            ORDER BY r.voucher_no DESC LIMIT 25
        """
        rows = self.db.fetch_all(query)
        bold_font = QFont(); bold_font.setBold(True)
        
        for r, row_data in enumerate(rows):
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(row_data[0]))) 
            self.table.setItem(r, 1, QTableWidgetItem(row_data[1])) 
            self.table.setItem(r, 2, QTableWidgetItem(row_data[2])) 
            self.table.setItem(r, 3, QTableWidgetItem(str(row_data[3]))) 
            
            amt_val = float(row_data[4] if row_data[4] is not None else 0.0)
            item_amt = QTableWidgetItem(f"{amt_val:,.2f}")
            item_amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_amt.setFont(bold_font)
            item_amt.setForeground(QColor("#27ae60"))
            self.table.setItem(r, 4, item_amt) 
            
            self.table.setItem(r, 5, QTableWidgetItem(row_data[5])) 
            
            btn = QPushButton("🗑️ Delete")
            btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border-radius: 3px; padding: 4px;} QPushButton:hover { background-color: #c0392b; }")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda ch, v=row_data[0]: self.delete_entry(v))
            self.table.setCellWidget(r, 6, btn)

    def delete_entry(self, voucher_no):
        if QMessageBox.question(self, "Confirm", "Delete this receipt?") == QMessageBox.Yes:
            self.db.execute_query("DELETE FROM receipts WHERE voucher_no=?", (voucher_no,))
            self.load_recent_entries()
            self.generate_voucher_no()

# ==========================================
# 2. PAYMENT VOUCHER TAB 
# ==========================================
class PaymentTab(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.db = DatabaseManager(company_name)
        self.db.execute_query("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_code TEXT,
                invoice_no TEXT,
                invoice_date TEXT,
                quantity REAL,
                payment_date TEXT,
                rate REAL,
                grace_day INTEGER,
                interest_amt REAL
            )
        """)
        self.init_ui()
        self.load_accounts()
        self.load_recent()

    def init_ui(self):
        # --- NEW: Import Shortcuts locally ---
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        form_frame = QFrame()
        form_frame.setStyleSheet(CARD_STYLE)
        grid = QGridLayout(form_frame)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(15)

        lbl_title = QLabel("🧮 Payment Interest Calculation")
        lbl_title.setStyleSheet("color: #d35400; font-size: 16px; font-weight: bold; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px;")

        self.combo_account = QComboBox()
        self.combo_account.setEditable(True)
        self.combo_account.setInsertPolicy(QComboBox.NoInsert)
        self.combo_account.setStyleSheet(COMMON_INPUT_STYLE)

        self.input_inv_no = QLineEdit()
        self.input_inv_no.setStyleSheet(COMMON_INPUT_STYLE)
        self.input_inv_no.setPlaceholderText("Inv No.")
        
        self.date_inv = FastDateInput()
        self.date_pay = FastDateInput()
        
        self.input_qty = QLineEdit("0")
        self.input_qty.setStyleSheet(COMMON_INPUT_STYLE)
        self.input_qty.setAlignment(Qt.AlignRight)
        
        self.input_rate = QLineEdit("0.0")
        self.input_rate.setStyleSheet(COMMON_INPUT_STYLE)
        self.input_rate.setAlignment(Qt.AlignRight)
        
        self.input_grace = QLineEdit("0")
        self.input_grace.setStyleSheet(COMMON_INPUT_STYLE)
        self.input_grace.setAlignment(Qt.AlignRight)
        
        self.lbl_result = QLabel("Calculated Interest: ₹ 0.00")
        self.lbl_result.setStyleSheet("""
            font-size: 16px; font-weight: bold; color: #c0392b; 
            background-color: #fdf2e9; border: 1px solid #e67e22; 
            padding: 10px; border-radius: 6px;
        """)
        self.lbl_result.setAlignment(Qt.AlignCenter)

        btn_save = QPushButton("💾 Save Entry")
        btn_save.setStyleSheet("""
            QPushButton { background-color: #2980b9; color: white; padding: 10px; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #3498db; }
        """)
        btn_save.setMinimumWidth(150)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self.save_payment)

        # Triggers for live calculation
        self.date_inv.editingFinished.connect(self.calculate)
        self.date_pay.editingFinished.connect(self.calculate)
        self.input_qty.textChanged.connect(self.calculate)
        self.input_rate.textChanged.connect(self.calculate)
        self.input_grace.textChanged.connect(self.calculate)

        grid.addWidget(lbl_title, 0, 0, 1, 4)
        grid.addWidget(QLabel("Account:"), 1, 0)
        grid.addWidget(self.combo_account, 1, 1, 1, 3) 
        
        grid.addWidget(QLabel("Invoice No:"), 2, 0)
        grid.addWidget(self.input_inv_no, 2, 1)
        grid.addWidget(QLabel("Invoice Date:"), 2, 2)
        grid.addWidget(self.date_inv, 2, 3)
        
        grid.addWidget(QLabel("Quantity:"), 3, 0)
        grid.addWidget(self.input_qty, 3, 1)
        grid.addWidget(QLabel("Payment Date:"), 3, 2)
        grid.addWidget(self.date_pay, 3, 3)
        
        grid.addWidget(QLabel("Rate:"), 4, 0)
        grid.addWidget(self.input_rate, 4, 1)
        grid.addWidget(QLabel("Grace Days:"), 4, 2)
        grid.addWidget(self.input_grace, 4, 3)

        grid.addWidget(self.lbl_result, 5, 0, 1, 2)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        grid.addLayout(btn_layout, 5, 2, 1, 2)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Date", "Account", "Inv No", "Qty", "Rate", "Interest (₹)", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(TABLE_STYLE + "QTableWidget::item { padding: 5px; }")

        layout.addWidget(form_frame)
        
        lbl_recent = QLabel("📋 Recent Payment Entries")
        lbl_recent.setStyleSheet("font-weight: bold; color: #34495e; font-size: 14px;")
        layout.addWidget(lbl_recent)
        
        layout.addWidget(self.table)
        self.setLayout(layout)

        # --- NEW: KEYBOARD SHORTCUTS FOR 'ENTER' ---
        self.shortcut_enter = QShortcut(QKeySequence("Return"), self)
        self.shortcut_enter.activated.connect(self.save_payment)
        
        self.shortcut_numpad = QShortcut(QKeySequence("Enter"), self)
        self.shortcut_numpad.activated.connect(self.save_payment)

    def load_accounts(self):
        self.combo_account.clear()
        rows = self.db.fetch_all("SELECT party_code, party_name FROM accounts")
        for code, name in rows:
            self.combo_account.addItem(f"{name} ({code})", code)
        
        completer = QCompleter([f"{name} ({code})" for code, name in rows])
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.combo_account.setCompleter(completer)

    def calculate(self):
        try:
            d1 = self.date_inv.date_obj()
            d2 = self.date_pay.date_obj()
            delta = (d2 - d1).days
            
            qty = float(self.input_qty.text() or 0)
            rate = float(self.input_rate.text() or 0)
            grace = int(self.input_grace.text() or 0)
            
            effective_days = delta - grace - 1
            
            if effective_days > 0:
                base_val = (rate * qty * 18) / (100 * 366)
                interest = base_val * effective_days
            else:
                interest = 0.00
                
            self.lbl_result.setText(f"Calculated Interest: ₹ {interest:,.2f}  |  (Days: {effective_days})")
            return interest
        except Exception:
            self.lbl_result.setText("Invalid Math/Dates")
            return 0.0

    def save_payment(self):
        # --- NEW: INSTANT EMPTY FIELD CHECKS ---
        acc_text = self.combo_account.currentText().strip()
        inv_no = self.input_inv_no.text().strip()
        qty_str = self.input_qty.text().strip()
        rate_str = self.input_rate.text().strip()
        
        if not acc_text:
            self.combo_account.setFocus()
            return QMessageBox.warning(self, "Missing Data", "Please select an Account.")
            
        if not inv_no:
            self.input_inv_no.setFocus()
            return QMessageBox.warning(self, "Missing Data", "Please enter the Invoice Number.")
            
        if not qty_str or qty_str == "0":
            self.input_qty.setFocus()
            self.input_qty.selectAll()
            return QMessageBox.warning(self, "Missing Data", "Please enter a valid Quantity.")
            
        if not rate_str or rate_str == "0.0":
            self.input_rate.setFocus()
            self.input_rate.selectAll()
            return QMessageBox.warning(self, "Missing Data", "Please enter a valid Rate.")

        amt = self.calculate()
        acc_data = self.combo_account.currentData()
        
        if not acc_data:
            if "(" in acc_text: acc_data = acc_text.split("(")[-1].strip(")")

        if not acc_data: 
            self.combo_account.setFocus()
            return QMessageBox.warning(self, "Error", "Select a valid Account from the list.")
            
        inv_date = self.date_inv.text()
        pay_date = self.date_pay.text()
        grace = self.input_grace.text()

        query = """INSERT INTO payments 
                   (account_code, invoice_no, invoice_date, quantity, payment_date, rate, grace_day, interest_amt) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        
        if self.db.execute_query(query, (acc_data, inv_no, inv_date, qty_str, pay_date, rate_str, grace, amt)):
            # --- NEW: RESET AND TELEPORT FOCUS ---
            self.input_inv_no.clear()
            self.input_qty.setText("0")
            self.input_rate.setText("0.0")
            
            self.load_recent()
            self.calculate() # Reset the label
            
            # Teleport cursor back to Invoice No for rapid multi-entry!
            self.input_inv_no.setFocus()

    def load_recent(self):
        self.table.setRowCount(0)
        query = """
            SELECT p.id, p.payment_date, a.party_name, p.invoice_no, p.quantity, p.rate, p.interest_amt
            FROM payments p
            LEFT JOIN accounts a ON p.account_code = a.party_code
            ORDER BY p.id DESC LIMIT 25
        """
        rows = self.db.fetch_all(query)
        bold_font = QFont(); bold_font.setBold(True)
        
        for r, row in enumerate(rows):
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row[1])) 
            self.table.setItem(r, 1, QTableWidgetItem(row[2])) 
            self.table.setItem(r, 2, QTableWidgetItem(row[3])) 
            self.table.setItem(r, 3, QTableWidgetItem(str(row[4]))) 
            self.table.setItem(r, 4, QTableWidgetItem(str(row[5]))) 
            
            amt_item = QTableWidgetItem(f"{float(row[6]):,.2f}")
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amt_item.setFont(bold_font)
            amt_item.setForeground(QColor("#c0392b"))
            self.table.setItem(r, 5, amt_item) 
            
            btn = QPushButton("🗑️ Delete")
            btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border-radius: 3px; padding: 4px;} QPushButton:hover { background-color: #c0392b; }")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda ch, pid=row[0]: self.delete_payment(pid))
            self.table.setCellWidget(r, 6, btn)

    def delete_payment(self, pid):
        if QMessageBox.question(self, "Confirm", "Delete this entry?") == QMessageBox.Yes:
            self.db.execute_query("DELETE FROM payments WHERE id=?", (pid,))
            self.load_recent()

# ==========================================
# MAIN MODULE CONTAINER
# ==========================================
class TransactionModule(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.company_name = company_name
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        self.tab_receipt = ReceiptTab(self.company_name)
        self.tab_payment = PaymentTab(self.company_name)
        
        self.tabs.addTab(self.tab_receipt, "💸 Receipt Voucher")
        self.tabs.addTab(self.tab_payment, "💳 Payment Voucher (Interest)")
        
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #bdc3c7; background: #ffffff; border-radius: 4px; }
            QTabBar::tab {
                background: #ecf0f1; color: #7f8c8d; padding: 12px 25px;
                border: 1px solid #dcdcdc; border-bottom: none;
                border-top-left-radius: 6px; border-top-right-radius: 6px;
                min-width: 220px; font-weight: bold; font-size: 13px;
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
        self.tab_receipt.load_accounts()
        self.tab_receipt.load_recent_entries()
        self.tab_payment.load_accounts()
        self.tab_payment.load_recent()