ESG Materiality Assessment & Scoring Suite
https://img.shields.io/badge/Python-3.9+-blue
https://img.shields.io/badge/Streamlit-1.28+-red
https://img.shields.io/badge/License-MIT-green
https://img.shields.io/badge/Status-Production_Ready-brightgreen

A comprehensive web application for Double Materiality Assessment and ESGFP Scoring with full export capabilities.

🚀 Live Demo
https://static.streamlit.io/badges/streamlit_badge_black_white.svg

📋 Table of Contents
Features

Quick Start

Installation

Usage

Project Structure

API Reference

Contributing

License

Acknowledgements

✨ Features
📊 Dual Assessment Modules
Materiality Assessment: Risk analysis with dynamic impact calculation

ESGFP Scoring: Indicator-based scoring with AHP/FAHP weighting

Integrated Dashboard: Cross-module insights and recommendations

🎨 Advanced Analytics
Interactive heatmaps and materiality matrices

Multiple weighting scenarios and sensitivity testing

Monte Carlo simulations and SMAA analysis

Comparative analysis across methods

💾 Data Management
Customizable risk categories and key issues

Flexible indicator library with configurable scoring

Session state persistence

Full import/export capabilities

📤 Export Formats
Excel Workbooks (multi-sheet)

PDF Reports (formatted)

JSON Data (structured)

Image Gallery (charts as PNG/SVG)

CSV Files (individual components)

🏗️ Quick Start
Prerequisites
Python 3.9+

pip package manager

Installation
Clone the repository

bash
git clone https://github.com/yourusername/esg-materiality-app.git
cd esg-materiality-app
Create virtual environment (recommended)

bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
Install dependencies

bash
pip install -r requirements.txt
Run the application

bash
streamlit run app.py
Open your browser at http://localhost:8501

📖 Usage
Materiality Assessment
Navigate to Materiality Assessment module

Add key issues by pillar

Configure risk categories

Run risk analysis and stakeholder assessment

Compare results and export

ESGFP Scoring
Select ESGFP Scoring module

Set up your model structure

Define AHP weights for key issues

Enter indicator values

Run scenarios and validation

Export Results
Go to Export Results section

Choose export format (Excel, PDF, JSON, etc.)

Select export scope

Generate and download

📁 Project Structure
text
esg-materiality-app/
├── app.py                          # Main Streamlit application
├── materiality_assessment_final.py # Materiality assessment module
├── check3.py                       # ESGFP scoring module
├── requirements.txt                # Python dependencies
├── .gitignore                      # Git ignore file
├── README.md                       # This file
├── data/                           # Data storage
│   ├── exports/                    # User downloads
│   └── temp/                       # Temporary files
└── assets/                         # Static assets
    └── images/                     # Logos and icons
📊 API Reference
Materiality Assessment Functions
python
from materiality_assessment_final import (
    DEFAULT_PILLARS,
    LIKELIHOOD_LABELS,
    IMPACT_LABELS,
    calculate_impact_from_risks_dynamic,
    get_risk_level,
    create_heatmap_matrix
)
ESGFP Scoring Functions
python
# Import from check3.py for ESGFP functionality
🛠️ Development
Setting Up Development Environment
bash
# Clone repository
git clone https://github.com/yourusername/esg-materiality-app.git
cd esg-materiality-app

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
Running Tests
bash
# Run the application
streamlit run app.py

# For development with auto-reload
streamlit run app.py --server.runOnSave true
Building for Production
bash
# Ensure all dependencies are installed
pip freeze > requirements.txt

# Test production build
streamlit run app.py --server.headless true
📈 Deployment
Deploy to Streamlit Cloud
Push code to GitHub repository

Sign in to Streamlit Cloud

Click "New app"

Select repository, branch, and main file (app.py)

Click "Deploy"

Deploy with Docker
dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
Build and run:

bash
docker build -t esg-materiality-app .
docker run -p 8501:8501 esg-materiality-app
🤝 Contributing
We welcome contributions! Here's how to get started:

Fork the repository

Create a feature branch

bash
git checkout -b feature/amazing-feature
Make your changes

Commit your changes

bash
git commit -m 'Add amazing feature'
Push to the branch

bash
git push origin feature/amazing-feature
Open a Pull Request

Contribution Guidelines
Follow PEP 8 style guide

Write descriptive commit messages

Add tests for new features

Update documentation as needed

Ensure backward compatibility

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

text
MIT License

Copyright (c) 2024 ESG Analytics Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
🙏 Acknowledgements
Streamlit for the amazing web framework

Plotly for interactive visualizations

Pandas & NumPy for data manipulation

OpenPyXL & ReportLab for export functionality

📚 References
Double Materiality: EU Sustainable Finance Disclosure Regulation

ESGFP Framework: Integrated sustainability scoring methodology

AHP Methodology: Saaty's Analytic Hierarchy Process

MCDA Methods: Multi-Criteria Decision Analysis techniques

🆘 Support
Common Issues & Solutions
Issue	Solution
Import errors	Check Python version and dependencies
Session state issues	Clear browser cache or restart app
Export failures	Verify write permissions in data directory
Chart rendering errors	Update Plotly/Matplotlib libraries
Getting Help
GitHub Issues: Report bugs or request features

Documentation: Check this README and inline code comments

Community: Join our discussion forum

🔮 Roadmap
Planned Features
Database integration for persistent storage

User authentication and multi-tenancy

API endpoints for external integration

Advanced machine learning predictions

Real-time data feeds and updates

Mobile-responsive design

Multi-language support

In Progress
Core materiality assessment module

ESGFP scoring system

Export functionality

Integrated dashboard

Completed ✓
Basic Streamlit application

Materiality matrix visualizations

Scenario analysis tools

Monte Carlo simulations

📊 Metrics
https://img.shields.io/github/stars/yourusername/esg-materiality-app?style=social
https://img.shields.io/github/forks/yourusername/esg-materiality-app?style=social
https://img.shields.io/github/issues/yourusername/esg-materiality-app
https://img.shields.io/github/issues-pr/yourusername/esg-materiality-app

📧 Contact
Project Maintainer: Your Name
Email: your.email@example.com
GitHub: @yourusername
Website: https://yourwebsite.com

Developed for sustainability professionals, ESG analysts, risk managers, and corporate decision-makers seeking integrated materiality assessment and performance scoring solutions.

Last Updated: January 2026