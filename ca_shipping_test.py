#!/usr/bin/env python3
"""
California UPS Shipping Test Script

Specialized script for testing UPS shipping rates within California
with weight comparison functionality (5-30 lbs range)

Usage:
    python ca_shipping_test.py --weight-comparison la_to_sf
    python ca_shipping_test.py --single-test sf_to_la --weight 15
    python ca_shipping_test.py --all-scenarios --weight 10
    python ca_shipping_test.py --quick-compare
"""

import argparse
import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

from ups_api_tester import UPSShippingTester

# Load environment variables
load_dotenv()


def print_ca_scenarios():
    """Print all available California test scenarios"""
    scenarios = {
        "la_to_sf": "Los Angeles Downtown → San Francisco Downtown",
        "sf_to_la": "San Francisco Downtown → Los Angeles Downtown",
        "la_to_san_diego": "Los Angeles → San Diego",
        "sf_to_sacramento": "San Francisco → Sacramento",
        "la_to_fresno": "Los Angeles → Fresno",
        "oakland_to_san_jose": "Oakland → San Jose",
        "la_metro": "LA Downtown → LA Westside (Metro)",
        "sf_metro": "SF Downtown → SF Mission (Metro)",
        "socal_central": "Los Angeles → Bakersfield",
        "norcal_central": "San Francisco → Fresno",
        "coast_to_inland": "Long Beach → Fresno",
        "orange_county": "Anaheim → Long Beach",
    }

    print("🏖️ California Test Scenarios Available:")
    print("=" * 60)

    # Group by region
    long_distance = ["la_to_sf", "sf_to_la", "la_to_san_diego", "sf_to_sacramento"]
    medium_distance = [
        "la_to_fresno",
        "oakland_to_san_jose",
        "socal_central",
        "norcal_central",
        "coast_to_inland",
    ]
    short_distance = ["la_metro", "sf_metro", "orange_county"]

    print("📍 Long Distance (200+ miles):")
    for scenario in long_distance:
        print(f"   {scenario:20} → {scenarios[scenario]}")

    print("\n📍 Medium Distance (100-200 miles):")
    for scenario in medium_distance:
        print(f"   {scenario:20} → {scenarios[scenario]}")

    print("\n📍 Short Distance (<100 miles):")
    for scenario in short_distance:
        print(f"   {scenario:20} → {scenarios[scenario]}")

    print("=" * 60)


def run_quick_comparison():
    """Run a quick comparison of popular California routes"""

    client_id = os.getenv("UPS_CLIENT_ID")
    client_secret = os.getenv("UPS_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "❌ Error: UPS credentials not found. Set UPS_CLIENT_ID and UPS_CLIENT_SECRET"
        )
        return

    tester = UPSShippingTester(client_id, client_secret, sandbox=True)

    print("🚀 California Quick Comparison Test")
    print("=" * 50)
    print("Testing popular CA routes with 10 lb package")
    print("=" * 50)

    quick_scenarios = ["la_to_sf", "la_to_san_diego", "sf_to_sacramento", "la_metro"]

    for scenario in quick_scenarios:
        print(f"\n📍 Testing: {scenario}")
        try:
            tester.run_ca_scenario_test(scenario, weight=10.0)
            print("✅ Test completed")
        except Exception as e:
            print(f"❌ Test failed: {e}")


def run_all_scenarios(weight=10.0):
    """Run all California scenarios with specified weight"""

    client_id = os.getenv("UPS_CLIENT_ID")
    client_secret = os.getenv("UPS_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "❌ Error: UPS credentials not found. Set UPS_CLIENT_ID and UPS_CLIENT_SECRET"
        )
        return

    tester = UPSShippingTester(client_id, client_secret, sandbox=True)

    scenarios = [
        "la_to_sf",
        "sf_to_la",
        "la_to_san_diego",
        "sf_to_sacramento",
        "la_to_fresno",
        "oakland_to_san_jose",
        "la_metro",
        "sf_metro",
        "socal_central",
        "norcal_central",
        "coast_to_inland",
        "orange_county",
    ]

    print(f"🏖️ California All Scenarios Test ({weight} lb package)")
    print("=" * 60)

    results = {}

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] Testing: {scenario}")
        try:
            result = tester.run_ca_scenario_test(scenario, weight=weight)
            results[scenario] = {"success": True, "result": result}
            print("✅ Completed")
        except Exception as e:
            print(f"❌ Failed: {e}")
            results[scenario] = {"success": False, "error": str(e)}

    # Save comprehensive results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ca_all_scenarios_{weight}lb_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            {
                "test_type": "all_california_scenarios",
                "weight": weight,
                "timestamp": datetime.now().isoformat(),
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\n📊 All scenario results saved to: {filename}")


