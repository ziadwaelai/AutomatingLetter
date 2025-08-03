from flask import Flask, request, jsonify
from ai_generator import ArabicLetterGenerator
from google_services import  append_letter_to_sheet , get_letter_config_by_category
from drive_logger import save_letter_to_drive_and_log
from LetterToPdf.letterToPdf import LetterPDF
from dotenv import load_dotenv
import os
import threading
from n8n.app import n8n_get_context , n8n_get_system_prompt
from ai_generator import generate_letter_id
from UserFeedback.interactive_chat import edit_letter_based_on_feedback
# Load environment variables
load_dotenv()

app = Flask(__name__)
# Initialize letter generator once
letter_generator = ArabicLetterGenerator()
pdfMaker = LetterPDF(template_dir="LetterToPdf/templates")

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
            reference_letter = letter_config["letter"] if letter_config["letter"] else " "
            instructions = letter_config["instruction"] if letter_config["instruction"] else " "
            member_info = letter_config["member_info"] if letter_config["member_info"] else " "
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
    data = request.json
    
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    try:
        letter_content = data.get('letter_content', '')
        letter_type = data.get('letter_type', 'General')
        recipient = data.get('recipient', '')
        title = data.get('title', 'undefined')
        is_first = data.get('is_first', False)
        id = data.get('ID', '')
        template = data.get('template', 'default_template.html')
        
        if not letter_content:
            return jsonify({"error": "letter_content is required"}), 400

        # Get Google Drive folder ID from environment variables
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        if not folder_id:
            return jsonify({"error": "Google Drive folder ID not configured"}), 500
            
        # Start a background thread to process the letter
        background_thread = threading.Thread(
            target=process_letter_in_background,
            args=(template, letter_content, id, letter_type, recipient, title, is_first, folder_id)
        )
        background_thread.daemon = True  # Make thread exit when main thread exits
        background_thread.start()
        
        # Immediately return success response
        return jsonify({
            "status": "success",
            "message": f"Letter processing started for ID: {id}",
            "processing": "background"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
def process_letter_in_background(template, letter_content, id, letter_type, recipient, title, is_first, folder_id):
    try:
        file = pdfMaker.save_pdf(
            template_filename=template,
            letter_text=letter_content,
            id=id,
            pdf_path=f"output_{id}.pdf"
        )
        
        # Use the function to save and log the letter
        result = save_letter_to_drive_and_log(
            letter_file=file,
            letter_content=letter_content,
            letter_type=letter_type,
            recipient=recipient,
            title=title,
            is_first=is_first,
            folder_id=folder_id,
            id=id
        )
        
        # Clean up temporary file
        try:
            os.remove(file)
        except Exception as e:
            print(f"Error deleting temporary file: {e}")
            
        print(f"Background processing completed for letter ID: {id}")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error in background processing for letter ID {id}: {str(e)}")


@app.route("/get-context", methods=["POST"])
def get_context_route():
    letter_id=generate_letter_id()
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    category = data.get("category")
    member_name = data.get("member_name", None)
    recipient = data.get("recipient")
    is_firstTime = data.get("isFirst")
    prompt = data.get("prompt")
    recipient_job_title = data.get("recipient_job_title", "")
    recipient_title = data.get("recipient_title", "")
    organization_name = data.get("organization_name", "")
    previous_letter_content = data.get("previous_letter_content", "")
    previous_letter_id = data.get("previous_letter_id", "")

    if not category or not prompt or not recipient or is_firstTime is None:
        return jsonify({"error": "Category, prompt, recipient, and isFirst are required"}), 400
    try:
        context = n8n_get_context(category, member_name)
        instruction= context.get("data", {}).get("instruction", "")
        member_info = context.get("data", {}).get("member_info", "")
        letter = context.get("data", {}).get("letter", "")

        return jsonify({
            "status": "success",
            "data": {
                "context": context.get("data", {}),
                "system_prompt": n8n_get_system_prompt(
                    user_prompt=prompt,
                    reference_context=letter,
                    member_info=member_info,
                    writing_instructions=instruction,
                    recipient=recipient,
                    recipient_title=recipient_title,
                    recipient_job_title=recipient_job_title,
                    is_first_contact=is_firstTime,
                    previous_letter_content=previous_letter_content,
                    previous_letter_id=previous_letter_id,
                    letter_id=letter_id
                )
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route("/edit-letter", methods=["POST"])
def edit_letter_route():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    letter = data.get("letter")
    feedback = data.get("feedback")
    if not letter or not feedback:
        return jsonify({"error": "Letter and feedback are required"}), 400
    try:
        edited_letter = edit_letter_based_on_feedback(letter, feedback)
        return jsonify({
            "status": "success",
            "edited_letter": edited_letter
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)