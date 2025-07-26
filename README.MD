# UPS API Tester

![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

A comprehensive Python application suite for testing UPS shipping services.

## Tools

### **1. `ups_api_tester.py` - General UPS Testing**

- **National routes** (NY to CA, cross-country, etc.)
- **Custom address testing** anywhere in the US
- **Quick testing** with predefined scenarios
- **Production-ready** OAuth 2.0 authentication
- **Enhanced delivery estimates** with business days and delivery times
- **Intelligent fallback** from time-in-transit to standard rating API

### **2. `ca_shipping_test.py` - California Shipping Analysis**

- **California-specific** routes and addresses
- **Weight comparison** testing (5-30 lbs range)
- **Rate analysis** across multiple weight points
- **Price optimization** for California businesses

## Test Mode Configuration

Both applications use **UPS Customer Integration Environment (CIE)** by default:

- **Default Environment**: UPS CIE (`https://wwwcie.ups.com`)
- **Safe Testing**: No real shipping charges or live operations
- **Consistent Responses**: CIE may return consistent responses for testing purposes
- **Test Tracking Numbers**: `1ZCIETST0111111114`, `1ZCIETST0422222228`

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get UPS API Credentials

1. Register at [UPS Developer Portal](https://www.ups.com/upsdeveloperkit)
2. Create an application to get your Client ID and Secret
3. Configure environment variables

### 3. Configure Environment

```bash
# Copy the sample environment file
cp .env.sample .env

# Edit .env and add your credentials
UPS_CLIENT_ID=your_client_id_here
UPS_CLIENT_SECRET=your_client_secret_here
```

### 4. Test Your Credentials

```bash
# Test which environment your credentials work with
python credential_test.py
```

### 5. Choose Your Tool

#### For General UPS Testing:

```bash
python ups_api_tester.py --quick-test
```

#### For California Shipping Analysis:

```bash
python ca_shipping_test.py --weight-comparison la_to_sf
```

---

## Enhanced Delivery Information

Both tools now provide comprehensive estimated delivery information:

### **Delivery Data Captured**

- **Business days in transit** (1, 2, or 3 business days)
- **Guaranteed delivery times** (e.g., "by 10:30 A.M.")
- **Service-specific estimates** for each UPS shipping option
- **Automatic fallback** when time-in-transit API is unavailable

### **Example Delivery Information**

```
UPS Next Day Air        USD 159.97    (1 business day)
UPS 2nd Day Air         USD 82.74     (2 business days)  
UPS 3 Day Select        USD 63.06     (3 business days)
UPS Ground              USD 25.98     N/A
```

### **API Integration Notes**

- **Time in Transit API**: Attempts to use enhanced delivery estimates first
- **Standard Rating API**: Falls back automatically if time-in-transit fails
- **Pickup Date Calculation**: Automatically calculates next business day for transit estimates
- **Weekend Handling**: Skips weekends when calculating pickup dates

---

## UPS API Tester (`ups_api_tester.py`)

### **Purpose:** General UPS shipping rate testing for national routes

### **Basic Commands**

#### Quick Test (National Routes)

```bash
# Default test scenario (NY to CA)
python ups_api_tester.py --quick-test

# Different national scenarios
python ups_api_tester.py --quick-test --test-case cross_country
python ups_api_tester.py --quick-test --test-case southeast
python ups_api_tester.py --quick-test --test-case south_north
python ups_api_tester.py --quick-test --test-case east_west

# With custom package details
python ups_api_tester.py --quick-test --weight 15 --length 20 --width 16 --height 12
```

#### Custom Address Testing

```bash
# Basic custom address test
python ups_api_tester.py \
  --from-address "123 Main St, New York, NY 10001" \
  --to-address "456 Oak Ave, Los Angeles, CA 90001"

# With specific package and environment
python ups_api_tester.py \
  --from-address "100 Main Street, Atlanta, GA 30309" \
  --to-address "200 Pine St, Seattle, WA 98101" \
  --weight 25 --length 20 --width 16 --height 14 \
  --production --verbose
```

#### Environment Options

```bash
# CIE environment (default - safe for testing)
python ups_api_tester.py --quick-test

# Production environment (live UPS services)
python ups_api_tester.py --quick-test --production

# Verbose logging for debugging
python ups_api_tester.py --quick-test --verbose
```

### **Available National Test Scenarios**

| Scenario        | Route   | Description                |
|-----------------|---------|----------------------------|
| `default`       | NY → CA | Default east-west shipping |
| `east_west`     | NY → CA | East coast to west coast   |
| `south_north`   | GA → WA | Southeast to northwest     |
| `southeast`     | FL → TX | Florida to Texas           |
| `cross_country` | NY → WA | New York to Seattle        |

### **UPS API Tester Parameters**

| Parameter        | Default   | Description                | Example                                |
|------------------|-----------|----------------------------|----------------------------------------|
| `--quick-test`   | -         | Use predefined addresses   | `--quick-test`                         |
| `--from-address` | -         | Origin address             | `"123 Main St, New York, NY 10001"`    |
| `--to-address`   | -         | Destination address        | `"456 Oak Ave, Los Angeles, CA 90001"` |
| `--weight`       | 5.0       | Package weight (lbs)       | `--weight 15`                          |
| `--length`       | 12.0      | Package length (inches)    | `--length 20`                          |
| `--width`        | 8.0       | Package width (inches)     | `--width 16`                           |
| `--height`       | 6.0       | Package height (inches)    | `--height 12`                          |
| `--test-case`    | `default` | National scenario          | `--test-case cross_country`            |
| `--production`   | False     | Use production environment | `--production`                         |
| `--verbose`      | False     | Detailed logging           | `--verbose`                            |

---

## California Shipping Tester (`ca_shipping_test.py`)

### **Purpose:** Specialized California shipping analysis with weight comparison (5-30 lbs)

### **California Weight Comparison**

#### Default Weight Range Testing

```bash
# Test weights 5, 10, 15, 20, 25, 30 lbs for LA to SF
python ca_shipping_test.py --weight-comparison la_to_sf

# Test LA to San Diego weight progression
python ca_shipping_test.py --weight-comparison la_to_san_diego

# Test SF to LA with weight analysis
python ca_shipping_test.py --weight-comparison sf_to_la
```

#### Custom Weight Range Testing

```bash
# Custom weight range (10-50 lbs, every 10 lbs)
python ca_shipping_test.py --weight-comparison la_to_fresno \
  --weight-min 10 --weight-max 50 --weight-step 10

# Precise weight testing (every 2.5 lbs)
python ca_shipping_test.py --weight-comparison sf_to_la \
  --weight-min 5 --weight-max 25 --weight-step 2.5

# Light packages for e-commerce (1-15 lbs)
python ca_shipping_test.py --weight-comparison la_metro \
  --weight-min 1 --weight-max 15 --weight-step 1

# Heavy packages for B2B (20-70 lbs)
python ca_shipping_test.py --weight-comparison coast_to_inland \
  --weight-min 20 --weight-max 70 --weight-step 5
```

### **California Single Tests**

#### Test Specific Routes

```bash
# Test SF to LA with 15 lb package
python ca_shipping_test.py --single-test sf_to_la --weight 15

# Test metro delivery (short distance)
python ca_shipping_test.py --single-test la_metro --weight 5

# Test long distance with heavy package
python ca_shipping_test.py --single-test la_to_sf --weight 30

# Test medium distance route
python ca_shipping_test.py --single-test oakland_to_san_jose --weight 10
```

#### Custom Package Dimensions

```bash
# Small packages
python ca_shipping_test.py --single-test sf_metro \
  --weight 3 --length 8 --width 6 --height 4

# Large packages
python ca_shipping_test.py --single-test socal_central \
  --weight 45 --length 36 --width 24 --height 18
```

### **Batch California Testing**

#### Quick Comparison

```bash
# Test popular CA routes with 10 lb packages
python ca_shipping_test.py --quick-compare
```

#### All Scenarios

```bash
# Test all 12 CA scenarios with 15 lb packages
python ca_shipping_test.py --all-scenarios --weight 15

# Test all scenarios with 25 lb packages
python ca_shipping_test.py --all-scenarios --weight 25
```

#### List Available Scenarios

```bash
# Show all California test scenarios
python ca_shipping_test.py --list-scenarios
```

### **California Test Scenarios**

#### Long Distance Routes (200+ miles)

| Scenario           | Route                       | Distance  | Best For             |
|--------------------|-----------------------------|-----------|----------------------|
| `la_to_sf`         | Los Angeles → San Francisco | 380 miles | Cross-state analysis |
| `sf_to_la`         | San Francisco → Los Angeles | 380 miles | Reverse cross-state  |
| `la_to_san_diego`  | Los Angeles → San Diego     | 120 miles | SoCal corridor       |
| `sf_to_sacramento` | San Francisco → Sacramento  | 90 miles  | NorCal corridor      |

#### Medium Distance Routes (100-200 miles)

| Scenario              | Route                     | Distance  | Best For                |
|-----------------------|---------------------------|-----------|-------------------------|
| `la_to_fresno`        | Los Angeles → Fresno      | 220 miles | Coast to Central Valley |
| `oakland_to_san_jose` | Oakland → San Jose        | 45 miles  | Bay Area shipping       |
| `socal_central`       | Los Angeles → Bakersfield | 110 miles | SoCal distribution      |
| `norcal_central`      | San Francisco → Fresno    | 185 miles | NorCal distribution     |
| `coast_to_inland`     | Long Beach → Fresno       | 230 miles | Coast to inland         |

#### Short Distance Routes (<100 miles)

| Scenario        | Route                     | Distance | Best For       |
|-----------------|---------------------------|----------|----------------|
| `la_metro`      | LA Downtown → LA Westside | 15 miles | Metro delivery |
| `sf_metro`      | SF Downtown → SF Mission  | 3 miles  | Urban delivery |
| `orange_county` | Anaheim → Long Beach      | 25 miles | Orange County  |

### **California Tester Parameters**

| Parameter             | Default | Description                | Example             |
|-----------------------|---------|----------------------------|---------------------|
| `--weight-comparison` | -       | Weight comparison test     | `la_to_sf`          |
| `--single-test`       | -       | Single scenario test       | `sf_to_la`          |
| `--quick-compare`     | -       | Quick popular routes       | -                   |
| `--all-scenarios`     | -       | Test all CA scenarios      | -                   |
| `--list-scenarios`    | -       | Show available scenarios   | -                   |
| `--weight`            | 10.0    | Single test weight (lbs)   | `--weight 15`       |
| `--weight-min`        | 5.0     | Min weight for comparison  | `--weight-min 10`   |
| `--weight-max`        | 30.0    | Max weight for comparison  | `--weight-max 50`   |
| `--weight-step`       | 5.0     | Weight increment           | `--weight-step 2.5` |
| `--length`            | 12.0    | Package length (inches)    | `--length 20`       |
| `--width`             | 8.0     | Package width (inches)     | `--width 16`        |
| `--height`            | 6.0     | Package height (inches)    | `--height 12`       |
| `--production`        | False   | Use production environment | `--production`      |
| `--verbose`           | False   | Detailed logging           | `--verbose`         |

---

## Expected Output Examples

### **UPS API Tester Output (National)**

```
UPS Shipping API Test
==================================================
RUNNING IN TEST MODE (Customer Integration Environment)
==================================================

1. Parsing addresses...
   From: 123 Main St, New York, NY 10001
   To: 456 Oak Ave, Los Angeles, CA 90001
   Package: 5.0 lbs, 12x8x6 inches

2. Validating addresses...
   ✓ Addresses validated successfully

3. Fetching shipping rates...

================================================================================
SHIPPING OPTIONS
================================================================================
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

Test completed successfully!
```

### **California Tester Output (Weight Comparison)**

```
UPS California Weight Comparison Test
============================================================
Route: la_to_san_diego
   From: 123 Spring St, Los Angeles, CA 90012
   To: 654 Broadway, San Diego, CA 92101
Weight Range: 5.0 - 30.0 lbs (step: 5.0 lbs)
Package Dimensions: 12x8x6 inches
============================================================

UPS Ground (Code: 03)
┌─────────┬────────────┬──────────────────────────┐
│ Weight  │ Price      │ Estimated Delivery       │
├─────────┼────────────┼──────────────────────────┤
│ 5 lbs   │ USD 8.45   │ 2025-07-28               │
│ 10 lbs  │ USD 10.67  │ 2025-07-28               │
│ 15 lbs  │ USD 12.90  │ 2025-07-28               │
│ 20 lbs  │ USD 15.34  │ 2025-07-28               │
│ 25 lbs  │ USD 17.67  │ 2025-07-28               │
│ 30 lbs  │ USD 20.45  │ 2025-07-28               │
└─────────┴────────────┴──────────────────────────┘
Price Analysis:
   • Price range: $8.45 - $20.45
   • Price per lb range: $1.69 - $0.68
   • Average rate increase: $0.48 per additional lb

WEIGHT IMPACT SUMMARY
======================================================================
┌─────────┬───────────┬─────────────────┬───────────────┬─────────────────┬─────────────┐
│ Weight  │ Cheapest  │ Service         │ Most Expensive │ Service         │ Price Spread │
├─────────┼───────────┼─────────────────┼───────────────┼─────────────────┼─────────────┤
│ 5 lbs   │ $8.45     │ UPS Ground      │ $65.45        │ UPS Next Day Air │ $57.00      │
│ 10 lbs  │ $10.67    │ UPS Ground      │ $72.67        │ UPS Next Day Air │ $62.00      │
│ 15 lbs  │ $12.90    │ UPS Ground      │ $79.90        │ UPS Next Day Air │ $67.00      │
└─────────┴───────────┴─────────────────┴───────────────┴─────────────────┴─────────────┘

Weight comparison completed!
Detailed results saved to 'ups_ca_weight_comparison_la_to_san_diego_20250726_143052.json'
```

---

## Use Case Examples

### **E-commerce Optimization (California Tester)**

```bash
# Find optimal pricing breaks for online store
python ca_shipping_test.py --weight-comparison la_to_sf \
  --weight-min 1 --weight-max 20 --weight-step 1

# Compare metro vs long-distance for small packages
python ca_shipping_test.py --weight-comparison la_metro --weight-min 1 --weight-max 5
python ca_shipping_test.py --weight-comparison la_to_sf --weight-min 1 --weight-max 5
```

### **National Distribution Analysis (UPS Tester)**

```bash
# Test cross-country shipping costs
python ups_api_tester.py --quick-test --test-case cross_country --weight 15

# Compare different national routes
python ups_api_tester.py --quick-test --test-case southeast --weight 10
python ups_api_tester.py --quick-test --test-case south_north --weight 10
```

### **B2B Regional Strategy (California Tester)**

```bash
# Test medium business packages across CA
python ca_shipping_test.py --weight-comparison la_to_fresno \
  --weight-min 10 --weight-max 40 --weight-step 5

# Compare bidirectional rates for route optimization
python ca_shipping_test.py --single-test la_to_sf --weight 15
python ca_shipping_test.py --single-test sf_to_la --weight 15
```

---

## Output Files

### **UPS API Tester Files**

- `ups_test_results.json` - Single test results
- `ups_api.log` - Application logs

### **California Tester Files**

- `ups_ca_weight_comparison_SCENARIO_TIMESTAMP.json` - Weight comparison analysis
- `ca_all_scenarios_WEIGHT_TIMESTAMP.json` - All scenarios results

### **View Results**

```bash
# View latest California weight comparison
ls -la ups_ca_weight_comparison_*.json
cat ups_ca_weight_comparison_*.json | python -m json.tool

# View UPS tester results
cat ups_test_results.json | python -m json.tool

# Monitor logs
tail -f ups_api.log
```

---

## Troubleshooting

### **Authentication Issues**

```bash
# Test your credentials first
python credential_test.py

# If using production credentials, add --production flag
python ups_api_tester.py --quick-test --production
python ca_shipping_test.py --weight-comparison la_to_sf --production
```

### **Missing Arguments**

```bash
# UPS API Tester - need either quick test or addresses
python ups_api_tester.py --quick-test
python ups_api_tester.py --from-address "From" --to-address "To"

# California Tester - need a command
python ca_shipping_test.py --weight-comparison la_to_sf
python ca_shipping_test.py --single-test sf_to_la --weight 15
```

### **Debugging**

```bash
# Enable verbose logging for both tools
python ups_api_tester.py --quick-test --verbose
python ca_shipping_test.py --weight-comparison la_to_sf --verbose

# Check environment variables
echo $UPS_CLIENT_ID
echo $UPS_CLIENT_SECRET
```

---

## Quick Command Reference

### **UPS API Tester (National Routes)**

```bash
# Essential commands
python credential_test.py                              # Test credentials
python ups_api_tester.py --quick-test                 # Basic national test
python ups_api_tester.py --quick-test --production    # Production test
python ups_api_tester.py --quick-test --verbose       # Detailed logging

# National scenarios
python ups_api_tester.py --quick-test --test-case cross_country
python ups_api_tester.py --quick-test --test-case southeast

# Custom addresses
python ups_api_tester.py --from-address "From" --to-address "To"
```

### **California Tester (CA Analysis)**

```bash
# Weight comparison tests
python ca_shipping_test.py --weight-comparison la_to_sf
python ca_shipping_test.py --weight-comparison sf_to_la --weight-min 10 --weight-max 50

# Single tests
python ca_shipping_test.py --single-test la_to_san_diego --weight 15
python ca_shipping_test.py --single-test sf_metro --weight 5

# Batch tests
python ca_shipping_test.py --quick-compare
python ca_shipping_test.py --all-scenarios --weight 10
python ca_shipping_test.py --list-scenarios
```

---

## When to Use Which Tool

### **Use `ups_api_tester.py` for:**

- **National shipping** routes (cross-country, regional)
- **Custom addresses** anywhere in the US
- **Quick testing** of UPS API functionality
- **Single shipping** rate lookups
- **General UPS** integration testing

### **Use `ca_shipping_test.py` for:**

- **California-specific** shipping analysis
- **Weight comparison** studies (5-30 lbs)
- **Rate optimization** for CA businesses
- **Price scaling** analysis across weight ranges
- **Distribution strategy** for California markets

---

For more information, visit the [UPS Developer Portal](https://www.ups.com/upsdeveloperkit) or check
the [API documentation](https://github.com/UPS-API/api-documentation).
gfdbmghjkhkghkgjdjgh