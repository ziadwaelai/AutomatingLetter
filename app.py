from flask import Flask, request, jsonify
from ai_generator import generate_arabic_letter
from google_services import get_letter_config_by_category , append_letter_to_sheet
# from drive_logger import save_letter_to_drive_and_log
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

app = Flask(__name__)

@app.route("/generate-letter", methods=["POST"])
def generate_letter_route():
    data = request.json
    category = data.get("category")
    title = data.get("title")
    recipient = data.get("recipient")
    is_firstTime = data.get("is_firstTime")
    prompt = data.get("prompt")

    if not category or not prompt or not title or not recipient or not is_firstTime:
        return jsonify({"error": "Missing required fields"}) , 400
    try:
        try:
            rerference_letter = get_letter_config_by_category(category)["ideal"]
            instractions = get_letter_config_by_category(category)["instruction"]
        except ValueError as e:
            rerference_letter = None
        letter = generate_arabic_letter(
            user_prompt=prompt,
            reference_letter= rerference_letter,
            title = title,
            recipient = recipient,
            writing_instructions=instractions,
            
        )
        return jsonify({"letter": letter}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



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


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)