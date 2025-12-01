"""
API Routes for WhatsApp Integration
Handles WhatsApp letter sending and status updates.
"""

import logging
import requests
from typing import Dict, Any
from flask import Blueprint, request, jsonify
from pydantic import ValidationError, BaseModel, Field

from ..models import ErrorResponse, SuccessResponse
from ..services import get_sheets_service
from ..utils import (
    ErrorContext,
    build_error_response,
    validate_and_raise,
    measure_performance
)

logger = logging.getLogger(__name__)

# Create blueprint
whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/api/v1/whatsapp')

class WhatsAppSendRequest(BaseModel):
    """Request model for WhatsApp sending."""
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number to send letter to")
    letter_id: str = Field(..., min_length=1, max_length=50, description="Letter ID to send")

class WhatsAppStatusUpdateRequest(BaseModel):
    """Request model for WhatsApp status update."""
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number used")
    status: str = Field(..., min_length=1, max_length=50, description="New status")
    clear_assignment: bool = Field(default=True, description="Whether to clear the letter assignment from WhatsApp sheet")

class GetLetterRequest(BaseModel):
    """Request model for getting letter data."""
    letter_id: str = Field(..., min_length=1, max_length=50, description="Letter ID to retrieve")

@whatsapp_bp.route('/send', methods=['POST'])
@measure_performance
def send_whatsapp_letter():
    """
    Send a letter via WhatsApp.
    
    Flow:
    1. Check if phone number already has a letter assigned (letter_id not empty)
    2. If assigned, return error
    3. If not assigned, assign the letter_id to the phone number
    4. Get letter data from Google Sheets
    5. Send to webhook
    
    Request Body:
        phone_number: str - Phone number to send to
        letter_id: str - Letter ID to send
        
    Returns:
        Success or error message
    """
    with ErrorContext("send_whatsapp_letter"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "Request must be JSON"}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            # Validate using Pydantic
            try:
                send_request = WhatsAppSendRequest(**data)
            except ValidationError as e:
                return jsonify({"error": "Validation error", "details": e.errors()}), 400
            
            sheets_service = get_sheets_service()
            
            # Step 1: Check WhatsApp sheet for existing assignment
            logger.info(f"Checking WhatsApp sheet for phone number: {send_request.phone_number}")
            
            try:
                # Get all records from WhatsApp sheet
                whatsapp_worksheet = sheets_service.client.open(sheets_service.config.database.spreadsheet_name).worksheet("WhatApp")
                whatsapp_records = whatsapp_worksheet.get_all_records()
                
                # Find the record with matching phone number
                target_row = None
                existing_letter_id = None
                Name=None
                
                for idx, record in enumerate(whatsapp_records):
                    if str(record.get('Number', '')).strip() == str(send_request.phone_number).strip():
                        target_row = idx + 2  # +2 because records start from row 2 (row 1 is header)
                        existing_letter_id = str(record.get('Letter_Id', '')).strip()
                        Name=str(record.get('Name', '')).strip()
                        break
                
                if target_row is None:
                    return jsonify({
                        "error": "Phone number not found in WhatsApp sheet",
                        "message": "The provided phone number is not registered"
                    }), 404
                
                # Step 2: Check if already assigned
                if existing_letter_id and existing_letter_id != "":
                    return jsonify({
                        "error": "Phone number already assigned",
                        "message": f"This phone number is already assigned to letter {existing_letter_id}. The signer is busy now."
                    }), 409
                
                # Step 3: Assign letter_id to the phone number
                logger.info(f"Assigning letter_id {send_request.letter_id} to phone number {send_request.phone_number} at row {target_row}")
                whatsapp_worksheet.update_cell(target_row, 3, send_request.letter_id)  # Column C (Letter_id)
                
                # Step 4: Get letter data from Submissions sheet
                logger.info(f"Fetching letter data for ID: {send_request.letter_id}")
                
                submissions_worksheet = sheets_service.client.open(sheets_service.config.database.spreadsheet_name).worksheet("Submissions")
                submissions_records = submissions_worksheet.get_all_records()
                
                letter_data = None
                for record in submissions_records:
                    if str(record.get('ID', '')).strip() == str(send_request.letter_id).strip():
                        letter_data = record
                        break
                
                if not letter_data:
                    # Rollback: Clear the letter_id we just assigned
                    whatsapp_worksheet.update_cell(target_row, 3, "")
                    return jsonify({
                        "error": "Letter not found",
                        "message": f"Letter with ID {send_request.letter_id} not found in submissions"
                    }), 404
                
                # Step 5: Send to webhook
                webhook_url = "https://superpowerss.app.n8n.cloud/webhook/send"
                webhook_payload = {
                    "phone_number": send_request.phone_number,
                    "name": Name,
                    "letter_id": send_request.letter_id,
                    "letter_data": letter_data
                }
                
                logger.info(f"Sending letter data to webhook: {webhook_url}")
                
                try:
                    webhook_response = requests.post(
                        webhook_url,
                        json=webhook_payload,
                        timeout=30,
                        headers={'Content-Type': 'application/json'}
                    )
                    webhook_response.raise_for_status()
                    
                    logger.info(f"Successfully sent letter {send_request.letter_id} to phone {send_request.phone_number}")
                    
                    return jsonify({
                        "message": "Letter sent successfully via WhatsApp",
                        "letter_id": send_request.letter_id,
                        "phone_number": send_request.phone_number,
                        "webhook_status": webhook_response.status_code
                    }), 200
                    
                except requests.RequestException as e:
                    # Rollback: Clear the letter_id we assigned
                    whatsapp_worksheet.update_cell(target_row, 3, "")
                    logger.error(f"Webhook request failed: {e}")
                    
                    return jsonify({
                        "error": "Webhook delivery failed",
                        "message": f"Failed to send to webhook: {str(e)}"
                    }), 500
                
            except Exception as e:
                logger.error(f"Error accessing Google Sheets: {e}")
                return jsonify({
                    "error": "Database error",
                    "message": f"Failed to access Google Sheets: {str(e)}"
                }), 500
                
        except Exception as e:
            logger.error(f"Unexpected error in send_whatsapp_letter: {e}")
            return build_error_response("send_whatsapp_letter", str(e)), 500

