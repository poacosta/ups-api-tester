#!/usr/bin/env python3
"""
Quick UPS Credential Test
Verifies that UPS API credentials are properly configured and determines the correct environment
"""

import os

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_environment(base_url, env_name):
    """Test authentication against a specific UPS environment"""

    client_id = os.getenv("UPS_CLIENT_ID")
    client_secret = os.getenv("UPS_CLIENT_SECRET")

    auth_url = f"{base_url}/security/v1/oauth/token"
    auth_data = {"grant_type": "client_credentials"}
    auth_headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(
            auth_url,
            data=auth_data,
            headers=auth_headers,
            auth=(client_id, client_secret),
            timeout=10,
        )

        print(f"📡 {env_name} Response: {response.status_code}")

        if response.status_code == 200:
            token_data = response.json()
            expires_in = token_data.get("expires_in", "unknown")
            print(
                f"✅ {env_name} authentication successful! (expires in {expires_in}s)"
            )
            return True

        print(f"❌ {env_name} authentication failed: {response.text}")
        return False

    except requests.exceptions.RequestException as e:
        print(f"❌ {env_name} network error: {e}")
        return False


def test_credentials():
    """Test UPS API credentials against both environments"""

    client_id = os.getenv("UPS_CLIENT_ID")
    client_secret = os.getenv("UPS_CLIENT_SECRET")

    print("🔐 UPS Credential Test")
    print("=" * 50)

    # Check if credentials exist
    if not client_id:
        print("❌ UPS_CLIENT_ID not found in environment")
        return False

    if not client_secret:
        print("❌ UPS_CLIENT_SECRET not found in environment")
        return False

    print(f"✅ UPS_CLIENT_ID found: {client_id[:8]}***")
    print(f"✅ UPS_CLIENT_SECRET found: {client_secret[:8]}***")

    print("\n🧪 Testing authentication against UPS environments...")
    print("-" * 50)

    # Test CIE environment
    print("Testing CIE (Customer Integration Environment):")
    cie_success = test_environment("https://wwwcie.ups.com", "CIE")

    print("\nTesting Production environment:")
    prod_success = test_environment("https://onlinetools.ups.com", "Production")

    print("\n" + "=" * 50)
    print("🎯 RESULTS & RECOMMENDATIONS:")
    print("=" * 50)

    if cie_success and prod_success:
        print("✅ Your credentials work with BOTH environments!")
        print("   For testing: python ups_api_tester.py --quick-test")
        print("   For production: python ups_api_tester.py --quick-test --production")

    elif cie_success and not prod_success:
        print("✅ Your credentials are configured for CIE (testing):")
        print("   Run: python ups_api_tester.py --quick-test")

    elif not cie_success and prod_success:
        print("✅ Your credentials are configured for Production:")
        print("   Run: python ups_api_tester.py --quick-test --production")
        print("   ⚠️  Note: This uses live UPS services")

    else:
        print("❌ Your credentials don't work with either environment.")
        print("\n💡 Troubleshooting:")
        print("   1. Verify Client ID and Secret in UPS Developer Portal")
        print("   2. Check if your UPS application is active/enabled")
        print("   3. Try regenerating credentials")
        print("   4. Ensure no extra spaces in .env file")
        print("   5. Visit: https://www.ups.com/upsdeveloperkit")
        return False

    return cie_success or prod_success


if __name__ == "__main__":
    SUCCESS = test_credentials()

    if not SUCCESS:
        print("\n🔧 Please fix the credential issues above, then try again.")
        print("   Get credentials at: https://www.ups.com/upsdeveloperkit")
