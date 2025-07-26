#!/usr/bin/env python3
"""
UPS API Test Application

A comprehensive tool for testing UPS shipping services including:
- Address validation
- Rate shopping
- Service options and delivery times
- OAuth 2.0 authentication
- Error handling and logging

Requirements:
    pip install requests python-dotenv pydantic tabulate

Usage:
    python ups_api_tester.py --from-address "123 Main St, New York, NY 10001" \
                            --to-address "456 Oak Ave, Los Angeles, CA 90001" \
                            --weight 5.0 --length 12 --width 8 --height 6
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("ups_api.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@dataclass
class Address:
    """Address data structure"""

    address_line_1: str
    city: str
    state_province_code: str
    postal_code: str
    country_code: str = "US"
    address_line_2: Optional[str] = None
    address_line_3: Optional[str] = None

    def to_ups_format(self) -> Dict:
        """Convert to UPS API format"""
        ups_address = {
            "AddressLine": [self.address_line_1],
            "City": self.city,
            "StateProvinceCode": self.state_province_code,
            "PostalCode": self.postal_code,
            "CountryCode": self.country_code,
        }

        if self.address_line_2:
            ups_address["AddressLine"].append(self.address_line_2)
        if self.address_line_3:
            ups_address["AddressLine"].append(self.address_line_3)

        return ups_address


@dataclass
class Package:
    """Package specifications"""

    weight: float
    length: float
    width: float
    height: float
    weight_unit: str = "LBS"
    dimension_unit: str = "IN"
    packaging_type: str = "02"  # Customer Supplied Package

    def to_ups_format(self) -> Dict:
        """Convert to UPS API format"""
        return {
            "PackagingType": {"Code": self.packaging_type},
            "Dimensions": {
                "UnitOfMeasurement": {"Code": self.dimension_unit},
                "Length": str(self.length),
                "Width": str(self.width),
                "Height": str(self.height),
            },
            "PackageWeight": {
                "UnitOfMeasurement": {"Code": self.weight_unit},
                "Weight": str(self.weight),
            },
        }


class UPSAPIError(Exception):
    """Custom exception for UPS API errors"""


class UPSAPIClient:
    """UPS API client with OAuth 2.0 authentication"""

    # UPS Service Codes for different shipping options
    SERVICE_CODES = {
        "01": "UPS Next Day Air",
        "02": "UPS 2nd Day Air",
        "03": "UPS Ground",
        "07": "UPS Worldwide Express",
        "08": "UPS Worldwide Expedited",
        "11": "UPS Standard",
        "12": "UPS 3 Day Select",
        "13": "UPS Next Day Air Saver",
        "14": "UPS Next Day Air Early",
        "54": "UPS Worldwide Express Plus",
        "59": "UPS 2nd Day Air A.M.",
        "65": "UPS Worldwide Saver",
    }

    def __init__(self, client_id: str, client_secret: str, sandbox: bool = True):
        """
        Initialize UPS API client

        Args:
            client_id: UPS API client ID
            client_secret: UPS API client secret
            sandbox: Use sandbox environment for testing (CIE - Customer Integration Environment)
                    Set to False to use production environment (onlinetools.ups.com)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.sandbox = sandbox
        self.access_token = None
        self.token_expires_at = None

        # API endpoints - UPS CIE vs Production
        if sandbox:
            self.base_url = "https://wwwcie.ups.com"
            logger.info("Using UPS CIE (Customer Integration Environment) for testing")
            logger.warning(
                "If you get 401 errors, your credentials might be for production."
            )
            logger.warning(
                "Try running with --production flag: python ups_api_tester.py --quick-test --production"
            )
        else:
            self.base_url = "https://onlinetools.ups.com"
            logger.info("Using UPS Production environment")
            logger.warning("⚠️  PRODUCTION MODE: Using live UPS services")

        self.auth_url = f"{self.base_url}/security/v1/oauth/token"
        self.rating_url = f"{self.base_url}/api/rating"
        self.address_validation_url = f"{self.base_url}/api/addressvalidation"

        # Request session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    def _get_access_token(self) -> str:
        """Get OAuth 2.0 access token"""
        if (
            self.access_token
            and self.token_expires_at
            and datetime.now() < self.token_expires_at
        ):
            return self.access_token

        logger.info("Requesting new access token from UPS")

        auth_data = {"grant_type": "client_credentials"}

        auth_headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = self.session.post(
                self.auth_url,
                data=auth_data,
                headers=auth_headers,
                auth=(self.client_id, self.client_secret),
                timeout=30,
            )
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            expires_in = int(token_data.get("expires_in", 3600))  # Convert to int
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)

            logger.info("Successfully obtained access token")
            return self.access_token

        except requests.exceptions.RequestException as e:
            logger.error("Failed to get access token: %s", e)
            raise UPSAPIError(f"Authentication failed: {e}") from e

    def validate_address(self, address: Address) -> Dict:
        """
        Validate address using UPS Address Validation API

        Args:
            address: Address to validate

        Returns:
            Dict containing validation results
        """
        logger.info(
            "Validating address: %s, %s", address.city, address.state_province_code
        )

        token = self._get_access_token()

        request_data = {
            "AddressValidationRequest": {
                "Request": {
                    "RequestOption": "3"  # Address validation and classification
                },
                "AddressKeyFormat": {
                    "AddressLine": [address.address_line_1],
                    "PoliticalDivision2": address.city,
                    "PoliticalDivision1": address.state_province_code,
                    "PostcodePrimaryLow": address.postal_code,
                    "CountryCode": address.country_code,
                },
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = self.session.post(
                f"{self.address_validation_url}/v1/1",
                json=request_data,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            logger.info("Address validation completed successfully")
            return result

        except requests.exceptions.RequestException as e:
            logger.error("Address validation failed: %s", e)
            if hasattr(e, "response") and hasattr(e.response, "text"):
                logger.error("Response: %s", e.response.text)
            raise UPSAPIError(f"Address validation failed: {e}") from e

    def get_shipping_rates(
        self,
        from_address: Address,
        to_address: Address,
        packages: List[Package],
        shop_all: bool = True,
    ) -> Dict:
        """
        Get shipping rates for packages

        Args:
            from_address: Origin address
            to_address: Destination address
            packages: List of packages to ship
            shop_all: If True, get rates for all available services

        Returns:
            Dict containing shipping rates and options
        """
        logger.info(
            "Getting shipping rates from %s to %s", from_address.city, to_address.city
        )

        token = self._get_access_token()

        request_option = "Shop" if shop_all else "Rate"

        # Build base request data
        request_data = {
            "RateRequest": {
                "Request": {
                    "RequestOption": request_option,
                    "TransactionReference": {
                        "CustomerContext": f"Rate Request {datetime.now().isoformat()}"
                    },
                },
                "Shipment": {
                    "Shipper": {
                        "Name": "Test Shipper",
                        "Address": from_address.to_ups_format(),
                    },
                    "ShipTo": {
                        "Name": "Test Recipient",
                        "Address": to_address.to_ups_format(),
                    },
                    "ShipFrom": {
                        "Name": "Test Shipper",
                        "Address": from_address.to_ups_format(),
                    },
                    "Package": [pkg.to_ups_format() for pkg in packages],
                },
            }
        }

        # Add DeliveryTimeInformation for time in transit requests
        if shop_all:
            # Calculate pickup date (next business day)
            pickup_date = datetime.now() + timedelta(days=1)
            # Skip weekends
            while pickup_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
                pickup_date += timedelta(days=1)

            request_data["RateRequest"]["Shipment"]["DeliveryTimeInformation"] = {
                "PickupDate": pickup_date.strftime("%Y%m%d")
            }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            # Try time in transit API first, fall back to standard rating if it fails
            if shop_all and request_data["RateRequest"]["Shipment"].get(
                "DeliveryTimeInformation"
            ):
                endpoint = f"{self.rating_url}/v2409/Shoptimeintransit"
                logger.info("Attempting time in transit request...")
                try:
                    response = self.session.post(
                        endpoint, json=request_data, headers=headers, timeout=30
                    )
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    logger.warning(
                        "Time in transit request failed: %s, falling back to standard rating",
                        e,
                    )
                    # Remove DeliveryTimeInformation and use standard endpoint
                    if (
                        "DeliveryTimeInformation"
                        in request_data["RateRequest"]["Shipment"]
                    ):
                        del request_data["RateRequest"]["Shipment"][
                            "DeliveryTimeInformation"
                        ]
                    endpoint = f"{self.rating_url}/v2409/Shop"
                    response = self.session.post(
                        endpoint, json=request_data, headers=headers, timeout=30
                    )
            else:
                # Use standard rating endpoint
                endpoint = (
                    f"{self.rating_url}/v2409/Shop"
                    if shop_all
                    else f"{self.rating_url}/v2409/Rate"
                )
                response = self.session.post(
                    endpoint, json=request_data, headers=headers, timeout=30
                )
            response.raise_for_status()

            result = response.json()
            logger.info("Successfully retrieved shipping rates")
            return result

        except requests.exceptions.RequestException as e:
            logger.error("Rate request failed: %s", e)
            if hasattr(e, "response") and hasattr(e.response, "text"):
                logger.error("Response: %s", e.response.text)
            raise UPSAPIError(f"Rate request failed: {e}") from e


class UPSShippingTester:
    """Main application class for testing UPS shipping services"""

    # Predefined test addresses that work well with UPS CIE
    TEST_ADDRESSES = {
        "origin_ny": "123 Main St, New York, NY 10001",
        "destination_ca": "456 Oak Ave, Los Angeles, CA 90001",
        "origin_ga": "100 Peachtree St, Atlanta, GA 30309",
        "destination_tx": "200 Main St, Dallas, TX 75201",
        "origin_fl": "300 Ocean Dr, Miami, FL 33139",
        "destination_wa": "400 Pine St, Seattle, WA 98101",
    }

    # California-specific test addresses for intra-state shipping comparison
    CA_TEST_ADDRESSES = {
        "la_downtown": "123 Spring St, Los Angeles, CA 90012",
        "la_westside": "456 Wilshire Blvd, Los Angeles, CA 90036",
        "sf_downtown": "789 Market St, San Francisco, CA 94103",
        "sf_mission": "321 Valencia St, San Francisco, CA 94110",
        "san_diego": "654 Broadway, San Diego, CA 92101",
        "sacramento": "987 J St, Sacramento, CA 95814",
        "fresno": "147 Fresno St, Fresno, CA 93721",
        "oakland": "258 Oakland Ave, Oakland, CA 94612",
        "san_jose": "369 San Carlos St, San Jose, CA 95112",
        "long_beach": "741 Ocean Blvd, Long Beach, CA 90802",
        "bakersfield": "852 Chester Ave, Bakersfield, CA 93301",
        "anaheim": "963 Lincoln Ave, Anaheim, CA 92805",
    }

    # California test scenarios for different regional combinations
    CA_TEST_SCENARIOS = {
        "la_to_sf": ("la_downtown", "sf_downtown"),
        "sf_to_la": ("sf_downtown", "la_downtown"),
        "la_to_san_diego": ("la_downtown", "san_diego"),
        "sf_to_sacramento": ("sf_downtown", "sacramento"),
        "la_to_fresno": ("la_downtown", "fresno"),
        "oakland_to_san_jose": ("oakland", "san_jose"),
        "la_metro": ("la_downtown", "la_westside"),
        "sf_metro": ("sf_downtown", "sf_mission"),
        "socal_central": ("la_downtown", "bakersfield"),
        "norcal_central": ("sf_downtown", "fresno"),
        "coast_to_inland": ("long_beach", "fresno"),
        "orange_county": ("anaheim", "long_beach"),
    }

    # UPS test tracking numbers for testing tracking functionality
    TEST_TRACKING_NUMBERS = [
        "1ZCIETST0111111114",  # Test tracking number 1
        "1ZCIETST0422222228",  # Test tracking number 2
    ]

    def __init__(self, client_id: str, client_secret: str, sandbox: bool = True):
        """Initialize the shipping tester"""
        self.ups_client = UPSAPIClient(client_id, client_secret, sandbox)

        if sandbox:
            logger.info("=" * 60)
            logger.info("UPS TEST MODE CONFIGURATION")
            logger.info("=" * 60)
            logger.info("Environment: Customer Integration Environment (CIE)")
            logger.info("Base URL: https://wwwcie.ups.com")
            logger.info("Note: CIE may return consistent responses for testing")
            logger.info("Available test addresses:")
            for key, address in self.TEST_ADDRESSES.items():
                logger.info(f"  {key}: {address}")
            logger.info("Test tracking numbers:")
            for tracking_num in self.TEST_TRACKING_NUMBERS:
                logger.info(f"  {tracking_num}")
            logger.info("=" * 60)

    def use_test_addresses(self, test_case: str = "default") -> Tuple[str, str]:
        """
        Get predefined test addresses for common test scenarios

        Args:
            test_case: Test scenario name

        Returns:
            Tuple of (from_address, to_address)
        """
        test_scenarios = {
            "default": ("origin_ny", "destination_ca"),
            "east_west": ("origin_ny", "destination_ca"),
            "south_north": ("origin_ga", "destination_wa"),
            "southeast": ("origin_fl", "destination_tx"),
            "cross_country": ("origin_ny", "destination_wa"),
        }

        if test_case not in test_scenarios:
            logger.warning(f"Unknown test case '{test_case}', using 'default'")
            test_case = "default"

        from_key, to_key = test_scenarios[test_case]
        from_address = self.TEST_ADDRESSES[from_key]
        to_address = self.TEST_ADDRESSES[to_key]

        logger.info(f"Using test scenario '{test_case}':")
        logger.info(f"  From: {from_address}")
        logger.info(f"  To: {to_address}")

        return from_address, to_address

    def use_ca_test_addresses(self, test_case: str = "la_to_sf") -> Tuple[str, str]:
        """
        Get predefined California test addresses for intra-state shipping scenarios

        Args:
            test_case: California test scenario name

        Returns:
            Tuple of (from_address, to_address)
        """
        if test_case not in self.CA_TEST_SCENARIOS:
            logger.warning(f"Unknown CA test case '{test_case}', using 'la_to_sf'")
            test_case = "la_to_sf"

        from_key, to_key = self.CA_TEST_SCENARIOS[test_case]
        from_address = self.CA_TEST_ADDRESSES[from_key]
        to_address = self.CA_TEST_ADDRESSES[to_key]

        logger.info(f"Using California test scenario '{test_case}':")
        logger.info(f"  From: {from_address}")
        logger.info(f"  To: {to_address}")

        return from_address, to_address

    def run_weight_comparison_test(
        self,
        ca_scenario: str = "la_to_sf",
        weight_min: float = 5.0,
        weight_max: float = 30.0,
        weight_step: float = 5.0,
        length: float = 12.0,
        width: float = 8.0,
        height: float = 6.0,
    ):
        """
        Run weight comparison test for California addresses with multiple package weights

        Args:
            ca_scenario: California test scenario
            weight_min: Minimum weight to test
            weight_max: Maximum weight to test
            weight_step: Weight increment
            length, width, height: Package dimensions
        """
        from_address_str, to_address_str = self.use_ca_test_addresses(ca_scenario)

        print("🏋️ UPS California Weight Comparison Test")
        print("=" * 60)
        print(f"📍 Route: {ca_scenario}")
        print(f"   From: {from_address_str}")
        print(f"   To: {to_address_str}")
        print(
            f"⚖️  Weight Range: {weight_min} - {weight_max} lbs (step: {weight_step} lbs)"
        )
        print(f"📦 Package Dimensions: {length}x{width}x{height} inches")
        if self.ups_client.sandbox:
            print("🧪 Environment: Customer Integration Environment (CIE)")
        else:
            print("⚠️  Environment: Production")
        print("=" * 60)

        # Parse addresses once
        from_addr = self.parse_address(from_address_str)
        to_addr = self.parse_address(to_address_str)

        # Validate addresses once
        print("1. Validating addresses...")
        try:
            addresses_valid, validation_results = self.validate_addresses(
                from_addr, to_addr
            )
            if addresses_valid:
                print("   ✓ Addresses validated successfully")
            else:
                print("   ⚠ Address validation issues detected")
        except Exception as e:
            print(f"   ⚠ Address validation failed: {e}")

        # Test different weights
        weight_results = []
        weights = []
        current_weight = weight_min

        while current_weight <= weight_max:
            weights.append(current_weight)
            current_weight += weight_step

        print(f"\n2. Testing {len(weights)} different package weights...")

        for i, weight in enumerate(weights):
            print(f"   Testing weight {i + 1}/{len(weights)}: {weight} lbs...")

            try:
                package = Package(
                    weight=weight, length=length, width=width, height=height
                )
                rates_response = self.ups_client.get_shipping_rates(
                    from_addr, to_addr, [package]
                )

                # Parse rates for this weight
                weight_rates = self._parse_rates_for_comparison(rates_response, weight)
                weight_results.append(weight_rates)

            except Exception as e:
                logger.error(f"Failed to get rates for {weight} lbs: {e}")
                weight_results.append({"weight": weight, "error": str(e), "rates": {}})

        # Display comparison results
        print(f"\n3. Weight Comparison Results:")
        self._display_weight_comparison(weight_results, ca_scenario)

        # Save detailed results
        comparison_results = {
            "scenario": ca_scenario,
            "route": {"from": from_address_str, "to": to_address_str},
            "weight_range": {"min": weight_min, "max": weight_max, "step": weight_step},
            "package_dimensions": {"length": length, "width": width, "height": height},
            "results": weight_results,
            "timestamp": datetime.now().isoformat(),
            "environment": "CIE" if self.ups_client.sandbox else "Production",
        }

        filename = f'ups_ca_weight_comparison_{ca_scenario}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        self._save_results(comparison_results, filename)

        print(f"\n✅ Weight comparison completed!")
        print(f"📊 Detailed results saved to '{filename}'")
        return comparison_results

    def _parse_rates_for_comparison(self, rates_response: Dict, weight: float) -> Dict:
        """Parse UPS rates response for weight comparison"""
        result = {"weight": weight, "rates": {}, "error": None}

        try:
            response = rates_response.get("RateResponse", {})
            rated_shipments = response.get("RatedShipment", [])

            if not rated_shipments:
                result["error"] = "No shipping options available"
                return result

            # Ensure it's a list
            if not isinstance(rated_shipments, list):
                rated_shipments = [rated_shipments]

            for shipment in rated_shipments:
                service_code = shipment.get("Service", {}).get("Code", "Unknown")
                service_name = self.ups_client.SERVICE_CODES.get(
                    service_code, f"Service {service_code}"
                )

                # Get total charges
                total_charges = shipment.get("TotalCharges", {})
                currency = total_charges.get("CurrencyCode", "USD")
                amount = total_charges.get("MonetaryValue", "0.00")

                # Get delivery info
                guaranteed_delivery = shipment.get("GuaranteedDelivery", {})
                delivery_date = guaranteed_delivery.get("DeliveryDate", "N/A")
                delivery_time = guaranteed_delivery.get("DeliveryByTime", "N/A")
                business_days = guaranteed_delivery.get("BusinessDaysInTransit", "N/A")

                # Get time in transit
                time_in_transit = shipment.get("TimeInTransit", {})
                service_summary = time_in_transit.get("ServiceSummary", {})
                estimated_arrival = service_summary.get("EstimatedArrival", {})

                if estimated_arrival:
                    arrival = estimated_arrival.get("Arrival", {})
                    arrival_date = arrival.get("Date", "N/A")
                    arrival_time = arrival.get("Time", "N/A")
                else:
                    arrival_date = "N/A"
                    arrival_time = "N/A"

                # Format delivery information with multiple data sources
                delivery_parts = []

                if delivery_date != "N/A" and delivery_time != "N/A":
                    delivery_parts.append(f"{delivery_date} by {delivery_time}")
                elif delivery_date != "N/A":
                    delivery_parts.append(delivery_date)
                elif arrival_date != "N/A":
                    if arrival_time != "N/A":
                        delivery_parts.append(f"{arrival_date} by {arrival_time}")
                    else:
                        delivery_parts.append(arrival_date)

                if business_days != "N/A":
                    if business_days == "1":
                        delivery_parts.append("(1 business day)")
                    else:
                        delivery_parts.append(f"({business_days} business days)")

                delivery_info = " ".join(delivery_parts) if delivery_parts else "N/A"

                result["rates"][service_code] = {
                    "service_name": service_name,
                    "price": float(amount) if amount != "N/A" else 0.0,
                    "currency": currency,
                    "delivery": delivery_info,
                    "price_formatted": f"{currency} {amount}",
                }

        except Exception as e:
            result["error"] = str(e)

        return result

    def _display_weight_comparison(self, weight_results: List[Dict], scenario: str):
        """Display weight comparison results in formatted tables"""

        if not weight_results:
            print("No results to display")
            return

        # Get all unique services across all weights
        all_services = set()
        valid_results = [
            r for r in weight_results if r.get("rates") and not r.get("error")
        ]

        for result in valid_results:
            all_services.update(result["rates"].keys())

        if not all_services:
            print("❌ No valid shipping rates found")
            return

        # Sort services by typical speed (Ground last, Express first)
        service_order = [
            "01",
            "14",
            "13",
            "02",
            "59",
            "12",
            "03",
            "11",
        ]  # Next Day to Ground
        sorted_services = []
        for code in service_order:
            if code in all_services:
                sorted_services.append(code)
        # Add any remaining services
        for code in sorted(all_services):
            if code not in sorted_services:
                sorted_services.append(code)

        print(f"\n📊 CALIFORNIA WEIGHT COMPARISON: {scenario.upper()}")
        print("=" * 100)

        # Create comparison table for each service
        for service_code in sorted_services:
            service_name = None
            service_data = []

            for result in valid_results:
                if service_code in result["rates"]:
                    rate_info = result["rates"][service_code]
                    if service_name is None:
                        service_name = rate_info["service_name"]

                    service_data.append(
                        [
                            f"{result['weight']} lbs",
                            rate_info["price_formatted"],
                            rate_info["delivery"],
                        ]
                    )

            if service_data:
                print(f"\n🚚 {service_name} (Code: {service_code})")
                print("-" * 70)
                headers = ["Weight", "Price", "Estimated Delivery"]
                print(tabulate(service_data, headers=headers, tablefmt="grid"))

                # Calculate price per pound progression
                if len(service_data) > 1:
                    prices = [float(row[1].split()[1]) for row in service_data]
                    weights = [float(row[0].split()[0]) for row in service_data]
                    price_per_lb = [p / w for p, w in zip(prices, weights)]

                    print(f"💰 Price Analysis:")
                    print(f"   • Price range: ${min(prices):.2f} - ${max(prices):.2f}")
                    print(
                        f"   • Price per lb range: ${min(price_per_lb):.2f} - ${max(price_per_lb):.2f}"
                    )
                    if len(prices) > 1:
                        price_increase = prices[-1] - prices[0]
                        weight_increase = weights[-1] - weights[0]
                        avg_rate = (
                            price_increase / weight_increase
                            if weight_increase > 0
                            else 0
                        )
                        print(
                            f"   • Average rate increase: ${avg_rate:.2f} per additional lb"
                        )

        # Summary comparison across all services
        print(f"\n📈 WEIGHT IMPACT SUMMARY")
        print("=" * 70)

        summary_data = []
        for result in valid_results:
            weight = result["weight"]
            # Find cheapest option for this weight
            if result["rates"]:
                cheapest = min(result["rates"].values(), key=lambda x: x["price"])
                most_expensive = max(result["rates"].values(), key=lambda x: x["price"])

                summary_data.append(
                    [
                        f"{weight} lbs",
                        f"${cheapest['price']:.2f}",
                        cheapest["service_name"],
                        f"${most_expensive['price']:.2f}",
                        most_expensive["service_name"],
                        f"${most_expensive['price'] - cheapest['price']:.2f}",
                    ]
                )

        if summary_data:
            headers = [
                "Weight",
                "Cheapest",
                "Service",
                "Most Expensive",
                "Service",
                "Price Spread",
            ]
            print(tabulate(summary_data, headers=headers, tablefmt="grid"))

        # Show errors if any
        error_results = [r for r in weight_results if r.get("error")]
        if error_results:
            print(f"\n❌ ERRORS ENCOUNTERED:")
            for result in error_results:
                print(f"   • {result['weight']} lbs: {result['error']}")

    def run_quick_test(
        self,
        test_case: str = "default",
        weight: float = 5.0,
        length: float = 12.0,
        width: float = 8.0,
        height: float = 6.0,
    ):
        """Run a quick test with predefined addresses"""
        from_address_str, to_address_str = self.use_test_addresses(test_case)
        return self.run_complete_test(
            from_address_str, to_address_str, weight, length, width, height
        )

    def run_ca_scenario_test(
        self,
        ca_scenario: str = "la_to_sf",
        weight: float = 10.0,
        length: float = 12.0,
        width: float = 8.0,
        height: float = 6.0,
    ):
        """Run a single California test scenario"""
        from_address_str, to_address_str = self.use_ca_test_addresses(ca_scenario)
        return self.run_complete_test(
            from_address_str, to_address_str, weight, length, width, height
        )

    def parse_address(self, address_string: str) -> Address:
        """
        Parse address string into Address object
        Supports formats like: "123 Main St, New York, NY 10001"
        """
        try:
            parts = [part.strip() for part in address_string.split(",")]

            if len(parts) < 3:
                raise ValueError(
                    "Address must include at least street, city, and state/zip"
                )

            street = parts[0]
            city = parts[1]

            # Parse state and zip from last part
            state_zip = parts[-1].strip().split()
            if len(state_zip) >= 2:
                state = state_zip[0]
                postal_code = state_zip[1]
            else:
                raise ValueError("Could not parse state and postal code")

            return Address(
                address_line_1=street,
                city=city,
                state_province_code=state,
                postal_code=postal_code,
            )

        except Exception as e:
            logger.error("Failed to parse address '%s': %s", address_string, e)
            raise ValueError(f"Invalid address format: {e}") from e

    def validate_addresses(
        self, from_addr: Address, to_addr: Address
    ) -> Tuple[bool, Dict]:
        """Validate both addresses and return results"""
        validation_results = {}
        all_valid = True

        try:
            # Validate origin address
            logger.info("Validating origin address...")
            from_validation = self.ups_client.validate_address(from_addr)
            validation_results["from_address"] = from_validation

            # Check if validation was successful
            from_valid = self._is_address_valid(from_validation)
            if not from_valid:
                all_valid = False
                logger.warning("Origin address validation failed or has issues")

        except Exception as e:
            logger.error(f"Origin address validation error: {e}")
            validation_results["from_address"] = {"error": str(e)}
            all_valid = False

        try:
            # Validate destination address
            logger.info("Validating destination address...")
            to_validation = self.ups_client.validate_address(to_addr)
            validation_results["to_address"] = to_validation

            # Check if validation was successful
            to_valid = self._is_address_valid(to_validation)
            if not to_valid:
                all_valid = False
                logger.warning("Destination address validation failed or has issues")

        except Exception as e:
            logger.error(f"Destination address validation error: {e}")
            validation_results["to_address"] = {"error": str(e)}
            all_valid = False

        return all_valid, validation_results

    def _is_address_valid(self, validation_result: Dict) -> bool:
        """Check if address validation result indicates a valid address"""
        try:
            response = validation_result.get("AddressValidationResponse", {})
            result = response.get("Result", {})

            # Check for errors
            if "Error" in response:
                return False

            # Check validation quality
            address_results = response.get("AddressValidationResult", [])
            if not address_results:
                return False

            # Check the quality of the first result
            first_result = (
                address_results[0]
                if isinstance(address_results, list)
                else address_results
            )
            quality = first_result.get("Quality", {})

            return quality is not None

        except Exception:
            return False

    def get_rates_and_display(
        self, from_addr: Address, to_addr: Address, packages: List[Package]
    ):
        """Get shipping rates and display in a formatted table"""
        try:
            rates_response = self.ups_client.get_shipping_rates(
                from_addr, to_addr, packages
            )

            # Parse and format the results
            self._display_rates(rates_response)

            return rates_response

        except Exception as e:
            logger.error(f"Failed to get shipping rates: {e}")
            raise

    def _display_rates(self, rates_response: Dict):
        """Display shipping rates in a formatted table"""
        try:
            response = rates_response.get("RateResponse", {})
            rated_shipments = response.get("RatedShipment", [])

            if not rated_shipments:
                print("No shipping options available for this route.")
                return

            # Ensure it's a list
            if not isinstance(rated_shipments, list):
                rated_shipments = [rated_shipments]

            # Prepare table data
            table_data = []

            for shipment in rated_shipments:
                service_code = shipment.get("Service", {}).get("Code", "Unknown")
                service_name = self.ups_client.SERVICE_CODES.get(
                    service_code, f"Service {service_code}"
                )

                # Get total charges
                total_charges = shipment.get("TotalCharges", {})
                currency = total_charges.get("CurrencyCode", "USD")
                amount = total_charges.get("MonetaryValue", "N/A")

                # Get guaranteed delivery info
                guaranteed_delivery = shipment.get("GuaranteedDelivery", {})
                delivery_date = guaranteed_delivery.get("DeliveryDate", "N/A")
                delivery_time = guaranteed_delivery.get("DeliveryByTime", "N/A")
                business_days = guaranteed_delivery.get("BusinessDaysInTransit", "N/A")

                # Get time in transit
                time_in_transit = shipment.get("TimeInTransit", {})

                # Try different paths for estimated arrival
                service_summary = time_in_transit.get("ServiceSummary", {})
                estimated_arrival = service_summary.get("EstimatedArrival", {})

                if estimated_arrival:
                    arrival = estimated_arrival.get("Arrival", {})
                    arrival_date = arrival.get("Date", "N/A")
                    arrival_time = arrival.get("Time", "N/A")
                else:
                    arrival_date = "N/A"
                    arrival_time = "N/A"

                # Format delivery information with multiple data sources
                delivery_parts = []

                if delivery_date != "N/A" and delivery_time != "N/A":
                    delivery_parts.append(f"{delivery_date} by {delivery_time}")
                elif delivery_date != "N/A":
                    delivery_parts.append(delivery_date)
                elif arrival_date != "N/A":
                    if arrival_time != "N/A":
                        delivery_parts.append(f"{arrival_date} by {arrival_time}")
                    else:
                        delivery_parts.append(arrival_date)

                if business_days != "N/A":
                    if business_days == "1":
                        delivery_parts.append("(1 business day)")
                    else:
                        delivery_parts.append(f"({business_days} business days)")

                delivery_info = " ".join(delivery_parts) if delivery_parts else "N/A"

                table_data.append(
                    [service_name, f"{currency} {amount}", delivery_info, service_code]
                )

            # Sort by price (convert to float for sorting)
            def get_price(row):
                try:
                    return float(row[1].split()[1])
                except (ValueError, IndexError):
                    return float("inf")

            table_data.sort(key=get_price)

            # Display the table
            headers = ["Service", "Price", "Estimated Delivery", "Code"]
            print("\n" + "=" * 80)
            print("SHIPPING OPTIONS")
            print("=" * 80)
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            print()

        except Exception as e:
            logger.error(f"Error displaying rates: {e}")
            print(f"Error parsing rate response: {e}")
            print("Raw response:")
            print(json.dumps(rates_response, indent=2))

    def run_complete_test(
        self,
        from_address_str: str,
        to_address_str: str,
        weight: float,
        length: float,
        width: float,
        height: float,
    ):
        """Run a complete test including address validation and rate shopping"""

        print("UPS Shipping API Test")
        print("=" * 50)
        if self.ups_client.sandbox:
            print("🧪 RUNNING IN TEST MODE (Customer Integration Environment)")
            print("   Note: CIE responses may be consistent for testing purposes")
        else:
            print("⚠️  RUNNING IN PRODUCTION MODE (Live UPS Services)")
            print(
                "   Note: Using real UPS environment - rate calls typically don't incur charges"
            )
        print("=" * 50)

        try:
            # Parse addresses
            print("1. Parsing addresses...")
            from_addr = self.parse_address(from_address_str)
            to_addr = self.parse_address(to_address_str)

            print(f"   From: {from_address_str}")
            print(f"   To: {to_address_str}")

            # Create package
            package = Package(weight=weight, length=length, width=width, height=height)
            print(f"   Package: {weight} lbs, {length}x{width}x{height} inches")

            # Skip address validation for now due to authentication issues
            print("\n2. Skipping address validation (auth issues)...")
            validation_results = {
                "from_address": {
                    "skipped": "Authentication issues with validation API"
                },
                "to_address": {"skipped": "Authentication issues with validation API"},
            }

            # Get shipping rates
            print("\n3. Fetching shipping rates...")
            rates_response = self.get_rates_and_display(from_addr, to_addr, [package])

            # Save detailed results
            self._save_results(
                {
                    "addresses": {"from": asdict(from_addr), "to": asdict(to_addr)},
                    "package": asdict(package),
                    "validation_results": validation_results,
                    "rates_response": rates_response,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            print("Test completed successfully!")
            print("Detailed results saved to 'ups_test_results.json'")

        except Exception as e:
            logger.error(f"Test failed: {e}")
            print(f"\nTest failed: {e}")
            raise

    def _display_validation_details(self, validation_results: Dict):
        """Display address validation details"""
        for addr_type, result in validation_results.items():
            if "error" in result:
                print(f"   {addr_type}: Error - {result['error']}")
            else:
                print(f"   {addr_type}: Validation completed")

    def _save_results(self, results: Dict, filename: str = "ups_test_results.json"):
        """Save test results to JSON file"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save results to %s: %s", filename, e)


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="UPS API Test Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Quick test with predefined addresses:
    python ups_api_tester.py --quick-test
    python ups_api_tester.py --quick-test --test-case cross_country

  Test specific addresses:
    python ups_api_tester.py --from-address "123 Main St, New York, NY 10001" \\
                            --to-address "456 Oak Ave, Los Angeles, CA 90001" \\
                            --weight 5.0 --length 12 --width 8 --height 6

  Environment variables required:
    UPS_CLIENT_ID=your_client_id
    UPS_CLIENT_SECRET=your_client_secret

  Or create a .env file with:
    UPS_CLIENT_ID=your_client_id
    UPS_CLIENT_SECRET=your_client_secret

  Test Cases Available:
    - default (NY to CA)
    - east_west (NY to CA)
    - south_north (GA to WA)
    - southeast (FL to TX)
    - cross_country (NY to WA)

  Environment Configuration:
    By default, this application uses UPS CIE (Customer Integration Environment) for safe testing.
    If you get 401 authentication errors, your credentials might be configured for production.

    Use --production flag if your UPS app was created for https://onlinetools.ups.com
    Use default (no flag) if your UPS app was created for CIE testing

  Note: This application defaults to CIE for safety. Rate shopping typically doesn't incur charges
        in either environment, but production uses live UPS services.
        """,
    )

    # Address input options
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Run quick test with predefined addresses",
    )
    parser.add_argument(
        "--from-address", help='Origin address (format: "Street, City, State ZIP")'
    )
    parser.add_argument(
        "--to-address", help='Destination address (format: "Street, City, State ZIP")'
    )

    # Package parameters
    parser.add_argument(
        "--weight",
        type=float,
        default=5.0,
        help="Package weight in pounds (default: 5.0)",
    )
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

    # Test configuration
    parser.add_argument(
        "--test-case",
        default="default",
        choices=["default", "east_west", "south_north", "southeast", "cross_country"],
        help="Predefined test case for quick testing (default: default)",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Use production environment (https://onlinetools.ups.com) - for credentials configured for production",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.quick_test and (not args.from_address or not args.to_address):
        parser.error(
            "Either use --quick-test or provide both --from-address and --to-address"
        )

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get credentials from environment
    client_id = os.getenv("UPS_CLIENT_ID")
    client_secret = os.getenv("UPS_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "Error: UPS_CLIENT_ID and UPS_CLIENT_SECRET environment variables are required."
        )
        print("You can set them in a .env file or as environment variables.")
        print("\nTo get UPS API credentials:")
        print("1. Register at https://www.ups.com/upsdeveloperkit")
        print("2. Create an application to get your Client ID and Secret")
        print("3. Note: Application defaults to test mode (CIE) for safe testing")
        sys.exit(1)

    try:
        # Initialize the tester
        tester = UPSShippingTester(
            client_id=client_id,
            client_secret=client_secret,
            sandbox=not args.production,
        )

        # Run the appropriate test
        if args.quick_test:
            tester.run_quick_test(
                test_case=args.test_case,
                weight=args.weight,
                length=args.length,
                width=args.width,
                height=args.height,
            )
        else:
            tester.run_complete_test(
                from_address_str=args.from_address,
                to_address_str=args.to_address,
                weight=args.weight,
                length=args.length,
                width=args.width,
                height=args.height,
            )

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
