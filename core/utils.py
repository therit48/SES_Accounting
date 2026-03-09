import os
import sys
from datetime import datetime

class Utils:
    import os
import sys

class Utils:
    
    @staticmethod
    def get_app_path():
        """
        Forces the app to ALWAYS use the Windows Documents folder.
        This prevents the .exe from saving data in the 'dist' folder.
        """
        # Finds C:\Users\YourName
        home_dir = os.path.expanduser('~') 
        
        # Creates C:\Users\YourName\Documents\SES_Data
        base_data_path = os.path.join(home_dir, 'Documents', 'SES_Data')
        
        # Ensure the folder exists
        os.makedirs(base_data_path, exist_ok=True)
        
        return base_data_path

    @staticmethod
    def get_company_path(company_name):
        """
        Creates a sub-folder for the specific company inside SES_Data.
        """
        # Uses the Documents path from above
        company_folder = os.path.join(Utils.get_app_path(), company_name)
        
        # Ensure the company folder exists
        os.makedirs(company_folder, exist_ok=True)
        
        return company_folder

    @staticmethod
    def format_date_str(date_str):
        """Enforces dd-mm-yyyy format logic"""
        try:
            # Try parsing various inputs like 12-5-25 or 12/05/2025
            for fmt in ('%d-%m-%y', '%d-%m-%Y', '%d/%m/%y', '%d/%m/%Y'):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%d-%m-%Y')
                except ValueError:
                    continue
            return datetime.now().strftime('%d-%m-%Y') # Fallback
        except:
            return datetime.now().strftime('%d-%m-%Y')

    @staticmethod
    def calculate_interest(rate, qty, inv_date, pay_date, grace_day):
        """
        Formula: (((Rate * Qty * 18) / (100 * 366)) * ((IntDays) - GraceDay - 1))
        """
        try:
            d1 = datetime.strptime(inv_date, '%d-%m-%Y')
            d2 = datetime.strptime(pay_date, '%d-%m-%Y')
            int_days = (d2 - d1).days
            
            effective_days = int_days - grace_day - 1
            if effective_days <= 0:
                return 0.0

            amount = (((rate * qty * 18) / (100 * 366)) * effective_days)
            return round(amount, 2)
        except Exception as e:
            print(f"Calc Error: {e}")
            return 0.0

    @staticmethod
    def get_logo_path():
        """Finds the logo.ico file whether running as Python or as an EXE"""
        if getattr(sys, 'frozen', False):
            # If running as an installed EXE
            base_path = os.path.dirname(sys.executable)
        else:
            # If running inside VS Code/Python
            base_path = os.path.abspath(os.path.dirname(sys.argv[0]))
            
        return os.path.join(base_path, "logo.ico")
    
    @staticmethod
    def format_indian_currency(number):
        """Converts a number to Indian numbering format (Lakhs/Crores)"""
        if number is None or number == "":
            return "0.00"
            
        try:
            num = float(number)
            is_negative = num < 0
            num = abs(num)
            
            # Split into integer and decimal parts (forces 2 decimal places)
            s = f"{num:.2f}"
            int_part, dec_part = s.split('.')
            
            # If it's less than 1,000, no commas needed
            if len(int_part) <= 3:
                result = int_part
            else:
                # Grab the last 3 digits
                last_3 = int_part[-3:]
                # Grab the rest of the numbers
                rest = int_part[:-3]
                
                # Group the remaining numbers by 2 (Lakhs, Crores, etc.)
                rest_parts = []
                while len(rest) > 0:
                    rest_parts.insert(0, rest[-2:])
                    rest = rest[:-2]
                
                # Stick it all back together with commas
                result = ",".join(rest_parts) + "," + last_3
                
            final_result = f"{result}.{dec_part}"
            
            # Put the negative sign back if it was a loss
            if is_negative:
                return f"-{final_result}"
            return final_result
            
        except (ValueError, TypeError):
            return "0.00"