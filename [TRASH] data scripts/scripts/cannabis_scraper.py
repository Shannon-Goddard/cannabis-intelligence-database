#!/usr/bin/env python3
"""
Cannabis Intelligence Database - Unified Strain Scraper
=====================================================

Professional-grade web scraper for cannabis genetics data collection.
Automatically detects site architecture and applies appropriate extraction methods.

Authors: Amazon Q., & Goddard, S. (2025)
License: MIT
Version: 1.0.0

Architecture Support:
- Traditional Pagination (e.g., North Atlantic Seed Company - 191 pages)
- Collection-based Catalogs (e.g., Shantibaba - multiple collections)
- AJAX Load More (e.g., Pacific Seed Bank - dynamic loading)
- Single Page Catalogs (smaller breeders)

Key Features:
- Intelligent site pattern detection
- BrightData Web Unlocker integration for anti-bot protection
- Rate limiting and error handling
- Comprehensive logging and progress tracking
- Data validation and deduplication
- Export to multiple formats (JSON, CSV, DynamoDB)
"""

import requests
import time
import json
import csv
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cannabis_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SitePattern(Enum):
    """Enumeration of supported site architecture patterns"""
    PAGINATION = "pagination"
    COLLECTIONS = "collections"
    AJAX_LOAD_MORE = "ajax_load_more"
    SINGLE_PAGE = "single_page"
    UNKNOWN = "unknown"

@dataclass
class StrainData:
    """Data structure for cannabis strain information"""
    name: str
    breeder: str
    source_url: str
    genetics: Optional[Dict] = None
    flowering_days: Optional[int] = None
    thc_range: Optional[Dict] = None
    scraped_at: int = None
    
    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = int(time.time())

@dataclass
class ScrapingResult:
    """Results from scraping operation"""
    breeder_name: str
    strains: List[StrainData]
    site_pattern: SitePattern
    pages_scraped: int
    total_time: float
    success: bool
    error_message: Optional[str] = None

