import sys
import os
import shutil
import zipfile
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QComboBox, QStackedWidget, QFrame, QDialog, 
                             QMessageBox, QFileDialog, QButtonGroup)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QFont, QIcon    

# Import your modules
from modules.company_manager import CompanySelector
from modules.master import AccountMaster
from modules.transactions import TransactionModule
from modules.reports import ReportModule
from modules.accounting import PnLReportWidget, YearCreationDialog
from core.database import DatabaseManager
from core.utils import Utils
from modules.inventory import InventoryModule

class MainWindow(QMainWindow):
    def __init__(self, company_name):
        super().__init__()
        self.company_name = company_name
        self.setWindowTitle(f"SES Accounting Software - {self.company_name}")
        self.resize(1280, 720) 
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ==========================================
        # UPGRADED PROFESSIONAL SIDEBAR
        # ==========================================
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260) # Slightly wider for comfort
        sidebar.setStyleSheet("""
            QFrame#Sidebar { 
                background-color: #1e272e; /* Midnight dark blue */
                border-right: 1px solid #000000; 
            }
            QLabel { background: transparent; color: #ecf0f1; }
            
            /* Professional Nav Buttons */
            QPushButton#SidebarBtn { 
                text-align: left; 
                padding: 12px 15px; 
                background: transparent; 
                color: #808e9b; 
                border: none; 
                font-size: 14px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 2px 10px;
            }
            QPushButton#SidebarBtn:hover { 
                background-color: #2b3e50; 
                color: #d2dae2; 
            }
            QPushButton#SidebarBtn:checked {
                background-color: #34495e; 
                color: #ffffff; 
                border-left: 4px solid #3498db; /* Blue accent line */
                border-radius: 4px;
            }
            
            /* Dark styled ComboBox for sidebar */
            QComboBox#SidebarCombo {
                background-color: #2b3e50;
                color: white;
                border: 1px solid #485460;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
            }
            QComboBox#SidebarCombo::drop-down { border: none; }
            QComboBox#SidebarCombo QAbstractItemView {
                background-color: #2b3e50;
                color: white;
                selection-background-color: #3498db;
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 25, 0, 15)
        
        # --- Brand & Top Section ---
        self.lbl_clock = QLabel()
        self.lbl_clock.setAlignment(Qt.AlignCenter)
        self.lbl_clock.setStyleSheet("color: #0fb9b1; font-size: 11px; font-weight: bold; margin-bottom: 5px;")
        sidebar_layout.addWidget(self.lbl_clock)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

        lbl_company = QLabel(self.company_name.upper())
        lbl_company.setStyleSheet("font-size: 17px; font-weight: 900; color: #ffffff; padding: 0px 15px; letter-spacing: 1px;")
        lbl_company.setAlignment(Qt.AlignCenter)
        lbl_company.setWordWrap(True)
        sidebar_layout.addWidget(lbl_company)
        
        # --- Year Selector Layout ---
        year_layout = QHBoxLayout()
        year_layout.setContentsMargins(15, 10, 15, 20)
        
        self.combo_year = QComboBox()
        self.combo_year.setObjectName("SidebarCombo")
        self.combo_year.currentTextChanged.connect(self.on_year_changed)
        
        btn_add_year = QPushButton("➕")
        btn_add_year.setFixedSize(32, 32)
        btn_add_year.setStyleSheet("""
            QPushButton { background-color: #05c46b; color: white; border-radius: 4px; font-size: 14px; }
            QPushButton:hover { background-color: #10ac64; }
        """)
        btn_add_year.setCursor(Qt.PointingHandCursor)
        btn_add_year.clicked.connect(self.open_year_creator)
        
        year_layout.addWidget(self.combo_year)
        year_layout.addWidget(btn_add_year)
        sidebar_layout.addLayout(year_layout)
        
        # --- Navigation Buttons ---
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True) # Ensures only one button is active at a time
        
        nav_buttons = [
            ("📊 Dashboard", 0), 
            ("📂 Account Master", 1), 
            ("💸 Transactions", 2),
            ("📈 Reports Module", 3), 
            ("📦 Yarn Inventory", 4), 
            ("💼 Accounting (P&L)", 5)
        ]
        
        for text, index in nav_buttons:
            btn = QPushButton(text)
            btn.setObjectName("SidebarBtn")
            btn.setCheckable(True) # Allows the button to stay highlighted
            btn.setCursor(Qt.PointingHandCursor)
            
            if index == 0:
                btn.setChecked(True) # Make Dashboard active by default
                
            btn.clicked.connect(lambda checked, idx=index: self.stack.setCurrentIndex(idx))
            self.btn_group.addButton(btn)
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch() 

        # --- Bottom Action Buttons ---
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(15, 0, 15, 0)
        bottom_layout.setSpacing(10)

        btn_logo = QPushButton("🖼️ Upload Logo")
        btn_logo.setStyleSheet("""
            QPushButton { background-color: #f39c12; color: white; padding: 10px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #f1c40f; }
        """)
        btn_logo.setCursor(Qt.PointingHandCursor)
        btn_logo.clicked.connect(self.upload_logo)
        bottom_layout.addWidget(btn_logo)

        btn_remove_logo = QPushButton("❌ Remove Logo")
        btn_remove_logo.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; padding: 10px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #c0392b; }
        """)
        btn_remove_logo.setCursor(Qt.PointingHandCursor)
        btn_remove_logo.clicked.connect(self.remove_logo)
        bottom_layout.addWidget(btn_remove_logo)

        btn_manual_backup = QPushButton("💾 Export Backup")
        btn_manual_backup.setStyleSheet("""
            QPushButton { background-color: #3c40c6; color: white; padding: 10px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #575fcf; }
        """)
        btn_manual_backup.setCursor(Qt.PointingHandCursor)
        btn_manual_backup.clicked.connect(self.perform_manual_backup)
        bottom_layout.addWidget(btn_manual_backup)

        btn_switch = QPushButton("🔄 Switch Company")
        btn_switch.setStyleSheet("""
            QPushButton { background-color: #ff3f34; color: white; padding: 10px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #ff5e57; }
        """)
        btn_switch.setCursor(Qt.PointingHandCursor)
        btn_switch.clicked.connect(self.switch_company)
        bottom_layout.addWidget(btn_switch)

        sidebar_layout.addLayout(bottom_layout)

        lbl_version = QLabel("SES Accounting v1.0.0")
        lbl_version.setAlignment(Qt.AlignCenter)
        lbl_version.setStyleSheet("color: #6FC276; font-size: 10px; margin-top: 10px;")
        sidebar_layout.addWidget(lbl_version)

        main_layout.addWidget(sidebar)
        
        # ==========================================
        # MAIN STACKED WIDGET
        # ==========================================
        self.stack = QStackedWidget()
        
        # Simple styled dashboard placeholder
        dash_widget = QWidget()
        dash_layout = QVBoxLayout(dash_widget)
        dash_lbl = QLabel(f"<h1 style='color: #2c3e50; font-size: 32px;'>Welcome to {self.company_name}</h1><p style='color: #7f8c8d; font-size: 16px;'>Select a module from the sidebar to begin.</p>")
        dash_lbl.setAlignment(Qt.AlignCenter)
        dash_layout.addWidget(dash_lbl)
        
        self.stack.addWidget(dash_widget)
        self.stack.addWidget(AccountMaster(self.company_name))
        self.stack.addWidget(TransactionModule(self.company_name))
        self.stack.addWidget(ReportModule(self.company_name))
        self.stack.addWidget(InventoryModule(self.company_name)) 
        self.stack.addWidget(PnLReportWidget(self.company_name)) 
        
        main_layout.addWidget(self.stack)
        self.stack.currentChanged.connect(self.on_tab_changed)

        # Trigger initial loads
        self.load_years()

    # ==========================================
    # LOGIC
    # ==========================================

    def on_year_changed(self, new_year):
        if not new_year: return
        acc_module = self.stack.widget(5) 
        if hasattr(acc_module, 'set_active_year'):
            acc_module.set_active_year(new_year)

    def load_years(self):
        self.combo_year.blockSignals(True) 
        self.combo_year.clear()
        
        db = DatabaseManager(self.company_name)
        db.execute_query("CREATE TABLE IF NOT EXISTS years (id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
        years = db.fetch_all("SELECT name FROM years ORDER BY name DESC")
        
        for (name,) in years: 
            self.combo_year.addItem(name)
            
        self.combo_year.blockSignals(False)
        
        if self.combo_year.currentText():
            self.on_year_changed(self.combo_year.currentText())

    def perform_manual_backup(self):
        path = Utils.get_company_path(self.company_name)
        ts = QDateTime.currentDateTime().toString("dd-MMM-yyyy_HHmm")
        name, _ = QFileDialog.getSaveFileName(self, "Export Full Backup", 
                                             f"SES_Backup_{self.company_name}_{ts}.zip", 
                                             "Zip Files (*.zip)")
        if name:
            try:
                with zipfile.ZipFile(name, 'w', zipfile.ZIP_DEFLATED) as z:
                    for root, _, files in os.walk(path):
                        for f in files:
                            fp = os.path.join(root, f)
                            z.write(fp, os.path.relpath(fp, path))
                QMessageBox.information(self, "Success", "Full Backup created successfully!")
            except Exception as e: 
                QMessageBox.critical(self, "Error", f"Backup failed: {e}")

    def update_clock(self):
        self.lbl_clock.setText(QDateTime.currentDateTime().toString("dd-MMM-yyyy  |  hh:mm:ss AP"))

    def on_tab_changed(self, index):
        current_widget = self.stack.widget(index)
        if hasattr(current_widget, 'refresh_data'):
            current_widget.refresh_data()

    def open_year_creator(self):
        dialog = YearCreationDialog(self.company_name)
        if dialog.exec_() == QDialog.Accepted: 
            self.load_years()

    def switch_company(self):
        confirm = QMessageBox.question(self, "Switch Company", "Are you sure you want to switch companies?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            selector = CompanySelector()
            if selector.exec_() == QDialog.Accepted:
                new = selector.selected_company
                if new:
                    self.new_window = MainWindow(new)
                    self.new_window.show()
                    self.close()

    def upload_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Company Logo", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            try:
                target_dir = Utils.get_company_path(self.company_name)
                # Always save it exactly as 'logo.png' so the PDF generator easily finds it
                target_path = os.path.join(target_dir, "logo.png")
                shutil.copy(path, target_path)
                QMessageBox.information(self, "Success", "Company logo updated successfully!\nIt will now appear on all your exported PDFs.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save logo: {str(e)}")

    def remove_logo(self):
        target_dir = Utils.get_company_path(self.company_name)
        logo_path = os.path.join(target_dir, "logo.png")
        
        # Check if a logo actually exists first
        if os.path.exists(logo_path):
            confirm = QMessageBox.question(self, "Confirm", "Are you sure you want to remove the company logo?", QMessageBox.Yes | QMessageBox.No)
            
            if confirm == QMessageBox.Yes:
                try:
                    os.remove(logo_path)
                    QMessageBox.information(self, "Success", "Logo removed successfully!\nAll future PDFs will revert to the standard text header.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to remove logo: {str(e)}")
        else:
            QMessageBox.information(self, "Notice", "No logo is currently set for this company.")

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Confirm Exit', "Are you sure you want to exit SES Accounting?", 
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon(Utils.get_logo_path()))
    
    app_font = QFont()
    app_font.setPointSize(11)  
    app.setFont(app_font)
    
    selector = CompanySelector()
    if selector.exec_() == QDialog.Accepted:
        if selector.selected_company:
            window = MainWindow(selector.selected_company)
            window.show()
            sys.exit(app.exec_())