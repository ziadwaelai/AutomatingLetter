"""
Test password hashing to debug the validation issue
"""
from werkzeug.security import generate_password_hash, check_password_hash

# Test the password
password = "ziad123"

# Generate hash
hashed = generate_password_hash(password)
print("=" * 80)
print("PASSWORD HASH TEST")
print("=" * 80)
print(f"\nOriginal Password: {password}")
print(f"Hashed Password: {hashed}")
print(f"Hash starts with 'pbkdf2:sha256:': {hashed.startswith('pbkdf2:sha256:')}")

# Test verification
print(f"\n--- Testing Verification ---")
print(f"check_password_hash(hashed, password): {check_password_hash(hashed, password)}")
print(f"check_password_hash(hashed, 'wrong'): {check_password_hash(hashed, 'wrong')}")

# Test with different hash methods
print("\n" + "=" * 80)
print("TESTING DIFFERENT HASH METHODS")
print("=" * 80)

methods = [
    'pbkdf2:sha256',
    'pbkdf2:sha256:260000',
    'pbkdf2:sha512',
]

for method in methods:
    hashed_custom = generate_password_hash(password, method=method)
    result = check_password_hash(hashed_custom, password)
    print(f"\nMethod: {method}")
    print(f"  Hash: {hashed_custom[:50]}...")
    print(f"  Verification: {result}")
    print(f"  Starts with 'pbkdf2:sha256:': {hashed_custom.startswith('pbkdf2:sha256:')}")

print("\n" + "=" * 80)
print("✅ Test completed")
print("=" * 80)
