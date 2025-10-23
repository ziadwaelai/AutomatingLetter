"""
API Routes for Submissions Data
Handles all submissions retrieval endpoints with pagination support.
"""

import logging
from typing import Dict, Any, List, Tuple
from flask import Blueprint, request, jsonify

from ..services import get_sheets_service
from ..utils import (
    ErrorContext,
    build_error_response,
    measure_performance,
    require_auth
)

logger = logging.getLogger(__name__)

# Create blueprint
submissions_bp = Blueprint('submissions', __name__, url_prefix='/api/v1/submissions')


def paginate_data(data: List[List[str]], page: int = 1, page_size: int = 10) -> Tuple[List[List[str]], int, int]:
    """
    Paginate a list of data rows.

    Args:
        data: List of rows to paginate
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Tuple of (paginated_rows, total_pages, total_items)
    """
    total_items = len(data)
    total_pages = (total_items + page_size - 1) // page_size

    # Validate page number
    if page < 1:
        page = 1
    if page > total_pages and total_items > 0:
        page = total_pages

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    paginated_rows = data[start_idx:end_idx]
    return paginated_rows, total_pages, total_items


def format_submissions_response(headers: List[str], rows: List[List[str]],
                               page: int, page_size: int, total_pages: int,
                               total_items: int) -> Dict[str, Any]:
    """
    Format submissions data into a structured response.

    Args:
        headers: Column headers
        rows: Data rows
        page: Current page number
        page_size: Page size
        total_pages: Total number of pages
        total_items: Total number of items

    Returns:
        Formatted response dictionary
    """
    submissions = []
    for row in rows:
        # Convert row list to dict using headers
        submission = {}
        for idx, header in enumerate(headers):
            if idx < len(row):
                submission[header.strip()] = row[idx]
            else:
                submission[header.strip()] = ""
        submissions.append(submission)

    return {
        "status": "success",
        "data": submissions,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_items": total_items,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "count": len(submissions)
    }


@submissions_bp.route('', methods=['GET'])
@measure_performance
@require_auth
def get_submissions(user_info):
    """
    Get all submissions from the user's Submissions sheet with pagination.

    Query Parameters:
        page (int): Page number (default: 1)
        page_size (int): Items per page (default: 10, max: 100)
        sort_by (str): Column to sort by (optional)
        sort_order (str): 'asc' or 'desc' (default: 'desc')

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        Paginated list of submissions from the Submissions sheet
    """
    with ErrorContext("get_submissions_api"):
        try:
            # Extract sheet_id from JWT token
            sheet_id = user_info.get('sheet_id')
            user_email = user_info.get('user', {}).get('email', 'unknown')

            if not sheet_id:
                return build_error_response("معرف الجدول غير موجود في التوكن", 400)

            logger.info(f"Submissions query request from user: {user_email}, sheet: {sheet_id}")

            # Get query parameters
            try:
                page = int(request.args.get('page', 1))
                page_size = int(request.args.get('page_size', 10))
            except ValueError:
                return build_error_response("معاملات الصفحة غير صحيحة (يجب أن تكون أرقام)", 400)

            # Validate pagination parameters
            if page < 1:
                return build_error_response("رقم الصفحة يجب أن يكون 1 أو أكثر", 400)
            if page_size < 1:
                return build_error_response("حجم الصفحة يجب أن يكون 1 أو أكثر", 400)
            if page_size > 100:
                page_size = 100  # Cap at 100 for performance

            sort_by = request.args.get('sort_by', None)
            sort_order = request.args.get('sort_order', 'desc').lower()

            if sort_order not in ['asc', 'desc']:
                return build_error_response("ترتيب الفرز يجب أن يكون 'asc' أو 'desc'", 400)

            # Get sheets service
            sheets_service = get_sheets_service()

            # Fetch submissions data from user's sheet
            logger.debug(f"Fetching Submissions sheet from user's sheet: {sheet_id}")
            try:
                spreadsheet = sheets_service.client.open_by_key(sheet_id)
                worksheet = spreadsheet.worksheet("Submissions")
            except Exception as e:
                logger.warning(f"Submissions sheet not found in sheet {sheet_id}: {e}")
                return build_error_response(
                    "لم يتم العثور على ورقة 'Submissions' في الجدول",
                    404
                )

            # Get all data from sheet
            all_values = worksheet.get_all_values()

            if not all_values:
                return build_error_response("ورقة Submissions فارغة", 404)

            # First row is headers
            headers = all_values[0]
            data_rows = all_values[1:]  # Data rows (skip header)

            logger.info(f"Found {len(data_rows)} submissions in sheet {sheet_id}")

            # Apply sorting if requested
            if sort_by and sort_by in headers:
                sort_idx = headers.index(sort_by)
                try:
                    # Try to sort as numbers first
                    data_rows.sort(
                        key=lambda row: float(row[sort_idx]) if sort_idx < len(row) and row[sort_idx] else 0,
                        reverse=(sort_order == 'desc')
                    )
                except (ValueError, IndexError):
                    # Fall back to string sorting
                    data_rows.sort(
                        key=lambda row: row[sort_idx] if sort_idx < len(row) else "",
                        reverse=(sort_order == 'desc')
                    )
                logger.debug(f"Sorted data by '{sort_by}' ({sort_order})")

            # Paginate data
            paginated_rows, total_pages, total_items = paginate_data(data_rows, page, page_size)

            # Format and return response
            response = format_submissions_response(
                headers, paginated_rows, page, page_size, total_pages, total_items
            )

            logger.info(f"Returning page {page} of {total_pages} with {len(paginated_rows)} submissions")
            return jsonify(response), 200

        except Exception as e:
            logger.error(f"Error retrieving submissions: {e}", exc_info=True)
            return build_error_response(f"خطأ في استرجاع البيانات: {str(e)}", 500)


