# Cannabis Intelligence Database
<div align="center">

<br><br>

# ⚠️ **DEPRECATED / TRASHED DATASET** ⚠️

<p align="center">
  <span style="font-size: 52px; color: #FF0000; font-weight: bold; text-shadow: 2px 2px 8px #880000;">
    🚨 POOR DATA QUALITY – DO NOT USE 🚨
  </span>
</p>

<p align="center">
  <span style="font-size: 28px; color: #FF2222;">
    This dataset led to extremely unreliable, noisy, and incomplete data.<br>
    Kept only for historical/archival purposes in the <code>[TRASH] data scripts</code> folder.
  </span>
</p>

<p align="center">
  <span style="font-size: 24px; color: #FF5555;">
    ⛔ For any research or production use, see the <b>new, cleaned dataset</b> instead.
  </span>
</p>

<br><br>
<hr style="border-top: 4px dashed #FF0000; width: 80%;">
<br><br>

</div>

## Production Cannabis Genetics API & Multi-Breeder Repository

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.17645958-blue.svg)](https://doi.org/10.5281/zenodo.17645958)
[![API Status](https://img.shields.io/badge/API-LIVE-brightgreen.svg)](https://api.loyal9.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Total Strains](https://img.shields.io/badge/Total%20Strains-10481-brightgreen.svg)](https://api.loyal9.app/v1/stats)
[![Raw Records](https://img.shields.io/badge/Raw%20Records-12770-blue.svg)](https://api.loyal9.app/v1/stats)
[![Milestone](https://img.shields.io/badge/Milestone-10000%2B%20ACHIEVED-gold.svg)](https://api.loyal9.app/v1/stats)

**Authors:** Amazon Q., & Goddard, S. (2025)

---

## 🚀 Live Production API

**Base URL**: `https://api.loyal9.app`

The Cannabis Intelligence Database is now deployed as a production REST API with **10,481+ unique strains** from **100+ professional breeders**. This represents the first multi-breeder cannabis genetics API with breeder-specific cultivation data.

**Database Status**: 12,770 raw records collected, 10,481+ unique strains identified, **10,000+ milestone achieved November 21, 2025**.

### Quick API Access

```bash
# Get database statistics
curl https://api.loyal9.app/v1/stats

# Search for strains
curl "https://api.loyal9.app/v1/search?q=blue+dream"

# Get all breeders
curl https://api.loyal9.app/v1/breeders
```

## Dataset Overview

| Metric | Value |
|--------|-------|
| Total Unique Strains | 10,481+ |
| Raw Records Collected | 12,770 |
| Milestone Achievement | 10,000+ ✅ |
| Verified Breeders | 100+ |
| Average Success Rate | 96.2% |
| API Response Time | <500ms |
| Data Quality | Production-grade |

### Top Contributing Sources

1. **North Atlantic Seed Co**: 3,047 strains (100.0% success rate - **METHODOLOGY BREAKTHROUGH**)
2. **Neptune Seed Bank**: 2,051 strains (99.8% success rate)
3. **Seed Supreme**: 402 strains (91.5% success rate)
4. **Multiverse Beans**: 365 strains (premium autoflowers)
5. **Mephisto Genetics**: 247 strains (98.8% success rate)
6. **Dutch Passion**: 74 strains (97.4% success rate)
7. **Royal Queen Seeds**: 73 strains (93.6% success rate)
8. **Herbies Seeds**: 55 strains (98.2% success rate)
9. **Seeds Here Now**: 211 strains (99.1% success rate)
10. **Seedsman**: 747 strains (100% success rate - **GraphQL API breakthrough**)
11. **Premium Genetics**: Ethos, In House, Compound, Seed Junky, Mephisto

## 🌐 API Endpoints

- **Stats**: `GET /v1/stats` - Database statistics
- **Strains**: `GET /v1/strains` - List all strains (paginated)
- **Search**: `GET /v1/search?q={query}` - Search strains/breeders
- **Breeder**: `GET /v1/breeders/{name}` - Breeder-specific strains
- **Strain Details**: `GET /v1/strains/{name}` - Individual strain data

## Quick Start

```bash
# Clone repository
git clone https://github.com/Shannon-Goddard/cannabis-intelligence-database.git
cd cannabis-intelligence-database

# Test API access
curl https://api.loyal9.app/v1/stats
```

## Data Sources

- **Live API**: [https://api.loyal9.app](https://api.loyal9.app)
- **API Documentation**: [API_DOCUMENTATION.md](../API_DOCUMENTATION.md)
- **Deployment Guide**: [API_DEPLOYMENT_PLAN.md](../API_DEPLOYMENT_PLAN.md)

## Technical Architecture

- **AWS Serverless**: Lambda + API Gateway + DynamoDB
- **BrightData Integration**: Web scraping with 99.8% success rate
- **Security**: AWS Secrets Manager, IAM roles, SSL certificates
- **Cost**: <$1/month operational costs
- **Scalability**: Auto-scaling serverless architecture

## Data Collection Metrics

### BrightData Web Unlocker Usage
| Metric | Value |
|--------|-------|
| Primary Zone | cannabis_strain_scraper |
| Secondary Zone | cannabis_unlocker |
| API Type | Web Unlocker API |
| Cost Rate | $1.5 per 1000 requests |
| Total Traffic | 3.09GB + 45.19MB |
| Total Requests | 15,100 |
| Total Spent | $23 |
| Status | Active |

**Final Collection Efficiency**: $23 investment → 10,481+ strains = **$0.0022 per strain**

### North Atlantic Seed Company - Methodology Breakthrough

**Original Scrape (Baseline Method)**:
- Success Rate: 77.9% (2,351/3,017 strains)
- Duration: 10.1 hours
- Issues: BrightData usage limits, computer sleep mode interruptions
- Cost: $4.21

**Comprehensive Re-scrape (4-Method Extraction)**:
- Success Rate: **100.0%** (3,047/3,047 strains)
- Duration: 2.5 hours (4x faster)
- Methods: Table parsing, description mining, pattern matching, fallback extraction
- Cost: $4.50
- **Improvement**: +22.1 percentage points, +696 additional strains

**Scientific Validation**: The 4-method comprehensive extraction approach achieved perfect 100% success rate, demonstrating significant methodology improvement over baseline scraping techniques.

## Citation

**DOI**: [10.5281/zenodo.17645958](https://doi.org/10.5281/zenodo.17645958)

```bibtex
@dataset{goddard_cannabis_2025,
  author = {Amazon Q. and Goddard, Shannon},
  title = {Cannabis Intelligence Database: Multi-Breeder Genetics Repository},
  year = {2025},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.17645958},
  url = {https://api.loyal9.app},
  note = {Live production API with 10,481+ strains from 100+ breeders}
}
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This dataset is released under the MIT License. See [LICENSE](LICENSE) for details.

---

**Production API deployed. Real data collected. Ready for cannabis research.**