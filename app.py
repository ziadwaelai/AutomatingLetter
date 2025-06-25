from flask import Flask, request, jsonify
from ai_generator import ArabicLetterGenerator
from google_services import  append_letter_to_sheet , get_letter_config_by_category
from drive_logger import save_letter_to_drive_and_log
from dotenv import load_dotenv
import os
# Load environment variables
load_dotenv()

app = Flask(__name__)
# Initialize letter generator once
letter_generator = ArabicLetterGenerator()

@app.route("/generate-letter", methods=["POST"])
def generate_letter_route():
    data = request.json
    category = data.get("category")
    recipient = data.get("recipient")
    is_firstTime = data.get("isFirst")
    prompt = data.get("prompt")
    member_name = data.get("member_name", "")
    recipient_job_title = data.get("recipient_job_title", "")
    recipient_title = data.get("recipient_title", "")
    organization_name = data.get("organization_name", "")
    previous_letter_content = data.get("previous_letter_content", "")
    previous_letter_id = data.get("previous_letter_id", "")

    if not category or not prompt or not recipient or is_firstTime is None :
        return jsonify({"error": "Missing required fields"}), 400
    try:
        try:
            letter_config = get_letter_config_by_category(category, member_name)
            reference_letter = letter_config["letter"]
            instructions = letter_config["instruction"]
            member_info = letter_config["member_info"]
        except ValueError as e:
            reference_letter = None
            instructions = None
        
        # Use the ArabicLetterGenerator instance
        letter_output = letter_generator.generate_letter(
            user_prompt=prompt,
            reference_letter=reference_letter,
            recipient=recipient,
            writing_instructions=instructions,
            is_first_contact=is_firstTime,
            category=category,
            member_info=member_info,
            recipient_job_title=recipient_job_title,
            recipient_title=recipient_title,
            organization_name=organization_name,
            previous_letter_content=previous_letter_content,
            previous_letter_id=previous_letter_id
        )
        
        # Return the JSON response
        return jsonify(letter_output.model_dump()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# deprecated
@app.route("/save-letter", methods=["POST"])
def save_letter_route():
    data = request.json
    letter = data.get("letter")
    letter_type = data.get("letter_type")
    recipient = data.get("recipient")
    subject = data.get("subject")
    is_first_comm = data.get("is_first_comm")

    if not letter :
        return jsonify({"error": "Missing letter content"}), 400

    try:
    # Simulate saving
        result=append_letter_to_sheet(
            letter_type=letter_type,
            recipient=recipient,
            subject=subject,
            content=letter,
            is_first_comm=is_first_comm,
        )
        return jsonify({"message": "Letter saved successfully", "result": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/archive-letter", methods=["POST"])
def upload_pdf_route():
    # Check if file exists in request
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        letter_content = request.form.get('letter_content', '')
        letter_type = request.form.get('letter_type', 'General')
        recipient = request.form.get('recipient', '')
        title = request.form.get('title', file.filename)
        is_first = request.form.get('is_first', 'false').lower() == 'true'
        ID = request.form.get('ID', '')

        # Get Google Drive folder ID from environment variables
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        if not folder_id:
            return jsonify({"error": "Google Drive folder ID not configured"}), 500
        
        # Use the new function to save and log the letter
        result = save_letter_to_drive_and_log(
            letter_file=file,
            letter_content=letter_content,
            letter_type=letter_type,
            recipient=recipient,
            title=title,
            is_first=is_first,
            folder_id=folder_id,
            ID=ID
        )
        
        if result["status"] == "success":
            return jsonify({
                "status": "success",
                "file_id": result["file_id"],
                "view_link": result["file_url"],
                "log_status": result["log_result"]["status"]
            }), 200
        else:
            return jsonify({"error": result["message"]}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)