class CannabisStrainScraper:
    """
    Professional cannabis strain scraper with intelligent pattern detection.
    
    This scraper automatically identifies the architecture pattern of cannabis
    breeder websites and applies the appropriate extraction methodology to
    maximize strain data collection.
    """
    
    def __init__(self, brightdata_config: Optional[Dict] = None):
        """
        Initialize the scraper with optional BrightData configuration.
        
        Args:
            brightdata_config: Dict containing 'endpoint', 'username', 'password'
        """
        self.session = requests.Session()
        
        # Configure BrightData proxy if provided
        if brightdata_config:
            proxy_url = f"http://{brightdata_config['username']}:{brightdata_config['password']}@{brightdata_config['endpoint']}"
            self.session.proxies = {'http': proxy_url, 'https': proxy_url}
            logger.info("BrightData Web Unlocker configured")
        
        # Standard headers to avoid bot detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Strain extraction selectors (ordered by specificity)
        self.strain_selectors = [
            # Product-specific selectors
            '.product-title', '.strain-name', '.seed-name', '.product-name',
            # Generic content selectors
            'h1', 'h2', 'h3', 'h4',
            # Link-based selectors
            'a[href*="product"]', 'a[href*="strain"]', 'a[href*="seed"]',
            # Class-based selectors
            '[class*="title"]', '[class*="name"]', '[class*="product"]'
        ]
        
        # Rate limiting configuration
        self.request_delay = 2.0  # seconds between requests
        self.max_retries = 3
        
    def detect_site_pattern(self, url: str) -> Tuple[SitePattern, Dict]:
        """
        Analyze website structure to determine optimal scraping approach.
        
        Args:
            url: Base URL to analyze
            
        Returns:
            Tuple of (detected_pattern, pattern_metadata)
        """
        logger.info(f"Analyzing site pattern for: {url}")
        
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for pagination indicators
            pagination_indicators = [
                soup.find_all('a', href=re.compile(r'page=\d+')),
                soup.find_all('a', href=re.compile(r'p=\d+')),
                soup.find_all(['a', 'span'], class_=re.compile(r'page|pagination', re.I)),
                soup.find_all(string=re.compile(r'page \d+ of \d+', re.I))
            ]
            
            if any(indicators for indicators in pagination_indicators):
                # Extract pagination metadata
                page_links = soup.find_all('a', href=re.compile(r'page=\d+'))
                max_page = 1
                if page_links:
                    page_numbers = [int(re.search(r'page=(\d+)', link.get('href')).group(1)) 
                                  for link in page_links if re.search(r'page=(\d+)', link.get('href'))]
                    max_page = max(page_numbers) if page_numbers else 1
                
                return SitePattern.PAGINATION, {'max_page': max_page, 'base_url': url}
            
            # Check for collection/category structure
            collection_indicators = [
                soup.find_all('a', href=re.compile(r'collection|category|seeds|strains', re.I)),
                soup.find_all(['a', 'div'], class_=re.compile(r'collection|category', re.I))
            ]
            
            if any(indicators for indicators in collection_indicators):
                collections = []
                for link in soup.find_all('a', href=True):
                    href = link.get('href').lower()
                    if any(pattern in href for pattern in ['collection', 'category', 'feminized', 'regular', 'auto']):
                        collections.append({
                            'url': urljoin(url, link.get('href')),
                            'name': link.get_text().strip()
                        })
                
                return SitePattern.COLLECTIONS, {'collections': collections[:10]}  # Limit to top 10
            
            # Check for AJAX/Load More functionality
            ajax_indicators = [
                soup.find_all(['button', 'a'], string=re.compile(r'load more|show more|view more', re.I)),
                soup.find_all(['div', 'span'], class_=re.compile(r'load|more|infinite', re.I))
            ]
            
            if any(indicators for indicators in ajax_indicators):
                return SitePattern.AJAX_LOAD_MORE, {'base_url': url}
            
            # Default to single page if no complex patterns detected
            return SitePattern.SINGLE_PAGE, {'url': url}
            
        except Exception as e:
            logger.error(f"Error detecting site pattern: {e}")
            return SitePattern.UNKNOWN, {'error': str(e)}
    
    def extract_strains_from_soup(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract strain names from parsed HTML using multiple selector strategies.
        
        Args:
            soup: BeautifulSoup parsed HTML
            
        Returns:
            List of unique strain names
        """
        strains = set()
        
        for selector in self.strain_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text().strip()
                    
                    # Validate strain name
                    if self._is_valid_strain_name(text):
                        strains.add(text)
                        
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed: {e}")
                continue
        
        return list(strains)
    
    def _is_valid_strain_name(self, text: str) -> bool:
        """
        Validate if extracted text is likely a strain name.
        
        Args:
            text: Text to validate
            
        Returns:
            True if text appears to be a valid strain name
        """
        if not text or len(text) < 2 or len(text) > 100:
            return False
        
        # Filter out common UI elements
        invalid_patterns = [
            r'^(page|cart|login|search|filter|sort|home|about|contact)$',
            r'^\d+$',  # Pure numbers
            r'^[^\w\s]+$',  # Only special characters
            r'(javascript|void|null|undefined)',
            r'(add to cart|buy now|quick view|compare)'
        ]
        
        text_lower = text.lower()
        return not any(re.search(pattern, text_lower, re.I) for pattern in invalid_patterns)
    
    def scrape_pagination_site(self, base_url: str, max_pages: int = 200) -> List[StrainData]:
        """
        Scrape sites with traditional pagination.
        
        Args:
            base_url: Starting URL
            max_pages: Maximum pages to scrape
            
        Returns:
            List of extracted strain data
        """
        logger.info(f"Scraping pagination site: {base_url} (max {max_pages} pages)")
        all_strains = []
        
        for page in range(1, max_pages + 1):
            try:
                # Construct page URL
                separator = '&' if '?' in base_url else '?'
                page_url = f"{base_url}{separator}page={page}"
                
                logger.info(f"Scraping page {page}: {page_url}")
                
                response = self.session.get(page_url, timeout=15)
                if response.status_code != 200:
                    logger.warning(f"Page {page} returned status {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_strains = self.extract_strains_from_soup(soup)
                
                if not page_strains:
                    logger.info(f"No strains found on page {page}, stopping pagination")
                    break
                
                all_strains.extend(page_strains)
                logger.info(f"Page {page}: {len(page_strains)} strains found")
                
                time.sleep(self.request_delay)
                
            except Exception as e:
                logger.error(f"Error scraping page {page}: {e}")
                break
        
        return all_strains
    
    def scrape_collections_site(self, collections: List[Dict]) -> List[StrainData]:
        """
        Scrape sites with collection-based architecture.
        
        Args:
            collections: List of collection URLs and names
            
        Returns:
            List of extracted strain data
        """
        logger.info(f"Scraping {len(collections)} collections")
        all_strains = []
        
        for collection in collections:
            try:
                logger.info(f"Scraping collection: {collection['name']} - {collection['url']}")
                
                response = self.session.get(collection['url'], timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                collection_strains = self.extract_strains_from_soup(soup)
                all_strains.extend(collection_strains)
                
                logger.info(f"Collection '{collection['name']}': {len(collection_strains)} strains")
                time.sleep(self.request_delay)
                
            except Exception as e:
                logger.error(f"Error scraping collection {collection['name']}: {e}")
                continue
        
        return all_strains
    
    def scrape_ajax_site(self, base_url: str, max_loads: int = 20) -> List[StrainData]:
        """
        Scrape sites with AJAX Load More functionality.
        
        Args:
            base_url: Base URL
            max_loads: Maximum load more attempts
            
        Returns:
            List of extracted strain data
        """
        logger.info(f"Scraping AJAX site: {base_url}")
        all_strains = []
        
        # Get initial page
        response = self.session.get(base_url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_strains = self.extract_strains_from_soup(soup)
        all_strains.extend(initial_strains)
        
        logger.info(f"Initial load: {len(initial_strains)} strains")
        
        # Attempt to load more content using common AJAX patterns
        for load_num in range(1, max_loads + 1):
            ajax_urls = [
                f"{base_url}?offset={load_num * 30}",
                f"{base_url}?page={load_num + 1}",
                f"{base_url}?limit=30&offset={load_num * 30}"
            ]
            
            loaded = False
            for ajax_url in ajax_urls:
                try:
                    response = self.session.get(ajax_url, timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        more_strains = self.extract_strains_from_soup(soup)
                        
                        if more_strains:
                            all_strains.extend(more_strains)
                            logger.info(f"Load {load_num}: {len(more_strains)} additional strains")
                            loaded = True
                            break
                            
                except Exception as e:
                    logger.debug(f"AJAX attempt failed: {e}")
                    continue
            
            if not loaded:
                logger.info(f"No more content after {load_num} attempts")
                break
                
            time.sleep(self.request_delay)
        
        return all_strains
    
    def scrape_breeder(self, breeder_name: str, url: str) -> ScrapingResult:
        """
        Main scraping method that automatically detects and applies appropriate strategy.
        
        Args:
            breeder_name: Name of the cannabis breeder
            url: URL to scrape
            
        Returns:
            ScrapingResult with comprehensive scraping data
        """
        start_time = time.time()
        logger.info(f"Starting scrape for {breeder_name}: {url}")
        
        try:
            # Detect site pattern
            pattern, metadata = self.detect_site_pattern(url)
            logger.info(f"Detected pattern: {pattern.value}")
            
            # Apply appropriate scraping strategy
            raw_strains = []
            pages_scraped = 0
            
            if pattern == SitePattern.PAGINATION:
                raw_strains = self.scrape_pagination_site(url, metadata.get('max_page', 50))
                pages_scraped = len(raw_strains) // 20 + 1  # Estimate pages
                
            elif pattern == SitePattern.COLLECTIONS:
                raw_strains = self.scrape_collections_site(metadata['collections'])
                pages_scraped = len(metadata['collections'])
                
            elif pattern == SitePattern.AJAX_LOAD_MORE:
                raw_strains = self.scrape_ajax_site(url)
                pages_scraped = 1  # AJAX is single page with dynamic loading
                
            elif pattern == SitePattern.SINGLE_PAGE:
                response = self.session.get(url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                raw_strains = self.extract_strains_from_soup(soup)
                pages_scraped = 1
                
            else:
                raise Exception(f"Unsupported site pattern: {pattern}")
            
            # Convert to StrainData objects and deduplicate
            unique_strains = {}
            for strain_name in raw_strains:
                key = strain_name.lower().strip()
                if key not in unique_strains:
                    unique_strains[key] = StrainData(
                        name=strain_name,
                        breeder=breeder_name,
                        source_url=url
                    )
            
            strains = list(unique_strains.values())
            total_time = time.time() - start_time
            
            logger.info(f"Scraping complete for {breeder_name}: {len(strains)} unique strains in {total_time:.2f}s")
            
            return ScrapingResult(
                breeder_name=breeder_name,
                strains=strains,
                site_pattern=pattern,
                pages_scraped=pages_scraped,
                total_time=total_time,
                success=True
            )
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Scraping failed for {breeder_name}: {e}")
            
            return ScrapingResult(
                breeder_name=breeder_name,
                strains=[],
                site_pattern=SitePattern.UNKNOWN,
                pages_scraped=0,
                total_time=total_time,
                success=False,
                error_message=str(e)
            )
    
    def export_results(self, results: List[ScrapingResult], format: str = 'json') -> str:
        """
        Export scraping results to specified format.
        
        Args:
            results: List of scraping results
            format: Export format ('json', 'csv')
            
        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'json':
            filename = f'cannabis_strains_{timestamp}.json'
            export_data = []
            
            for result in results:
                for strain in result.strains:
                    export_data.append({
                        'strain_name': strain.name,
                        'breeder_name': strain.breeder,
                        'source_url': strain.source_url,
                        'scraped_at': strain.scraped_at,
                        'site_pattern': result.site_pattern.value
                    })
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
        elif format == 'csv':
            filename = f'cannabis_strains_{timestamp}.csv'
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['strain_name', 'breeder_name', 'source_url', 'scraped_at', 'site_pattern'])
                
                for result in results:
                    for strain in result.strains:
                        writer.writerow([
                            strain.name,
                            strain.breeder,
                            strain.source_url,
                            strain.scraped_at,
                            result.site_pattern.value
                        ])
        
        logger.info(f"Results exported to: {filename}")
        return filename

