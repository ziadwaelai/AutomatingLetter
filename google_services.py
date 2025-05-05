import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from typing import List, Dict, Any

def get_letter_config_by_category(category):
    """Fetch letter and instruction by category from two separate Google Sheets."""
    try:
        # Connect to Google Sheets using Service Account credentials
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]        
        creds = ServiceAccountCredentials.from_json_keyfile_name('automating-letter-creations.json', scope)
        client = gspread.authorize(creds)

        # Connect to 'Letters' workbook and 'Ideal' sheet
        letters_sheet = client.open("Letters").worksheet("Ideal")
        letters_data = letters_sheet.get_all_values()

        # Connect to 'Instruction' workbook and 'Instructions' sheet
        instruction_sheet = client.open("Letters").worksheet("Instructions")
        instruction_data = instruction_sheet.get_all_values()

        # Helper to find value by category
        def find_by_category(data, category):
            for row in data:
                if row and row[0].strip().lower() == category.strip().lower():
                    return row[1]
            return None

        # Fetch the values
        letter_value = find_by_category(letters_data, category)
        instruction_value = find_by_category(instruction_data, category)

        if not letter_value and not instruction_value:
            raise ValueError(f"❌ Neither letter nor instruction found for category '{category}'.")

        return {
            "ideal": letter_value ,
            "instruction": instruction_value 
        }

    except Exception as e:
        raise ValueError(f"❌ Error fetching data for category '{category}': {e}")


def append_letter_to_sheet(
    letter_type: str,
    recipient: str,
    subject: str,
    content: str,
    is_first_comm: bool = False,
) -> dict:

    try:
        # Define the scope
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Authenticate and create client
        creds = ServiceAccountCredentials.from_json_keyfile_name("automating-letter-creations.json", scope)
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        spreadsheet = client.open("SQUAD Letter Generator Dummy Data")
        
        # Select the first worksheet (or specify a specific sheet if needed)
        worksheet = spreadsheet.sheet1
        
        # Get the current timestamp in Arabic format
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare the row to be appended
        row_data = [
            letter_type,     # Column B
            recipient,       # Column C
            subject,         # Column D
            content,         # Column E
            created_at,      # Column F
            str(is_first_comm)  # Column G
        ]
        full_row_data = [''] + row_data
        # Append the row
        worksheet.append_row(full_row_data,value_input_option='RAW')
        
        # Get the number of existing rows
        existing_rows = len(worksheet.get_all_values())
        
        # Return information about the appended row
        return {
            "status": "success",
            "sheet_name": "SQUAD Letter Generator Dummy Data",
            "row_number": existing_rows,
            "message": "Letter details successfully appended to the sheet"
        }
    
    except Exception as e:

        # Detailed error handling
        return {
            "status": "error",
            "message": f"Error appending letter: {str(e)}",
            "details": str(e)
        }
def Log(
    creds_json_path: str,
    spreadsheet_name: str,
    worksheet_name: str,
    entries: List[Dict[str, Any]],
    value_input_option: str = 'RAW'
) -> Dict[str, Any]:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_json_path, scope)
    client = gspread.authorize(creds)

    worksheet = client.open(spreadsheet_name).worksheet(worksheet_name)

    headers = worksheet.row_values(1)
    header_map = {h.strip(): idx for idx, h in enumerate(headers)}

    appended = 0
    for entry in entries:
        row = [''] * len(headers)
        for key, value in entry.items():
            if key in header_map:
                row[header_map[key]] = value
            else:
                raise KeyError(f"Column '{key}' not found in sheet headers {headers}")
        worksheet.append_row(row, value_input_option=value_input_option)
        appended += 1

    return {
        "status": "success",
        "spreadsheet": spreadsheet_name,
        "worksheet": worksheet_name,
        "rows_appended": appended
    }