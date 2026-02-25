from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QMessageBox, QHeaderView, 
                             QTabWidget, QFrame, QAbstractItemView, QGridLayout, 
                             QCompleter, QFileDialog)
from PyQt5.QtCore import Qt
from core.database import DatabaseManager
from core.utils import Utils
from datetime import datetime
import os
import sys
import subprocess
import pandas as pd
# Add this alongside your other ReportLab imports
from reportlab.platypus import Image as RLImage

# For PDF Export
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER

# ==========================================
# CUSTOM FAST DATE INPUT 
# ==========================================
class FastDateInput(QLineEdit):
    def __init__(self, default_date=None):
        super().__init__()
        self.setPlaceholderText("dd-mm-yyyy")
        if default_date:
            self.setText(default_date)
        else:
            self.setText(datetime.now().strftime("%d-%m-%Y"))
        
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
        except ValueError:
            pass

    def date_obj(self):
        try:
            return datetime.strptime(self.text(), "%d-%m-%Y").date()
        except:
            return datetime.now().date()

# ==========================================
# PARTY WISE REPORT TAB
# ==========================================
class PartyReportTab(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.company_name = company_name
        self.db = DatabaseManager(company_name)
        self.current_displayed_records = [] 
        self.init_ui()
        self.load_accounts()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # --- Filters Section ---
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame { background-color: #ffffff; border: 1px solid #dcdcdc; border-radius: 6px; }
            QLabel { border: none; font-weight: bold; color: #2c3e50; }
        """)
        grid = QGridLayout(filter_frame)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(15)

        lbl_title = QLabel("Party Wise Ledger Report")
        lbl_title.setStyleSheet("font-size: 16px; border-bottom: 2px solid #8e44ad; padding-bottom: 5px;")

        self.combo_account = QComboBox()
        self.combo_account.setEditable(True)
        self.combo_account.setInsertPolicy(QComboBox.NoInsert)
        self.combo_account.setStyleSheet("padding: 5px;")

        today = datetime.now()
        first_day = today.replace(day=1).strftime("%d-%m-%Y")
        
        self.date_from = FastDateInput(first_day)
        self.date_to = FastDateInput(today.strftime("%d-%m-%Y"))

        btn_generate = QPushButton("Generate Report")
        btn_generate.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_generate.setCursor(Qt.PointingHandCursor)
        btn_generate.clicked.connect(self.generate_report)

        grid.addWidget(lbl_title, 0, 0, 1, 4)
        grid.addWidget(QLabel("Account:"), 1, 0)
        grid.addWidget(self.combo_account, 1, 1, 1, 3)
        grid.addWidget(QLabel("From Date:"), 2, 0)
        grid.addWidget(self.date_from, 2, 1)
        grid.addWidget(QLabel("To Date:"), 2, 2)
        grid.addWidget(self.date_to, 2, 3)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_generate)
        grid.addLayout(btn_layout, 3, 0, 1, 4)

        # --- Action Buttons Section ---
        action_layout = QHBoxLayout()
        
        btn_pdf = QPushButton("📄 Export & Open PDF")
        btn_pdf.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.clicked.connect(self.export_pdf)

        btn_excel = QPushButton("📊 Import Data (Excel)")
        btn_excel.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_excel.setCursor(Qt.PointingHandCursor)
        btn_excel.clicked.connect(self.import_excel)

        btn_delete_all = QPushButton("🗑️ Clear Displayed Data")
        btn_delete_all.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_delete_all.setCursor(Qt.PointingHandCursor)
        btn_delete_all.clicked.connect(self.delete_bulk)

        action_layout.addWidget(btn_pdf)
        action_layout.addWidget(btn_excel)
        action_layout.addStretch()
        action_layout.addWidget(btn_delete_all) 

        # --- Report Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Invoice", "Inv Date", "Qty", "Payment Date", "Rate", "Grc", "Int Days", "Credit (Rec)", "Debit (Int)", "Balance", "Action"
        ])
        
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.Stretch) 
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(filter_frame)
        layout.addLayout(action_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_accounts(self):
        self.combo_account.clear()
        self.db.execute_query("CREATE TABLE IF NOT EXISTS accounts (party_code TEXT, party_name TEXT)")
        rows = self.db.fetch_all("SELECT party_code, party_name FROM accounts")
        for code, name in rows:
            self.combo_account.addItem(f"{name} ({code})", code)
        
        completer = QCompleter([f"{name} ({code})" for code, name in rows])
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.combo_account.setCompleter(completer)

    def generate_report(self):
        acc_data = self.combo_account.currentData()
        if not acc_data:
            text = self.combo_account.currentText()
            if "(" in text: acc_data = text.split("(")[-1].strip(")")

        if not acc_data:
            QMessageBox.warning(self, "Error", "Please select a valid Account")
            return

        d_from = self.date_from.date_obj()
        d_to = self.date_to.date_obj()

        self.table.setRowCount(0)
        raw_data = []
        self.current_displayed_records.clear() 

        # 1. Fetch Receipts (Credits)
        try:
            r_rows = self.db.fetch_all("SELECT date, voucher_no, amount, remark FROM receipts WHERE account_code=?", (acc_data,))
            for r in r_rows:
                r_date_obj = datetime.strptime(r[0], "%d-%m-%Y").date()
                if d_from <= r_date_obj <= d_to:
                    amt = r[2] if r[2] is not None else 0.0
                    raw_data.append({
                        "db_type": "receipt",
                        "db_id": r[1],  
                        "sort_date": r_date_obj,
                        "inv": f"Rcpt-{r[1]}",
                        "inv_date": "-",
                        "qty": "-",
                        "payment_date": r[0],
                        "rate": "-",
                        "grc": "-",
                        "int_days": "-",
                        "debit": 0.0,
                        "credit": amt
                    })
        except: pass 

        # 2. Fetch Payments / Interest (Debits)
        try:
            p_rows = self.db.fetch_all("SELECT payment_date, invoice_no, invoice_date, quantity, rate, grace_day, interest_amt, id FROM payments WHERE account_code=?", (acc_data,))
            for p in p_rows:
                p_date_obj = datetime.strptime(p[0], "%d-%m-%Y").date()
                if d_from <= p_date_obj <= d_to:
                    try:
                        # ===== EXACT FORMULA IMPLEMENTED =====
                        inv_date_obj = datetime.strptime(p[2], "%d-%m-%Y").date()
                        grace_val = int(p[5]) if p[5] else 0
                        # Int Days = (Payment Date - Inv Date) - Grc - 1
                        int_days = (p_date_obj - inv_date_obj).days - grace_val - 1
                    except:
                        int_days = 0

                    raw_int_amt = p[6] if p[6] is not None else 0.0
                    rounded_int = round(raw_int_amt)

                    raw_data.append({
                        "db_type": "payment",
                        "db_id": p[7], 
                        "sort_date": p_date_obj,
                        "inv": str(p[1]),
                        "inv_date": p[2],
                        "qty": str(p[3]),
                        "payment_date": p[0],
                        "rate": str(p[4]),
                        "grc": str(p[5]),
                        "int_days": str(int_days), 
                        "debit": rounded_int, 
                        "credit": 0.0
                    })
        except: pass

        raw_data.sort(key=lambda x: x["sort_date"])
        self.current_displayed_records = raw_data 

        running_balance = 0.0
        
        for r_idx, row in enumerate(raw_data):
            self.table.insertRow(r_idx)
            running_balance += (row["debit"] - row["credit"])

            cols = [
                row["inv"], row["inv_date"], row["qty"], row["payment_date"], 
                row["rate"], row["grc"], row["int_days"]
            ]
            
            for c_idx, val in enumerate(cols):
                self.table.setItem(r_idx, c_idx, QTableWidgetItem(val))
            
            item_cr = QTableWidgetItem(f"{row['credit']:,.2f}" if row["credit"] > 0 else "")
            item_cr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_cr.setForeground(Qt.darkGreen)
            self.table.setItem(r_idx, 7, item_cr)

            item_dr = QTableWidgetItem(f"{row['debit']:,.2f}" if row["debit"] > 0 else "")
            item_dr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_dr.setForeground(Qt.darkRed)
            self.table.setItem(r_idx, 8, item_dr)

            bal_suffix = " Dr" if running_balance > 0 else " Cr"
            item_bal = QTableWidgetItem(f"{abs(running_balance):,.2f}{bal_suffix}")
            item_bal.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_bal.setFont(self.get_bold_font())
            self.table.setItem(r_idx, 9, item_bal)

            btn_del = QPushButton("Delete")
            btn_del.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 3px; padding: 2px 10px;")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.clicked.connect(lambda checked, t=row['db_type'], i=row['db_id']: self.delete_single(t, i))
            self.table.setCellWidget(r_idx, 10, btn_del)

    def get_bold_font(self):
        font = self.table.font()
        font.setBold(True)
        return font

    # ==========================================
    # DELETE LOGIC
    # ==========================================
    def delete_single(self, db_type, db_id):
        confirm = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this entry?\nThis action cannot be undone.", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            if db_type == "receipt":
                self.db.execute_query("DELETE FROM receipts WHERE voucher_no=?", (db_id,))
            elif db_type == "payment":
                self.db.execute_query("DELETE FROM payments WHERE id=?", (db_id,))
            self.generate_report()

    def delete_bulk(self):
        if not self.current_displayed_records:
            QMessageBox.warning(self, "Empty", "There is no data currently displayed to delete.")
            return

        total_records = len(self.current_displayed_records)
        msg = f"⚠️ WARNING ⚠️\n\nYou are about to permanently delete ALL {total_records} records currently shown in this table.\n\nAre you absolutely sure you want to do this?"
        confirm = QMessageBox.question(self, "BULK DELETE CONFIRMATION", msg, QMessageBox.Yes | QMessageBox.No)
        
        if confirm == QMessageBox.Yes:
            receipts_deleted = 0
            payments_deleted = 0
            
            for record in self.current_displayed_records:
                if record["db_type"] == "receipt":
                    if self.db.execute_query("DELETE FROM receipts WHERE voucher_no=?", (record["db_id"],)):
                        receipts_deleted += 1
                elif record["db_type"] == "payment":
                    if self.db.execute_query("DELETE FROM payments WHERE id=?", (record["db_id"],)):
                        payments_deleted += 1

            QMessageBox.information(self, "Bulk Delete Complete", f"Successfully deleted:\n- {receipts_deleted} Receipts\n- {payments_deleted} Payments/Interest")
            self.generate_report()

    # ==========================================
    # PDF & EXCEL
    # ==========================================
    def export_pdf(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Warning", "No data to export. Generate a report first.")
            return

        full_party_name = self.combo_account.currentText()
        file_party_name = full_party_name.split('(')[0].strip()
        
        reports_dir = os.path.join(Utils.get_company_path(self.company_name), "PDF_Reports")
        os.makedirs(reports_dir, exist_ok=True) 
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"Ledger_{file_party_name.replace(' ', '_')}_{timestamp}.pdf"
        path = os.path.join(reports_dir, file_name)

        try:
            doc = SimpleDocTemplate(path, pagesize=landscape(letter),
                                    rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=40)
            elements = []
            
            styles = getSampleStyleSheet()
            title_center = ParagraphStyle('TitleCenter', parent=styles['Normal'], fontSize=22, textColor=colors.HexColor("#2c3e50"), fontName='Helvetica-Bold', alignment=TA_CENTER)
            sub_left = ParagraphStyle('SubLeft', parent=styles['Normal'], fontSize=11, textColor=colors.dimgrey, spaceTop=5)
            sub_right = ParagraphStyle('SubRight', parent=styles['Normal'], fontSize=12, textColor=colors.black, alignment=TA_RIGHT, spaceTop=5)

            # ==========================================
            # 1. CLEAN TEXT HEADER
            # ==========================================
            header_data = [
                [Paragraph(self.company_name.upper(), title_center), ""], 
                [Paragraph(f"<b>Period:</b> {self.date_from.text()}  to  {self.date_to.text()}", sub_left), 
                 Paragraph(f"<b>Account:</b> {full_party_name}", sub_right)]
            ]
            
            header_table = Table(header_data, colWidths=[365, 365]) 
            header_table.setStyle(TableStyle([
                ('SPAN', (0, 0), (1, 0)),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 0),
                ('LINEBELOW', (0, 1), (-1, 1), 2, colors.HexColor("#2c3e50")), 
            ]))
            
            elements.append(header_table)
            elements.append(Spacer(1, 20)) 

            # ==========================================
            # 2. TABLE DATA (WITH TRANSPARENT ROWS)
            # ==========================================
            data = [["Invoice", "Inv Date", "Qty", "Payment Date", "Rate", "Grc", "Int Days", "Credit (Rs)", "Debit (Rs)", "Balance"]]
            
            total_dr = 0.0
            total_cr = 0.0

            style_cmds = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2980b9")), 
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (7, 1), (-1, -1), 'RIGHT'), 
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
            ]

            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(10):
                    val = self.table.item(row, col).text()
                    row_data.append(val)
                data.append(row_data)

                pdf_row_idx = row + 1 

                # ✨ MAGIC FIX: Make alternating rows slightly transparent grey, and leave others 100% transparent!
                if pdf_row_idx % 2 == 0:
                    bg_color = colors.Color(0.95, 0.96, 0.98, alpha=0.7) 
                    style_cmds.append(('BACKGROUND', (0, pdf_row_idx), (-1, pdf_row_idx), bg_color))

                cr_val = row_data[7].replace(',', '') if row_data[7] else '0'
                dr_val = row_data[8].replace(',', '') if row_data[8] else '0'
                
                if float(cr_val) > 0:
                    style_cmds.append(('TEXTCOLOR', (7, pdf_row_idx), (7, pdf_row_idx), colors.HexColor("#27ae60")))
                if float(dr_val) > 0:
                    style_cmds.append(('TEXTCOLOR', (8, pdf_row_idx), (8, pdf_row_idx), colors.HexColor("#c0392b")))

                total_cr += float(cr_val)
                total_dr += float(dr_val)

            final_bal = total_dr - total_cr
            bal_suffix = " Dr" if final_bal > 0 else " Cr"
            data.append(["", "", "", "", "", "", "TOTALS:", f"{total_cr:,.2f}", f"{total_dr:,.2f}", f"{abs(final_bal):,.2f}{bal_suffix}"])
            
            total_row_idx = len(data) - 1
            style_cmds.extend([
                ('FONTNAME', (6, total_row_idx), (-1, total_row_idx), 'Helvetica-Bold'),
                ('BACKGROUND', (0, total_row_idx), (-1, total_row_idx), colors.HexColor("#fdedbd")), 
                ('TEXTCOLOR', (0, total_row_idx), (-1, total_row_idx), colors.black),
                ('BOTTOMPADDING', (0, total_row_idx), (-1, total_row_idx), 10),
                ('TOPPADDING', (0, total_row_idx), (-1, total_row_idx), 10),
            ])

            table = Table(data, colWidths=[85, 65, 40, 75, 45, 35, 55, 80, 80, 100])
            table.setStyle(TableStyle(style_cmds))
            elements.append(table)

            # ==========================================
            # 3. WATERMARK & FADING LOGIC
            # ==========================================
            def add_page_number(canvas, doc):
                canvas.saveState()
                logo_path = os.path.join(Utils.get_company_path(self.company_name), "logo.png")
                
                if os.path.exists(logo_path):
                    from reportlab.lib.utils import ImageReader
                    try:
                        img = ImageReader(logo_path)
                        iw, ih = img.getSize()
                        aspect = iw / float(ih)
                        
                        new_w = 400
                        new_h = 400 / aspect
                        
                        # Move to dead center of Landscape Letter (792x612)
                        canvas.translate(396, 306)
                        
                        # 1. Draw the full-color image
                        canvas.drawImage(logo_path, -new_w/2, -new_h/2, width=new_w, height=new_h, mask='auto')
                        
                        # ✨ MAGIC FIX: Draw a semi-transparent white box over the image to fade it!
                        canvas.setFillColor(colors.Color(1, 1, 1, alpha=0.60)) # 85% opacity white
                        canvas.rect(-new_w/2, -new_h/2, new_w, new_h, fill=1, stroke=0)
                    except Exception:
                        pass
                else:
                    # Fallback Text Watermark if no logo is uploaded
                    canvas.setFont('Helvetica-Bold', 65)
                    canvas.setFillColorRGB(0.85, 0.85, 0.85, alpha=0.25)
                    canvas.translate(396, 306)
                    canvas.rotate(45)
                    canvas.drawCentredString(0, 0, self.company_name.upper()) 
                    
                canvas.restoreState()

                # Draw the Standard Footer
                page_num = canvas.getPageNumber()
                text = f"Page {page_num}  |  Ledger: {file_party_name}  |  Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
                canvas.saveState()
                canvas.setFont('Helvetica', 9)
                canvas.setFillColor(colors.dimgrey)
                canvas.setStrokeColor(colors.lightgrey)
                canvas.line(30, 30, 760, 30)
                canvas.drawRightString(760, 15, text)
                canvas.restoreState()

            doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
            
            import sys
            if sys.platform == "win32":
                os.startfile(path) 
            elif sys.platform == "darwin":
                import subprocess
                subprocess.call(["open", path]) 
            else:
                import subprocess
                subprocess.call(["xdg-open", path]) 

        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def import_excel(self):
        acc_data = self.combo_account.currentData()
        if not acc_data:
            QMessageBox.warning(self, "Error", "Please select an Account to import data into.")
            return

        path, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel Files (*.xlsx *.xls)")
        if not path: return

        try:
            df = pd.read_excel(path, header=None)
            
            self.db.execute_query("CREATE TABLE IF NOT EXISTS receipts (voucher_no INTEGER PRIMARY KEY, date TEXT, account_code TEXT, amount REAL, remark TEXT)")
            self.db.execute_query("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, account_code TEXT, invoice_no TEXT, invoice_date TEXT, quantity REAL, payment_date TEXT, rate REAL, grace_day INTEGER, interest_amt REAL)")
            
            v_rows = self.db.fetch_all("SELECT MAX(voucher_no) FROM receipts")
            v_no = v_rows[0][0] if v_rows and v_rows[0][0] else 0

            first_row = [str(x).strip().upper() for x in df.iloc[0].tolist()]
            expected_headers = ['DATE', 'INVOICE', 'INV NO', 'INVOICE NO', 'INV DATE', 'INVOICE DATE', 
                                'QTY', 'QUANTITY', 'PAYMENT DATE', 'RATE', 'GRC', 'GRACE', 'GRACE DAYS', 
                                'INT DAYS', 'INT DAY', 'DAYS', 'CREDIT', 'DEBIT', 'AMOUNT', 'REMARK', 'REMARKS']
            
            has_header = any(cell in expected_headers for cell in first_row)
            
            if has_header:
                df.columns = first_row
                df = df[1:].reset_index(drop=True)
            else:
                num_cols = len(df.columns)
                if num_cols >= 8:
                    standard = ['INVOICE', 'INV DATE', 'QTY', 'PAYMENT DATE', 'RATE', 'GRC', 'INT DAYS', 'CREDIT', 'DEBIT', 'REMARK']
                else:
                    standard = ['PAYMENT DATE', 'CREDIT', 'DEBIT', 'REMARK']
                
                new_cols = []
                for i in range(num_cols):
                    if i < len(standard): new_cols.append(standard[i])
                    else: new_cols.append(f"UNKNOWN_{i}")
                df.columns = new_cols

            count_receipts = 0
            count_payments = 0

            for index, row in df.iterrows():
                try:
                    def get_val(col_names, default=""):
                        for c in col_names:
                            if c in df.columns:
                                val = row[c]
                                if pd.isna(val): return default
                                return val
                        return default

                    def parse_num(val):
                        if pd.isna(val) or val == "": return 0.0
                        if isinstance(val, (int, float)): return float(val)
                        clean_str = str(val).replace(',', '').replace('₹', '').replace('Rs', '').replace(' ', '').strip()
                        try: return float(clean_str)
                        except: return 0.0

                    inv_no = str(get_val(['INVOICE', 'INV NO', 'INVOICE NO'], ''))
                    remark = str(get_val(['REMARK', 'REMARKS'], 'Excel Import'))
                    
                    pay_date_raw = get_val(['PAYMENT DATE', 'DATE'])
                    pay_date_obj = pd.to_datetime(pay_date_raw) if pay_date_raw else datetime.now()
                    pay_date = pay_date_obj.strftime("%d-%m-%Y")
                    
                    inv_date_raw = get_val(['INV DATE', 'INVOICE DATE'])
                    int_days = int(parse_num(get_val(['INT DAYS', 'INT DAY', 'DAYS'])))
                    grace = int(parse_num(get_val(['GRC', 'GRACE', 'GRACE DAYS'])))
                    
                    # ===== REVERSE CALCULATION LOGIC FIX =====
                    if inv_date_raw:
                        inv_date = pd.to_datetime(inv_date_raw).strftime("%d-%m-%Y")
                    elif int_days > 0:
                        # Since Int Days = (Pay - Inv) - Grc - 1
                        # Then Inv = Pay - (Int Days + Grc + 1)
                        total_days_back = int_days + grace + 1
                        i_date_obj = pay_date_obj - pd.Timedelta(days=total_days_back)
                        inv_date = i_date_obj.strftime("%d-%m-%Y")
                    else:
                        inv_date = ""

                    qty = parse_num(get_val(['QTY', 'QUANTITY']))
                    rate = parse_num(get_val(['RATE']))
                    
                    credit = parse_num(get_val(['CREDIT', 'CREDIT COLUMN', 'AMOUNT']))
                    debit = parse_num(get_val(['DEBIT', 'DEBIT COLUMN', 'INTEREST']))

                    if credit > 0:
                        v_no += 1
                        r_remark = remark if remark != 'Excel Import' else (inv_no if inv_no else 'Excel Import')
                        self.db.execute_query("INSERT INTO receipts (voucher_no, date, account_code, amount, remark) VALUES (?, ?, ?, ?, ?)",
                                              (v_no, pay_date, acc_data, credit, r_remark))
                        count_receipts += 1

                    if debit > 0 or qty > 0:
                        self.db.execute_query("""INSERT INTO payments 
                                               (account_code, invoice_no, invoice_date, quantity, payment_date, rate, grace_day, interest_amt) 
                                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                              (acc_data, inv_no, inv_date, qty, pay_date, rate, grace, debit))
                        count_payments += 1

                except Exception:
                    continue
            
            total = count_receipts + count_payments
            if total > 0:
                QMessageBox.information(self, "Import Success", f"Successfully imported:\n✔️ {count_receipts} Credit Entries\n✔️ {count_payments} Debit Entries")
                self.generate_report()
            else:
                QMessageBox.warning(self, "No Data Found", "No valid Credit or Debit entries were found.\nPlease verify your Excel file formatting.")

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to read Excel.\nError: {str(e)}")


# ==========================================
# YARN INVENTORY REPORT TAB
# ==========================================
# ==========================================
# YARN INVENTORY REPORT TAB (PDF + IMPORT)
# ==========================================
# ==========================================
# YARN INVENTORY REPORT TAB (UPDATED)
# ==========================================
# ==========================================
# YARN INVENTORY REPORT TAB (UPDATED & FIXED)
# ==========================================
class YarnReportTab(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.company_name = company_name
        self.db = DatabaseManager(company_name)
        self.current_displayed_ids = []  # Track IDs for bulk deletion
        self.init_ui()
        self.load_items()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # --- Filters Section ---
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame { background-color: #ffffff; border: 1px solid #dcdcdc; border-radius: 6px; }
            QLabel { border: none; font-weight: bold; color: #2c3e50; }
        """)
        grid = QGridLayout(filter_frame)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(15)

        lbl_title = QLabel("Yarn Inventory Monthly Summary")
        lbl_title.setStyleSheet("font-size: 16px; border-bottom: 2px solid #27ae60; padding-bottom: 5px;")

        self.combo_item = QComboBox()
        self.combo_item.setEditable(True)
        
        self.date_from = FastDateInput("01-01-2026")
        self.date_to = FastDateInput(datetime.now().strftime("%d-%m-%Y"))

        btn_generate = QPushButton("Generate Report")
        btn_generate.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_generate.setCursor(Qt.PointingHandCursor)
        btn_generate.clicked.connect(self.generate_report)

        grid.addWidget(lbl_title, 0, 0, 1, 4)
        grid.addWidget(QLabel("Item Name:"), 1, 0)
        grid.addWidget(self.combo_item, 1, 1, 1, 3)
        grid.addWidget(QLabel("From Date:"), 2, 0)
        grid.addWidget(self.date_from, 2, 1)
        grid.addWidget(QLabel("To Date:"), 2, 2)
        grid.addWidget(self.date_to, 2, 3)
        grid.addWidget(btn_generate, 3, 3)

        # --- Action Buttons Section ---
        action_layout = QHBoxLayout()
        
        btn_pdf = QPushButton("📄 Export PDF")
        btn_pdf.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_pdf.clicked.connect(self.export_pdf)

        btn_import = QPushButton("📊 Import Excel")
        btn_import.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_import.clicked.connect(self.import_inventory_excel)

        btn_delete_all = QPushButton("🗑️ Clear Displayed Data")
        btn_delete_all.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_delete_all.clicked.connect(self.delete_bulk)

        action_layout.addWidget(btn_pdf)
        action_layout.addWidget(btn_import)
        action_layout.addStretch()
        action_layout.addWidget(btn_delete_all)

        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(10) # 9 data columns + 1 Action column
        self.table.setHorizontalHeaderLabels([
            "Date", "Invoice", "Weight", "Rate", "Broker", "Delivery", "Company", "Del. Date", "Remark", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch) # Stretch Company column
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(filter_frame)
        layout.addLayout(action_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_items(self):
        self.combo_item.clear()
        self.combo_item.addItem("--- ALL ITEMS ---", "ALL")
        rows = self.db.fetch_all("SELECT name FROM items ORDER BY name ASC")
        for (name,) in rows: self.combo_item.addItem(name, name)

    def generate_report(self):
        from PyQt5.QtGui import QColor, QFont
        item_filter = self.combo_item.currentText().strip()
        d_from, d_to = self.date_from.text(), self.date_to.text()
        
        try:
            def to_iso(d):
                parts = d.split('-')
                return f"{parts[2]}-{parts[1]}-{parts[0]}" if len(parts[0]) == 2 else d
            
            iso_from = to_iso(d_from)
            iso_to = to_iso(d_to)
        except Exception as e:
            print(f"Date Parsing Error: {e}")
            return

        query = """
            SELECT entry_date, invoice, weight, rate, broker, 
                   delivery_company, company, delivery_date, remark, id
            FROM yarn_entries
            WHERE (
                CASE 
                    WHEN entry_date LIKE '__-__-____' THEN 
                        substr(entry_date,7,4)||'-'||substr(entry_date,4,2)||'-'||substr(entry_date,1,2)
                    ELSE entry_date 
                END
            ) BETWEEN ? AND ?
        """
        params = [iso_from, iso_to]
        
        if item_filter != "--- ALL ITEMS ---":
            query += " AND item_name = ? COLLATE NOCASE"
            params.append(item_filter)

        query += """ ORDER BY 
            CASE WHEN entry_date LIKE '__-__-____' THEN 
                substr(entry_date,7,4)||'-'||substr(entry_date,4,2)||'-'||substr(entry_date,1,2)
            ELSE entry_date END ASC
        """
        
        rows = self.db.fetch_all(query, tuple(params))

        self.table.setRowCount(0)
        self.current_displayed_ids.clear()
        
        if not rows:
            return

        bold_font = QFont()
        bold_font.setBold(True)
        
        current_month = None
        m_w, m_r_sum, m_c = 0.0, 0.0, 0
        g_w, g_r_sum, g_c = 0.0, 0.0, 0

        # --- NEW DATE CLEANER HELPER ---
        def clean_date(d_raw):
            if not d_raw: return ""
            d_str = str(d_raw).strip().split(' ')[0] # Remove 00:00:00
            parts = d_str.replace('/','-').replace('.','-').split('-')
            if len(parts) == 3:
                if len(parts[0]) == 4: # YYYY-MM-DD to DD-MM-YYYY
                    return f"{parts[2].zfill(2)}-{parts[1].zfill(2)}-{parts[0]}"
                else: # D-M-YY to DD-MM-YYYY
                    y = parts[2]
                    if len(y) == 2: y = "20" + y
                    return f"{parts[0].zfill(2)}-{parts[1].zfill(2)}-{y}"
            return d_str

        def insert_summary(label, weight, rate_sum, count, is_grand=False):
            r_idx = self.table.rowCount()
            self.table.insertRow(r_idx)
            avg = rate_sum / count if count > 0 else 0
            bg = QColor("#f1c40f") if is_grand else QColor("#ecf0f1")
            
            for c in range(10):
                text = ""
                if c == 0: text = label
                elif c == 2: text = f"{weight:,.2f}"
                elif c == 3: text = f"{avg:,.2f} (Avg)"
                
                item = QTableWidgetItem(text)
                item.setBackground(bg)
                item.setFont(bold_font)
                if c in [2, 3]: item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r_idx, c, item)

        for row in rows:
            clean_entry_date = clean_date(row[0])
            this_m = clean_entry_date[3:10] # Safely grab MM-YYYY
            
            if current_month and this_m != current_month:
                insert_summary(f"TOTAL ({current_month})", m_w, m_r_sum, m_c)
                m_w, m_r_sum, m_c = 0.0, 0.0, 0
            
            current_month = this_m
            r = self.table.rowCount()
            self.table.insertRow(r)
            
            for c in range(9):
                raw_val = row[c]
                if c in [0, 7]: # Clean Date columns
                    item = QTableWidgetItem(clean_date(raw_val))
                elif c in [2, 3]: # Numbers
                    try:
                        val = float(raw_val or 0)
                        item = QTableWidgetItem(f"{val:,.2f}")
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    except:
                        item = QTableWidgetItem("0.00")
                else: # Everything else
                    item = QTableWidgetItem(str(raw_val if raw_val is not None else ""))
                
                self.table.setItem(r, c, item)
            
            btn_del = QPushButton("Delete")
            btn_del.setFixedWidth(60)
            btn_del.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; border-radius: 2px;")
            entry_id = row[9] 
            btn_del.clicked.connect(lambda checked, i=entry_id: self.delete_single(i))
            self.table.setCellWidget(r, 9, btn_del)

            try:
                w_val = float(row[2] or 0)
                r_val = float(row[3] or 0)
            except (ValueError, TypeError):
                w_val, r_val = 0.0, 0.0

            m_w += w_val; m_r_sum += r_val; m_c += 1
            g_w += w_val; g_r_sum += r_val; g_c += 1
            self.current_displayed_ids.append(entry_id)

        if current_month:
            insert_summary(f"TOTAL ({current_month})", m_w, m_r_sum, m_c)
            insert_summary("GRAND TOTAL", g_w, g_r_sum, g_c, True)
            
    def delete_single(self, db_id):
        if QMessageBox.question(self, "Confirm", "Delete this entry?") == QMessageBox.Yes:
            self.db.execute_query("DELETE FROM yarn_entries WHERE id=?", (db_id,))
            self.generate_report()

    def delete_bulk(self):
        if not self.current_displayed_ids: return
        msg = f"⚠️ Permanent Delete {len(self.current_displayed_ids)} displayed entries?"
        if QMessageBox.question(self, "Bulk Delete", msg) == QMessageBox.Yes:
            for eid in self.current_displayed_ids:
                self.db.execute_query("DELETE FROM yarn_entries WHERE id=?", (eid,))
            self.generate_report()

    def export_pdf(self):
        item_filter = self.combo_item.currentText().strip()
        d_from, d_to = self.date_from.text(), self.date_to.text()
        
        # 1. Use the safe date parsing logic (same as generate_report)
        try:
            def to_iso(d):
                parts = d.split('-')
                return f"{parts[2]}-{parts[1]}-{parts[0]}" if len(parts[0]) == 2 else d
            
            iso_from = to_iso(d_from)
            iso_to = to_iso(d_to)
        except Exception as e:
            QMessageBox.warning(self, "Date Error", f"Invalid date format: {e}")
            return
        
        # 2. Use the robust SQL query (same as generate_report)
        query = """
            SELECT entry_date, invoice, weight, rate, broker, 
                   delivery_company, company, delivery_date, remark
            FROM yarn_entries
            WHERE (
                CASE 
                    WHEN entry_date LIKE '__-__-____' THEN 
                        substr(entry_date,7,4)||'-'||substr(entry_date,4,2)||'-'||substr(entry_date,1,2)
                    ELSE entry_date 
                END
            ) BETWEEN ? AND ?
        """
        params = [iso_from, iso_to]
        if item_filter != "--- ALL ITEMS ---":
            query += " AND item_name = ? COLLATE NOCASE"
            params.append(item_filter)
        
        query += """ ORDER BY 
            CASE WHEN entry_date LIKE '__-__-____' THEN 
                substr(entry_date,7,4)||'-'||substr(entry_date,4,2)||'-'||substr(entry_date,1,2)
            ELSE entry_date END ASC
        """
        
        details = self.db.fetch_all(query, tuple(params))

        if not details:
            QMessageBox.warning(self, "No Data", "No records found.")
            return

        reports_dir = os.path.join(Utils.get_company_path(self.company_name), "PDF_Reports")
        os.makedirs(reports_dir, exist_ok=True)
        path = os.path.join(reports_dir, f"Yarn_Report_{datetime.now().strftime('%H%M%S')}.pdf")
        
        try:
            doc = SimpleDocTemplate(path, pagesize=landscape(letter), 
                                    rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=40)
            elements = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle('TitleCenter', parent=styles['Normal'], fontSize=22, 
                                       textColor=colors.HexColor("#2c3e50"), fontName='Helvetica-Bold', alignment=TA_CENTER)
            sub_left = ParagraphStyle('SubLeft', parent=styles['Normal'], fontSize=11, textColor=colors.dimgrey)
            sub_right = ParagraphStyle('SubRight', parent=styles['Normal'], fontSize=12, textColor=colors.black, alignment=TA_RIGHT)

            header_data = [
                [Paragraph(self.company_name.upper(), title_style), ""], 
                [Paragraph(f"<b>Period:</b> {d_from} to {d_to}", sub_left), 
                 Paragraph(f"<b>Item:</b> {item_filter}", sub_right)]
            ]
            
            header_table = Table(header_data, colWidths=[365, 365]) 
            header_table.setStyle(TableStyle([
                ('SPAN', (0, 0), (1, 0)),
                ('LINEBELOW', (0, 1), (-1, 1), 2, colors.HexColor("#2c3e50")),
                ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 20))

            data = [["Date", "Invoice", "Weight", "Rate", "Broker", "Delivery", "Company", "Del. Date", "Remark"]]
            current_month, m_w, m_r_sum, m_c = None, 0.0, 0.0, 0
            g_w, g_r_sum, g_c = 0.0, 0.0, 0
            
            style_cmds = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2980b9")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (2, 1), (3, -1), 'RIGHT'), 
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8)
            ]

            # Date Cleaner Helper
            def clean_date(d_raw):
                if not d_raw: return ""
                d_str = str(d_raw).strip().split(' ')[0]
                parts = d_str.replace('/','-').replace('.','-').split('-')
                if len(parts) == 3:
                    if len(parts[0]) == 4: return f"{parts[2].zfill(2)}-{parts[1].zfill(2)}-{parts[0]}"
                    y = parts[2]
                    if len(y) == 2: y = "20" + y
                    return f"{parts[0].zfill(2)}-{parts[1].zfill(2)}-{y}"
                return d_str

            for row in details:
                clean_entry_date = clean_date(row[0])
                this_month = clean_entry_date[3:10]
                
                if current_month and this_month != current_month:
                    avg = m_r_sum / m_c if m_c > 0 else 0
                    data.append([f"TOTAL ({current_month})", "MONTHLY", f"{m_w:,.2f}", f"{avg:,.2f}", "", "", "", "", ""])
                    idx = len(data)-1
                    style_cmds.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor("#f8f9fa")))
                    style_cmds.append(('FONTNAME', (0, idx), (-1, idx), 'Helvetica-Bold'))
                    m_w, m_r_sum, m_c = 0.0, 0.0, 0

                current_month = this_month
                r_list = list(row)
                r_list[0] = clean_entry_date # Cleaned Date
                r_list[2] = f"{float(row[2]):,.2f}" 
                r_list[3] = f"{float(row[3]):,.2f}" 
                r_list[7] = clean_date(r_list[7]) # Cleaned Del Date
                r_list = [str(item) if item is not None else "" for item in r_list]
                data.append(r_list)
                
                m_w += row[2]; m_r_sum += row[3]; m_c += 1
                g_w += row[2]; g_r_sum += row[3]; g_c += 1

            if current_month:
                avg = m_r_sum / m_c if m_c > 0 else 0
                data.append([f"TOTAL ({current_month})", "MONTHLY", f"{m_w:,.2f}", f"{avg:,.2f}", "", "", "", "", ""])
                style_cmds.append(('BACKGROUND', (0, len(data)-1), (-1, len(data)-1), colors.HexColor("#f8f9fa")))
                style_cmds.append(('FONTNAME', (0, len(data)-1), (-1, len(data)-1), 'Helvetica-Bold'))

            g_avg = g_r_sum / g_c if g_c > 0 else 0
            data.append(["GRAND TOTAL", "PERIOD", f"{g_w:,.2f}", f"{g_avg:,.2f}", "", "", "", "", ""])
            style_cmds.append(('BACKGROUND', (0, len(data)-1), (-1, len(data)-1), colors.HexColor("#fdedbd")))
            style_cmds.append(('FONTNAME', (0, len(data)-1), (-1, len(data)-1), 'Helvetica-Bold'))

            t = Table(data, colWidths=[70, 60, 65, 55, 80, 100, 100, 70, 130])
            t.setStyle(TableStyle(style_cmds))
            elements.append(t)

            def add_footer(canvas, doc):
                canvas.saveState()
                canvas.setFont('Helvetica', 9)
                canvas.setFillColor(colors.dimgrey)
                canvas.line(30, 30, 760, 30)
                canvas.drawRightString(760, 15, f"Page {canvas.getPageNumber()}  |  SES Inventory Report  |  Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
                canvas.restoreState()

            doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
            
            if sys.platform == "win32": os.startfile(path)
            else: subprocess.call(["open", path])

        except Exception as e:
            QMessageBox.critical(self, "PDF Error", f"Failed: {str(e)}")

    def import_inventory_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Excel", "", "Excel Files (*.xlsx *.xls)")
        if not path: return
        
        try:
            df = pd.read_excel(path, header=None)
            
            first_row = [str(x).strip().upper() for x in df.iloc[0].tolist()]
            has_header = any(x in ["DATE", "INVOICE", "WEIGHT", "RATE"] for x in first_row)
            start_row = 1 if has_header else 0
            
            item_filter = self.combo_item.currentText().strip()
            
            if item_filter == "--- ALL ITEMS ---" or not item_filter:
                QMessageBox.warning(self, "Item Required", "Please select a specific Item Name first.")
                return

            # --- NEW DATE CLEANER HELPER (handles pandas Timestamps too) ---
            def clean_excel_date(val):
                if pd.isna(val) or not str(val).strip(): return ""
                if hasattr(val, 'strftime'): return val.strftime("%d-%m-%Y") # Handle Excel timestamps
                
                d_str = str(val).strip().split(' ')[0]
                parts = d_str.replace('/','-').replace('.','-').split('-')
                if len(parts) == 3:
                    if len(parts[0]) == 4: return f"{parts[2].zfill(2)}-{parts[1].zfill(2)}-{parts[0]}"
                    y = parts[2]
                    if len(y) == 2: y = "20" + y
                    return f"{parts[0].zfill(2)}-{parts[1].zfill(2)}-{y}"
                return d_str

            count = 0
            for i in range(start_row, len(df)):
                row = df.iloc[i].tolist()
                
                def get_val(idx):
                    if idx < len(row) and not pd.isna(row[idx]):
                        return str(row[idx]).strip()
                    return ""

                try:
                    weight_val = float(str(row[2]).replace(',', '')) if not pd.isna(row[2]) else 0.0
                    rate_val = float(str(row[3]).replace(',', '')) if not pd.isna(row[3]) else 0.0
                except:
                    weight_val, rate_val = 0.0, 0.0

                query = """INSERT INTO yarn_entries 
                           (item_name, entry_date, invoice, weight, rate, broker, 
                            company, delivery_company, delivery_date, remark) 
                           VALUES (?,?,?,?,?,?,?,?,?,?)"""
                
                # Apply date cleaner here so bad dates never touch the DB
                params = (
                    item_filter,   
                    clean_excel_date(row[0] if len(row) > 0 else ""),    
                    get_val(1),    
                    weight_val,    
                    rate_val,      
                    get_val(4),    
                    get_val(5),    
                    get_val(6),    
                    clean_excel_date(row[7] if len(row) > 7 else ""),    
                    get_val(8)     
                )

                if self.db.execute_query(query, params):
                    count += 1
            
            QMessageBox.information(self, "Success", f"Successfully Imported {count} Yarn Entries.")
            self.generate_report()

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed: {str(e)}")


   


# ==========================================
# MAIN REPORT MODULE CONTAINER
# ==========================================
class ReportModule(QWidget):
    def __init__(self, company_name):
        super().__init__()
        self.company_name = company_name
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tab_party = PartyReportTab(self.company_name)
        self.tab_yarn = YarnReportTab(self.company_name)
        self.tabs.addTab(self.tab_party, "Party Wise Report")
        self.tabs.addTab(self.tab_yarn, "Inventory Report")
        
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #bdc3c7; background: white; margin-top: -1px; }
            QTabBar::tab {
                background: #e0e0e0; color: #333; padding: 12px 25px;
                border: 1px solid #ccc; border-bottom: none;
                border-top-left-radius: 4px; border-top-right-radius: 4px;
                min-width: 180px; font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #8e44ad; color: white; border-bottom: 2px solid #8e44ad;
            }
        """)

        layout.addWidget(QLabel("<h2>Reports Management</h2>"))
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def refresh_data(self):
        self.tab_party.load_accounts()
        self.tab_yarn.load_items()