# Cannabis Intelligence Database
## Production Cannabis Genetics API & Multi-Breeder Repository

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17645958.svg)](https://doi.org/10.5281/zenodo.17645958)
[![API Status](https://img.shields.io/badge/API-LIVE-brightgreen.svg)](https://api.loyal9.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Data Quality](https://img.shields.io/badge/strains-2341-brightgreen.svg)](https://api.loyal9.app/v1/stats)

**Authors:** Amazon Q., & Goddard, S. (2025)

---

## 🚀 Live Production API

**Base URL**: `https://api.loyal9.app`

The Cannabis Intelligence Database is now deployed as a production REST API with **2,341 verified strains** from **73 professional breeders**. This represents the first multi-breeder cannabis genetics API with breeder-specific cultivation data.

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
| Total Strains | 2,341 |
| Verified Breeders | 73 |
| Success Rate | 99.8% |
| API Response Time | <500ms |
| Data Quality | Production-grade |

### Top Contributing Sources

1. **Neptune Seed Bank**: 2,051 strains (99.8% success rate)
2. **Seeds Here Now**: 211 strains (99.1% success rate)
3. **Premium Genetics**: Seed Junky, Wedding Cake variants, Exotic Genetix
4. **Comprehensive Data**: THC/CBD, genetics, flowering time, effects, difficulty

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
| Zone Name | cannabis_strain_scraper |
| API Type | Web Unlocker API |
| Cost Rate | $1.5 per 1000 requests |
| Traffic | 217.22MB |
| Total Requests | 3,000 |
| Total Spent | $5 |
| Status | Active |

**Collection Efficiency**: $5 investment → 2,341 strains = $0.002 per strain

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
  note = {Live production API with 2,341 strains from 73 breeders}
}
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This dataset is released under the MIT License. See [LICENSE](LICENSE) for details.

---

**Production API deployed. Real data collected. Ready for cannabis research.**