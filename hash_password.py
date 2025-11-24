#!/usr/bin/env python3
"""
Password Hashing Utility
Generates hashed passwords using the same method as the backend (werkzeug PBKDF2-SHA256).
"""

from werkzeug.security import generate_password_hash, check_password_hash
import sys


def hash_password(plain_password: str) -> str:
    """
    Hash a password using werkzeug's PBKDF2-SHA256 algorithm.
    This is the same method used by the backend.

    Args:
        plain_password: The plain text password to hash

    Returns:
        Hashed password string (pbkdf2:sha256:...)
    """
    hashed = generate_password_hash(plain_password)
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to check against

    Returns:
        True if password matches, False otherwise
    """
    return check_password_hash(hashed_password, plain_password)


def main():
    """Main function for command line usage."""
    print("=" * 60)
    print("Password Hashing Utility")
    print("=" * 60)
    print()

    # Check if password provided as argument
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        # Interactive mode
        print("Enter password to hash (or press Ctrl+C to exit):")
        password = input("> ").strip()

    if not password:
        print("❌ Error: Password cannot be empty")
        sys.exit(1)

    # Hash the password
    hashed = hash_password(password)

    # Display results
    print()
    print("✅ Password hashed successfully!")
    print()
    print("-" * 60)
    print("Plain Password:")
    print(password)
    print()
    print("Hashed Password:")
    print(hashed)
    print("-" * 60)
    print()
    print("📋 Copy the hashed password above and paste it in the")
    print("   'password' column of your Users worksheet")
    print()

    # Verify the hash works
    print("🔍 Verification test...")
    if verify_password(password, hashed):
        print("✅ Verification successful! Hash is valid.")
    else:
        print("❌ Verification failed! Something went wrong.")
    print()

    # Show example usage
    print("💡 Usage Examples:")
    print()
    print("  Interactive mode:")
    print("    python hash_password.py")
    print()
    print("  Command line mode:")
    print("    python hash_password.py MyPassword123")
    print()
    print("  Batch mode:")
    print("    python hash_password.py MyPassword123 | grep pbkdf2")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
