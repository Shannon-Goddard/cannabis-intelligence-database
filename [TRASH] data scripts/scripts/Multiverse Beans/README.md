# Multiverse Beans Cannabis Strain Database

## 🎯 TARGET SITE
**URL**: https://multiversebeans.com  
**Focus**: Premium US genetics, exclusives, collaborations  
**Estimated Strains**: ~2,000  

## 🚫 CURRENT STATUS: ANTI-BOT PROTECTION ACTIVE

### Issue Detected
- **Date**: January 27, 2025
- **Problem**: BrightData Web Unlocker returning empty content
- **Response**: 200 status, 0 characters
- **Cause**: Advanced anti-bot measures

### Site Structure Confirmed
- **Autoflower**: https://multiversebeans.com/flowering-type/autoflower/
- **Photoperiod**: https://multiversebeans.com/flowering-type/photoperiod/
- **Product Example**: https://multiversebeans.com/product/blue-dream-full-term-atlas-seeds-photoperiod-cannabis-seeds-female/

## 🛠️ SCRAPER READY

### Files Created
- `multiverse_scraper.py`: Complete two-phase scraper
- `test_multiverse_product.py`: Product page analyzer
- `check_multiverse_status.py`: Connectivity tester
- `MULTIVERSE_STRATEGY.md`: Detailed execution plan

### Technical Approach
1. **Phase 1**: Extract product URLs from category pages
2. **Phase 2**: Scrape individual product data
3. **Storage**: Direct to DynamoDB cannabis-strains table

## 🎯 TARGET BREEDERS

Based on seed-banks.md, Multiverse Beans specializes in:
- **Ethos, Compound, Exotic Genetix**
- **In House, Bloom, Oni, Relentless**  
- **Dying Breed, Archive, Mephisto**
- **Exclusives & collaborations**

## 💰 ECONOMICS

### Estimated Costs
- **BrightData**: ~$3.75 (2,500 requests)
- **AWS**: <$0.01/month (DynamoDB)
- **Cost per Strain**: ~$0.002

### Expected Value
- **Premium Genetics**: $200-500+ strains accessible
- **Exclusive Drops**: Collaborations not found elsewhere
- **Academic Dataset**: Significant research expansion

## 🔄 EXECUTION PLAN

### Immediate
1. **Wait 48-72 hours** for anti-bot reset
2. **Test daily** with check_multiverse_status.py
3. **Execute scraper** when accessible

### Monitoring
```bash
# Daily connectivity check
python check_multiverse_status.py

# Execute when ready
python multiverse_scraper.py
```

### Success Indicators
- Content length > 1000 characters
- Product URLs successfully extracted
- Strain data parsing functional

## 📊 INTEGRATION

### Database Schema
Uses existing cannabis-strains DynamoDB table with fields:
- strain_name, breeder_name
- genetics_sativa, genetics_indica  
- flowering_days_indoor
- thc_min, thc_max
- source_url, source_site

### Multi-Source Intelligence
Multiverse Beans will be **4th major source**:
1. Neptune Seed Bank: 2,051 strains ✅
2. Seeds Here Now: 211 strains ✅  
3. North Atlantic: 165 strains (paused) ⏸️
4. Multiverse Beans: ~2,000 strains (blocked) 🚫

**Total Target**: 4,427+ strains from premium sources

## 🚀 READY TO EXECUTE

All technical infrastructure complete. Waiting for anti-bot measures to reset before proceeding with data collection.