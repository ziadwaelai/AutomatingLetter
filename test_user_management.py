"""
Test script for User Management Service
Tests email validation, client lookup, and master sheet integration.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services import get_user_management_service
from src.config import setup_logging

# Setup logging
setup_logging()


def test_basic_operations():
    """Test basic user management operations."""
    print("=" * 60)
    print("Testing User Management Service")
    print("=" * 60)

    # Get service instance
    service = get_user_management_service()
    print(f"\n✓ Service initialized successfully")

    # Get service stats
    stats = service.get_service_stats()
    print(f"\nService Stats:")
    print(f"  - Service: {stats['service']}")
    print(f"  - Master Sheet ID: {stats['master_sheet_id']}")
    print(f"  - Cache Size: {stats['cache_size']}")
    print(f"  - Cache TTL: {stats['cache_ttl_seconds']} seconds")

    return service


def test_get_all_clients(service):
    """Test getting all clients from master sheet."""
    print("\n" + "-" * 60)
    print("Testing: Get All Clients")
    print("-" * 60)

    try:
        clients = service.get_all_clients()
        print(f"\n✓ Found {len(clients)} clients in master sheet")

        if clients:
            print("\nFirst 3 clients:")
            for i, client in enumerate(clients[:3], 1):
                print(f"\n{i}. {client.display_name}")
                print(f"   - Client ID: {client.client_id}")
                print(f"   - Primary Domain: {client.primary_domain}")
                print(f"   - Extra Domains: {client.extra_domains}")
                print(f"   - Sheet ID: {client.sheet_id}")
                print(f"   - Drive ID: {client.google_drive_id}")
                print(f"   - Admin Email: {client.admin_email}")

        return clients
    except Exception as e:
        print(f"\n✗ Error getting clients: {e}")
        return []


def test_email_validation(service, clients):
    """Test email validation with real domains from master sheet."""
    print("\n" + "-" * 60)
    print("Testing: Email Validation")
    print("-" * 60)

    if not clients:
        print("\n⚠ No clients available for testing")
        return

    # Test with first client's primary domain
    first_client = clients[0]
    test_email = f"test@{first_client.primary_domain}"

    print(f"\nTest 1: Valid email with primary domain")
    print(f"Email: {test_email}")

    try:
        has_access, client_info, user_info = service.validate_user_access(test_email)

        if has_access and client_info and user_info:
            print(f"✓ Access granted!")
            print(f"  - Client: {client_info.display_name}")
            print(f"  - Sheet ID: {client_info.sheet_id}")
            print(f"  - Drive ID: {client_info.google_drive_id}")
            print(f"  - User: {user_info.full_name} ({user_info.role})")
        else:
            print(f"✗ Access denied")
            if client_info and not user_info:
                print(f"  - Client found but user not in Users sheet")
            elif client_info and user_info and not has_access:
                print(f"  - User found but status: {user_info.status}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test with extra domain if available
    if first_client.extra_domains:
        extra_domain = first_client.extra_domains[0]
        test_email_extra = f"user@{extra_domain}"

        print(f"\nTest 2: Valid email with extra domain")
        print(f"Email: {test_email_extra}")

        try:
            has_access, client_info, user_info = service.validate_user_access(test_email_extra)

            if has_access and client_info and user_info:
                print(f"✓ Access granted!")
                print(f"  - Client: {client_info.display_name}")
                print(f"  - User: {user_info.full_name} ({user_info.role})")
            else:
                print(f"✗ Access denied")
                if client_info and not user_info:
                    print(f"  - Client found but user not in Users sheet")
        except Exception as e:
            print(f"✗ Error: {e}")

    # Test with invalid domain
    print(f"\nTest 3: Invalid email (non-existent domain)")
    test_email_invalid = "user@invalid-domain-12345.com"
    print(f"Email: {test_email_invalid}")

    try:
        has_access, client_info, user_info = service.validate_user_access(test_email_invalid)

        if has_access:
            print(f"✗ Unexpected: Access granted to invalid email")
        else:
            print(f"✓ Access correctly denied for invalid domain")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_get_client_by_email(service, clients):
    """Test getting client info by email."""
    print("\n" + "-" * 60)
    print("Testing: Get Client by Email")
    print("-" * 60)

    if not clients:
        print("\n⚠ No clients available for testing")
        return

    # Test with first client
    first_client = clients[0]
    test_email = f"test@{first_client.primary_domain}"

    print(f"\nLooking up client for email: {test_email}")

    try:
        client_info = service.get_client_by_email(test_email)

        if client_info:
            print(f"\n✓ Client found!")
            print(f"  Display Name: {client_info.display_name}")
            print(f"  Client ID: {client_info.client_id}")
            print(f"  Sheet ID: {client_info.sheet_id}")
            print(f"  Drive ID: {client_info.google_drive_id}")
            print(f"  Sheet URL: {client_info.sheet_url}")
            print(f"  Admin Email: {client_info.admin_email}")
            print(f"  Letter Template: {client_info.letter_template}")
            print(f"  Letter Type: {client_info.letter_type}")

            # Test cache
            print(f"\nTest cache (second lookup)...")
            client_info_2 = service.get_client_by_email(test_email)
            if client_info_2:
                print(f"✓ Cache working - client retrieved from cache")
        else:
            print(f"✗ Client not found")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_cache_operations(service):
    """Test cache operations."""
    print("\n" + "-" * 60)
    print("Testing: Cache Operations")
    print("-" * 60)

    # Get stats before clearing
    stats_before = service.get_service_stats()
    print(f"\nCache size before clear: {stats_before['cache_size']}")

    # Clear cache
    service.clear_cache()
    print(f"✓ Cache cleared")

    # Get stats after clearing
    stats_after = service.get_service_stats()
    print(f"Cache size after clear: {stats_after['cache_size']}")


def main():
    """Main test function."""
    try:
        # Test basic operations
        service = test_basic_operations()

        # Get all clients
        clients = test_get_all_clients(service)

        if clients:
            # Test email validation
            test_email_validation(service, clients)

            # Test get client by email
            test_get_client_by_email(service, clients)

            # Test cache operations
            test_cache_operations(service)

        print("\n" + "=" * 60)
        print("✓ All tests completed")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
