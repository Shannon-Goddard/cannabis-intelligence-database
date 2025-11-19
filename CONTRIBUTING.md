# Contributing to Cannabis Intelligence Database

## Welcome Contributors!

We're building the most comprehensive cannabis genetics database for research and cultivation optimization. Your contributions help advance cannabis science and improve cultivation outcomes worldwide.

## Ways to Contribute

### 🌿 Add Missing Breeders
**High Impact**: Expand database coverage

**Process**:
1. Identify reputable cannabis breeder with official website
2. Verify they have strain listings (not just company info)
3. Add to `CANNABIS_BREEDERS.md` with proper formatting
4. Test URL with validation script
5. Submit pull request

**Requirements**:
- Official breeder website (not seed bank resellers)
- Active strain catalog with names visible
- Established reputation in cannabis community

### 📊 Improve Data Quality
**Medium Impact**: Enhance accuracy and completeness

**Areas**:
- **Strain Name Standardization**: Fix naming inconsistencies
- **Duplicate Detection**: Identify and merge duplicate entries
- **Missing Data**: Fill gaps in strain information
- **Source Verification**: Validate breeder attributions

### 🔧 Technical Improvements
**High Impact**: Enhance collection capabilities

**Opportunities**:
- **New Site Patterns**: Add support for complex website architectures
- **Performance Optimization**: Improve scraping speed and reliability
- **Error Handling**: Better recovery from collection failures
- **Data Validation**: Enhanced quality control algorithms

### 📚 Documentation
**Medium Impact**: Improve usability and academic value

**Needs**:
- **Usage Examples**: Real-world analysis scenarios
- **API Documentation**: Clear interface descriptions
- **Research Applications**: Case studies and use cases
- **Methodology Refinements**: Improve scientific rigor

## Getting Started

### 1. Fork and Clone
```bash
git clone https://github.com/YOUR-USERNAME/cannabis-intelligence-database.git
cd cannabis-intelligence-database
```

### 2. Set Up Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Test Your Setup
```bash
python scripts/validate_breeders.py --test
python scripts/cannabis_scraper.py --help
```

## Contribution Guidelines

### Code Standards
- **Python Style**: Follow PEP 8 guidelines
- **Documentation**: Docstrings for all functions
- **Testing**: Include tests for new functionality
- **Error Handling**: Comprehensive exception management

### Data Standards
- **Source Attribution**: Always maintain breeder source
- **Naming Conventions**: Use standardized strain names
- **Quality Validation**: Verify data accuracy before submission
- **Metadata**: Include collection timestamps and methods

### Commit Guidelines
```bash
# Good commit messages
git commit -m "Add Exotic Genetix breeder with 81 strains"
git commit -m "Fix duplicate detection for similar strain names"
git commit -m "Improve pagination handling for seed bank sites"

# Bad commit messages
git commit -m "updates"
git commit -m "fix stuff"
git commit -m "more changes"
```

## Pull Request Process

### 1. Create Feature Branch
```bash
git checkout -b add-new-breeder-xyz
# or
git checkout -b fix-duplicate-detection
```

### 2. Make Changes
- Follow coding standards
- Add appropriate tests
- Update documentation
- Validate data quality

### 3. Test Thoroughly
```bash
# Test new breeder additions
python scripts/validate_breeders.py --breeder="New Breeder Name"

# Test data collection
python scripts/cannabis_scraper.py --breeder="New Breeder Name" --test

# Run quality checks
python scripts/analyze_data.py --validate
```

### 4. Submit Pull Request
**Template**:
```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] New breeder addition
- [ ] Bug fix
- [ ] Feature enhancement
- [ ] Documentation update

## Testing
- [ ] Validated new URLs
- [ ] Tested data collection
- [ ] Verified data quality
- [ ] Updated documentation

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## Specific Contribution Types

### Adding New Breeders

**Research Phase**:
1. Verify breeder legitimacy and reputation
2. Confirm official website with strain listings
3. Check for existing coverage in database

**Implementation**:
```markdown
| New Breeder Name | Signature Strains | https://newbreeder.com/strains | Direct from breeder |
```

**Validation**:
```bash
python scripts/validate_breeders.py --url="https://newbreeder.com/strains"
python scripts/cannabis_scraper.py --breeder="New Breeder Name" --dry-run
```

### Fixing Collection Issues

**Common Problems**:
- **403/401 Errors**: Site blocking automated requests
- **Pattern Detection Failures**: Complex site architectures
- **Timeout Issues**: Slow loading pages
- **Data Quality**: Inconsistent strain naming

**Solution Process**:
1. Identify root cause through debugging
2. Implement targeted fix with error handling
3. Test with multiple similar sites
4. Document solution for future reference

### Data Quality Improvements

**Validation Checklist**:
- [ ] Strain names properly formatted
- [ ] Breeder attribution accurate
- [ ] No obvious duplicates
- [ ] Source URLs functional
- [ ] Collection metadata complete

## Recognition

### Contributor Acknowledgment
- **README Credits**: Major contributors listed in main README
- **Commit Attribution**: All commits properly attributed
- **Academic Citations**: Research contributors included in papers
- **Community Recognition**: Outstanding contributions highlighted

### Contribution Levels
- **🌱 Seedling**: First contribution (1+ commits)
- **🌿 Cultivator**: Regular contributor (5+ commits)
- **🏆 Master Grower**: Major feature contributor (20+ commits)
- **👑 Breeder**: Core team member (50+ commits)

## Code of Conduct

### Our Standards
- **Respectful Communication**: Professional and inclusive language
- **Scientific Integrity**: Accurate data and transparent methods
- **Collaborative Spirit**: Help others learn and contribute
- **Quality Focus**: Maintain high standards for research applications

### Unacceptable Behavior
- Harassment or discriminatory language
- Intentionally submitting false or misleading data
- Violating intellectual property rights
- Disrupting collaborative processes

## Questions and Support

### Getting Help
- **GitHub Issues**: Technical questions and bug reports
- **Discussions**: General questions and feature requests
- **Documentation**: Check existing docs first
- **Community**: Connect with other contributors

### Contact Information
- **Project Maintainer**: Shannon Goddard
- **Repository**: [cannabis-intelligence-database](https://github.com/Shannon-Goddard/cannabis-intelligence-database)
- **Issues**: [GitHub Issues](https://github.com/Shannon-Goddard/cannabis-intelligence-database/issues)

---

**Thank you for contributing to cannabis research and cultivation science!**

*Together, we're building the foundation for precision cannabis cultivation.*