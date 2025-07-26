# UPS API Developer Guide

This comprehensive guide demonstrates how to integrate with the UPS API using the implementation patterns from this project. It covers authentication, rate shopping, address validation, and best practices for production use.

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Environment Setup](#authentication--environment-setup)
3. [Core API Classes](#core-api-classes)
4. [Authentication Flow](#authentication-flow)
5. [Address Validation](#address-validation)
6. [Rate Shopping](#rate-shopping)
7. [Error Handling](#error-handling)
8. [Production Considerations](#production-considerations)
9. [Code Examples](#code-examples)
10. [Testing Strategy](#testing-strategy)

## Overview

This project provides a comprehensive UPS API integration with the following key features:

- **OAuth 2.0 Authentication** - Secure token-based authentication
- **Environment Management** - Support for both CIE (test) and Production environments
- **Rate Shopping** - Get shipping rates for multiple service types
- **Address Validation** - Validate and standardize addresses
- **Enhanced Delivery Information** - Business days, guaranteed delivery times
- **Time in Transit API** - Advanced delivery estimates with intelligent fallback
- **Error Handling** - Robust error handling and logging
- **Testing Tools** - Comprehensive testing utilities

### Key Files

- `ups_api_tester.py` - Main UPS API client and testing framework (lines 1-1198)
- `credential_test.py` - Credential validation utility (lines 1-119)
- `ca_shipping_test.py` - California-specific shipping tests (lines 1-308)

## Authentication & Environment Setup

### Environment Configuration

The UPS API supports two environments:

```python
# ups_api_tester.py:147-156
if sandbox:
    self.base_url = "https://wwwcie.ups.com"
    logger.info("Using UPS CIE (Customer Integration Environment) for testing")
else:
    self.base_url = "https://onlinetools.ups.com"
    logger.info("Using UPS Production environment")
    logger.warning("⚠️  PRODUCTION MODE: Using live UPS services")
```

### Credential Management

Store credentials securely using environment variables:

```bash
# .env file
UPS_CLIENT_ID=your_client_id_here
UPS_CLIENT_SECRET=your_client_secret_here
```

### Credential Testing

Test your credentials against both environments:

```python
# credential_test.py:16-48
def test_environment(base_url, env_name):
    """Test authentication against a specific UPS environment"""
    client_id = os.getenv('UPS_CLIENT_ID')
    client_secret = os.getenv('UPS_CLIENT_SECRET')
    
    auth_url = f"{base_url}/security/v1/oauth/token"
    auth_data = {"grant_type": "client_credentials"}
    auth_headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    try:
        response = requests.post(
            auth_url,
            data=auth_data,
            headers=auth_headers,
            auth=(client_id, client_secret),
            timeout=10
        )
        
        if response.status_code == 200:
            token_data = response.json()
            expires_in = token_data.get('expires_in', 'unknown')
            print(f"✅ {env_name} authentication successful! (expires in {expires_in}s)")
            return True
        else:
            print(f"❌ {env_name} authentication failed: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {env_name} network error: {e}")
        return False
```

## Core API Classes

### Address Data Structure

```python
# ups_api_tester.py:49-76
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
            "CountryCode": self.country_code
        }
        
        if self.address_line_2:
            ups_address["AddressLine"].append(self.address_line_2)
        if self.address_line_3:
            ups_address["AddressLine"].append(self.address_line_3)
            
        return ups_address
```

### Package Data Structure

```python
# ups_api_tester.py:78-104
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
                "Height": str(self.height)
            },
            "PackageWeight": {
                "UnitOfMeasurement": {"Code": self.weight_unit},
                "Weight": str(self.weight)
            }
        }
```

### UPS API Client

```python
# ups_api_tester.py:111-167
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
        "65": "UPS Worldwide Saver"
    }
    
    def __init__(self, client_id: str, client_secret: str, sandbox: bool = True):
        """Initialize UPS API client"""
        self.client_id = client_id
        self.client_secret = client_secret
        self.sandbox = sandbox
        self.access_token = None
        self.token_expires_at = None
        
        # API endpoints - UPS CIE vs Production
        if sandbox:
            self.base_url = "https://wwwcie.ups.com"
        else:
            self.base_url = "https://onlinetools.ups.com"
            
        self.auth_url = f"{self.base_url}/security/v1/oauth/token"
        self.rating_url = f"{self.base_url}/api/rating"
        self.address_validation_url = f"{self.base_url}/api/addressvalidation"
```

## Authentication Flow

### OAuth 2.0 Token Management

```python
# ups_api_tester.py:168-204
def _get_access_token(self) -> str:
    """Get OAuth 2.0 access token"""
    if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
        return self.access_token

    logger.info("Requesting new access token from UPS")

    auth_data = {
        "grant_type": "client_credentials"
    }

    auth_headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = self.session.post(
            self.auth_url,
            data=auth_data,
            headers=auth_headers,
            auth=(self.client_id, self.client_secret),
            timeout=30
        )
        response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data["access_token"]
        expires_in = int(token_data.get("expires_in", 3600))
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)

        logger.info("Successfully obtained access token")
        return self.access_token

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get access token: {e}")
        raise UPSAPIError(f"Authentication failed: {e}")
```

## Address Validation

### Address Validation API Call

```python
# ups_api_tester.py:205-257
def validate_address(self, address: Address) -> Dict:
    """Validate address using UPS Address Validation API"""
    logger.info(f"Validating address: {address.city}, {address.state_province_code}")

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
                "CountryCode": address.country_code
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = self.session.post(
            f"{self.address_validation_url}/v1/1",
            json=request_data,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        logger.info("Address validation completed successfully")
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Address validation failed: {e}")
        if hasattr(e.response, 'text'):
            logger.error(f"Response: {e.response.text}")
        raise UPSAPIError(f"Address validation failed: {e}")
```

### Address Parsing

```python
# ups_api_tester.py:732-764
def parse_address(self, address_string: str) -> Address:
    """Parse address string into Address object"""
    try:
        parts = [part.strip() for part in address_string.split(',')]

        if len(parts) < 3:
            raise ValueError("Address must include at least street, city, and state/zip")

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
            postal_code=postal_code
        )

    except Exception as e:
        logger.error(f"Failed to parse address '{address_string}': {e}")
        raise ValueError(f"Invalid address format: {e}")
```

## Rate Shopping & Enhanced Delivery Information

### Time in Transit API with Intelligent Fallback

The updated rate shopping implementation includes enhanced delivery information with intelligent fallback:

```python
# ups_api_tester.py:322-356 (Enhanced Version)
def get_shipping_rates(self, from_address: Address, to_address: Address,
                       packages: List[Package], shop_all: bool = True) -> Dict:
    """Get shipping rates for packages with enhanced delivery information"""
    logger.info(f"Getting shipping rates from {from_address.city} to {to_address.city}")

    token = self._get_access_token()
    request_option = "Shop" if shop_all else "Rate"

    # Build base request data
    request_data = {
        "RateRequest": {
            "Request": {
                "RequestOption": request_option,
                "TransactionReference": {
                    "CustomerContext": f"Rate Request {datetime.now().isoformat()}"
                }
            },
            "Shipment": {
                "Shipper": {"Name": "Test Shipper", "Address": from_address.to_ups_format()},
                "ShipTo": {"Name": "Test Recipient", "Address": to_address.to_ups_format()},
                "ShipFrom": {"Name": "Test Shipper", "Address": from_address.to_ups_format()},
                "Package": [pkg.to_ups_format() for pkg in packages]
            }
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
        "Content-Type": "application/json"
    }

    try:
        # Try time in transit API first, fall back to standard rating if it fails
        if shop_all and request_data["RateRequest"]["Shipment"].get("DeliveryTimeInformation"):
            endpoint = f"{self.rating_url}/v2409/Shoptimeintransit"
            logger.info("Attempting time in transit request...")
            try:
                response = self.session.post(endpoint, json=request_data, headers=headers, timeout=30)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Time in transit request failed: {e}, falling back to standard rating")
                # Remove DeliveryTimeInformation and use standard endpoint
                if "DeliveryTimeInformation" in request_data["RateRequest"]["Shipment"]:
                    del request_data["RateRequest"]["Shipment"]["DeliveryTimeInformation"]
                endpoint = f"{self.rating_url}/v2409/Shop"
                response = self.session.post(endpoint, json=request_data, headers=headers, timeout=30)
        else:
            # Use standard rating endpoint
            endpoint = f"{self.rating_url}/v2409/Shop" if shop_all else f"{self.rating_url}/v2409/Rate"
            response = self.session.post(endpoint, json=request_data, headers=headers, timeout=30)
        
        response.raise_for_status()
        result = response.json()
        logger.info("Successfully retrieved shipping rates")
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Rate request failed: {e}")
        if hasattr(e.response, 'text'):
            logger.error(f"Response: {e.response.text}")
        raise UPSAPIError(f"Rate request failed: {e}")
```

### Enhanced Delivery Information Processing

The response processing now captures comprehensive delivery information:

```python
# ups_api_tester.py:943-984 (Enhanced Version)
def _display_rates(self, rates_response: Dict):
    """Display shipping rates with enhanced delivery information"""
    try:
        response = rates_response.get('RateResponse', {})
        rated_shipments = response.get('RatedShipment', [])

        if not rated_shipments:
            print("No shipping options available for this route.")
            return

        # Ensure it's a list
        if not isinstance(rated_shipments, list):
            rated_shipments = [rated_shipments]

        # Prepare table data
        table_data = []

        for shipment in rated_shipments:
            service_code = shipment.get('Service', {}).get('Code', 'Unknown')
            service_name = self.ups_client.SERVICE_CODES.get(service_code, f"Service {service_code}")

            # Get total charges
            total_charges = shipment.get('TotalCharges', {})
            currency = total_charges.get('CurrencyCode', 'USD')
            amount = total_charges.get('MonetaryValue', 'N/A')

            # Get guaranteed delivery info
            guaranteed_delivery = shipment.get('GuaranteedDelivery', {})
            delivery_date = guaranteed_delivery.get('DeliveryDate', 'N/A')
            delivery_time = guaranteed_delivery.get('DeliveryByTime', 'N/A')
            business_days = guaranteed_delivery.get('BusinessDaysInTransit', 'N/A')

            # Get time in transit
            time_in_transit = shipment.get('TimeInTransit', {})
            service_summary = time_in_transit.get('ServiceSummary', {})
            estimated_arrival = service_summary.get('EstimatedArrival', {})
            
            if estimated_arrival:
                arrival = estimated_arrival.get('Arrival', {})
                arrival_date = arrival.get('Date', 'N/A')
                arrival_time = arrival.get('Time', 'N/A')
            else:
                arrival_date = 'N/A'
                arrival_time = 'N/A'

            # Format delivery information with multiple data sources
            delivery_parts = []
            
            if delivery_date != 'N/A' and delivery_time != 'N/A':
                delivery_parts.append(f"{delivery_date} by {delivery_time}")
            elif delivery_date != 'N/A':
                delivery_parts.append(delivery_date)
            elif arrival_date != 'N/A':
                if arrival_time != 'N/A':
                    delivery_parts.append(f"{arrival_date} by {arrival_time}")
                else:
                    delivery_parts.append(arrival_date)
            
            if business_days != 'N/A':
                if business_days == '1':
                    delivery_parts.append("(1 business day)")
                else:
                    delivery_parts.append(f"({business_days} business days)")
            
            delivery_info = " ".join(delivery_parts) if delivery_parts else "N/A"

            table_data.append([
                service_name,
                f"{currency} {amount}",
                delivery_info,
                service_code
            ])

        # Sort by price and display
        headers = ["Service", "Price", "Estimated Delivery", "Code"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    except Exception as e:
        logger.error(f"Error displaying rates: {e}")
```

## Enhanced Delivery Information Features

### Delivery Data Types Captured

The enhanced implementation captures multiple types of delivery information:

```python
# Delivery information data sources:
delivery_sources = {
    "GuaranteedDelivery": {
        "DeliveryDate": "Specific delivery date (YYYY-MM-DD)",
        "DeliveryByTime": "Guaranteed delivery time (e.g., '10:30 A.M.')",
        "BusinessDaysInTransit": "Number of business days for delivery"
    },
    "TimeInTransit": {
        "PickupDate": "Calculated pickup date",
        "ServiceSummary": {
            "EstimatedArrival": {
                "Arrival": {
                    "Date": "Estimated arrival date",
                    "Time": "Estimated arrival time"
                }
            }
        }
    }
}
```

### Business Day Calculation

The system automatically calculates the next business day for pickup:

```python
# ups_api_tester.py:307-315
# Calculate pickup date (next business day)
pickup_date = datetime.now() + timedelta(days=1)
# Skip weekends
while pickup_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
    pickup_date += timedelta(days=1)
    
request_data["RateRequest"]["Shipment"]["DeliveryTimeInformation"] = {
    "PickupDate": pickup_date.strftime("%Y%m%d")
}
```

### Delivery Information Output Examples

The enhanced system provides detailed delivery estimates:

```
┌─────────────────────────┬─────────────┬──────────────────────────┬──────┐
│ Service                 │ Price       │ Estimated Delivery       │ Code │
├─────────────────────────┼─────────────┼──────────────────────────┼──────┤
│ UPS Ground              │ USD 25.98   │ N/A                      │ 03   │
│ UPS 3 Day Select        │ USD 63.06   │ (3 business days)        │ 12   │
│ UPS 2nd Day Air         │ USD 82.74   │ (2 business days)        │ 02   │
│ UPS 2nd Day Air A.M.    │ USD 93.78   │ (2 business days)        │ 59   │
│ UPS Next Day Air Saver  │ USD 150.19  │ (1 business day)         │ 13   │
│ UPS Next Day Air        │ USD 159.97  │ (1 business day)         │ 01   │
│ UPS Next Day Air Early  │ USD 195.90  │ (1 business day)         │ 14   │
└─────────────────────────┴─────────────┴──────────────────────────┴──────┘
```

### API Fallback Strategy

The system implements intelligent fallback when time-in-transit API fails:

1. **Primary**: Attempt `Shoptimeintransit` endpoint with `DeliveryTimeInformation`
2. **Fallback**: Remove delivery information and use standard `Shop` endpoint
3. **Logging**: Detailed logging of fallback reasons and responses

### Rate Response Processing

```python
# ups_api_tester.py:563-617
def _parse_rates_for_comparison(self, rates_response: Dict, weight: float) -> Dict:
    """Parse UPS rates response for weight comparison"""
    result = {
        'weight': weight,
        'rates': {},
        'error': None
    }

    try:
        response = rates_response.get('RateResponse', {})
        rated_shipments = response.get('RatedShipment', [])

        if not rated_shipments:
            result['error'] = "No shipping options available"
            return result

        # Ensure it's a list
        if not isinstance(rated_shipments, list):
            rated_shipments = [rated_shipments]

        for shipment in rated_shipments:
            service_code = shipment.get('Service', {}).get('Code', 'Unknown')
            service_name = self.ups_client.SERVICE_CODES.get(service_code, f"Service {service_code}")

            # Get total charges
            total_charges = shipment.get('TotalCharges', {})
            currency = total_charges.get('CurrencyCode', 'USD')
            amount = total_charges.get('MonetaryValue', '0.00')

            # Get delivery info
            guaranteed_delivery = shipment.get('GuaranteedDelivery', {})
            delivery_date = guaranteed_delivery.get('DeliveryDate', 'N/A')
            delivery_time = guaranteed_delivery.get('DeliveryTime', 'N/A')

            # Format delivery information
            if delivery_date != 'N/A' and delivery_time != 'N/A':
                delivery_info = f"{delivery_date} by {delivery_time}"
            elif delivery_date != 'N/A':
                delivery_info = delivery_date
            else:
                delivery_info = "N/A"

            result['rates'][service_code] = {
                'service_name': service_name,
                'price': float(amount) if amount != 'N/A' else 0.0,
                'currency': currency,
                'delivery': delivery_info,
                'price_formatted': f"{currency} {amount}"
            }

    except Exception as e:
        result['error'] = str(e)

    return result
```

## Error Handling

### Custom Exception Class

```python
# ups_api_tester.py:106-109
class UPSAPIError(Exception):
    """Custom exception for UPS API errors"""
    pass
```

### Error Handling in API Calls

```python
# ups_api_tester.py:200-204
except requests.exceptions.RequestException as e:
    logger.error(f"Failed to get access token: {e}")
    raise UPSAPIError(f"Authentication failed: {e}")
```

### Robust Error Recovery

```python
# ups_api_tester.py:873-897
def _is_address_valid(self, validation_result: Dict) -> bool:
    """Check if address validation result indicates a valid address"""
    try:
        response = validation_result.get('AddressValidationResponse', {})
        result = response.get('Result', {})

        # Check for errors
        if 'Error' in response:
            return False

        # Check validation quality
        address_results = response.get('AddressValidationResult', [])
        if not address_results:
            return False

        # Check the quality of the first result
        first_result = address_results[0] if isinstance(address_results, list) else address_results
        quality = first_result.get('Quality', {})

        return quality is not None

    except Exception:
        return False
```

## Production Considerations

### Environment Selection

```python
# ups_api_tester.py:1134-1137
parser.add_argument('--production', action='store_true',
                   help='Use production environment (https://onlinetools.ups.com) - for credentials configured for production')
```

### Connection Management

```python
# ups_api_tester.py:161-167
# Request session for connection pooling
self.session = requests.Session()
self.session.headers.update({
    "Content-Type": "application/json",
    "Accept": "application/json"
})
```

### Token Caching

```python
# ups_api_tester.py:168-171
def _get_access_token(self) -> str:
    """Get OAuth 2.0 access token"""
    if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
        return self.access_token
```

## Code Examples

### Basic Rate Request

```python
from ups_api_tester import UPSAPIClient, Address, Package

# Initialize client
client = UPSAPIClient("your_client_id", "your_client_secret", sandbox=True)

# Create addresses
from_addr = Address(
    address_line_1="123 Main St",
    city="New York",
    state_province_code="NY",
    postal_code="10001"
)

to_addr = Address(
    address_line_1="456 Oak Ave",
    city="Los Angeles",
    state_province_code="CA",
    postal_code="90001"
)

# Create package
package = Package(weight=5.0, length=12.0, width=8.0, height=6.0)

# Get rates
rates = client.get_shipping_rates(from_addr, to_addr, [package])
```

### Weight Comparison Testing

```python
# ca_shipping_test.py:273-283
if args.weight_comparison:
    print(f"🏋️ Starting California weight comparison test: {scenario}")
    tester.run_weight_comparison_test(
        ca_scenario=scenario,
        weight_min=args.weight_min,
        weight_max=args.weight_max,
        weight_step=args.weight_step,
        length=args.length,
        width=args.width,
        height=args.height
    )
```

### Complete Test Flow

```python
# ups_api_tester.py:991-1051
def run_complete_test(self, from_address_str: str, to_address_str: str,
                      weight: float, length: float, width: float, height: float):
    """Run a complete test including address validation and rate shopping"""
    
    print("UPS Shipping API Test")
    print("=" * 50)
    
    try:
        # Parse addresses
        print("1. Parsing addresses...")
        from_addr = self.parse_address(from_address_str)
        to_addr = self.parse_address(to_address_str)
        
        # Create package
        package = Package(weight=weight, length=length, width=width, height=height)
        print(f"   Package: {weight} lbs, {length}x{width}x{height} inches")
        
        # Validate addresses
        print("2. Validating addresses...")
        addresses_valid, validation_results = self.validate_addresses(from_addr, to_addr)
        
        # Get shipping rates
        print("3. Fetching shipping rates...")
        rates_response = self.get_rates_and_display(from_addr, to_addr, [package])
        
        # Save results
        self._save_results({
            'addresses': {
                'from': asdict(from_addr),
                'to': asdict(to_addr)
            },
            'package': asdict(package),
            'validation_results': validation_results,
            'rates_response': rates_response,
            'timestamp': datetime.now().isoformat()
        })
        
        print("Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
```

## Testing Strategy

### Environment Testing

Use the credential test to verify environment compatibility:

```bash
python credential_test.py
```

### Quick Testing

Test basic functionality with predefined addresses:

```bash
python ups_api_tester.py --quick-test
```

### Production Testing

Test with production environment:

```bash
python ups_api_tester.py --quick-test --production
```

### California-Specific Testing

Test weight comparisons for California routes:

```bash
python ca_shipping_test.py --weight-comparison la_to_sf
```

### Custom Address Testing

Test specific addresses:

```bash
python ups_api_tester.py \
  --from-address "123 Main St, New York, NY 10001" \
  --to-address "456 Oak Ave, Los Angeles, CA 90001" \
  --weight 10 --verbose
```

## Best Practices

1. **Environment Management**: Always start with CIE (sandbox) for testing
2. **Token Caching**: Implement proper token expiration handling
3. **Error Handling**: Use comprehensive error handling for all API calls
4. **Logging**: Implement detailed logging for debugging
5. **Address Validation**: Always validate addresses before rate shopping
6. **Connection Pooling**: Use session objects for multiple requests
7. **Rate Limiting**: Implement appropriate delays between requests
8. **Credential Security**: Never hardcode credentials, use environment variables

## API Endpoints Used

- **Authentication**: `/security/v1/oauth/token`
- **Address Validation**: `/api/addressvalidation/v1/1`
- **Rate Shopping (Standard)**: `/api/rating/v2409/Shop`
- **Rate Shopping (Individual)**: `/api/rating/v2409/Rate`
- **Time in Transit (Shopping)**: `/api/rating/v2409/Shoptimeintransit`
- **Time in Transit (Individual)**: `/api/rating/v2409/Ratetimeintransit`

## Service Codes Reference

From `ups_api_tester.py:115-128`:

```python
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
    "65": "UPS Worldwide Saver"
}
```

This guide provides a complete foundation for integrating with the UPS API using the patterns and best practices demonstrated in this project.