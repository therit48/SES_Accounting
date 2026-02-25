import os
import zipfile
import shutil
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QPushButton, QLineEdit, QMessageBox, QLabel, QFileDialog)
from PyQt5.QtCore import Qt
from core.database import DatabaseManager

class CompanySelector(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SES - Company Manager")
        self.resize(500, 650) 
        self.selected_company = None
        
        # Connect to Global DB
        self.global_db = DatabaseManager("master")
        self.global_db.execute_query("CREATE TABLE IF NOT EXISTS companies (name TEXT UNIQUE)")
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # --- SECTION 1: SELECTION ---
        lbl_select = QLabel("Select an Existing Company")
        lbl_select.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        
        self.list_companies = QListWidget()
        self.list_companies.setAlternatingRowColors(True)
        self.list_companies.setStyleSheet("font-size: 13px; padding: 5px;")
        self.list_companies.itemDoubleClicked.connect(self.open_company)
        
        # Selection Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_open = QPushButton("Open Selected")
        self.btn_open.clicked.connect(self.open_company)
        self.btn_open.setStyleSheet("background-color: #2980b9; color: white; padding: 10px; font-weight: bold;")
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_company)
        self.btn_delete.setStyleSheet("background-color: #c0392b; color: white; padding: 10px; font-weight: bold;")
        
        btn_layout.addWidget(self.btn_open)
        btn_layout.addWidget(self.btn_delete)

        # --- SECTION 2: RESTORE (NEW) ---
        self.btn_restore = QPushButton("📂 Restore Company from Backup (.zip)")
        self.btn_restore.clicked.connect(self.restore_company)
        self.btn_restore.setStyleSheet("""
            QPushButton { background-color: #34495e; color: white; padding: 10px; font-weight: bold; margin-top: 5px; }
            QPushButton:hover { background-color: #2c3e50; }
        """)

        # --- SECTION 3: CREATION ---
        lbl_create = QLabel("Create New Company")
        lbl_create.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; margin-top: 15px;")
        
        self.input_new = QLineEdit()
        self.input_new.setPlaceholderText("Enter New Company Name...")
        self.input_new.returnPressed.connect(self.create_company)
        self.input_new.setStyleSheet("padding: 10px; border: 2px solid #27ae60; border-radius: 4px; font-size: 14px;")
        
        btn_create = QPushButton("Create and Add to List")
        btn_create.clicked.connect(self.create_company)
        btn_create.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold;")

        # --- Add to Main Layout ---
        main_layout.addWidget(lbl_select)
        main_layout.addWidget(self.list_companies)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.btn_restore) # Added Restore Button here
        
        line = QLabel() 
        line.setStyleSheet("background-color: #bdc3c7; max-height: 1px; margin: 15px 0px;")
        main_layout.addWidget(line)
        
        main_layout.addWidget(lbl_create)
        main_layout.addWidget(self.input_new)
        main_layout.addWidget(btn_create)
        
        self.setLayout(main_layout)
        self.refresh_list()

    def refresh_list(self):
        self.list_companies.clear()
        try:
            companies = self.global_db.fetch_all("SELECT name FROM companies ORDER BY name ASC")
            for (name,) in companies:
                self.list_companies.addItem(name)
        except Exception as e:
            print(f"Error refreshing list: {e}")

    # ==========================================
    # RESTORE LOGIC
    # ==========================================
    def restore_company(self):
        """Extracts a ZIP backup and adds it back to the system"""
        zip_path, _ = QFileDialog.getOpenFileName(self, "Select Backup File", "", "Zip Files (*.zip)")
        if not zip_path: return

        try:
            # Get company name from filename (removes 'SES_Backup_' and timestamp)
            filename = os.path.basename(zip_path)
            # Try to clean the name: removes prefix and date part
            comp_name = filename.replace("SES_Backup_", "").split("_202")[0].split("_19-")[0]
            
            if not comp_name or comp_name == ".zip":
                comp_name = "Restored_Company"

            target_path = os.path.join("data", comp_name)

            # Check if exists
            if os.path.exists(target_path):
                confirm = QMessageBox.question(self, "Confirm Overwrite", 
                    f"Company '{comp_name}' already exists.\nRestoring will replace ALL existing data. Continue?",
                    QMessageBox.Yes | QMessageBox.No)
                if confirm == QMessageBox.No: return
                shutil.rmtree(target_path)

            # Extract
            os.makedirs(target_path, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(target_path)

            # Register in Master DB if not already there
            self.global_db.execute_query("INSERT OR IGNORE INTO companies (name) VALUES (?)", (comp_name,))
            
            self.refresh_list()
            QMessageBox.information(self, "Success", f"Company '{comp_name}' restored successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Restore Error", f"Failed to restore: {str(e)}")

    def create_company(self):
        name = self.input_new.text().strip()
        if not name: 
            QMessageBox.warning(self, "Input Error", "Please enter a company name.")
            return
        
        try:
            success = self.global_db.execute_query("INSERT INTO companies (name) VALUES (?)", (name,))
            if success:
                db = DatabaseManager(name)
                db.init_company_tables()
                db.close()
                self.refresh_list()
                self.input_new.clear()
                QMessageBox.information(self, "Success", f"Company '{name}' created!")
            else:
                QMessageBox.critical(self, "Error", "Company already exists.")
        except Exception as e:
            QMessageBox.critical(self, "Crash", f"Error: {str(e)}")

    def open_company(self):
        item = self.list_companies.currentItem()
        if item:
            self.selected_company = item.text()
            self.accept()
        else:
            QMessageBox.warning(self, "Selection Required", "Please select a company.")

    def delete_company(self):
        item = self.list_companies.currentItem()
        if not item: return
            
        company_name = item.text()
        confirm = QMessageBox.question(self, "Confirm Delete", 
                                     f"Delete '{company_name}' from the list?",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if confirm == QMessageBox.Yes:
            self.global_db.execute_query("DELETE FROM companies WHERE name = ?", (company_name,))
            self.refresh_list()