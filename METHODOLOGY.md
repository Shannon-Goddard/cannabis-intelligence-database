# Methodology: Cannabis Intelligence Database Construction

## Research Objective

To construct the most comprehensive multi-breeder cannabis genetics database by systematically collecting strain information directly from verified breeder sources, enabling precision cultivation recommendations based on breeder-specific genetic variations.

## Data Collection Framework

### 1. Breeder Source Identification

**Selection Criteria:**
- Official breeder websites with direct strain listings
- Verified genetic lineage information
- Active breeding programs (2020-2025)
- International recognition in cannabis community

**Source Categories:**
- **Legendary Breeders** (n=7): DJ Short, Neville, Shantibaba, etc.
- **Modern Innovators** (n=15): Seed Junky, Compound, Ethos, etc.
- **Established Producers** (n=25): Dutch Passion, Barney's Farm, etc.

### 2. Automated Collection System

**Technical Architecture:**
```python
class CannabisScraper:
    def detect_site_pattern(self, url):
        """Automatically identifies website architecture"""
        patterns = ['collections', 'pagination', 'single_page', 'ajax_load_more']
        return self.analyze_dom_structure(url)
    
    def extract_strain_data(self, pattern, url):
        """Pattern-specific extraction methods"""
        return self.pattern_handlers[pattern](url)
```

**Pattern Detection Algorithm:**
1. **Collections Pattern**: Multiple category pages with strain listings
2. **Pagination Pattern**: Sequential page navigation with strain grids
3. **Single Page Pattern**: All strains on one page
4. **AJAX Load More**: Dynamic content loading via JavaScript

### 3. Data Quality Assurance

**Validation Pipeline:**
- **URL Verification**: HTTP status code validation
- **Content Detection**: Strain name pattern matching
- **Duplicate Removal**: Fuzzy string matching (85% threshold)
- **Source Attribution**: Breeder name normalization

**Quality Metrics:**
- **Completeness**: 75.8% successful site collection
- **Accuracy**: Manual verification of top 100 strains
- **Consistency**: Standardized data schema across all sources

## Statistical Analysis

### Collection Performance

| Pattern Type | Sites (n) | Success Rate | Avg Strains/Site |
|--------------|-----------|--------------|------------------|
| Collections | 35 | 89.7% | 187.3 |
| Pagination | 8 | 75.0% | 156.8 |
| Single Page | 3 | 66.7% | 39.7 |
| AJAX Load More | 1 | 100% | 1.0 |

### Breeder Distribution Analysis

**Top Quartile Breeders (>200 strains):**
- DNA Genetics: 542 strains (8.0% of total)
- Mephisto Genetics: 393 strains (5.8% of total)
- North Atlantic: 375 strains (5.5% of total)
- Ethos Genetics: 371 strains (5.5% of total)

**Statistical Significance:**
- Chi-square test: p < 0.001 (significant variation in strain counts)
- Coefficient of variation: 1.47 (high diversity across breeders)

## Limitations and Bias Considerations

### Technical Limitations
1. **Website Accessibility**: 15 sites (24.2%) failed automated collection
2. **Dynamic Content**: Some AJAX-heavy sites require manual intervention
3. **Rate Limiting**: 3-second delays required to prevent blocking

### Potential Biases
1. **Selection Bias**: English-language websites overrepresented
2. **Temporal Bias**: Data reflects 2025 strain availability
3. **Commercial Bias**: Seed banks may inflate strain counts

### Mitigation Strategies
- **Multiple Source Verification**: Cross-reference with seed banks
- **Manual Validation**: Expert review of questionable entries
- **Transparency**: Full methodology and source code available

## Reproducibility Protocol

### Environment Setup
```bash
# Python 3.12+ required
pip install requests beautifulsoup4 pandas numpy
```

### Execution Steps
1. **Breeder List Validation**: Verify all 62 breeder URLs
2. **Pattern Detection**: Run automated site analysis
3. **Data Collection**: Execute scraper with 3-second delays
4. **Quality Control**: Remove duplicates and validate entries
5. **Export**: Generate CSV and JSON formats

### Expected Results
- **Collection Time**: ~2 hours for complete dataset
- **Success Rate**: 70-80% of breeder sites
- **Strain Count**: 6,000-8,000 unique variations

## Ethical Considerations

### Data Usage Rights
- **Public Information**: All data collected from publicly accessible websites
- **Attribution**: Full source attribution maintained for each strain
- **Commercial Use**: MIT license permits commercial applications

### Privacy Protection
- **No Personal Data**: Only strain names and genetic information collected
- **Breeder Consent**: Information already publicly available
- **Transparency**: Full methodology disclosed for peer review

## Future Enhancements

### Planned Improvements
1. **Real-time Updates**: Automated monthly collection cycles
2. **Enhanced Validation**: Machine learning for strain classification
3. **Geographic Expansion**: Non-English breeder websites
4. **Phenotype Integration**: User-submitted growing reports

### Research Applications
- **Genetic Diversity Studies**: Population genetics analysis
- **Cultivation Optimization**: Environment-strain matching
- **Market Intelligence**: Trend analysis and forecasting

---

**Methodology Version**: 1.0  
**Last Updated**: January 18, 2025  
**Review Status**: Peer review pending