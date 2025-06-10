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

def get_letter_config_by_category(category, sub_category=None):
    """Fetch both letter and instruction by category."""
    letter = get_letter_by_category(category, sub_category)
    all_instructions = get_instruction_by_category("الجميع")
    all_instructions = all_instructions if all_instructions else ""
    instruction = get_instruction_by_category(category)
    instruction = instruction if instruction else ""
    instruction = all_instructions + "\n" + instruction

    if not letter and not instruction:
        raise ValueError(f"❌ Neither letter nor instruction found for category '{category}' and sub-category '{sub_category}'.")

    return {
        "ideal": letter,
        "instruction": instruction
    }

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