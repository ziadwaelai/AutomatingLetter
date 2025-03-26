import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def get_letter_by_category(category):

    """Fetch letter by category from the specified sheet."""
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

        # Open the spreadsheet and select the sheet
        sheet = client.open("Letters").sheet1  # You can change sheet1 to the desired sheet name if needed

        # Fetch all values from the sheet
        data = sheet.get_all_values()

        # If there are no rows or not enough data, raise an error
        if len(data) < 2:
            raise ValueError("❌ The sheet doesn't contain any data or the category is missing.")

        # Loop through the rows to find the matching category
        for row in data:
            if row and row[0].strip().lower() == category.strip().lower():  # Match the category (case insensitive)
                return row[1]  # Return the letter (second column)

        # If category not found, return a not found message
        raise ValueError( f"❌ Letter for category '{category}' not found.")

    except Exception as e:
        raise ValueError (f"❌ Error fetching letter for category '{category}': {e}")
    

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