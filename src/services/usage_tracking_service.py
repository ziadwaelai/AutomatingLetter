"""
Usage Tracking Service
Handles token counting and cost calculation for letter generation.
Tracks monthly usage in the Usage sheet.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import tiktoken

from .google_services import get_sheets_service
from ..utils import ErrorContext, StorageServiceError, measure_performance, handle_storage_errors

logger = logging.getLogger(__name__)


class UsageTrackingService:
    """Service for tracking token usage and calculating costs."""
    
    # OpenAI pricing (as of 2024-2025)
    # Approximate rates - adjust as needed
    PRICING = {
        "gpt-4o": {
            "input": 0.005 / 1000,      # $0.005 per 1K input tokens
            "output": 0.015 / 1000,     # $0.015 per 1K output tokens
        },
        "gpt-4-turbo": {
            "input": 0.01 / 1000,       # $0.01 per 1K input tokens
            "output": 0.03 / 1000,      # $0.03 per 1K output tokens
        },
        "gpt-3.5-turbo": {
            "input": 0.0005 / 1000,     # $0.0005 per 1K input tokens
            "output": 0.0015 / 1000,    # $0.0015 per 1K output tokens
        }
    }
    
    def __init__(self):
        """Initialize usage tracking service."""
        self.sheets_service = get_sheets_service()
        self.encoding = tiktoken.get_encoding("cl100k_base")  # For gpt-4/gpt-3.5
        logger.info("Usage Tracking Service initialized")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        try:
            if not text:
                return 0
            
            tokens = self.encoding.encode(text)
            count = len(tokens)
            logger.debug(f"Counted {count} tokens in text of {len(text)} characters")
            return count
            
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}, estimating as {len(text) / 4} tokens")
            # Fallback: rough estimate of 4 characters per token
            return max(1, len(text) // 4)
    
    def calculate_cost(self, 
                      input_tokens: int, 
                      output_tokens: int, 
                      model: str = "gpt-4o") -> float:
        """
        Calculate cost in USD for token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name (gpt-4o, gpt-4-turbo, gpt-3.5-turbo)
            
        Returns:
            Cost in USD
        """
        try:
            # Get pricing for model, fallback to gpt-4o if not found
            pricing = self.PRICING.get(model, self.PRICING["gpt-4o"])
            
            input_cost = input_tokens * pricing["input"]
            output_cost = output_tokens * pricing["output"]
            total_cost = input_cost + output_cost
            
            logger.debug(f"Calculated cost for {model}: {input_tokens} input tokens (${input_cost:.6f}) + {output_tokens} output tokens (${output_cost:.6f}) = ${total_cost:.6f}")
            
            return round(total_cost, 6)
            
        except Exception as e:
            logger.error(f"Error calculating cost: {e}")
            return 0.0
    
    def estimate_usage(self, 
                      prompt: str, 
                      response: str, 
                      model: str = "gpt-4o") -> Dict[str, Any]:
        """
        Estimate token usage and cost for a prompt-response pair.
        Note: This is an estimate. Actual OpenAI tokens may vary slightly.
        
        Args:
            prompt: The input prompt text
            response: The generated response text
            model: Model name
            
        Returns:
            Dictionary with token and cost information
        """
        try:
            input_tokens = self.count_tokens(prompt)
            output_tokens = self.count_tokens(response)
            total_tokens = input_tokens + output_tokens
            
            cost = self.calculate_cost(input_tokens, output_tokens, model)
            
            result = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost,
                "model": model
            }
            
            logger.info(f"Usage estimate: {total_tokens} tokens (${cost:.6f})")
            return result
            
        except Exception as e:
            logger.error(f"Error estimating usage: {e}")
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "model": model,
                "error": str(e)
            }
    
    def get_current_month_key(self) -> str:
        """
        Get current month in yyyy_mm format.
        
        Returns:
            Month key like "2024_10" for October 2024
        """
        now = datetime.now()
        return now.strftime("%Y_%m")
    
    @handle_storage_errors
    @measure_performance
    def get_or_create_usage_row(self, sheet_id: str, month_key: str) -> Tuple[int, Dict[str, Any]]:
        """
        Get existing usage row for month or create new one.
        Columns: yyyy_mm, letters_count, tokens_sum, cost_sum_usd

        Args:
            sheet_id: Google Sheet ID
            month_key: Month in yyyy_mm format

        Returns:
            Tuple of (row_number, row_data) where row_number is 0-indexed from data (not including header)
        """
        with ErrorContext("get_or_create_usage_row", {"sheet_id": sheet_id, "month": month_key}):
            try:
                sheets_service = self.sheets_service
                with sheets_service.get_client_context() as client:
                    spreadsheet = client.open_by_key(sheet_id)
                    worksheet = spreadsheet.worksheet("Usage")

                    all_values = worksheet.get_all_values()

                    if not all_values:
                        # Create headers if sheet is empty
                        headers = ["yyyy_mm", "letters_count", "tokens_sum", "cost_sum_usd"]
                        worksheet.append_row(headers)
                        all_values = [headers]
                        logger.info(f"Created headers in Usage sheet: {headers}")

                    headers = all_values[0]

                    # Check if month already exists
                    for idx, row in enumerate(all_values[1:], start=1):
                        if row and len(row) > 0 and row[0].strip() == month_key:
                            # Parse existing values
                            row_data = {
                                "yyyy_mm": row[0] if len(row) > 0 else month_key,
                                "letters_count": int(row[1]) if len(row) > 1 and row[1] else 0,
                                "tokens_sum": int(row[2]) if len(row) > 2 and row[2] else 0,
                                "cost_sum_usd": float(row[3]) if len(row) > 3 and row[3] else 0.0
                            }
                            logger.info(f"Found existing usage row for {month_key} at row {idx + 1}: {row_data}")
                            return idx + 1, row_data  # Row number (1-indexed from spreadsheet, which is idx+1 for data rows)

                    # Create new row for this month
                    new_row = [month_key, "1", "0", "0"]
                    worksheet.append_row(new_row)
                    logger.info(f"Created new usage row for {month_key}")

                    # Return the row number of the newly created row
                    new_row_number = len(all_values) + 1  # +1 because we just added a row
                    row_data = {
                        "yyyy_mm": month_key,
                        "letters_count": 1,
                        "tokens_sum": 0,
                        "cost_sum_usd": 0.0
                    }
                    return new_row_number, row_data
                
            except Exception as e:
                logger.error(f"Error getting/creating usage row: {e}")
                raise StorageServiceError(f"Failed to access Usage sheet: {e}")
    
    @handle_storage_errors
    @measure_performance
    def update_usage(self, 
                    sheet_id: str, 
                    tokens_used: int, 
                    cost_usd: float) -> Dict[str, Any]:
        """
        Update usage statistics for current month.
        Increments letters_count by 1, adds tokens to tokens_sum, adds cost to cost_sum_usd.
        
        Args:
            sheet_id: Google Sheet ID
            tokens_used: Number of tokens used in this letter generation
            cost_usd: Cost in USD for this letter generation
            
        Returns:
            Update result dictionary
        """
        with ErrorContext("update_usage", {"sheet_id": sheet_id, "tokens": tokens_used, "cost": cost_usd}):
            try:
                # Get current month
                month_key = self.get_current_month_key()
                
                # Get or create row for this month
                row_number, current_data = self.get_or_create_usage_row(sheet_id, month_key)
                
                # Calculate new values
                new_letters_count = current_data["letters_count"] + 1
                new_tokens_sum = current_data["tokens_sum"] + tokens_used
                new_cost_sum = current_data["cost_sum_usd"] + cost_usd
                
                # Prepare update data
                update_data = {
                    "yyyy_mm": month_key,
                    "letters_count": str(new_letters_count),
                    "tokens_sum": str(new_tokens_sum),
                    "cost_sum_usd": f"{new_cost_sum:.6f}"
                }
                
                # Update the row using context manager
                sheets_service = self.sheets_service
                with sheets_service.get_client_context() as client:
                    spreadsheet = client.open_by_key(sheet_id)
                    worksheet = spreadsheet.worksheet("Usage")

                    # Update cells (row_number is already 1-indexed from spreadsheet perspective)
                    worksheet.update_cell(row_number, 1, update_data["yyyy_mm"])
                    worksheet.update_cell(row_number, 2, update_data["letters_count"])
                    worksheet.update_cell(row_number, 3, update_data["tokens_sum"])
                    worksheet.update_cell(row_number, 4, update_data["cost_sum_usd"])
                
                logger.info(f"Updated usage for {month_key}: letters={new_letters_count}, tokens={new_tokens_sum}, cost=${new_cost_sum:.6f}")
                
                return {
                    "status": "success",
                    "month": month_key,
                    "row": row_number,
                    "letters_count": new_letters_count,
                    "tokens_sum": new_tokens_sum,
                    "cost_sum_usd": new_cost_sum
                }
                
            except Exception as e:
                logger.error(f"Error updating usage: {e}")
                raise StorageServiceError(f"Failed to update usage statistics: {e}")
    
    @handle_storage_errors
    @measure_performance
    def get_quota_limit(self, sheet_id: str) -> Optional[int]:
        """
        Get monthly quota limit from Settings sheet.
        Searches for key "quota_month" and returns the value.

        Args:
            sheet_id: Google Sheet ID

        Returns:
            Quota limit (int) or None if not found
        """
        with ErrorContext("get_quota_limit", {"sheet_id": sheet_id}):
            try:
                sheets_service = self.sheets_service
                with sheets_service.get_client_context() as client:
                    spreadsheet = client.open_by_key(sheet_id)

                    try:
                        worksheet = spreadsheet.worksheet("Settings")
                    except Exception:
                        logger.warning(f"Settings sheet not found in sheet {sheet_id}")
                        return None

                    all_values = worksheet.get_all_values()
                    if not all_values or len(all_values) < 2:
                        logger.warning(f"Settings sheet is empty in sheet {sheet_id}")
                        return None

                    # Parse headers (first row)
                    headers = all_values[0]

                    # Find column indices for key and value
                    key_idx = None
                    value_idx = None
                    for idx, header in enumerate(headers):
                        if header.strip().lower() == "key":
                            key_idx = idx
                        elif header.strip().lower() == "value":
                            value_idx = idx

                    if key_idx is None or value_idx is None:
                        logger.error(f"Settings sheet missing 'key' or 'value' columns")
                        return None

                    # Search for quota_month key
                    for row in all_values[1:]:  # Skip header row
                        if len(row) > max(key_idx, value_idx):
                            row_key = row[key_idx].strip().lower() if key_idx < len(row) else ""
                            if row_key == "quota_month":
                                try:
                                    quota_value = int(row[value_idx].strip()) if value_idx < len(row) else None
                                    if quota_value is not None:
                                        logger.info(f"Found quota_month limit: {quota_value}")
                                        return quota_value
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid quota_month value: {row[value_idx]}")
                                    return None

                    logger.warning(f"quota_month not found in Settings sheet")
                    return None
                
            except Exception as e:
                logger.error(f"Error getting quota limit: {e}")
                return None
    
    @handle_storage_errors
    @measure_performance
    def check_quota(self, sheet_id: str) -> Dict[str, Any]:
        """
        Check if current month has exceeded quota.
        
        Args:
            sheet_id: Google Sheet ID
            
        Returns:
            Dictionary with:
            - "status": "allowed" or "exceeded"
            - "current_count": Current month's letter count
            - "quota_limit": Monthly quota limit (None if not set)
            - "remaining": Remaining letters this month (only if status is "allowed")
        """
        with ErrorContext("check_quota", {"sheet_id": sheet_id}):
            try:
                # Get quota limit from Settings sheet
                quota_limit = self.get_quota_limit(sheet_id)
                
                if quota_limit is None:
                    # No quota set, allow unlimited
                    logger.info("No quota limit set, allowing generation")
                    return {
                        "status": "allowed",
                        "current_count": 0,
                        "quota_limit": None,
                        "remaining": None,
                        "reason": "No quota configured"
                    }
                
                # Get current month's usage
                month_key = self.get_current_month_key()
                
                try:
                    row_number, usage_data = self.get_or_create_usage_row(sheet_id, month_key)
                    current_count = usage_data["letters_count"]
                except Exception as e:
                    logger.warning(f"Could not get usage data: {e}, assuming 0 letters")
                    current_count = 0
                
                # Check if quota exceeded
                if current_count >= quota_limit:
                    logger.warning(f"Quota exceeded: {current_count} >= {quota_limit}")
                    return {
                        "status": "exceeded",
                        "current_count": current_count,
                        "quota_limit": quota_limit,
                        "reason": f"Monthly quota of {quota_limit} letters has been reached"
                    }
                
                # Quota available
                remaining = quota_limit - current_count
                logger.info(f"Quota check passed: {current_count}/{quota_limit} ({remaining} remaining)")
                return {
                    "status": "allowed",
                    "current_count": current_count,
                    "quota_limit": quota_limit,
                    "remaining": remaining,
                    "reason": f"{remaining} letters remaining this month"
                }
                
            except Exception as e:
                logger.error(f"Error checking quota: {e}")
                # If error, allow generation (fail open)
                return {
                    "status": "allowed",
                    "error": str(e),
                    "reason": "Error checking quota, allowing generation"
                }
    
    @handle_storage_errors
    @measure_performance
    def get_memory_instructions(self, sheet_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get memory instructions from Settings sheet.
        Searches for key "memory_instructions" and returns parsed JSON value.
        
        Args:
            sheet_id: Google Sheet ID
            
        Returns:
            List of instruction dictionaries or None if not found
        """
        with ErrorContext("get_memory_instructions", {"sheet_id": sheet_id}):
            try:
                sheets_service = self.sheets_service
                with sheets_service.get_client_context() as client:
                    spreadsheet = client.open_by_key(sheet_id)

                    try:
                        worksheet = spreadsheet.worksheet("Settings")
                    except Exception:
                        logger.warning(f"Settings sheet not found in sheet {sheet_id}")
                        return None

                    all_values = worksheet.get_all_values()
                    if not all_values or len(all_values) < 2:
                        logger.warning(f"Settings sheet is empty in sheet {sheet_id}")
                        return None

                    # Parse headers (first row)
                    headers = all_values[0]

                    # Find column indices
                    key_idx = None
                    value_idx = None
                    for idx, header in enumerate(headers):
                        if header.strip().lower() == "key":
                            key_idx = idx
                        elif header.strip().lower() == "value":
                            value_idx = idx

                    if key_idx is None or value_idx is None:
                        logger.error(f"Settings sheet missing 'key' or 'value' columns")
                        return None

                    # Search for memory_instructions key
                    for row in all_values[1:]:  # Skip header row
                        if len(row) > max(key_idx, value_idx):
                            row_key = row[key_idx].strip().lower() if key_idx < len(row) else ""
                            if row_key == "memory_instructions":
                                try:
                                    import json
                                    instructions_json = row[value_idx].strip() if value_idx < len(row) else ""
                                    if instructions_json:
                                        instructions = json.loads(instructions_json)
                                        logger.info(f"Found {len(instructions)} memory instructions from Settings sheet")
                                        return instructions
                                except (json.JSONDecodeError, ValueError) as e:
                                    logger.error(f"Failed to parse memory_instructions JSON: {e}")
                                    return None

                    logger.debug(f"memory_instructions not found in Settings sheet")
                    return None
                
            except Exception as e:
                logger.error(f"Error getting memory instructions: {e}")
                return None
    
    @handle_storage_errors
    @measure_performance
    def save_memory_instructions(self, sheet_id: str, instructions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Save/update memory instructions in Settings sheet.
        Searches for key "memory_instructions" and updates or creates the row.
        
        Args:
            sheet_id: Google Sheet ID
            instructions: List of instruction dictionaries to save
            
        Returns:
            Update result dictionary
        """
        with ErrorContext("save_memory_instructions", {"sheet_id": sheet_id}):
            try:
                import json

                sheets_service = self.sheets_service
                with sheets_service.get_client_context() as client:
                    spreadsheet = client.open_by_key(sheet_id)

                    try:
                        worksheet = spreadsheet.worksheet("Settings")
                    except Exception:
                        logger.error(f"Settings sheet not found in sheet {sheet_id}")
                        return {
                            "status": "error",
                            "message": "Settings sheet not found"
                        }

                    all_values = worksheet.get_all_values()

                    if not all_values:
                        # Create headers if sheet is empty
                        headers = ["key", "value"]
                        worksheet.append_row(headers)
                        all_values = [headers]
                        logger.info("Created headers in Settings sheet")

                    # Convert instructions to JSON string
                    instructions_json = json.dumps(instructions, ensure_ascii=False, indent=2)

                    # Search for existing memory_instructions row
                    headers = all_values[0]
                    key_idx = None
                    value_idx = None
                    for idx, header in enumerate(headers):
                        if header.strip().lower() == "key":
                            key_idx = idx
                        elif header.strip().lower() == "value":
                            value_idx = idx

                    if key_idx is None or value_idx is None:
                        logger.error(f"Settings sheet missing 'key' or 'value' columns")
                        return {
                            "status": "error",
                            "message": "Settings sheet missing required columns"
                        }

                    # Find and update existing row or create new one
                    found = False
                    for row_idx, row in enumerate(all_values[1:], start=2):  # Start at row 2 (after header)
                        if len(row) > key_idx:
                            row_key = row[key_idx].strip().lower() if key_idx < len(row) else ""
                            if row_key == "memory_instructions":
                                # Update existing row
                                worksheet.update_cell(row_idx, value_idx + 1, instructions_json)
                                logger.info(f"Updated memory_instructions in Settings sheet at row {row_idx}")
                                found = True
                                break

                    if not found:
                        # Create new row
                        new_row = [""] * len(headers)
                        new_row[key_idx] = "memory_instructions"
                        new_row[value_idx] = instructions_json
                        worksheet.append_row(new_row)
                        logger.info(f"Created new memory_instructions row in Settings sheet")

                    return {
                        "status": "success",
                        "sheet_id": sheet_id,
                        "instructions_count": len(instructions),
                        "row_type": "updated" if found else "created"
                    }
                
            except Exception as e:
                logger.error(f"Error saving memory instructions: {e}")
                raise StorageServiceError(f"Failed to save memory instructions: {e}")
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "service": "UsageTrackingService",
            "pricing_models": list(self.PRICING.keys()),
            "status": "healthy"
        }

    @handle_storage_errors
    @measure_performance
    def get_prompt_template(self, sheet_id: str) -> Optional[str]:
        """
        Get prompt template from Settings sheet.
        Searches for key "Prompt" and returns the template value.

        Args:
            sheet_id: Google Sheet ID

        Returns:
            Prompt template string if found, None otherwise
        """
        with ErrorContext("get_prompt_template", {"sheet_id": sheet_id}):
            try:
                sheets_service = self.sheets_service
                with sheets_service.get_client_context() as client:
                    spreadsheet = client.open_by_key(sheet_id)

                    try:
                        worksheet = spreadsheet.worksheet("Settings")
                    except Exception as e:
                        logger.warning(f"Settings sheet not found in sheet {sheet_id}: {e}")
                        return None

                    all_values = worksheet.get_all_values()
                    if not all_values or len(all_values) < 2:
                        logger.warning(f"Settings sheet is empty or has no data rows in sheet {sheet_id}")
                        return None

                    # Parse headers (first row)
                    headers = all_values[0]
                    logger.debug(f"Settings sheet headers: {headers}")

                    # Find column indices
                    key_idx = None
                    value_idx = None
                    for idx, header in enumerate(headers):
                        if header.strip().lower() == "key":
                            key_idx = idx
                        elif header.strip().lower() == "value":
                            value_idx = idx

                    if key_idx is None or value_idx is None:
                        logger.error(f"Settings sheet missing 'key' or 'value' columns. Headers: {headers}")
                        return None

                    logger.debug(f"key_idx={key_idx}, value_idx={value_idx}")

                    # Search for Prompt key
                    for row_idx, row in enumerate(all_values[1:], start=2):  # Skip header row
                        if len(row) > max(key_idx, value_idx):
                            row_key = row[key_idx].strip() if key_idx < len(row) else ""
                            logger.debug(f"Row {row_idx}: key='{row_key}'")
                            if row_key == "Prompt":
                                template = row[value_idx].strip() if value_idx < len(row) else ""
                                if template:
                                    logger.info(f"Found prompt template from Settings sheet (length: {len(template)} chars)")
                                    return template
                                else:
                                    logger.warning(f"Prompt key found but value is empty")
                                    return None

                    logger.info(f"Prompt key not found in Settings sheet. Available keys: {[row[key_idx].strip() for row in all_values[1:] if len(row) > key_idx]}")
                    return None

            except Exception as e:
                logger.error(f"Error getting prompt template: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return None

    @handle_storage_errors
    @measure_performance
    def get_context_instructions(self, sheet_id: str, instruction_key: str) -> Optional[str]:
        """
        Get context instructions from Settings sheet by key.
        Searches for a specific instruction key and returns the value.

        Args:
            sheet_id: Google Sheet ID
            instruction_key: The instruction key to search for (e.g., "recipient_title_instructions", "recipient_job_title_instructions", "first_contact_instructions", "existing_contact_instructions")

        Returns:
            Instruction text if found, None otherwise
        """
        with ErrorContext("get_context_instructions", {"sheet_id": sheet_id, "instruction_key": instruction_key}):
            try:
                sheets_service = self.sheets_service
                with sheets_service.get_client_context() as client:
                    spreadsheet = client.open_by_key(sheet_id)

                    try:
                        worksheet = spreadsheet.worksheet("Settings")
                    except Exception:
                        logger.warning(f"Settings sheet not found in sheet {sheet_id}")
                        return None

                    all_values = worksheet.get_all_values()
                    if not all_values or len(all_values) < 2:
                        logger.warning(f"Settings sheet is empty in sheet {sheet_id}")
                        return None

                    # Parse headers (first row)
                    headers = all_values[0]

                    # Find column indices
                    key_idx = None
                    value_idx = None
                    for idx, header in enumerate(headers):
                        if header.strip().lower() == "key":
                            key_idx = idx
                        elif header.strip().lower() == "value":
                            value_idx = idx

                    if key_idx is None or value_idx is None:
                        logger.error(f"Settings sheet missing 'key' or 'value' columns")
                        return None

                    # Search for the instruction key
                    for row in all_values[1:]:  # Skip header row
                        if len(row) > max(key_idx, value_idx):
                            row_key = row[key_idx].strip() if key_idx < len(row) else ""
                            if row_key == instruction_key:
                                instruction = row[value_idx].strip() if value_idx < len(row) else ""
                                if instruction:
                                    logger.debug(f"Found context instruction '{instruction_key}' from Settings sheet")
                                    return instruction

                    logger.debug(f"Context instruction '{instruction_key}' not found in Settings sheet")
                    return None

            except Exception as e:
                logger.error(f"Error getting context instructions: {e}")
                return None


# Global service instance
_usage_service = None


def get_usage_tracking_service() -> UsageTrackingService:
    """Get the global usage tracking service instance."""
    global _usage_service
    if _usage_service is None:
        _usage_service = UsageTrackingService()
    return _usage_service
