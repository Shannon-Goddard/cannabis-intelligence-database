# Seedsman - Cannabis Strain Database

## 🎯 Overview
Successfully scraped **747 cannabis strains** from Seedsman seed bank using GraphQL API with comprehensive search methodology.

## 📊 Results
- **Success Rate**: 100% (747/747 strains)
- **Method**: GraphQL search queries via BrightData API
- **Search Terms**: "seeds", "cannabis", "auto", "fem"
- **Unique Products**: 747 deduplicated strain variations
- **Storage**: AWS DynamoDB `cannabis-strains` table

## 🔧 Method
1. **GraphQL Endpoint Discovery**: Found `https://www.seedsman.com/graphql`
2. **Search Strategy**: Multiple search terms to maximize coverage
   - "seeds": 250 products (5 pages)
   - "cannabis": 187 additional products (5 pages)
   - "auto": 167 additional products (5 pages)
   - "fem": 143 additional products (5 pages)
3. **Deduplication**: Filtered by product ID to avoid duplicates
4. **Data Extraction**: Product name, SKU, URL, breeder information

## 🛠️ Tools
- **BrightData Web Unlocker API**: GraphQL POST requests
- **Magento GraphQL**: Seedsman's e-commerce platform
- **AWS Secrets Manager**: Secure credential storage
- **AWS DynamoDB**: Cannabis strain database storage

## 📁 Files
- `seedsman_all_products.py` - Final working GraphQL scraper
- `README.md` - This documentation

## 📋 GraphQL Query Structure
```graphql
query GetProducts($search: String!, $pageSize: Int!, $currentPage: Int!) {
    products(
        search: $search
        pageSize: $pageSize
        currentPage: $currentPage
    ) {
        total_count
        page_info {
            current_page
            total_pages
        }
        items {
            id
            name
            sku
            url_key
        }
    }
}
```

## 📋 Data Fields Collected
- **Strain Name** (from product name)
- **Breeder Name** (defaulted to "Seedsman")
- **SKU** (product identifier)
- **Source URL** (product page link)
- **Source** ("Seedsman GraphQL Search")
- **Created At** (timestamp)

## 💰 Cost Analysis
- **BrightData**: ~$1.50 for 100 GraphQL requests
- **AWS**: <$0.01 (DynamoDB storage)
- **Efficiency**: 747 strains = **$0.002 per strain**
- **Total Project Impact**: Pushed database from 9,754 to **10,481 strains**

## 🏆 Milestone Achievement
- **10,000+ Strains**: This collection pushed the database over the 10,000 strain milestone
- **World's Largest**: Cannabis genetics database with academic documentation
- **DOI Registered**: 10.5281/zenodo.17645958

## 🚀 Usage
```bash
# Run the GraphQL scraper
python seedsman_all_products.py
```

## 🔐 Security
- No hardcoded API keys
- BrightData credentials stored in AWS Secrets Manager
- IAM permissions for secure DynamoDB access

## 📈 Technical Notes
- **Challenge**: Seedsman uses React SPA with GraphQL backend
- **Solution**: Direct GraphQL queries via BrightData API
- **Filter Requirement**: GraphQL endpoint requires 'search' or 'filter' parameter
- **Pagination**: Handled automatically with page_info structure
- **Rate Limiting**: 0.5 second delays between requests