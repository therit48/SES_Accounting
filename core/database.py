import sqlite3
import os
from .utils import Utils

class DatabaseManager:
    def __init__(self, company_name="master"):
        self.company_name = company_name
        self.conn = None
        self.connect()

    def connect(self):
        """Connects to the specific company's SQLite DB"""
        if self.company_name == "master":
            # Global DB for list of companies
            db_path = os.path.join(Utils.get_app_path(), "app_data", "global.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        else:
            # Company specific DB
            folder = Utils.get_company_path(self.company_name)
            db_path = os.path.join(folder, "data.db")
        
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def execute_query(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"DB Error: {e}")
            return False

    def fetch_all(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def close(self):
        if self.conn:
            self.conn.close()

    def init_company_tables(self):
        """Initialize tables for a new company"""
        # Table: Schedules
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                name TEXT
            )
        """)
        # Table: Account Master (Parties)
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                party_code TEXT UNIQUE,
                party_name TEXT,
                schedule_code TEXT
            )
        """)
        # Add other tables (Inventory, Transactions) here...