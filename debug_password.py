"""
Debug script to check what's stored in the Google Sheet for the user
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import only what we need
from src.services.user_management_service import get_user_management_service
from src.config import setup_logging
from werkzeug.security import check_password_hash

setup_logging()

service = get_user_management_service()

# The user email
email = "ziaasd@nabatik.com"
password = "ziad123"

print("=" * 80)
print("DEBUGGING PASSWORD VALIDATION ISSUE")
print("=" * 80)

# Get client info
client_info = service.get_client_by_email(email)
if not client_info:
    print(f"\n❌ No client found for email: {email}")
    exit(1)

print(f"\n✅ Client found: {client_info.display_name}")
print(f"   Sheet ID: {client_info.sheet_id}")

# Get user info
user_info = service.get_user_info(client_info.sheet_id, email)
if not user_info:
    print(f"\n❌ User not found in Users sheet")
    exit(1)

print(f"\n✅ User found: {user_info.full_name}")
print(f"   Email: {user_info.email}")
print(f"   Role: {user_info.role}")
print(f"   Status: {user_info.status}")
print(f"   Created: {user_info.created_at}")

print(f"\n" + "=" * 80)
print("PASSWORD ANALYSIS")
print("=" * 80)

stored_password = user_info.password
print(f"\nStored password length: {len(stored_password)}")
print(f"First 50 chars: {stored_password[:50]}")
print(f"Last 50 chars: {stored_password[-50:]}")
print(f"Full password: {stored_password}")

print(f"\nPassword format checks:")
print(f"  Starts with 'pbkdf2:': {stored_password.startswith('pbkdf2:')}")
print(f"  Starts with 'pbkdf2:sha256:': {stored_password.startswith('pbkdf2:sha256:')}")
print(f"  Starts with 'pbkdf2:sha512:': {stored_password.startswith('pbkdf2:sha512:')}")

print(f"\n" + "=" * 80)
print("PASSWORD VERIFICATION TEST")
print("=" * 80)

print(f"\nTesting password: '{password}'")

if stored_password.startswith('pbkdf2:'):
    result = check_password_hash(stored_password, password)
    print(f"check_password_hash result: {result}")
    
    if not result:
        print("\n❌ Hash verification FAILED")
        print("\nTrying with different passwords:")
        for test_pwd in ["ziad123", "Ziad123", "ZIAD123", " ziad123", "ziad123 "]:
            result = check_password_hash(stored_password, test_pwd)
            print(f"  '{test_pwd}': {result}")
    else:
        print("\n✅ Hash verification SUCCESS")
else:
    # Plain text comparison
    result = (stored_password == password)
    print(f"Plain text comparison: {result}")
    if not result:
        print(f"\n❌ Passwords don't match")
        print(f"  Stored: '{stored_password}'")
        print(f"  Provided: '{password}'")
    else:
        print("\n✅ Plain text match SUCCESS")

print("\n" + "=" * 80)