@submissions_bp.route('/<submission_id>', methods=['GET'])
@measure_performance
@require_auth
def get_submission_by_id(user_info, submission_id):
    """
    Get a specific submission by ID.

    Path Parameters:
        submission_id (str): The ID of the submission to retrieve

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        Single submission data
    """
    with ErrorContext("get_submission_by_id_api"):
        try:
            # Extract sheet_id from JWT token
            sheet_id = user_info.get('sheet_id')
            user_email = user_info.get('user', {}).get('email', 'unknown')

            if not sheet_id:
                return build_error_response("معرف الجدول غير موجود في التوكن", 400)

            logger.info(f"Submission query (ID: {submission_id}) from user: {user_email}, sheet: {sheet_id}")

            # Get sheets service
            sheets_service = get_sheets_service()

            # Fetch submissions data
            try:
                spreadsheet = sheets_service.client.open_by_key(sheet_id)
                worksheet = spreadsheet.worksheet("Submissions")
            except Exception as e:
                logger.warning(f"Submissions sheet not found: {e}")
                return build_error_response("لم يتم العثور على ورقة Submissions", 404)

            # Get all data
            all_values = worksheet.get_all_values()

            if not all_values:
                return build_error_response("ورقة Submissions فارغة", 404)

            headers = all_values[0]

            # Find ID column
            id_column = None
            for idx, header in enumerate(headers):
                if header.strip().lower() == 'id':
                    id_column = idx
                    break

            if id_column is None:
                return build_error_response("عمود ID غير موجود في الورقة", 500)

            # Search for submission with matching ID
            for row in all_values[1:]:
                if id_column < len(row) and row[id_column] == submission_id:
                    # Convert row to dict
                    submission = {}
                    for idx, header in enumerate(headers):
                        if idx < len(row):
                            submission[header.strip()] = row[idx]
                        else:
                            submission[header.strip()] = ""

                    return jsonify({
                        "status": "success",
                        "data": submission
                    }), 200

            # Not found
            logger.warning(f"Submission with ID '{submission_id}' not found")
            return build_error_response(f"لم يتم العثور على الخطاب برقم: {submission_id}", 404)

        except Exception as e:
            logger.error(f"Error retrieving submission: {e}", exc_info=True)
            return build_error_response(f"خطأ في استرجاع البيانات: {str(e)}", 500)


@submissions_bp.route('/stats', methods=['GET'])
@measure_performance
@require_auth
def get_submissions_stats(user_info):
    """
    Get statistics about submissions (count, statuses, etc).

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        Statistics object with counts and breakdowns
    """
    with ErrorContext("get_submissions_stats_api"):
        try:
            # Extract sheet_id from JWT token
            sheet_id = user_info.get('sheet_id')
            user_email = user_info.get('user', {}).get('email', 'unknown')

            if not sheet_id:
                return build_error_response("معرف الجدول غير موجود في التوكن", 400)

            logger.info(f"Submissions stats request from user: {user_email}, sheet: {sheet_id}")

            # Get sheets service
            sheets_service = get_sheets_service()

            # Fetch submissions data
            try:
                spreadsheet = sheets_service.client.open_by_key(sheet_id)
                worksheet = spreadsheet.worksheet("Submissions")
            except Exception as e:
                logger.warning(f"Submissions sheet not found: {e}")
                return build_error_response("لم يتم العثور على ورقة Submissions", 404)

            # Get all data
            all_values = worksheet.get_all_values()

            if not all_values:
                return build_error_response("ورقة Submissions فارغة", 404)

            headers = all_values[0]
            data_rows = all_values[1:]

            # Calculate statistics
            stats = {
                "total_submissions": len(data_rows),
                "headers": headers,
            }

            # Find status columns and count by status if they exist
            status_column = None
            for idx, header in enumerate(headers):
                if header.strip().lower() == 'review_status':
                    status_column = idx
                    break

            if status_column is not None:
                status_counts = {}
                for row in data_rows:
                    if status_column < len(row):
                        status = row[status_column].strip() or "Unknown"
                        status_counts[status] = status_counts.get(status, 0) + 1
                stats["by_review_status"] = status_counts

            # Count by letter type if column exists
            letter_type_column = None
            for idx, header in enumerate(headers):
                if header.strip().lower() == 'letter_type':
                    letter_type_column = idx
                    break

            if letter_type_column is not None:
                type_counts = {}
                for row in data_rows:
                    if letter_type_column < len(row):
                        letter_type = row[letter_type_column].strip() or "Unknown"
                        type_counts[letter_type] = type_counts.get(letter_type, 0) + 1
                stats["by_letter_type"] = type_counts

            logger.info(f"Returning stats with {stats['total_submissions']} submissions")

            return jsonify({
                "status": "success",
                "data": stats
            }), 200

        except Exception as e:
            logger.error(f"Error calculating submissions stats: {e}", exc_info=True)
            return build_error_response(f"خطأ في حساب الإحصائيات: {str(e)}", 500)
