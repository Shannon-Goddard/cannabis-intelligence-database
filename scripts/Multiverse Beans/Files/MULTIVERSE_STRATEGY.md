# Multiverse Beans Scraping Strategy

## 🚫 CURRENT STATUS: BLOCKED
**Date**: January 27, 2025  
**Issue**: Strong anti-bot protection blocking BrightData Web Unlocker API  
**Response**: 200 status but 0 characters content  

## 🎯 SITE STRUCTURE IDENTIFIED

### Category URLs
- **Autoflower**: https://multiversebeans.com/flowering-type/autoflower/
- **Photoperiod**: https://multiversebeans.com/flowering-type/photoperiod/

### Product URL Pattern
- **Format**: https://multiversebeans.com/product/{strain-name}/
- **Example**: https://multiversebeans.com/product/blue-dream-full-term-atlas-seeds-photoperiod-cannabis-seeds-female/

### Expected Pagination
- **Format**: https://multiversebeans.com/flowering-type/autoflower/page/2/
- **WooCommerce**: Standard WordPress e-commerce pagination

## 🛠️ TECHNICAL APPROACH

### Two-Phase Scraping Strategy
1. **Phase 1**: Collect product URLs from category pages
2. **Phase 2**: Extract strain data from individual product pages

### Expected Data Points
- **Strain Name**: From product title (h1.product_title)
- **Breeder**: From title or product details
- **Genetics**: Sativa/Indica percentages
- **Flowering Time**: Days or weeks
- **THC Content**: Min/max percentages
- **Seed Type**: Autoflower vs Photoperiod (from category)

## 🔧 SCRAPER IMPLEMENTATION

### Product URL Extraction
```python
selectors = [
    'a[href*="/product/"]',
    '.product a',
    '.woocommerce-loop-product__link',
    'h2.woocommerce-loop-product__title a'
]
```

### Data Extraction Patterns
```python
# Genetics
r'(\d+)%?\s*sativa[^\d]*(\d+)%?\s*indica'

# Flowering Time  
r'flowering[^\d]*(\d+)[^\d]*(\d+)?\s*(?:days?|weeks?)'

# THC Content
r'thc[^\d]*(\d+(?:\.\d+)?)%?[^\d]*(\d+(?:\.\d+)?)?%?'
```

## 🚀 RESUME STRATEGY

### Wait Period Approach
- **Initial Wait**: 48-72 hours before retry
- **Retry Schedule**: Every 2-3 days
- **Success Indicators**: Content length > 1000 characters

### Alternative Methods
1. **Residential Proxies**: Different BrightData zone
2. **Manual Collection**: Browser automation tools
3. **API Discovery**: Check for hidden REST endpoints
4. **Partnership**: Direct data sharing agreement

## 📊 EXPECTED RESULTS

### Estimated Catalog Size
- **Autoflower**: ~500-800 strains
- **Photoflower**: ~1,200-1,500 strains  
- **Total**: ~2,000 strains expected

### Target Breeders (from seed-banks.md)
- Ethos, Compound, Exotic Genetix
- In House, Bloom, Oni, Relentless
- Dying Breed, Archive, Mephisto

### Success Metrics
- **Target Success Rate**: >90%
- **Cost per Strain**: <$0.002 (BrightData)
- **Data Completeness**: 8+ fields per strain

## 🔄 MONITORING PLAN

### Daily Checks
```bash
python check_multiverse_status.py
```

### Resume Execution
```bash
python multiverse_scraper.py
```

### Progress Tracking
- Track successful product URLs collected
- Monitor strain data extraction success
- Document breeder coverage

## 💰 COST ANALYSIS

### BrightData Usage
- **Estimated Requests**: ~2,500 (50 pages + 2,000 products)
- **Cost**: ~$3.75 (2,500 × $0.0015)
- **Cost per Strain**: ~$0.002

### ROI Calculation
- **Investment**: <$4 total
- **Expected Strains**: ~2,000
- **Value**: Premium genetics database
- **Academic Impact**: Significant dataset expansion

## 🎯 NEXT STEPS

1. **Wait 48-72 hours** for anti-bot measures to reset
2. **Test connectivity** with check_multiverse_status.py
3. **Execute scraper** when site becomes accessible
4. **Document results** and update strategy

## 📁 FILES CREATED

- `multiverse_scraper.py`: Main scraping script
- `test_multiverse_product.py`: Product page analyzer  
- `check_multiverse_status.py`: Connectivity checker
- `MULTIVERSE_STRATEGY.md`: This strategy document

**Status**: READY TO EXECUTE - Waiting for anti-bot measures to reset