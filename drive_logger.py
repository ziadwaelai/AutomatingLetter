from google_services import upload_file_to_drive, upload_file_path_to_drive, log
import datetime
import os

def save_letter_to_drive_and_log(
    letter_file, 
    letter_content, 
    letter_type, 
    recipient, 
    title, 
    is_first, 
    folder_id,
    id,
    username
):
    try:
        # Check if letter_file is a string (file path) or file object
        if isinstance(letter_file, str):
            # It's a file path, use the new function
            filename = f"{title}_{id}.pdf" if title != 'undefined' else f"letter_{id}.pdf"
            file_id, file_url = upload_file_path_to_drive(letter_file, folder_id, filename)
        else:
            # It's a file object, use the original function
            file_id, file_url = upload_file_to_drive(letter_file, folder_id)        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "Timestamp": timestamp,
            "Type of Letter": letter_type,
            "Recipient": recipient,
            "Title": title,
            "First Time?": "Yes" if is_first else "No",
            "Content": letter_content,
            "URL": file_url,
            "Revision":"في الانتظار",
            "ID": id,
            "Username": username
        }
        log_result = log(
            spreadsheet_name="AI Letter Generating", 
            worksheet_name="Submissions",
            entries=[log_entry]
        )
        return {
            "status": "success",
            "file_id": file_id,
            "file_url": file_url,
            "log_result": log_result
        }
        
    except Exception as e:
        error_message = f"Error saving letter to Drive and logging: {str(e)}"
        print(error_message)
        return {
            "status": "error",
            "message": error_message
        }