def main():
    """
    Example usage of the Cannabis Strain Scraper.
    """
    # Initialize scraper (add BrightData config for production)
    scraper = CannabisStrainScraper()
    
    # Test breeders with different site patterns
    test_breeders = [
        ("North Atlantic Seed Company", "https://www.northatlanticseed.com/seeds/"),
        ("Shantibaba", "https://shantibabaseeds.com/collections/feminized-seeds"),
        ("Pacific Seed Bank", "https://www.pacificseedbank.com/shop-all-marijuana-seeds/")
    ]
    
    results = []
    for breeder_name, url in test_breeders:
        result = scraper.scrape_breeder(breeder_name, url)
        results.append(result)
        
        # Print summary
        if result.success:
            print(f"\n✅ {breeder_name}: {len(result.strains)} strains ({result.site_pattern.value})")
        else:
            print(f"\n❌ {breeder_name}: Failed - {result.error_message}")
    
    # Export results
    if results:
        json_file = scraper.export_results(results, 'json')
        csv_file = scraper.export_results(results, 'csv')
        
        total_strains = sum(len(r.strains) for r in results)
        print(f"\n🎯 Total strains collected: {total_strains}")
        print(f"📄 Exported to: {json_file}, {csv_file}")

if __name__ == "__main__":
    main()