from google_services import upload_file_to_drive, log
import datetime

def save_letter_to_drive_and_log(
    letter_file, 
    letter_content, 
    letter_type, 
    recipient, 
    title, 
    is_first, 
    folder_id
):
    try:
        file_id, file_url = upload_file_to_drive(letter_file, folder_id)        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "Timestamp": timestamp,
            "Type of Letter": letter_type,
            "Recipient": recipient,
            "Title": title,
            "First Time?": "Yes" if is_first else "No",
            "Content": letter_content,
            "URL": file_url
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