@whatsapp_bp.route('/update-status', methods=['POST'])
@measure_performance
def update_whatsapp_status():
    """
    Update letter status and clear WhatsApp assignment.
    
    Flow:
    1. Get letter_id from WhatsApp sheet by phone number
    2. Update status in Submissions sheet by letter_id
    3. Clear letter_id from WhatsApp sheet by phone number
    
    Request Body:
        phone_number: str - Phone number to clear assignment
        status: str - New status value
        
    Returns:
        Success or error message
    """
    with ErrorContext("update_whatsapp_status"):
        try:
            # Validate request data
            if not request.is_json:
                return jsonify({"error": "Request must be JSON"}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            # Validate using Pydantic
            try:
                status_request = WhatsAppStatusUpdateRequest(**data)
            except ValidationError as e:
                return jsonify({"error": "Validation error", "details": e.errors()}), 400
            
            sheets_service = get_sheets_service()
            
            # Step 1: Get letter_id from WhatsApp sheet
            logger.info(f"Getting letter_id for phone number {status_request.phone_number}")
            
            try:
                whatsapp_worksheet = sheets_service.client.open(sheets_service.config.database.spreadsheet_name).worksheet("WhatApp")
                whatsapp_records = whatsapp_worksheet.get_all_records()
                
                target_row = None
                letter_id = None
                
                for idx, record in enumerate(whatsapp_records):
                    if str(record.get('Number', '')).strip() == str(status_request.phone_number).strip():
                        target_row = idx + 2  # +2 because records start from row 2
                        letter_id = str(record.get('Letter_Id', '')).strip()
                        break
                
                if target_row is None:
                    return jsonify({
                        "error": "Phone number not found",
                        "message": f"Phone number {status_request.phone_number} not found in WhatsApp sheet"
                    }), 404
                
                if not letter_id or letter_id == "":
                    return jsonify({
                        "error": "No letter assigned",
                        "message": f"Phone number {status_request.phone_number} has no letter assigned"
                    }), 400
                
                logger.info(f"Found letter_id {letter_id} for phone number {status_request.phone_number}")
                
            except Exception as e:
                logger.error(f"Error accessing WhatsApp sheet: {e}")
                return jsonify({
                    "error": "Database error",
                    "message": f"Failed to access WhatsApp sheet: {str(e)}"
                }), 500
            
            # Step 2: Update status in Submissions sheet
            logger.info(f"Updating status for letter_id {letter_id} to {status_request.status}")
            
            try:
                update_result = sheets_service.update_row_by_id(
                    spreadsheet_name=sheets_service.config.database.spreadsheet_name,
                    worksheet_name="Submissions",
                    letter_id=letter_id,
                    updates={"Status": status_request.status},
                    id_column="ID"
                )
                
                logger.info(f"Successfully updated status in Submissions sheet: {update_result}")
                
            except Exception as e:
                logger.error(f"Failed to update status in Submissions sheet: {e}")
                return jsonify({
                    "error": "Failed to update letter status",
                    "message": str(e)
                }), 500
            
            # Step 3: Clear letter_id from WhatsApp sheet (if flag is True)
            if status_request.clear_assignment:
                logger.info(f"Clearing letter_id for phone number {status_request.phone_number}")

                try:
                    # Clear the letter_id (column C)
                    whatsapp_worksheet.update_cell(target_row, 3, "")
                    logger.info(f"Successfully cleared letter_id for phone number {status_request.phone_number}")

                    return jsonify({
                        "message": "Status updated and WhatsApp assignment cleared successfully",
                        "letter_id": letter_id,
                        "phone_number": status_request.phone_number,
                        "new_status": status_request.status,
                        "submissions_updated": True,
                        "whatsapp_cleared": True
                    }), 200

                except Exception as e:
                    logger.error(f"Failed to clear WhatsApp assignment: {e}")
                    # Main update was successful, so return partial success
                    return jsonify({
                        "message": "Status updated but failed to clear WhatsApp assignment",
                        "letter_id": letter_id,
                        "phone_number": status_request.phone_number,
                        "new_status": status_request.status,
                        "submissions_updated": True,
                        "whatsapp_cleared": False,
                        "warning": str(e)
                    }), 200
            else:
                # Don't clear assignment, just return success
                logger.info(f"Status updated without clearing assignment (clear_assignment=False)")

                return jsonify({
                    "message": "Status updated successfully (assignment not cleared)",
                    "letter_id": letter_id,
                    "phone_number": status_request.phone_number,
                    "new_status": status_request.status,
                    "submissions_updated": True,
                    "whatsapp_cleared": False
                }), 200
                
        except Exception as e:
            logger.error(f"Unexpected error in update_whatsapp_status: {e}")
            return build_error_response("update_whatsapp_status", str(e)), 500

@whatsapp_bp.route('/letter/<letter_id>', methods=['GET'])
@measure_performance
def get_letter_by_id(letter_id: str):
    """
    Get letter data by ID from Submissions sheet.
    
    Args:
        letter_id: Letter ID to retrieve
        
    Returns:
        Letter data or error message
    """
    with ErrorContext("get_letter_by_id"):
        try:
            # Validate letter_id
            if not letter_id or not letter_id.strip():
                return jsonify({
                    "error": "Invalid letter ID",
                    "message": "Letter ID is required and cannot be empty"
                }), 400
            
            letter_id = letter_id.strip()
            
            sheets_service = get_sheets_service()
            
            # Get letter data from Submissions sheet
            logger.info(f"Fetching letter data for ID: {letter_id}")
            
            try:
                submissions_worksheet = sheets_service.client.open(sheets_service.config.database.spreadsheet_name).worksheet("Submissions")
                submissions_records = submissions_worksheet.get_all_records()
                
                letter_data = None
                for record in submissions_records:
                    if str(record.get('ID', '')).strip() == letter_id:
                        letter_data = record
                        break
                
                if not letter_data:
                    return jsonify({
                        "error": "Letter not found",
                        "message": f"Letter with ID {letter_id} not found in submissions"
                    }), 404
                
                logger.info(f"Successfully retrieved letter data for ID: {letter_id}")
                
                return jsonify({
                    "message": "Letter data retrieved successfully",
                    "letter_id": letter_id,
                    "letter_data": letter_data
                }), 200
                
            except Exception as e:
                logger.error(f"Error accessing Google Sheets: {e}")
                return jsonify({
                    "error": "Database error",
                    "message": f"Failed to access Google Sheets: {str(e)}"
                }), 500
                
        except Exception as e:
            logger.error(f"Unexpected error in get_letter_by_id: {e}")
            return build_error_response("get_letter_by_id", str(e)), 500

@whatsapp_bp.route('/assigned-letter/<phone_number>', methods=['GET'])
@measure_performance
def get_assigned_letter_id(phone_number: str):
    """
    Get assigned letter ID, Title, and Sign by phone number from WhatsApp sheet.

    Args:
        phone_number: Phone number to check

    Returns:
        Assigned letter ID, Name, Title (from WhatsApp sheet with fallback to Submissions),
        Sign URL (from WhatsApp sheet) or error message
    """
    with ErrorContext("get_assigned_letter_id"):
        try:
            # Validate phone number
            if not phone_number or not phone_number.strip():
                return jsonify({
                    "error": "Invalid phone number",
                    "message": "Phone number is required and cannot be empty"
                }), 400

            phone_number = phone_number.strip()

            sheets_service = get_sheets_service()

            # Get assigned letter_id from WhatsApp sheet
            logger.info(f"Getting assigned letter_id for phone number: {phone_number}")

            try:
                whatsapp_worksheet = sheets_service.client.open(sheets_service.config.database.spreadsheet_name).worksheet("WhatApp")
                whatsapp_records = whatsapp_worksheet.get_all_records()

                # Find the record with matching phone number
                assigned_letter_id = None
                name = None
                sign = None
                title_from_whatsapp = None

                for record in whatsapp_records:
                    if str(record.get('Number', '')).strip() == str(phone_number).strip():
                        assigned_letter_id = str(record.get('Letter_Id', '')).strip()
                        name = str(record.get('Name', '')).strip()
                        sign = str(record.get('Sign', '')).strip()
                        title_from_whatsapp = str(record.get('Title', '')).strip()
                        break

                if assigned_letter_id is None:
                    return jsonify({
                        "error": "Phone number not found",
                        "message": f"Phone number {phone_number} not found in WhatsApp sheet"
                    }), 404

                # Check if letter is assigned
                if not assigned_letter_id or assigned_letter_id == "":
                    return jsonify({
                        "message": "No letter assigned",
                        "phone_number": phone_number,
                        "name": name,
                        "assigned_letter_id": None,
                        "title": title_from_whatsapp if title_from_whatsapp else None,
                        "sign": sign if sign else None,
                        "is_assigned": False
                    }), 200

                logger.info(f"Found assigned letter_id {assigned_letter_id} for phone number {phone_number}")

                # Fetch Title from Submissions sheet as fallback
                title = title_from_whatsapp  # Use WhatsApp sheet title first

                # If no title in WhatsApp sheet, try to get it from Submissions sheet
                if not title:
                    try:
                        submissions_worksheet = sheets_service.client.open(sheets_service.config.database.spreadsheet_name).worksheet("Submissions")
                        submissions_records = submissions_worksheet.get_all_records()

                        # Find the record with matching letter ID
                        for submission in submissions_records:
                            if str(submission.get('ID', '')).strip() == str(assigned_letter_id).strip():
                                title = str(submission.get('Title', '')).strip()
                                logger.info(f"Found Title from Submissions: {title} for letter_id {assigned_letter_id}")
                                break

                    except Exception as submissions_error:
                        logger.warning(f"Could not fetch Title from Submissions sheet: {submissions_error}")
                        # Continue with None value if we can't fetch from Submissions

                return jsonify({
                    "message": "Letter assignment found",
                    "phone_number": phone_number,
                    "name": name,
                    "assigned_letter_id": assigned_letter_id,
                    "title": title if title else None,
                    "sign": sign if sign else None,
                    "is_assigned": True
                }), 200

            except Exception as e:
                logger.error(f"Error accessing WhatsApp sheet: {e}")
                return jsonify({
                    "error": "Database error",
                    "message": f"Failed to access WhatsApp sheet: {str(e)}"
                }), 500

        except Exception as e:
            logger.error(f"Unexpected error in get_assigned_letter_id: {e}")
            return build_error_response("get_assigned_letter_id", str(e)), 500

@whatsapp_bp.route('/users', methods=['GET'])
@measure_performance
def list_whatsapp_users():
    """
    List all users from the WhatsApp sheet with their name and phone number.

    Returns:
        List of users with name and number in format: [{"name": "...", "number": "..."}]
    """
    with ErrorContext("list_whatsapp_users"):
        try:
            sheets_service = get_sheets_service()

            # Get all records from WhatsApp sheet
            logger.info("Fetching all users from WhatsApp sheet")

            try:
                whatsapp_worksheet = sheets_service.client.open(sheets_service.config.database.spreadsheet_name).worksheet("WhatApp")
                whatsapp_records = whatsapp_worksheet.get_all_records()

                # Extract name and number from each record
                users_list = []
                for record in whatsapp_records:
                    name = str(record.get('Name', '')).strip()
                    number = str(record.get('Number', '')).strip()

                    # Only include records that have both name and number
                    if name and number:
                        users_list.append({
                            "name": name,
                            "number": number
                        })

                logger.info(f"Successfully retrieved {len(users_list)} users from WhatsApp sheet")

                return jsonify({
                    "message": "Users retrieved successfully",
                    "count": len(users_list),
                    "users": users_list
                }), 200

            except Exception as e:
                logger.error(f"Error accessing WhatsApp sheet: {e}")
                return jsonify({
                    "error": "Database error",
                    "message": f"Failed to access WhatsApp sheet: {str(e)}"
                }), 500

        except Exception as e:
            logger.error(f"Unexpected error in list_whatsapp_users: {e}")
            return build_error_response("list_whatsapp_users", str(e)), 500