#endpoint get_context
from google_services import get_letter_config_by_category


def n8n_get_context(category, member_name=None):
    try:
        letter_config = get_letter_config_by_category(category, member_name)
        return {
            "status": "success",
            "data": letter_config
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }