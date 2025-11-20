# Seeds Here Now - Cannabis Strain Database

## 🎯 Overview
Successfully scraped **211 cannabis strains** from Seeds Here Now seed bank with comprehensive cultivation data.

## 📊 Results
- **Success Rate**: 99.1% (211/213 strains)
- **Data Points**: THC/CBD levels, genetics, flowering time, effects, flavors, difficulty
- **Breeders**: Barney's Farm, Exotic Genetix, Cali Connection, Irie Genetics, Aficinado Seeds
- **Storage**: AWS DynamoDB `cannabis-strains` table

## 🔧 Method
1. **Catalog Scraping**: Extracted strain names from product category pages
   - `https://seedsherenow.com/product-category/feminized-cannabis-seeds/`
   - `https://seedsherenow.com/product-category/regular-cannabis-seeds/`
   - `https://seedsherenow.com/product-category/autoflower-cannabis-seeds/`

2. **Detail Scraping**: For each strain, scraped individual product pages
   - URL format: `https://seedsherenow.com/shop/{strain-name}/`
   - Extracted data from product specification tables

## 🛠️ Tools
- **BrightData Web Unlocker API**: Bypassed bot protection
- **AWS Secrets Manager**: Secure credential storage
- **AWS DynamoDB**: Cannabis strain database storage

## 📁 Files
- `strain_names.txt` - List of 213 strain names collected
- `shn_scraper.py` - Python scraper using BrightData API

## 📋 Data Fields Collected
- **Strain Name** & **Breeder**
- **Genetics** (parent strains)
- **THC/CBD** ranges
- **Seed Type** (Feminized/Regular/Autoflower)
- **Flowering Time**
- **Yield Level**
- **Difficulty Rating**
- **Aroma/Flavor Profile**
- **Effects Description**

## 💰 Cost
- **BrightData**: Part of $5 total project cost (3,000 total requests across all sources)
- **AWS**: <$0.01 (DynamoDB storage)
- **Efficiency**: 211 strains collected = **$0.002 per strain**

## 🚀 Usage
```bash
# Collect strain names only
python shn_scraper.py names-only

# Full scrape (reads from strain_names.txt)
python shn_scraper.py
```

## 🔐 Security
- No hardcoded API keys
- BrightData credentials stored in AWS Secrets Manager
- IAM permissions for secure access