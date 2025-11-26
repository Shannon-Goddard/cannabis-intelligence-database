# Dutch Passion - Enhanced 4-Method Execution Plan

## 🎯 TARGET SITE ANALYSIS

**URL**: https://dutch-passion.us/  
**Catalog URLs**:
- https://dutch-passion.us/feminized-seeds
- https://dutch-passion.us/autoflower-seeds  
- https://dutch-passion.us/regular-seeds

**Sample Products**:
- https://dutch-passion.us/cannabis-seeds/strawberry-cough
- https://dutch-passion.us/cannabis-seeds/auto-red-tropicana-cookies
- https://dutch-passion.us/cannabis-seeds/ice-cream-haze

**Unique Position**: Dutch Passion is BOTH seed bank AND breeder (original seed company since 1987)

### Key Characteristics
- **Legacy Genetics**: Original cannabis seed company (1987)
- **Professional Quality**: Comprehensive specifications with descriptive values
- **Detailed Terpenes**: Specific terpene names (B-Caryophyllene, Limonene, etc.)
- **Clean Structure**: Simple HTML table with alternating row colors
- **Comprehensive Data**: Multi-descriptor flavors and effects

## 🔧 DUTCH PASSION-SPECIFIC 4-METHOD IMPLEMENTATION

### Method 1: Structured Data Extraction (PRIMARY)
**Target**: Extract from Dutch Passion's specifications table

```python
def method1_structured_extraction(soup, url):
    """Dutch Passion's clean table structure"""
    data = {}
    
    # Dutch Passion's specifications table
    table = soup.find('table')
    if table:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                label_cell = cells[0]
                value_cell = cells[1]
                
                # Extract label from <strong> tag
                strong_tag = label_cell.find('strong')
                if strong_tag:
                    label = strong_tag.get_text().strip().rstrip(':')
                    value = value_cell.get_text().strip()
                    
                    field_map = {
                        'Flowering time': 'flowering_time',      # "9-11 weeks"
                        'Plant height': 'plant_height',         # "Very tall"
                        'Yield': 'yield',                       # "XXL"
                        'THC level': 'thc_level',              # "Extremely high (>20%)"
                        'Terpenes': 'terpenes',                # "B-Caryophyllene, Limonene"
                        'Taste': 'taste',                      # "Herbal, piney, peppery"
                        'Effects': 'effects'                   # "Head high"
                    }
                    
                    if label in field_map and value:
                        data[field_map[label]] = value
    
    return data
```

### Method 2: Description Mining (SECONDARY)
**Target**: Extract from product descriptions

```python
def method2_description_mining(soup, url):
    """Mine Dutch Passion's rich content"""
    data = {}
    
    # Extract main product description
    description_selectors = [
        'div.product-description',
        'div.description-content',
        'div.product-info'
    ]
    
    for selector in description_selectors:
        desc_elem = soup.select_one(selector)
        if desc_elem:
            data['about_info'] = desc_elem.get_text().strip()
            break
    
    return data
```

### Method 3: Advanced Patterns (TERTIARY)
**Target**: Strain naming, seed type detection

```python
def method3_advanced_patterns(soup, url):
    """Dutch Passion-specific patterns"""
    data = {}
    
    # Extract strain name from H1 or title
    h1_tag = soup.find('h1')
    if h1_tag:
        strain_name = h1_tag.get_text().strip()
        strain_name = re.sub(r'\s*-\s*Dutch Passion.*$', '', strain_name, re.IGNORECASE)
        data['strain_name'] = strain_name.strip()
    
    # Dutch Passion is always both seed bank and breeder
    data['breeder_name'] = 'Dutch Passion'
    
    # Detect seed types from URL
    if '/autoflower-seeds' in url:
        data['growth_type'] = 'Autoflower'
        data['seed_type'] = 'Feminized'
    elif '/regular-seeds' in url:
        data['growth_type'] = 'Photoperiod'
        data['seed_type'] = 'Regular'
    elif '/feminized-seeds' in url:
        data['growth_type'] = 'Photoperiod'
        data['seed_type'] = 'Feminized'
    
    return data
```

### Method 4: Universal Fallback (FINAL)
**Target**: Meta tags, URL parsing

```python
def method4_fallback_extraction(soup, url):
    """Universal fallback extraction"""
    data = {}
    
    # Extract strain name from URL if not found
    if 'strain_name' not in data:
        path_parts = url.split('/')
        for part in reversed(path_parts):
            if part and 'cannabis-seeds' not in part and len(part) > 3:
                strain_name = part.replace('-', ' ').title()
                data['strain_name'] = strain_name.strip()
                break
    
    # Meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and not data.get('about_info'):
        data['about_info'] = meta_desc.get('content', '')
    
    return data
```

## 📊 QUALITY SCORING WEIGHTS

```python
DUTCH_PASSION_FIELD_WEIGHTS = {
    'strain_name': 10,
    'breeder_name': 10,
    'flowering_time': 9,
    'thc_level': 9,
    'plant_height': 8,
    'yield': 8,
    'terpenes': 8,
    'taste': 7,
    'effects': 7,
    'seed_type': 6,
    'growth_type': 6,
    'about_info': 6
}
```

## 🎯 EXPECTED RESULTS

- **Strain Count**: 70-100 strains
- **Success Rate**: 95%+
- **Cost**: ~$0.15 (100 strains × $0.0015)
- **Quality**: 70% Premium, 25% High, 5% Medium

## 🚀 EXECUTION COMMAND

Execute Dutch Passion scraper using the 4-method plan. Target: 70-100 legacy genetics strains with 95%+ success rate. Hardcode seed_bank and breeder_name as 'Dutch Passion' for all strains. Three catalogs: feminized-seeds, autoflower-seeds, regular-seeds.

---

*Ready for implementation with proven 4-method approach optimized for Dutch Passion's legacy genetics and professional specifications.*