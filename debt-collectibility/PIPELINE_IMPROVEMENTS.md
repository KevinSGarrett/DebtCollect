# Pipeline Stages Improvements

## Overview
This document outlines the improvements made to ensure both `skiptrace_apify.py` and `verify_contacts.py` stages work correctly individually and together, with proper name+address matching and contact verification.

## Stage 1: skiptrace_apify.py Improvements

### ✅ **Enhanced Name+Address Matching**
- **Strict Matching**: Only accepts candidates with 90+ confidence scores
- **Address Verification**: Requires state to match exactly and zip codes to be similar (first 5 digits)
- **Fallback Logic**: If no strict matches, tries name-only with address verification (85+ name similarity)
- **Quality Control**: Prevents false positives like "KEVIN GARRETT FORD" when searching for "KEVIN GARRETT"

### ✅ **Improved Data Processing**
- **Age Handling**: Extracts numeric age from strings like "39 years old"
- **DOB Parsing**: Handles multiple date formats with fallback parsing
- **Phone/Email Separation**: Each contact is stored as a separate record (not comma-separated)
- **Provenance Tracking**: Accurately tracks data source (apify, rapidapi, manual)

### ✅ **RapidAPI Integration**
- **Response Structure**: Handles RapidAPI's unique response format (`Source1` array, `FullName`, `PeoplePhone`, `Email`)
- **Name Validation**: Only accepts candidates with exact name matches
- **Data Transformation**: Converts RapidAPI format to match Apify format for consistency

## Stage 2: verify_contacts.py Improvements

### ✅ **Comprehensive Contact Verification**
- **Phone Verification**: 
  - Primary: Real Phone Validation API
  - Fallback: Twilio API
  - Removes invalid phone numbers
- **Email Verification**:
  - Primary: Hunter.io API
  - Fallback: Marked as unverified (Twilio doesn't do email validation)
  - Removes invalid email addresses

### ✅ **Data Cleanup & Quality**
- **Invalid Contact Removal**: Automatically removes contacts without proper data
- **Verification Scoring**: Assigns confidence scores based on API responses
- **Best Contact Selection**: Chooses highest-scoring verified contacts
- **Debtor Updates**: Updates debtor with best phone/email references

### ✅ **Error Handling & Logging**
- **Comprehensive Logging**: Tracks all verification steps and results
- **Graceful Fallbacks**: Continues processing even if individual verifications fail
- **Summary Reporting**: Provides detailed counts of verified/removed contacts

## Testing & Validation

### 🧪 **Test Scripts Created**
1. **`test_individual_stages.py`**: Tests each stage function independently
2. **`test_pipeline_stages.py`**: Tests both stages working together end-to-end

### 🔍 **Test Coverage**
- **RapidAPI Function**: Direct function testing
- **Hunter.io Function**: Email verification testing  
- **RPV Function**: Phone validation testing
- **Full Pipeline**: Complete debtor processing workflow

## Data Flow & Quality Assurance

### 📊 **Stage 1 → Stage 2 Flow**
```
Debtor Input → Skiptrace → Contact Discovery → Contact Creation → Verification → Cleanup → Best Contact Selection
```

### 🎯 **Quality Gates**
1. **Name+Address Match**: 90+ confidence required for strict matching
2. **Contact Validation**: Only verified contacts remain after Stage 2
3. **Data Integrity**: Invalid contacts automatically removed
4. **Provenance Tracking**: Full audit trail of data sources

### 🔒 **Data Security**
- **Environment Variables**: All API keys stored securely
- **Error Handling**: No sensitive data exposed in error messages
- **Validation**: All inputs validated before processing

## Environment Variables Required

### **Skiptrace Stage**
- `APIFY_TOKEN`: Apify API access token
- `RAPIDAPI_KEY`: RapidAPI access key
- `MANUAL_APIFY_DIR`: Directory for manual test data

### **Verification Stage**
- `HUNTER_API_KEY`: Hunter.io email verification API key
- `REALPHONEVALIDATION_API_KEY`: Real Phone Validation API key
- `TWILIO_ACCOUNT_SID`: Twilio account SID (fallback)
- `TWILIO_AUTH_TOKEN`: Twilio auth token (fallback)

## Usage Examples

### **Running Individual Tests**
```bash
cd debt-collectibility
python scripts/test_individual_stages.py
```

### **Running Full Pipeline Test**
```bash
cd debt-collectibility
python scripts/test_pipeline_stages.py
```

### **Manual Testing**
```python
from src.stages.skiptrace_apify import run as skiptrace_run
from src.stages.verify_contacts import run as verify_contacts_run

# Test debtor
debtor = {
    "first_name": "Kevin",
    "last_name": "Garrett", 
    "address_line1": "1212 N Loop 336 W",
    "city": "Conroe",
    "state": "TX",
    "zip": "77301"
}

# Run stages
skiptrace_result = skiptrace_run(debtor, dx)
verify_result = verify_contacts_run(debtor, dx)
```

## Expected Results

### **Stage 1 Output**
- Creates phone and email records in Directus
- Updates debtor with age/DOB if available
- All contacts have proper provenance tracking
- Match strength scores reflect confidence levels

### **Stage 2 Output**
- Verifies all contacts using external APIs
- Removes invalid contacts automatically
- Updates contact records with verification status
- Selects and assigns best contacts to debtor
- Provides comprehensive verification summary

## Troubleshooting

### **Common Issues**
1. **Missing API Keys**: Check environment variables
2. **API Rate Limits**: Implement delays if needed
3. **Network Errors**: Functions include fallback mechanisms
4. **Data Format Issues**: Logs provide detailed debugging info

### **Debug Mode**
- Enable detailed logging in both stages
- Check `logs/` directory for API responses
- Use test scripts to isolate issues

## Future Enhancements

### **Potential Improvements**
1. **Batch Processing**: Process multiple debtors simultaneously
2. **Caching**: Cache verification results to reduce API calls
3. **Advanced Matching**: Implement fuzzy address matching
4. **Metrics Dashboard**: Track verification success rates
5. **Webhook Integration**: Real-time verification notifications

## Conclusion

The improved pipeline stages now provide:
- **Robust Name+Address Matching**: Prevents false positives
- **Comprehensive Contact Verification**: Ensures data quality
- **Automatic Cleanup**: Removes invalid contacts
- **Full Audit Trail**: Tracks all data sources and changes
- **Production Ready**: Includes proper error handling and logging

Both stages work independently and together, providing a complete solution for debtor contact enrichment and verification.
