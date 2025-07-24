import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from typing import List, Dict, Any
import tempfile
import os
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google.oauth2 import service_account
import time
import concurrent.futures

SERVICE_ACCOUNT_FILE = 'automating-letter-creations.json'
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",

            
            ]

def get_instruction_by_category(category):
    """Fetch instruction by category from Instructions sheet."""
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
        client = gspread.authorize(creds)

        # Connect to 'Instruction' sheet
        instruction_sheet = client.open("Letters").worksheet("Instructions")
        instruction_data = instruction_sheet.get_all_values()

        # Find instruction by category
        for row in instruction_data:
            if row and row[0].strip().lower() == category.strip().lower():
                return row[1]
        return None

    except Exception as e:
        raise ValueError(f"❌ Error fetching instruction for category '{category}': {e}")

def get_Data_by_key(key, sheet, flag=False):
    """
    Fetches data by key from a specified sheet in the 'Letters' Google Spreadsheet.

    Args:
        key (str): The key/category to search for (case-insensitive).
        sheet (str): The worksheet name.
        flag (bool, optional): If True, fetches up to two matching entries and concatenates them. Defaults to False.

    Returns:
        str or None: The found data, concatenated if flag is True, or None if not found.
    """
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
        client = gspread.authorize(creds)
        worksheet = client.open("Letters").worksheet(sheet)
        rows = worksheet.get_all_values()

        matches = [
            row[1] for row in rows
            if row and row[0].strip().lower() == key.strip().lower()
        ]

        if flag:
            # Concatenate up to two matches with separator
            result = ""
            for i, match in enumerate(matches[:2]):
                if i > 0:
                    result += "\nالخطاب الثاني:\n"
                result += match
            return result.strip() if result else None
        else:
            return matches[0] if matches else None

    except Exception as e:
        raise ValueError(f"❌ Error fetching data for key '{key}' from sheet '{sheet}': {e}") from e
    
    
def get_info_by_name(name):
    if name =="":
        return None
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open("Letters").worksheet("Info")
        data = sheet.get_all_values()
        for row in data:
            if row and row[0].strip().lower() == name.strip().lower():
                return row[1]
        return None
    except Exception as e:
        raise ValueError(f"❌ Error fetching info for name '{name}': {e}")
    
def get_letter_by_category(category, sub_category=None):
    """
    Fetch letter by category and optionally sub-category from Ideal sheet.
    First column: Sub-category
    Second column: Category
    Third column: Letter content
    If sub-category is provided but not found, falls back to category-only search.
    """
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
        client = gspread.authorize(creds)

        # Connect to 'Letters' sheet
        letters_sheet = client.open("Letters").worksheet("Ideal")
        letters_data = letters_sheet.get_all_values()

        # Find letter by category and sub-category
        matching_letters = []
        category_only_matches = []  # Fallback matches
        
        for row in letters_data:
            if len(row) < 3:  # Skip rows without enough columns
                continue
                
            row_sub_cat = row[0].strip()
            row_cat = row[1].strip()
            
            # Always collect category-only matches as fallback
            if row_cat == category.strip():
                category_only_matches.append(row[2])
                
                # If sub-category matches too, add to primary matches
                if sub_category and row_sub_cat == sub_category.strip():
                    matching_letters.append(row[2])
        
        # If we found matches with sub-category, use those
        # Otherwise fall back to category-only matches
        final_matches = matching_letters if matching_letters else category_only_matches
        
        # Return the latest matching letter
        return final_matches[-1] if final_matches else None

    except Exception as e:
        raise ValueError(f"❌ Error fetching letter for category '{category}' and sub-category '{sub_category}': {e}")

def get_letter_config_by_category(category, name=""):
    """
    Fetches letter template, combined instructions, and member info by category and name.
    Uses parallel execution to improve response time.

    Args:
        category (str): The category to fetch data for.
        name (str, optional): The member name to fetch info for. Defaults to "".

    Returns:
        dict: {
            "letter": str,
            "instruction": str,
            "member_info": str
        }

    Raises:
        ValueError: If data fetching fails.
    """
    try:
        # Define the tasks to be executed in parallel
        def get_letter():
            return get_Data_by_key(category, "Ideal", True) or ""
            
        def get_instruction():
            return get_Data_by_key(category, "Instructions") or ""
            
        def get_all_instructions():
            return get_Data_by_key("الجميع", "Instructions") or ""
            
        def get_member_info():
            return get_Data_by_key(name, "Info") or ""
        
        # Execute all tasks in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all tasks and get future objects
            letter_future = executor.submit(get_letter)
            instruction_future = executor.submit(get_instruction)
            all_instructions_future = executor.submit(get_all_instructions)
            member_info_future = executor.submit(get_member_info)
            
            # Get results from futures
            letter = letter_future.result()
            instruction = instruction_future.result()
            all_instructions = all_instructions_future.result()
            member_info = member_info_future.result()

        # Combine instructions, avoid leading/trailing newlines
        instructions = "\n".join(
            filter(None, [all_instructions.strip(), instruction.strip()])
        )

        return {
            "letter": letter,
            "instruction": instructions,
            "member_info": member_info
        }
    except Exception as e:
        raise ValueError(
            f"❌ Error fetching letter config for category '{category}': {e}"
        ) from e

def append_letter_to_sheet(
    letter_type: str,
    recipient: str,
    subject: str,
    content: str,
    is_first_comm: bool = False,
) -> dict:

    try:
        # Authenticate and create client
        creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
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

def log(
    spreadsheet_name: str,
    worksheet_name: str,
    entries: List[Dict[str, Any]],
    value_input_option: str = 'RAW'
) -> Dict[str, Any]:
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
    client = gspread.authorize(creds)
    try:
        worksheet = client.open(spreadsheet_name).worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        raise ValueError(f"Worksheet '{worksheet_name}' not found in spreadsheet '{spreadsheet_name}'.")

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

def upload_file_to_drive(file, folder_id):
    """Upload a file to Google Drive and return its ID and web view link."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)
    # Create a temporary file path
    fd, tmp_filepath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)  # Close file descriptor to avoid Windows locking
    filename = file.filename
    try:
        file.save(tmp_filepath)
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        with open(tmp_filepath, 'rb') as f:
            media = MediaFileUpload(
                tmp_filepath, 
                mimetype='application/pdf',
                resumable=True
            )
            uploaded = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
        time.sleep(0.5)
        return uploaded['id'], uploaded['webViewLink']
    except Exception as e:
        print(f"Error uploading file to Drive: {e}")
        raise
    finally:
        for _ in range(3):
            try:
                if os.path.exists(tmp_filepath):
                    os.remove(tmp_filepath)
                break
            except PermissionError:
                time.sleep(1)

def upload_file_path_to_drive(file_path, folder_id, filename=None):
    """Upload a file from file path to Google Drive and return its ID and web view link."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Use provided filename or extract from path
    if filename is None:
        filename = os.path.basename(file_path)
    
    try:
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(
            file_path, 
            mimetype='application/pdf',
            resumable=True
        )
        
        uploaded = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        time.sleep(0.5)
        return uploaded['id'], uploaded['webViewLink']
    except Exception as e:
        print(f"Error uploading file to Drive: {e}")
        raise