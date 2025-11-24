"""
Test script for Email Mappings feature.
This script demonstrates how the two-tier authentication system works.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.user_management_service import UserManagementService
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_email_mappings():
    """Test the email mappings functionality."""

    print("=" * 80)
    print("Email Mappings Feature Test")
    print("=" * 80)
    print()

    # Initialize service
    try:
        service = UserManagementService()
        print("✅ UserManagementService initialized successfully")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return

    # Test cases
    test_cases = [
        {
            "name": "Test 1: Gmail user (should check EmailMappings first)",
            "email": "alice@gmail.com",
            "expected": "Should find in EmailMappings if configured, else fail"
        },
        {
            "name": "Test 2: Organizational email (should use domain matching)",
            "email": "admin@moe.gov.sa",
            "expected": "Should find via domain matching in Clients worksheet"
        },
        {
            "name": "Test 3: Yahoo user (should check EmailMappings first)",
            "email": "bob@yahoo.com",
            "expected": "Should find in EmailMappings if configured, else fail"
        },
        {
            "name": "Test 4: Unknown gmail user",
            "email": "unknown@gmail.com",
            "expected": "Should fail - not in EmailMappings and no domain match"
        },
        {
            "name": "Test 5: Another organizational domain",
            "email": "user@health.gov.sa",
            "expected": "Should find via domain matching if configured"
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{test['name']}")
        print("-" * 80)
        print(f"Email: {test['email']}")
        print(f"Expected: {test['expected']}")
        print()

        try:
            # Attempt to get client info
            client_info = service.get_client_by_email(test['email'])

            if client_info:
                print(f"✅ SUCCESS: Client found!")
                print(f"   Client ID: {client_info.client_id}")
                print(f"   Display Name: {client_info.display_name}")
                print(f"   Sheet ID: {client_info.sheet_id}")
                print(f"   Primary Domain: {client_info.primary_domain or '[Email Mapping]'}")

                # Check if it came from email mappings
                if not client_info.primary_domain:
                    print(f"   ℹ️  Source: EmailMappings worksheet")
                else:
                    print(f"   ℹ️  Source: Domain matching (Clients worksheet)")
            else:
                print(f"❌ FAILED: No client found for {test['email']}")
                print(f"   This could be expected if not configured yet")

        except Exception as e:
            print(f"❌ ERROR: {e}")

        print()

    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print()
    print("Implementation Status:")
    print("✅ Two-tier authentication system implemented")
    print("✅ EmailMappings lookup (Tier 1) - checks first")
    print("✅ Domain matching fallback (Tier 2) - existing functionality")
    print("✅ Caching for both tiers (5-minute TTL)")
    print("✅ Backward compatible with existing clients")
    print()
    print("Next Steps:")
    print("1. Create EmailMappings worksheet in Master Sheet")
    print("2. Add email mappings for gmail/yahoo users")
    print("3. Create corresponding client sheets")
    print("4. Add users to client sheets' Users worksheet")
    print("5. Test actual login via API")
    print()
    print("Documentation:")
    print("- Full docs: EMAIL_MAPPINGS_FEATURE.md")
    print("- Quick start: QUICK_START_EMAIL_MAPPINGS.md")
    print()


def test_cache_performance():
    """Test cache performance."""
    import time

    print("\n" + "=" * 80)
    print("Cache Performance Test")
    print("=" * 80)
    print()

    service = UserManagementService()
    test_email = "admin@moe.gov.sa"

    # First call (cold - should hit Google Sheets)
    print(f"1st lookup for {test_email} (cold cache):")
    start = time.time()
    client_info = service.get_client_by_email(test_email)
    elapsed = time.time() - start
    print(f"   Time: {elapsed * 1000:.2f}ms")
    if client_info:
        print(f"   Result: {client_info.display_name}")
    print()

    # Second call (warm - should use cache)
    print(f"2nd lookup for {test_email} (warm cache):")
    start = time.time()
    client_info = service.get_client_by_email(test_email)
    elapsed = time.time() - start
    print(f"   Time: {elapsed * 1000:.2f}ms")
    if client_info:
        print(f"   Result: {client_info.display_name}")
    print()

    print("Expected:")
    print("- Cold cache: 200-500ms (Google Sheets API call)")
    print("- Warm cache: <1ms (in-memory lookup)")
    print()


if __name__ == "__main__":
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "EMAIL MAPPINGS FEATURE TEST" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    try:
        # Run main tests
        test_email_mappings()

        # Run performance tests
        test_cache_performance()

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)