def main():
    """Main CLI for California testing"""

    parser = argparse.ArgumentParser(
        description="California UPS Shipping Test Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🏖️ California UPS Shipping Rate Tester

Examples:
  # Weight comparison (5-30 lbs) for LA to SF
  python ca_shipping_test.py --weight-comparison la_to_sf
  
  # Weight comparison with custom range
  python ca_shipping_test.py --weight-comparison sf_to_la --weight-min 10 --weight-max 50 --weight-step 10
  
  # Single test scenario
  python ca_shipping_test.py --single-test la_to_san_diego --weight 15
  
  # Test all CA scenarios with 10 lb package
  python ca_shipping_test.py --all-scenarios --weight 10
  
  # Quick comparison of popular routes
  python ca_shipping_test.py --quick-compare
  
  # List all available scenarios
  python ca_shipping_test.py --list-scenarios

Environment Setup:
  Set these in your .env file:
    UPS_CLIENT_ID=your_client_id
    UPS_CLIENT_SECRET=your_client_secret
        """,
    )

    # Command options
    command_group = parser.add_mutually_exclusive_group(required=True)

    command_group.add_argument(
        "--weight-comparison",
        metavar="SCENARIO",
        help="Run weight comparison test (5-30 lbs) for specified CA scenario",
    )

    command_group.add_argument(
        "--single-test",
        metavar="SCENARIO",
        help="Run single test for specified CA scenario",
    )

    command_group.add_argument(
        "--all-scenarios",
        action="store_true",
        help="Test all California scenarios with specified weight",
    )

    command_group.add_argument(
        "--quick-compare",
        action="store_true",
        help="Quick comparison of popular CA routes",
    )

    command_group.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List all available California scenarios",
    )

    # Weight parameters
    parser.add_argument(
        "--weight",
        type=float,
        default=10.0,
        help="Package weight for single test (default: 10.0 lbs)",
    )

    parser.add_argument(
        "--weight-min",
        type=float,
        default=5.0,
        help="Minimum weight for comparison (default: 5.0 lbs)",
    )

    parser.add_argument(
        "--weight-max",
        type=float,
        default=30.0,
        help="Maximum weight for comparison (default: 30.0 lbs)",
    )

    parser.add_argument(
        "--weight-step",
        type=float,
        default=5.0,
        help="Weight increment for comparison (default: 5.0 lbs)",
    )

    # Package dimensions
    parser.add_argument(
        "--length",
        type=float,
        default=12.0,
        help="Package length in inches (default: 12.0)",
    )

    parser.add_argument(
        "--width",
        type=float,
        default=8.0,
        help="Package width in inches (default: 8.0)",
    )

    parser.add_argument(
        "--height",
        type=float,
        default=6.0,
        help="Package height in inches (default: 6.0)",
    )

    # Environment options
    parser.add_argument(
        "--production",
        action="store_true",
        help="Use production UPS environment (default: CIE test environment)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Handle list scenarios
    if args.list_scenarios:
        print_ca_scenarios()
        return

    # Handle quick compare
    if args.quick_compare:
        run_quick_comparison()
        return

    # Handle all scenarios
    if args.all_scenarios:
        run_all_scenarios(args.weight)
        return

    # Validate CA scenario names
    valid_scenarios = [
        "la_to_sf",
        "sf_to_la",
        "la_to_san_diego",
        "sf_to_sacramento",
        "la_to_fresno",
        "oakland_to_san_jose",
        "la_metro",
        "sf_metro",
        "socal_central",
        "norcal_central",
        "coast_to_inland",
        "orange_county",
    ]

    scenario = args.weight_comparison or args.single_test
    if scenario not in valid_scenarios:
        print(f"❌ Error: '{scenario}' is not a valid California scenario")
        print("Use --list-scenarios to see available options")
        sys.exit(1)

    # Get credentials
    client_id = os.getenv("UPS_CLIENT_ID")
    client_secret = os.getenv("UPS_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "❌ Error: UPS_CLIENT_ID and UPS_CLIENT_SECRET environment variables are required."
        )
        print("Create a .env file with your UPS API credentials")
        print("Get credentials at: https://www.ups.com/upsdeveloperkit")
        sys.exit(1)

    try:
        # Initialize tester
        tester = UPSShippingTester(
            client_id=client_id,
            client_secret=client_secret,
            sandbox=not args.production,
        )

        # Run appropriate test
        if args.weight_comparison:
            print(f"🏋️ Starting California weight comparison test: {scenario}")
            tester.run_weight_comparison_test(
                ca_scenario=scenario,
                weight_min=args.weight_min,
                weight_max=args.weight_max,
                weight_step=args.weight_step,
                length=args.length,
                width=args.width,
                height=args.height,
            )

        elif args.single_test:
            print(f"📦 Starting California single test: {scenario}")
            tester.run_ca_scenario_test(
                ca_scenario=scenario,
                weight=args.weight,
                length=args.length,
                width=args.width,
                height=args.height,
            )

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
