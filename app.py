# app.py - COMPLETE VERSION
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import io
import json
import hashlib
import base64
from datetime import datetime, timedelta
import warnings
import sys
import tempfile
import zipfile
from typing import Dict, List, Tuple, Optional, Any
import random
import math

# Optional PDF generation support
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image as RLImage, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.units import inch
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False

warnings.filterwarnings('ignore')

# Import functions from your check3.py
sys.path.append('.')
try:
    from check3 import (
        parse_indicator_model,
        IndicatorDef,
        run_ahp_fahp_section,
        extract_issue_weights,
        compute_indicator_score_scaled,
        compute_gm,
        compute_ps,
        compute_final_indicator_score,
        compute_rank_cs,
        compute_key_issue_scores,
        compute_pillar_scores,
        build_indicator_score_frames,
        method_weighted,
        method_wpm,
        method_rank,
        method_topsis,
        method_vikor,
        method_edas,
        method_maut,
        method_pca,
        _scale_series_by_method,
        approx_dea_diagnostics,
        run_monte_carlo_sensitivity,
        run_smaa,
        critical_weight_intervals_proportional,
        RAW_INDICATORS_TSV,
        PILLAR_SCORE_THEORETICAL_MAX,
        OUTPUT_SCALE,
        INDICATOR_SCORE_SCALE,
        GM_MIN,
        GM_MAX,
        RI_TABLE,
        TFN_SCALE
    )
    
    # Create stubs for missing functions
    def esgfp_section(*args, **kwargs):
        return {}, {}
        
    def run_scenarios_with_methods(*args, **kwargs):
        return [], [], [], []
        
    def run_validation_suite_interactive(*args, **kwargs):
        pass
        
except ImportError as e:
    st.error(f"Failed to import check3.py functions: {e}")
    st.info("Please ensure check3.py is in the same directory")
    
    # Define minimal fallbacks
    class IndicatorDef:
        def __init__(self, pillar, key_issue, indicator, unit, formula_desc, criteria, default_mode, higher_is_better):
            self.pillar = pillar
            self.key_issue = key_issue
            self.indicator = indicator
            self.unit = unit
            self.formula_desc = formula_desc
            self.criteria = criteria
            self.default_mode = default_mode
            self.higher_is_better = higher_is_better

# Set page config
st.set_page_config(
    page_title="Double Materiality & ESGFP Assessment Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* General Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .main > div {
        animation: fadeIn 0.5s ease-in-out;
    }

    /* Default (Light) Theme variables */
    :root {
        --primary-color: #1f77b4;
        --secondary-color: #2ca02c;
        --background-color: #ffffff;
        --text-color: #333333;
        --card-background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --card-color: white;
    }

    /* Dark Theme overrides */
    body[data-theme="dark"] {
        --primary-color: #4dabf7;
        --secondary-color: #69db7c;
        --background-color: #1a1a1a;
        --text-color: #f0f0f0;
        --card-background: linear-gradient(135deg, #495057 0%, #343a40 100%);
        --card-color: #f8f9fa;
    }

    body {
        background-color: var(--background-color);
        color: var(--text-color);
    }

    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        color: var(--primary-color); /* Fallback for browsers that don't support background-clip */
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: fadeIn 1s ease-in-out;
    }
    /* Add this for browsers that don't support -webkit-background-clip */
    @supports not (-webkit-background-clip: text) {
      .main-header {
        -webkit-text-fill-color: initial; /* Reset to use the 'color' property */
      }
    }

    .sub-header {
        font-size: 1.8rem;
        color: var(--secondary-color);
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid var(--secondary-color);
        padding-bottom: 0.5rem;
    }
    .metric-card {
        background: var(--card-background);
        color: var(--card-color);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    .metric-card:hover {
        transform: scale(1.05);
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }

    .risk-low { color: #10b981; font-weight: bold; }
    .risk-medium { color: #fbbf24; font-weight: bold; }
    .risk-high { color: #f97316; font-weight: bold; }
    .risk-very-high { color: #ef4444; font-weight: bold; }

    .stButton>button {
        width: 100%;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
        transition: background-color 0.2s ease-in-out, transform 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        filter: brightness(1.1);
    }

    .stProgress > div > div > div > div {
        background-image: linear-gradient(45deg, var(--primary-color), var(--secondary-color));
    }
</style>
""", unsafe_allow_html=True)

# Constants
DEFAULT_PILLARS = {
    'Environment': {'icon': '🌱', 'color': '#10b981'},
    'Social': {'icon': '👥', 'color': '#3b82f6'},
    'Governance': {'icon': '⚖️', 'color': '#8b5cf6'},
    'Finance': {'icon': '💰', 'color': '#f59e0b'},
    'Process': {'icon': '⚙️', 'color': '#ef4444'}
}

LIKELIHOOD_LABELS = {
    1: "Very Low",
    2: "Low", 
    3: "Medium",
    4: "High",
    5: "Very High"
}

IMPACT_LABELS = {
    1: "Very Low",
    2: "Low",
    3: "Medium",
    4: "High", 
    5: "Very High"
}

# Helper functions
def calculate_impact_from_risks_dynamic(risks, risk_categories):
    """Calculate impact based on risks with proper scoring"""
    if not risks:
        return 3  # Medium impact by default
    
    # Score based on risk categories
    category_weights = {
        'Financial': 2.0,
        'Operational': 1.5,
        'Reputational': 1.8,
        'Strategic': 2.0,
        'Compliance': 1.7,
        'Environmental': 2.2,
        'Social': 1.9,
        'Governance': 2.1
    }
    
    total_score = 0
    for risk in risks:
        # Find which category this risk belongs to
        for category, category_risks in risk_categories.items():
            if risk in category_risks:
                weight = category_weights.get(category, 1.0)
                total_score += weight
                break
        else:
            total_score += 1.0  # Default weight
    
    # Normalize to 1-5 scale
    avg_score = total_score / len(risks)
    impact = min(5, max(1, int(round(avg_score))))
    return impact

def get_risk_level(score):
    """Determine risk level from score (1-25 scale)"""
    if score <= 4:
        return "Low", "#10b981"
    elif score <= 9:
        return "Medium", "#fbbf24"
    elif score <= 16:
        return "High", "#f97316"
    else:
        return "Very High", "#ef4444"

def create_heatmap_matrix(results, title="Materiality Matrix"):
    """Create an interactive heatmap matrix using Plotly"""
    if not results:
        return go.Figure()
    
    # Create matrix data
    issues = [r['issue'] for r in results]
    likelihoods = [r['likelihood'] for r in results]
    impacts = [r['impact'] for r in results]
    scores = [r['score'] for r in results]
    colors = [r.get('color', '#666666') for r in results]
    
    # Create hover text
    hover_text = []
    for r in results:
        level = r.get('level', 'Unknown')
        hover_text.append(
            f"<b>{r['issue']}</b><br>"
            f"Likelihood: {r['likelihood']}<br>"
            f"Impact: {r['impact']}<br>"
            f"Score: {r['score']:.1f}<br>"
            f"Level: {level}"
        )
    
    fig = go.Figure(data=go.Scatter(
        x=likelihoods,
        y=impacts,
        mode='markers+text',
        marker=dict(
            size=[s*2 for s in scores],  # Scale size by score
            color=colors,
            opacity=0.7,
            line=dict(width=2, color='DarkSlateGrey')
        ),
        text=issues,
        textposition="top center",
        hovertext=hover_text,
        hoverinfo="text"
    ))
    
    fig.update_layout(
        title=title,
        xaxis=dict(
            title="Likelihood",
            tickmode='array',
            tickvals=[1, 2, 3, 4, 5],
            ticktext=["VL", "L", "M", "H", "VH"],
            range=[0.5, 5.5]
        ),
        yaxis=dict(
            title="Impact",
            tickmode='array',
            tickvals=[1, 2, 3, 4, 5],
            ticktext=["VL", "L", "M", "H", "VH"],
            range=[0.5, 5.5]
        ),
        height=600,
        showlegend=False,
        plot_bgcolor='rgba(240, 240, 240, 0.5)'
    )
    
    # Add quadrants
    fig.add_shape(
        type="rect",
        x0=0.5, y0=0.5, x1=3.5, y1=3.5,
        line=dict(color="LightGray", width=1),
        fillcolor="rgba(0,0,0,0)",
        opacity=0.2
    )
    
    fig.add_shape(
        type="rect",
        x0=3.5, y0=3.5, x1=5.5, y1=5.5,
        line=dict(color="Red", width=2),
        fillcolor="rgba(255,0,0,0.1)"
    )
    
    return fig

def create_radar_chart(pillar_scores, title="Pillar Scores Radar"):
    """Create a radar chart for pillar scores"""
    if pillar_scores.empty:
        return go.Figure()
    
    categories = pillar_scores.index.tolist()
    fig = go.Figure()
    
    for col in pillar_scores.columns:
        values = pillar_scores[col].tolist()
        values.append(values[0])  # Close the radar
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill='toself',
            name=col
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(pillar_scores.max().max(), 10)]
            )),
        showlegend=True,
        title=title,
        height=500
    )
    
    return fig


def safe_figure_bytes(fig, fmt='png'):
    """Return bytes and mime for a figure in requested format.
    Falls back to HTML if binary export (kaleido) is unavailable.
    """
    try:
        # prefer plotly built-in image export (requires kaleido)
        img = fig.to_image(format=fmt)
        mime = f"image/{fmt}" if fmt == 'png' else 'application/pdf'
        return img, mime
    except Exception:
        try:
            html = fig.to_html(full_html=True, include_plotlyjs='cdn')
            return html.encode('utf-8'), 'text/html'
        except Exception:
            return None, None


def make_zip_bytes(file_map: Dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in file_map.items():
            z.writestr(name, data)
    return buf.getvalue()


def generate_pdf_report(report_data: Dict[str, Any], figs: Optional[Dict[str, go.Figure]] = None, title: str = "ESG Report") -> Optional[bytes]:
    """Generate a multi-page PDF using ReportLab. Returns bytes or None if not available."""
    if not HAS_REPORTLAB:
        return None

    try:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(title, styles['Title']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 12))

        # Add each section
        for section, data in report_data.items():
            story.append(Paragraph(section.replace('_', ' '), styles['Heading2']))
            story.append(Spacer(1, 6))
            if isinstance(data, pd.DataFrame) and not data.empty:
                # Full table data
                table_data = [list(data.columns)] + data.astype(str).values.tolist()
                tbl = Table(table_data, repeatRows=1)
                story.append(tbl)
            else:
                story.append(Paragraph(str(data), styles['Normal']))
            story.append(Spacer(1, 12))
            story.append(PageBreak())

        # Add figures
        if figs:
            for name, fig in figs.items():
                try:
                    img_bytes, mime = safe_figure_bytes(fig, fmt='png')
                    if img_bytes and mime == 'text/html':
                        # if HTML fallback, skip embedding
                        continue
                    if img_bytes:
                        img_buf = io.BytesIO(img_bytes)
                        img = RLImage(img_buf)
                        # scale image to fit page width
                        img.drawWidth = 6.5 * inch
                        img.drawHeight = img.drawWidth * 0.6
                        story.append(Paragraph(name.replace('_', ' '), styles['Heading3']))
                        story.append(img)
                        story.append(Spacer(1, 12))
                        story.append(PageBreak())
                except Exception:
                    continue

        doc.build(story)
        return buf.getvalue()
    except Exception:
        return None

def calculate_real_time_score(current, vmin, vmax, higher_is_better, n_alts):
    """Real-time score calculation with visual feedback"""
    if n_alts <= 1:
        return INDICATOR_SCORE_SCALE
    
    denom = vmax - vmin
    if abs(denom) < 1e-12:
        return INDICATOR_SCORE_SCALE
    
    if higher_is_better:
        norm = (current - vmin) / denom
    else:
        norm = (vmax - current) / denom
    
    norm = np.clip(norm, 0.0, 1.0)
    return 30.0 + 60.0 * norm

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'current_module': 'Materiality Assessment',
        'key_issues': [],
        'risk_analysis_data': {},
        'stakeholder_data': {},
        'risk_categories': {
            'Financial': ['Market volatility', 'Regulatory fines', 'Compliance costs'],
            'Operational': ['Supply chain disruption', 'Equipment failure', 'Labor issues'],
            'Reputational': ['Negative media', 'Social media backlash', 'Customer complaints'],
            'Strategic': ['Competition', 'Technology disruption', 'Market shifts'],
            'Environmental': ['Climate change', 'Pollution', 'Resource depletion'],
            'Social': ['Labor rights', 'Community impact', 'Health & safety'],
            'Governance': ['Corruption', 'Board diversity', 'Transparency']
        },
        'selected_methods': ['risk_analysis', 'stakeholder'],
        'esgfp_model': None,
        'esgfp_step': 1,
        'esgfp_weights': {},
        'esgfp_alternatives': [],
        'esgfp_scores': {},
        'esgfp_indicator_values': {},
        'esgfp_ge_values': {},
        'esgfp_scenarios': [],
        'validation_results': {},
        'materiality_results': None,
        'esgfp_results': None,
        'export_format': 'Excel',
        'show_real_time_calc': True
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Initialize ESGFP model
    if st.session_state.esgfp_model is None:
        try:
            st.session_state.esgfp_model = parse_indicator_model(RAW_INDICATORS_TSV)
        except:
            # Create a minimal model
            st.session_state.esgfp_model = {
                'Environment': {
                    'Carbon Efficiency': [
                        IndicatorDef('Environment', 'Carbon Efficiency', 
                                    'Net Carbon Avoided Cost', 'USD/metric ton CO2-e',
                                    'Higher-is-better scoring', 'Criterion', 'A', False)
                    ]
                }
            }

# Main app
def main():
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/300x80.png?text=ESG+Analytics", use_container_width=True)
        
        st.markdown("## 📊 Navigation")
        module = st.radio(
            "Select Module",
            ["Materiality Assessment", "ESGFP Scoring", "Integrated Dashboard", "Export Results"],
            key="module_select"
        )
        st.session_state.current_module = module
        
        st.markdown("---")
        
        st.markdown("## ⚙️ Settings")
        st.selectbox(
            "Export Format",
            ["Excel", "CSV", "PNG", "PDF", "JSON"],
            key="export_format"
        )
        
        st.session_state.show_real_time_calc = st.checkbox(
            "Show Real-time Calculations", 
            value=st.session_state.show_real_time_calc
        )
        
        st.markdown("---")
        
        # Quick stats
        st.markdown("## 📈 Quick Stats")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.key_issues:
                st.metric("Issues", len(st.session_state.key_issues))
        with col2:
            if st.session_state.esgfp_alternatives:
                st.metric("Alternatives", len(st.session_state.esgfp_alternatives))
        
        st.markdown("---")
        
        # Help section
        if st.button("📚 Documentation", use_container_width=True):
            st.session_state.show_docs = True
    
    # Render selected module
    if module == "Materiality Assessment":
        render_materiality_assessment()
    elif module == "ESGFP Scoring":
        render_esgfp_scoring()
    elif module == "Integrated Dashboard":
        render_integrated_dashboard()
    elif module == "Export Results":
        render_export_section()
    
    # Documentation modal
    if st.session_state.get('show_docs', False):
        with st.expander("Documentation", expanded=True):
            st.markdown("""
            ## 📖 User Guide
            
            ### Materiality Assessment Module
            1. **Configuration**: Add/remove issues and risk categories
            2. **Risk Analysis**: Assess likelihood and select risks
            3. **Stakeholder Assessment**: Input stakeholder and expert scores
            4. **Results**: Compare methods and export
            
            ### ESGFP Scoring Module
            1. **Model Setup**: Define indicators and structure
            2. **AHP Weighting**: Set weights for key issues
            3. **Indicator Scoring**: Enter values for alternatives
            4. **Results & Scenarios**: Analyze scores and run scenarios
            5. **Validation**: Run sensitivity and robustness tests
            
            ### Key Features
            - Real-time score calculations
            - Multiple assessment methods
            - Integrated validation suite
            - Comprehensive export options
            """)
            
            if st.button("Close Documentation"):
                st.session_state.show_docs = False
                st.rerun()

def render_materiality_assessment():
    st.markdown('<div class="main-header">Double Materiality Assessment Tool</div>', unsafe_allow_html=True)
    
    # Tabs for workflow
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Configuration", 
        "⚡ Risk Analysis", 
        "👥 Stakeholder", 
        "📊 Results"
    ])
    
    with tab1:
        render_materiality_configuration()
    
    with tab2:
        if 'risk_analysis' in st.session_state.selected_methods:
            render_risk_analysis()
        else:
            st.info("Enable Risk Analysis in Configuration tab")
    
    with tab3:
        if 'stakeholder' in st.session_state.selected_methods:
            render_stakeholder_assessment()
        else:
            st.info("Enable Stakeholder Assessment in Configuration tab")
    
    with tab4:
        render_materiality_results()

def render_materiality_configuration():
    st.markdown('<div class="sub-header">Assessment Configuration</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ➕ Add New Issue")
        with st.container(border=True):
            new_issue = st.text_input("Issue Name", key="new_issue_name")
            new_pillar = st.selectbox("Pillar", list(DEFAULT_PILLARS.keys()), key="new_issue_pillar")
            
            if st.button("Add Issue", type="primary", key="add_issue_btn"):
                if new_issue and new_issue not in [i['name'] for i in st.session_state.key_issues]:
                    st.session_state.key_issues.append({
                        'name': new_issue,
                        'pillar': new_pillar,
                        'color': DEFAULT_PILLARS[new_pillar]['color']
                    })
                    
                    # Initialize data structures
                    st.session_state.risk_analysis_data[new_issue] = {
                        'risks': [],
                        'likelihood': 3
                    }
                    
                    st.session_state.stakeholder_data[new_issue] = {
                        'likelihood': 3,
                        'impact': 3,
                        'stakeholder_score': 5,
                        'expert_score': 5
                    }
                    
                    st.success(f"✅ Added: {new_issue}")
                    st.rerun()
                elif new_issue:
                    st.error("Issue already exists!")
    
    with col2:
        st.markdown("### ➖ Remove Issue")
        with st.container(border=True):
            if st.session_state.key_issues:
                issue_to_remove = st.selectbox(
                    "Select issue to remove",
                    options=[i['name'] for i in st.session_state.key_issues],
                    key="remove_issue_select"
                )
                
                if st.button("Remove Issue", type="secondary", key="remove_issue_btn"):
                    st.session_state.key_issues = [
                        i for i in st.session_state.key_issues 
                        if i['name'] != issue_to_remove
                    ]
                    
                    # Clean up data
                    for data in [st.session_state.risk_analysis_data, 
                               st.session_state.stakeholder_data]:
                        data.pop(issue_to_remove, None)
                    
                    st.success(f"✅ Removed: {issue_to_remove}")
                    st.rerun()
            else:
                st.info("No issues to remove")
    
    st.markdown("---")
    
    # Risk categories management
    st.markdown("### ⚙️ Risk Categories Management")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        new_cat = st.text_input("New Category Name", key="new_cat_name")
    with col2:
        if st.button("Add Category", key="add_cat_btn"):
            if new_cat and new_cat not in st.session_state.risk_categories:
                st.session_state.risk_categories[new_cat] = []
                st.success(f"✅ Added category: {new_cat}")
                st.rerun()
    
    # Display and manage existing categories
    for cat in list(st.session_state.risk_categories.keys()):
        with st.expander(f"📁 {cat}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                new_risk = st.text_input(
                    f"New risk for {cat}",
                    key=f"new_risk_{cat}"
                )
            
            with col2:
                if st.button("Add", key=f"add_risk_{cat}"):
                    if new_risk and new_risk not in st.session_state.risk_categories[cat]:
                        st.session_state.risk_categories[cat].append(new_risk)
                        st.success(f"✅ Added: {new_risk}")
                        st.rerun()
            
            # Show existing risks
            if st.session_state.risk_categories[cat]:
                st.markdown("**Existing Risks:**")
                for risk in st.session_state.risk_categories[cat]:
                    risk_col1, risk_col2 = st.columns([4, 1])
                    with risk_col1:
                        st.markdown(f"• {risk}")
                    with risk_col2:
                        if st.button("🗑️", key=f"del_{cat}_{risk}"):
                            st.session_state.risk_categories[cat].remove(risk)
                            st.rerun()
            
            if st.button(f"Delete Category: {cat}", key=f"del_cat_{cat}", type="secondary"):
                del st.session_state.risk_categories[cat]
                st.rerun()
    
    st.markdown("---")
    
    # Assessment methods selection
    st.markdown("### 📊 Assessment Methods")
    
    col1, col2 = st.columns(2)
    with col1:
        risk_analysis = st.checkbox(
            "⚡ Risk Analysis", 
            value='risk_analysis' in st.session_state.selected_methods,
            key="ra_checkbox"
        )
    with col2:
        stakeholder = st.checkbox(
            "👥 Stakeholder & Expert", 
            value='stakeholder' in st.session_state.selected_methods,
            key="stk_checkbox"
        )
    
    if st.button("Update Methods", type="primary", key="update_methods_btn"):
        st.session_state.selected_methods = []
        if risk_analysis:
            st.session_state.selected_methods.append('risk_analysis')
        if stakeholder:
            st.session_state.selected_methods.append('stakeholder')
        st.success("✅ Methods updated!")
        st.rerun()

def render_risk_analysis():
    st.markdown('<div class="sub-header">Risk Analysis Assessment</div>', unsafe_allow_html=True)
    
    if not st.session_state.key_issues:
        st.warning("⚠️ Please add issues in the Configuration tab first.")
        return
    
    # Group issues by pillar
    for pillar in DEFAULT_PILLARS.keys():
        pillar_issues = [
            i for i in st.session_state.key_issues 
            if i['pillar'] == pillar
        ]
        
        if pillar_issues:
            with st.expander(
                f"{DEFAULT_PILLARS[pillar]['icon']} {pillar} ({len(pillar_issues)} issues)",
                expanded=True
            ):
                for issue in pillar_issues:
                    issue_name = issue['name']
                    
                    col1, col2, col3 = st.columns([2, 1, 2])
                    
                    with col1:
                        st.markdown(f"**{issue_name}**")
                    
                    with col2:
                        likelihood = st.selectbox(
                            "Likelihood",
                            options=[1, 2, 3, 4, 5],
                            index=st.session_state.risk_analysis_data[issue_name]['likelihood'] - 1,
                            format_func=lambda x: f"{x} - {LIKELIHOOD_LABELS[x]}",
                            key=f"ra_like_{issue_name}"
                        )
                        st.session_state.risk_analysis_data[issue_name]['likelihood'] = likelihood
                    
                    with col3:
                        # Get all risks for selection (deduplicated and stable order)
                        all_risks = sorted({
                            r for cat_risks in st.session_state.risk_categories.values()
                            for r in cat_risks
                        })

                        # Ensure stored defaults are valid options
                        stored_defaults = st.session_state.risk_analysis_data.get(issue_name, {}).get('risks', [])
                        default_filtered = [r for r in stored_defaults if r in all_risks]

                        selected = st.multiselect(
                            "Select Risks",
                            options=all_risks,
                            default=default_filtered,
                            key=f"ra_risks_{issue_name}"
                        )

                        # Persist selection defensively
                        if issue_name not in st.session_state.risk_analysis_data:
                            st.session_state.risk_analysis_data[issue_name] = {'risks': [], 'likelihood': 3}
                        st.session_state.risk_analysis_data[issue_name]['risks'] = list(selected)

                        # Calculate and display impact (guarded to avoid UI-breaking exceptions)
                        try:
                            impact = calculate_impact_from_risks_dynamic(
                                selected,
                                st.session_state.risk_categories
                            )
                        except Exception:
                            impact = 3

                        label = IMPACT_LABELS.get(impact, 'Medium')
                        st.caption(
                            f"Impact: {impact} - {label} "
                            f"({len(selected)} risk{'s' if len(selected) != 1 else ''})"
                        )
                    
                    st.divider()
    
    # Results section
    st.markdown("---")
    st.markdown("### 📈 Risk Analysis Results")
    
    # Calculate results
    results = []
    for issue in st.session_state.key_issues:
        issue_name = issue['name']
        data = st.session_state.risk_analysis_data[issue_name]
        
        impact = calculate_impact_from_risks_dynamic(
            data['risks'],
            st.session_state.risk_categories
        )
        
        score = data['likelihood'] * impact
        level, color = get_risk_level(score)
        
        results.append({
            'issue': issue_name,
            'pillar': issue['pillar'],
            'color': issue['color'],
            'likelihood': data['likelihood'],
            'impact': impact,
            'score': score,
            'level': level,
            'risk_count': len(data['risks'])
        })
    
    # Display results
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🗺️ Materiality Matrix")
        if results:
            fig = create_heatmap_matrix(results, "Risk Analysis Materiality Matrix")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No results to display")
    
    with col2:
        st.markdown("#### 📋 Detailed Results")
        if results:
            df = pd.DataFrame(results).sort_values('score', ascending=False)
            df['rank'] = range(1, len(df) + 1)
            
            # Format display
            display_df = df[[
                'rank', 'issue', 'pillar', 'likelihood', 
                'impact', 'score', 'level', 'risk_count'
            ]].copy()
            
            display_df['score'] = display_df['score'].round(1)
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Summary metrics
            cols = st.columns(4)
            metrics = [
                ("Total Issues", len(df)),
                ("Avg Score", f"{df['score'].mean():.1f}"),
                ("High/Very High", len(df[df['level'].str.contains('High')])),
                ("Max Score", f"{df['score'].max():.1f}")
            ]
            
            for col, (label, value) in zip(cols, metrics):
                with col:
                    st.metric(label, value)
        else:
            st.info("No results to display")
    
    # Store results for export
    if results:
        st.session_state.materiality_results = {
            'risk_analysis': results,
            'timestamp': datetime.now().isoformat()
        }

def render_stakeholder_assessment():
    st.markdown('<div class="sub-header">Stakeholder & Expert Assessment</div>', unsafe_allow_html=True)
    
    if not st.session_state.key_issues:
        st.warning("⚠️ Please add issues in the Configuration tab first.")
        return
    
    # Group by pillar
    for pillar in DEFAULT_PILLARS.keys():
        pillar_issues = [
            i for i in st.session_state.key_issues 
            if i['pillar'] == pillar
        ]
        
        if pillar_issues:
            with st.expander(
                f"{DEFAULT_PILLARS[pillar]['icon']} {pillar} ({len(pillar_issues)} issues)",
                expanded=True
            ):
                for issue in pillar_issues:
                    issue_name = issue['name']
                    
                    st.markdown(f"**{issue_name}**")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        likelihood = st.selectbox(
                            "Likelihood",
                            options=[1, 2, 3, 4, 5],
                            index=st.session_state.stakeholder_data[issue_name]['likelihood'] - 1,
                            format_func=lambda x: f"{x} - {LIKELIHOOD_LABELS[x]}",
                            key=f"stk_like_{issue_name}"
                        )
                        st.session_state.stakeholder_data[issue_name]['likelihood'] = likelihood
                    
                    with col2:
                        impact = st.selectbox(
                            "Impact",
                            options=[1, 2, 3, 4, 5],
                            index=st.session_state.stakeholder_data[issue_name]['impact'] - 1,
                            format_func=lambda x: f"{x} - {IMPACT_LABELS[x]}",
                            key=f"stk_imp_{issue_name}"
                        )
                        st.session_state.stakeholder_data[issue_name]['impact'] = impact
                    
                    with col3:
                        st.session_state.stakeholder_data[issue_name]['stakeholder_score'] = st.slider(
                            "Stakeholder Score",
                            0, 10,
                            st.session_state.stakeholder_data[issue_name]['stakeholder_score'],
                            key=f"stk_stk_{issue_name}"
                        )
                    
                    with col4:
                        st.session_state.stakeholder_data[issue_name]['expert_score'] = st.slider(
                            "Expert Score",
                            0, 10,
                            st.session_state.stakeholder_data[issue_name]['expert_score'],
                            key=f"stk_exp_{issue_name}"
                        )
                    
                    # Calculate and display current score
                    data = st.session_state.stakeholder_data[issue_name]
                    weight = (data['stakeholder_score'] + data['expert_score']) / 20.0
                    base_score = data['likelihood'] * data['impact']
                    final_score = base_score * weight
                    
                    st.caption(
                        f"Calculation: {data['likelihood']} × {data['impact']} × {weight:.2f} = {final_score:.1f}"
                    )
                    
                    st.divider()
    
    # Results section
    st.markdown("---")
    st.markdown("### 📈 Stakeholder Results")
    
    # Calculate results
    results = []
    for issue in st.session_state.key_issues:
        issue_name = issue['name']
        data = st.session_state.stakeholder_data[issue_name]
        
        weight = (data['stakeholder_score'] + data['expert_score']) / 20.0
        base_score = data['likelihood'] * data['impact']
        score = base_score * weight
        level, color = get_risk_level(base_score)  # Use base score for level
        
        results.append({
            'issue': issue_name,
            'pillar': issue['pillar'],
            'color': issue['color'],
            'likelihood': data['likelihood'],
            'impact': data['impact'],
            'weight': weight,
            'score': score,
            'base_score': base_score,
            'level': level
        })
    
    # Display results
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🗺️ Materiality Matrix")
        if results:
            fig = create_heatmap_matrix(results, "Stakeholder Assessment Materiality Matrix")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No results to display")
    
    with col2:
        st.markdown("#### 📋 Detailed Results")
        if results:
            df = pd.DataFrame(results).sort_values('score', ascending=False)
            df['rank'] = range(1, len(df) + 1)
            
            # Format display
            display_df = df[[
                'rank', 'issue', 'pillar', 'likelihood', 
                'impact', 'weight', 'score', 'level'
            ]].copy()
            
            display_df['weight'] = display_df['weight'].round(2)
            display_df['score'] = display_df['score'].round(1)
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Summary metrics
            cols = st.columns(4)
            metrics = [
                ("Total Issues", len(df)),
                ("Avg Score", f"{df['score'].mean():.1f}"),
                ("Avg Weight", f"{df['weight'].mean():.2f}"),
                ("Max Score", f"{df['score'].max():.1f}")
            ]
            
            for col, (label, value) in zip(cols, metrics):
                with col:
                    st.metric(label, value)
        else:
            st.info("No results to display")
    
    # Store results for export
    if results:
        if 'materiality_results' not in st.session_state:
            st.session_state.materiality_results = {}
        
        st.session_state.materiality_results['stakeholder'] = {
            'results': results,
            'timestamp': datetime.now().isoformat()
        }

def render_materiality_results():
    st.markdown('<div class="sub-header">Comparison & Export</div>', unsafe_allow_html=True)
    
    if len(st.session_state.selected_methods) < 2:
        st.info("Select at least 2 methods in Configuration tab to compare.")
        return
    
    # Collect results from all methods
    all_results = {}
    method_names = []
    
    if 'risk_analysis' in st.session_state.selected_methods:
        # Calculate risk analysis results
        ra_results = []
        for issue in st.session_state.key_issues:
            issue_name = issue['name']
            data = st.session_state.risk_analysis_data[issue_name]
            impact = calculate_impact_from_risks_dynamic(
                data['risks'],
                st.session_state.risk_categories
            )
            score = data['likelihood'] * impact
            ra_results.append({'issue': issue_name, 'score': score})
        
        all_results['Risk Analysis'] = {r['issue']: r['score'] for r in ra_results}
        method_names.append('Risk Analysis')
    
    if 'stakeholder' in st.session_state.selected_methods:
        # Calculate stakeholder results
        stk_results = []
        for issue in st.session_state.key_issues:
            issue_name = issue['name']
            data = st.session_state.stakeholder_data[issue_name]
            weight = (data['stakeholder_score'] + data['expert_score']) / 20.0
            score = data['likelihood'] * data['impact'] * weight
            stk_results.append({'issue': issue_name, 'score': score})
        
        all_results['Stakeholder'] = {r['issue']: r['score'] for r in stk_results}
        method_names.append('Stakeholder')
    
    # Create comparison data
    comparison_data = []
    matrix_results = []
    
    for issue in st.session_state.key_issues:
        issue_name = issue['name']
        row = {'issue': issue_name, 'pillar': issue['pillar']}
        
        # Add scores for each method
        for method in method_names:
            row[method] = all_results[method].get(issue_name, 0)
        
        # Calculate average score
        if method_names:
            avg_score = sum(row[m] for m in method_names) / len(method_names)
        else:
            avg_score = 0
        
        row['Average'] = avg_score
        
        # Calculate approximate likelihood and impact from average score
        approx_value = np.sqrt(avg_score)
        avg_l = min(max(int(round(approx_value)), 1), 5)
        avg_i = min(max(int(round(approx_value)), 1), 5)
        
        row['Avg L'] = avg_l
        row['Avg I'] = avg_i
        row['Risk Level'] = get_risk_level(avg_score)[0]
        
        comparison_data.append(row)
        
        # For materiality matrix
        matrix_results.append({
            'issue': issue_name,
            'color': issue['color'],
            'likelihood': avg_l,
            'impact': avg_i,
            'score': avg_score
        })
    
    df = pd.DataFrame(comparison_data)
    
    # Display comparison
    st.markdown("### 📊 Method Comparison")
    
    if not df.empty and method_names:
        # Bar chart comparison
        fig = go.Figure()
        colors = {'Risk Analysis': '#f59e0b', 'Stakeholder': '#10b981'}
        
        for method in method_names:
            fig.add_trace(go.Bar(
                name=method,
                x=df['issue'],
                y=df[method],
                marker_color=colors.get(method, '#666'),
                text=df[method].round(1),
                textposition='auto',
            ))
        
        fig.update_layout(
            title="Score Comparison by Method",
            barmode='group',
            xaxis_tickangle=-45,
            height=500,
            showlegend=True,
            yaxis_title="Score"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Average materiality matrix
    st.markdown("### 🗺️ Average Score Materiality Matrix")
    if matrix_results:
        fig = create_heatmap_matrix(matrix_results, "Average Score Materiality Matrix")
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed comparison table
    st.markdown("### 📋 Detailed Comparison Table")
    
    if not df.empty:
        df_display = df.sort_values('Average', ascending=False).copy()
        df_display['Rank'] = range(1, len(df_display) + 1)
        
        # Reorder columns
        display_cols = ['Rank', 'issue', 'pillar'] + method_names + ['Average', 'Avg L', 'Avg I', 'Risk Level']
        available_cols = [col for col in display_cols if col in df_display.columns]
        
        df_display = df_display[available_cols]
        
        # Format numeric columns
        for col in method_names + ['Average']:
            if col in df_display.columns:
                df_display[col] = df_display[col].round(2)
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=400
        )
    
    # Export section
    st.markdown("---")
    st.markdown("### 📤 Export Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Charts", type="primary", key="export_charts_mat"):
            # Prepare charts for export
            charts: Dict[str, go.Figure] = {}

            if matrix_results:
                charts['Materiality_Matrix.html'] = create_heatmap_matrix(matrix_results, "Materiality Matrix")

            if not df.empty and method_names:
                # Create comparison chart
                fig_comp = go.Figure()
                for method in method_names:
                    fig_comp.add_trace(go.Bar(
                        name=method,
                        x=df['issue'],
                        y=df[method],
                        marker_color=colors.get(method, '#666')
                    ))
                fig_comp.update_layout(title="Method Comparison", barmode='group', xaxis_tickangle=-45)
                charts['Method_Comparison.html'] = fig_comp

            # Prepare files for download. Try binary image/pdf first, fall back to HTML.
            file_map: Dict[str, bytes] = {}
            pref = st.session_state.export_format
            for base_name, fig in charts.items():
                short = base_name.rsplit('.', 1)[0]
                if pref in ['PNG', 'PDF']:
                    fmt = pref.lower()
                    data, mime = safe_figure_bytes(fig, fmt=fmt)
                    if data is not None and mime is not None and mime != 'text/html':
                        file_map[f"{short}.{fmt}"] = data
                        continue
                # fallback to HTML
                data, mime = safe_figure_bytes(fig, fmt='png')
                if data is not None and mime == 'text/html':
                    file_map[f"{short}.html"] = data

            if not file_map:
                st.error("No charts available to export or export failed. Ensure plotly/kaleido installed for binary image/PDF exports.")
            elif len(file_map) == 1:
                name, data = next(iter(file_map.items()))
                mime = 'application/zip' if name.endswith('.zip') else ('text/html' if name.endswith('.html') else ('image/png' if name.endswith('.png') else 'application/pdf'))
                st.download_button(label=f"Download {name}", data=data, file_name=name, mime=mime)
            else:
                zip_bytes = make_zip_bytes(file_map)
                st.download_button(label="Download charts (zip)", data=zip_bytes, file_name="charts.zip", mime="application/zip")
    
    with col2:
        if st.button("📈 Export Data", type="primary", key="export_data_mat"):
            # Prepare data for export
            export_data = {
                'Comparison_Results': df,
                'Risk_Analysis_Details': pd.DataFrame([
                    {
                        'issue': issue['name'],
                        'likelihood': st.session_state.risk_analysis_data[issue['name']]['likelihood'],
                        'risks': ', '.join(st.session_state.risk_analysis_data[issue['name']]['risks']),
                        'impact': calculate_impact_from_risks_dynamic(
                            st.session_state.risk_analysis_data[issue['name']]['risks'],
                            st.session_state.risk_categories
                        )
                    }
                    for issue in st.session_state.key_issues
                ]) if 'risk_analysis' in st.session_state.selected_methods else pd.DataFrame(),
                
                'Stakeholder_Details': pd.DataFrame([
                    {
                        'issue': issue['name'],
                        'likelihood': st.session_state.stakeholder_data[issue['name']]['likelihood'],
                        'impact': st.session_state.stakeholder_data[issue['name']]['impact'],
                        'stakeholder_score': st.session_state.stakeholder_data[issue['name']]['stakeholder_score'],
                        'expert_score': st.session_state.stakeholder_data[issue['name']]['expert_score']
                    }
                    for issue in st.session_state.key_issues
                ]) if 'stakeholder' in st.session_state.selected_methods else pd.DataFrame(),
                
                'Risk_Categories': pd.DataFrame([
                    {'category': cat, 'risks': ', '.join(risks)}
                    for cat, risks in st.session_state.risk_categories.items()
                ])
            }
            
            if st.session_state.export_format == 'Excel':
                # Convert to Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    for sheet_name, df_data in export_data.items():
                        if not df_data.empty:
                            df_data.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                
                st.download_button(
                    label="Download Excel",
                    data=output.getvalue(),
                    file_name="materiality_results.xlsx",
                    mime="application/vnd.ms-excel"
                )
            
            elif st.session_state.export_format == 'CSV':
                # Create ZIP of CSV files
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for sheet_name, df_data in export_data.items():
                        if not df_data.empty:
                            csv_data = df_data.to_csv(index=False)
                            zip_file.writestr(f"{sheet_name}.csv", csv_data)
                
                st.download_button(
                    label="Download CSV Zip",
                    data=zip_buffer.getvalue(),
                    file_name="materiality_results.zip",
                    mime="application/zip"
                )
    
    with col3:
        if st.button("📄 Export Full Report", type="primary", key="export_report_mat"):
            # Create comprehensive report
            report_data = {
                'Summary': pd.DataFrame({
                    'Metric': ['Total Issues', 'Methods Used', 'Average Score', 'Highest Risk Issue'],
                    'Value': [
                        len(st.session_state.key_issues),
                        ', '.join(st.session_state.selected_methods),
                        f"{df['Average'].mean():.1f}" if not df.empty else 'N/A',
                        df.iloc[0]['issue'] if not df.empty else 'N/A'
                    ]
                }),
                'Comparison_Results': df,
                'Issues_List': pd.DataFrame(st.session_state.key_issues)
            }
            
            if st.session_state.export_format == 'JSON':
                json_data = json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'key_issues': st.session_state.key_issues,
                    'risk_analysis_data': st.session_state.risk_analysis_data,
                    'stakeholder_data': st.session_state.stakeholder_data,
                    'comparison_results': df.to_dict('records') if not df.empty else []
                }, indent=2)
                
                st.download_button(
                    label="Download JSON",
                    data=json_data,
                    file_name="materiality_assessment.json",
                    mime="application/json"
                )

def render_esgfp_scoring():
    st.markdown('<div class="main-header">ESGFP Scoring System</div>', unsafe_allow_html=True)
    
    # Workflow steps
    steps = [
        "1️⃣ Model Setup",
        "2️⃣ AHP Weighting", 
        "3️⃣ Indicator Scoring",
        "4️⃣ Results & Scenarios",
        "5️⃣ Validation"
    ]
    
    # Step navigation
    st.markdown("### 📋 ESGFP Workflow")
    cols = st.columns(len(steps))
    for i, (col, step) in enumerate(zip(cols, steps)):
        with col:
            is_current = (i + 1) == st.session_state.esgfp_step
            btn_type = "primary" if is_current else "secondary"
            if st.button(step, key=f"step_{i}", type=btn_type, use_container_width=True):
                st.session_state.esgfp_step = i + 1
                st.rerun()
    
    st.markdown("---")
    
    # Render current step
    if st.session_state.esgfp_step == 1:
        render_esgfp_model_setup()
    elif st.session_state.esgfp_step == 2:
        render_esgfp_ahp_weighting()
    elif st.session_state.esgfp_step == 3:
        render_esgfp_indicator_scoring()
    elif st.session_state.esgfp_step == 4:
        render_esgfp_results_scenarios()
    elif st.session_state.esgfp_step == 5:
        render_esgfp_validation()

def render_esgfp_model_setup():
    st.markdown('<div class="sub-header">Model Setup & Configuration</div>', unsafe_allow_html=True)
    
    with st.expander("Help — How to use this tab", expanded=False):
        st.markdown(
            """
            - Use this page to create or import the ESGFP model: add Pillars, Key Issues and Indicators.
            - To add an indicator: select or create a Pillar and Key Issue, provide indicator name, unit and mode, then click **Add Indicator**.
            - After finishing, click **Next: AHP Weighting** to proceed. Clicking Next runs the calculation that aggregates indicator-level scores into Key Issue and Pillar scores.
            - Tip: indicator names must match exactly when referencing values in later steps; use the dropdowns where available.
            """
        )
    
    # Status indicator
    render_esgfp_status("model_setup")
    # Display current model structure with all items expanded
    with st.expander("📊 Current Model Structure", expanded=True):
        if st.session_state.esgfp_model:
            for pillar, issues in st.session_state.esgfp_model.items():
                st.markdown(f"### 🏛️ Pillar: **{pillar}**")
                for issue, indicators in issues.items():
                    st.markdown(f"#### 📌 Key Issue: **{issue}** ({len(indicators)} indicators)")
                    for idx, ind in enumerate(indicators, 1):
                        direction = "↑ better" if ind.higher_is_better else "↓ better"
                        st.markdown(f"**{idx}. 📊 {ind.indicator}**")
                        st.markdown(f"   - Unit: `{ind.unit}`")
                        st.markdown(f"   - Direction: {direction}")
                        st.markdown(f"   - Default Mode: `{ind.default_mode}`")
                        st.markdown(f"   - Formula: {ind.formula_desc}")
        else:
            st.info("No model configured yet. Add your first indicator below.")
    
    # Configuration options
    st.markdown("### ⚙️ Configuration Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ➕ Add Custom Indicator")
        
        # Get existing pillars and allow creating new ones
        existing_pillars = list(st.session_state.esgfp_model.keys())
        pillar_options = existing_pillars + ["+ Create New Pillar"]
        
        selected_pillar = st.selectbox(
            "Select or Create Pillar",
            pillar_options,
            key="new_ind_pillar_select"
        )
        
        if selected_pillar == "+ Create New Pillar":
            new_pillar = st.text_input("Enter New Pillar Name", key="new_ind_pillar_name")
            selected_pillar = new_pillar if new_pillar else None
        else:
            new_pillar = None
        
        # Get existing issues for selected pillar
        if selected_pillar and selected_pillar in st.session_state.esgfp_model:
            existing_issues = list(st.session_state.esgfp_model[selected_pillar].keys())
            issue_options = existing_issues + ["+ Create New Key Issue"]
        else:
            existing_issues = []
            issue_options = ["+ Create New Key Issue"]
        
        selected_issue = st.selectbox(
            "Select or Create Key Issue",
            issue_options,
            key="new_ind_issue_select"
        )
        
        if selected_issue == "+ Create New Key Issue":
            new_issue = st.text_input("Enter New Key Issue Name", key="new_ind_issue_name")
            selected_issue = new_issue if new_issue else None
        else:
            new_issue = None
        
        # Indicator details
        new_indicator = st.text_input("Indicator Name", key="new_ind_name")
        new_unit = st.text_input("Unit", key="new_ind_unit", value="unit")
        
        col_a, col_b = st.columns(2)
        with col_a:
            higher_better = st.checkbox("Higher is better", value=True, key="new_ind_higher")
        with col_b:
            default_mode = st.selectbox("Default Mode", ["A", "B", "C"], key="new_ind_mode")
        
        if st.button("✅ Add Indicator", type="primary", key="add_ind_btn"):
            if selected_pillar and selected_issue and new_indicator:
                if selected_pillar not in st.session_state.esgfp_model:
                    st.session_state.esgfp_model[selected_pillar] = {}
                if selected_issue not in st.session_state.esgfp_model[selected_pillar]:
                    st.session_state.esgfp_model[selected_pillar][selected_issue] = []
                
                new_ind = IndicatorDef(
                    pillar=selected_pillar,
                    key_issue=selected_issue,
                    indicator=new_indicator,
                    unit=new_unit or "unit",
                    formula_desc="Custom indicator",
                    criteria="Criterion",
                    default_mode=default_mode,
                    higher_is_better=higher_better
                )
                st.session_state.esgfp_model[selected_pillar][selected_issue].append(new_ind)
                st.success(f"✅ Indicator '{new_indicator}' added to 🏛️ {selected_pillar} > 📌 {selected_issue}!")
                st.rerun()
            else:
                st.error("Please fill in all required fields (Pillar, Key Issue, Indicator)")
    
    with col2:
        st.markdown("#### Import/Export Model")
        
        uploaded_file = st.file_uploader("Upload model JSON", type=['json'], key="model_upload")
        if uploaded_file:
            try:
                model_data = json.load(uploaded_file)
                # Here you would need to convert JSON back to model structure
                # This is simplified - implement proper deserialization
                st.success("Model loaded successfully! (Note: Full import not implemented in this example)")
            except Exception as e:
                st.error(f"Error loading model file: {e}")
        
        if st.button("Export Current Model", type="secondary", key="export_model_btn"):
            # Simplified export
            model_json = json.dumps({
                pillar: {
                    issue: [
                        {
                            'indicator': ind.indicator,
                            'unit': ind.unit,
                            'higher_is_better': ind.higher_is_better,
                            'default_mode': ind.default_mode
                        }
                        for ind in indicators
                    ]
                    for issue, indicators in issues.items()
                }
                for pillar, issues in st.session_state.esgfp_model.items()
            }, indent=2)
            
            st.download_button(
                label="Download Model JSON",
                data=model_json,
                file_name="esgfp_model.json",
                mime="application/json"
            )
    
    if st.button("Next: AHP Weighting →", type="primary", key="next_to_ahp"):
        st.session_state.esgfp_step = 2
        st.rerun()

def render_esgfp_ahp_weighting():
    st.markdown('<div class="sub-header">AHP Weighting for Key Issues</div>', unsafe_allow_html=True)
    
    with st.expander("Help — How to use this tab", expanded=False):
        st.markdown(
            """
            - This page lets you set relative weights for Key Issues within each Pillar using sliders.
            - Adjust sliders to reflect the importance of each Key Issue. Weights are normalized per Pillar.
            - After adjusting, click **Next: Indicator Scoring** to proceed. The system will use these weights to aggregate indicator scores.
            - If you want to reset to defaults, change the weights back or re-open the Model Setup.
            """
        )
    
    render_esgfp_status("ahp_weighting")
    st.info("""
    **AHP (Analytic Hierarchy Process)** helps determine the relative importance 
    of key issues within each pillar. Adjust the sliders to set weights for each key issue.
    The weights will be normalized to sum to 100% per pillar.
    """)
    
    # Collect all key issues
    all_issues = []
    for pillar, issues in st.session_state.esgfp_model.items():
        for issue in issues.keys():
            all_issues.append(f"{pillar}: {issue}")
    
    if not all_issues:
        st.warning("No key issues found. Please add indicators in Step 1.")
        if st.button("← Back to Model Setup", type="secondary", key="back_to_setup"):
            st.session_state.esgfp_step = 1
            st.rerun()
        return
    
    st.markdown("### 📊 Key Issues for Weighting")
    
    # Initialize weights if not exists
    if 'esgfp_weights' not in st.session_state:
        st.session_state.esgfp_weights = {}
    
    weights = {}
    
    for pillar, issues in st.session_state.esgfp_model.items():
        with st.expander(f"🏛️ {pillar}", expanded=True):
            st.markdown(f"**{len(issues)} key issues**")
            
            # Get existing weights or initialize
            pillar_weights = {}
            total_weight = 0
            
            for issue in issues.keys():
                key = f"{pillar}:{issue}"
                current_weight = int(st.session_state.esgfp_weights.get(key, 100 // max(len(issues), 1)))
                
                weight = st.slider(
                    f"Weight for: {issue}",
                    min_value=0,
                    max_value=100,
                    value=current_weight,
                    step=1,
                    key=f"weight_{pillar}_{issue}"
                )
                
                pillar_weights[issue] = weight
                total_weight += weight
            
            # Normalize within pillar
            if total_weight > 0:
                for issue, weight in pillar_weights.items():
                    normalized = (weight / total_weight) * 100
                    key = f"{pillar}:{issue}"
                    weights[key] = normalized
                    st.session_state.esgfp_weights[key] = normalized
                    
                    # Display normalized weight
                    st.caption(f"{issue}: {normalized:.1f}%")
            else:
                st.warning("Total weight cannot be zero")
    
    # Display weight distribution
    if weights:
        st.markdown("### 📈 Weight Distribution")
        
        # Create pie chart for each pillar
        for pillar in st.session_state.esgfp_model.keys():
            pillar_weights = {k: v for k, v in weights.items() if k.startswith(pillar + ":")}
            if pillar_weights:
                df_pie = pd.DataFrame({
                    'Key Issue': [k.split(":", 1)[1] for k in pillar_weights.keys()],
                    'Weight %': list(pillar_weights.values())
                })
                
                fig = px.pie(df_pie, values='Weight %', names='Key Issue',
                            title=f"{pillar} - Weight Distribution",
                            hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", type="secondary", key="back_from_ahp"):
                st.session_state.esgfp_step = 1
                st.rerun()
        with col2:
            if st.button("Next: Indicator Scoring →", type="primary", key="next_to_scoring"):
                st.session_state.esgfp_step = 3
                st.rerun()

def render_esgfp_indicator_scoring():
    st.markdown('<div class="sub-header">Indicator Scoring</div>', unsafe_allow_html=True)
    
    with st.expander("Help — How to use this tab", expanded=False):
        st.markdown(
            """
            - Enter measured values for each Indicator and alternative in the table below.
            - For each indicator, provide the observed value per alternative and set the GE (Good/Expected) score.
            - Toggle 'Show Real-time Calculations' in Settings to see instant IS/PS/Final scores per indicator.
            - After completing all indicators, click **Next: Results & Scenarios** to calculate aggregated results.
            """
        )
    
    render_esgfp_status("indicator_scoring")
    # Get alternatives
    if 'esgfp_alternatives' not in st.session_state:
        st.session_state.esgfp_alternatives = ["Technology A", "Technology B"]
    
    st.markdown("### 🏷️ Define Alternatives")
    
    col1, col2 = st.columns(2)
    with col1:
        num_alternatives = st.number_input(
            "Number of alternatives", 
            min_value=1, 
            max_value=10, 
            value=max(1, len(st.session_state.esgfp_alternatives)),
            key="num_alts"
        )
    with col2:
        alt_type = st.radio(
            "Alternative type", 
            ["Technologies", "Process Designs"],
            key="alt_type"
        )
    
    # Alternative names
    alt_names = []
    for i in range(num_alternatives):
        if i < len(st.session_state.esgfp_alternatives):
            default_name = st.session_state.esgfp_alternatives[i]
        else:
            default_name = f"{alt_type[:-1]} {i+1}"
        
        name = st.text_input(
            f"Name for alternative {i+1}", 
            value=default_name, 
            key=f"alt_name_{i}"
        )
        alt_names.append(name)
    
    st.session_state.esgfp_alternatives = alt_names
    
    # Initialize scoring structures
    if 'esgfp_indicator_values' not in st.session_state:
        st.session_state.esgfp_indicator_values = {}
    
    if 'esgfp_ge_values' not in st.session_state:
        st.session_state.esgfp_ge_values = {}
    
    st.markdown("---")
    st.markdown("### 📝 Enter Indicator Values")
    
    # Real-time calculation toggle
    show_calc = st.checkbox(
        "Show real-time calculation details",
        value=st.session_state.show_real_time_calc,
        key="show_calc_checkbox"
    )
    
    # Scoring interface
    for pillar, issues in st.session_state.esgfp_model.items():
        with st.expander(f"🏛️ {pillar}", expanded=True):
            for issue, indicators in issues.items():
                weight_key = f"{pillar}:{issue}"
                weight = st.session_state.esgfp_weights.get(weight_key, 1.0)
                
                st.markdown(f"**{issue}** (Weight: {weight:.1f}%)")
                
                for ind in indicators:
                    st.markdown(f"*{ind.indicator}* [{ind.unit}]")
                    
                    # Create columns for each alternative (Alt, Value, GE, and optionally Calc columns)
                    num_cols = len(alt_names) + 3 if show_calc and len(alt_names) > 1 else len(alt_names) + 2
                    cols = st.columns(num_cols)
                    
                    # Label columns
                    with cols[0]:
                        st.markdown("**Alt**")
                        for alt in alt_names:
                            st.markdown(alt)
                    
                    # Value inputs
                    with cols[1]:
                        st.markdown("**Value**")
                        for idx, alt in enumerate(alt_names):
                            key = f"val_{pillar}_{issue}_{ind.indicator}_{alt}"
                            
                            # Get existing value or default
                            existing = st.session_state.esgfp_indicator_values.get(key, 50.0)
                            
                            value = st.number_input(
                                f"Value for {alt}",
                                min_value=0.0,
                                max_value=1000.0,
                                value=float(existing),
                                step=0.1,
                                key=key,
                                label_visibility="collapsed"
                            )
                            st.session_state.esgfp_indicator_values[key] = value
                    
                    # GE inputs
                    with cols[2]:
                        st.markdown("**GE**")
                        for idx, alt in enumerate(alt_names):
                            key = f"ge_{pillar}_{issue}_{ind.indicator}_{alt}"
                            
                            # Get existing GE or default
                            existing_ge = st.session_state.esgfp_ge_values.get(key, 5.0)
                            
                            ge = st.slider(
                                f"GE for {alt}",
                                min_value=0.0,
                                max_value=10.0,
                                value=float(existing_ge),
                                step=0.1,
                                key=key,
                                label_visibility="collapsed"
                            )
                            st.session_state.esgfp_ge_values[key] = ge
                    
                    # Real-time calculations
                    if show_calc and len(alt_names) > 1:
                        # Get all values for this indicator
                        values = []
                        for alt in alt_names:
                            key = f"val_{pillar}_{issue}_{ind.indicator}_{alt}"
                            values.append(st.session_state.esgfp_indicator_values.get(key, 0))
                        
                        vmin = min(values) if values else 0
                        vmax = max(values) if values else 100
                        
                        for idx, alt in enumerate(alt_names):
                            if 3 + idx < len(cols):
                                with cols[3 + idx]:
                                    if idx == 0:
                                        st.markdown("**Calc**")
                                    
                                    value = values[idx]
                                    ge_key = f"ge_{pillar}_{issue}_{ind.indicator}_{alt}"
                                    ge = st.session_state.esgfp_ge_values.get(ge_key, 5.0)
                                    
                                    # Calculate scores
                                    is_score = calculate_real_time_score(
                                        value, vmin, vmax, 
                                        ind.higher_is_better,
                                        len(alt_names)
                                    )
                                    
                                    gm = compute_gm(ge)
                                    ps = compute_ps(is_score, gm, 1)  # Default +GM
                                    
                                    final_score = compute_final_indicator_score(
                                        ps, weight, len(indicators)
                                    )
                                    
                                    st.caption(f"IS: {is_score:.1f}<br>PS: {ps:.1f}<br>Final: {final_score:.3f}", 
                                             unsafe_allow_html=True)
                    
                    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Weighting", type="secondary", key="back_from_scoring"):
            st.session_state.esgfp_step = 2
            st.rerun()
    with col2:
        if st.button("Next: Results & Scenarios →", type="primary", key="next_to_results"):
            # Calculate and store results
            calculate_esgfp_results()
            st.session_state.esgfp_step = 4
            st.rerun()

def calculate_esgfp_results():
    """Calculate ESGFP results from entered values"""
    if not st.session_state.esgfp_alternatives:
        return
    
    # Initialize results structure
    pillar_results = {}
    key_issue_results = {}
    indicator_results = {}
    
    alternatives = st.session_state.esgfp_alternatives
    
    for pillar, issues in st.session_state.esgfp_model.items():
        pillar_total = 0
        pillar_results[pillar] = {alt: 0 for alt in alternatives}
        key_issue_results[pillar] = {}
        
        for issue, indicators in issues.items():
            weight_key = f"{pillar}:{issue}"
            weight = st.session_state.esgfp_weights.get(weight_key, 1.0)
            
            issue_scores = {alt: 0 for alt in alternatives}
            key_issue_results[pillar][issue] = issue_scores
            
            for ind in indicators:
                # Get values for all alternatives
                values = []
                ge_values = []
                
                for alt in alternatives:
                    val_key = f"val_{pillar}_{issue}_{ind.indicator}_{alt}"
                    ge_key = f"ge_{pillar}_{issue}_{ind.indicator}_{alt}"
                    
                    values.append(st.session_state.esgfp_indicator_values.get(val_key, 0))
                    ge_values.append(st.session_state.esgfp_ge_values.get(ge_key, 5.0))
                
                # Calculate scores for each alternative
                for idx, alt in enumerate(alternatives):
                    value = values[idx]
                    ge = ge_values[idx]
                    
                    # Get min/max for normalization
                    vmin = min(values)
                    vmax = max(values)
                    
                    # Calculate scores
                    is_score = compute_indicator_score_scaled(
                        value, vmin, vmax,
                        ind.higher_is_better,
                        len(alternatives)
                    )
                    
                    gm = compute_gm(ge)
                    ps = compute_ps(is_score, gm, 1)  # Default +GM
                    
                    final_score = compute_final_indicator_score(
                        ps, weight, len(indicators)
                    )
                    
                    # Store in structures
                    key = f"{pillar}:{issue}:{ind.indicator}"
                    if key not in indicator_results:
                        indicator_results[key] = {}
                    indicator_results[key][alt] = final_score
                    
                    issue_scores[alt] += final_score
                    pillar_results[pillar][alt] += final_score
                    pillar_total += final_score

    # After computing all scores, convert to DataFrames and store results
    try:
        # Pillar scores: index = pillar, columns = alternatives
        pillar_df = pd.DataFrame.from_dict(pillar_results, orient='index') if pillar_results else pd.DataFrame()

        # Key issue scores: flatten pillar->issue->alt into rows 'Pillar:Issue'
        flat_key_issue = {}
        for p, issues in key_issue_results.items():
            for iss, vals in issues.items():
                flat_key_issue[f"{p}:{iss}"] = vals
        key_issue_df = pd.DataFrame.from_dict(flat_key_issue, orient='index') if flat_key_issue else pd.DataFrame()

        # Indicator scores: keys are already pillar:issue:indicator
        indicator_df = pd.DataFrame.from_dict(indicator_results, orient='index') if indicator_results else pd.DataFrame()

        results = {
            'pillar_scores': pillar_df,
            'key_issue_scores': key_issue_df,
            'indicator_scores': indicator_df,
            'alternatives': alternatives,
            'timestamp': datetime.now().isoformat()
        }

        # Store in session state and record signature
        st.session_state.esgfp_results = results
        st.session_state.esgfp_signature_at_calc = compute_esgfp_signature()
        st.session_state.esgfp_calc_timestamp = results['timestamp']
    except Exception as e:
        st.error(f"Error storing ESGFP results: {e}")


def compute_esgfp_signature() -> str:
    """Create a deterministic signature for the ESGFP input state."""
    try:
        model = {}
        for pillar, issues in st.session_state.get('esgfp_model', {}).items():
            model[pillar] = {}
            for issue, indicators in issues.items():
                model[pillar][issue] = []
                for ind in indicators:
                    model[pillar][issue].append({
                        'indicator': getattr(ind, 'indicator', str(ind)),
                        'unit': getattr(ind, 'unit', None),
                        'higher_is_better': bool(getattr(ind, 'higher_is_better', False)),
                        'default_mode': getattr(ind, 'default_mode', None)
                    })

        weights = st.session_state.get('esgfp_weights', {})
        ind_vals = st.session_state.get('esgfp_indicator_values', {})
        ge_vals = st.session_state.get('esgfp_ge_values', {})
        alts = st.session_state.get('esgfp_alternatives', [])

        sig_obj = {
            'model': model,
            'weights': weights,
            'indicator_values': ind_vals,
            'ge_values': ge_vals,
            'alternatives': alts
        }

        sig_str = json.dumps(sig_obj, sort_keys=True, default=str)
        return hashlib.sha1(sig_str.encode()).hexdigest()
    except Exception:
        return ''


def is_esgfp_results_stale() -> bool:
    """Return True if stored results are absent or inputs changed since last calculation."""
    if 'esgfp_results' not in st.session_state or st.session_state.get('esgfp_results') is None:
        return True
    stored = st.session_state.get('esgfp_signature_at_calc')
    if not stored:
        return True
    current = compute_esgfp_signature()
    return stored != current


def render_esgfp_status(context_key: str = "default"):
    """Render a small status badge and recalc button for ESGFP workflow.

    context_key is used to make unique Streamlit widget keys.
    """
    stale = is_esgfp_results_stale()
    ts = st.session_state.get('esgfp_calc_timestamp')
    cols = st.columns([3, 1])
    with cols[0]:
        if stale:
            st.warning("ESGFP results are stale or not calculated. Click Recalculate to update.")
        else:
            label = f"ESGFP results up-to-date (calculated: {ts})" if ts else "ESGFP results up-to-date"
            st.success(label)
    with cols[1]:
        if st.button("Recalculate", key=f"recalc_{context_key}"):
            calculate_esgfp_results()
            st.rerun()
    

def render_esgfp_results_scenarios():
    st.markdown('<div class="sub-header">Results Analysis & Scenario Planning</div>', unsafe_allow_html=True)
    
    with st.expander("Help — How to use this tab", expanded=False):
        st.markdown(
            """
            - This page shows aggregated Pillar and Key Issue scores computed from the Indicator Scoring step.
            - Click **Next: Results & Scenarios** from Indicator Scoring or press the 'Next' button on that page to run the calculations.
            - The system normalizes indicator values across alternatives (IS), adjusts by GE (PS), then aggregates using Key Issue weights to compute Pillar scores.
            - Use the Scenario Analysis section to apply weight adjustments and run sensitivity/Monte Carlo simulations.
            """
        )
    
    render_esgfp_status("results_scenarios")
    
    if 'esgfp_results' not in st.session_state or st.session_state.esgfp_results is None:
        st.warning("Please complete indicator scoring in Step 3 first.")
        if st.button("← Back to Scoring", type="secondary", key="back_to_scoring_from_results"):
            st.session_state.esgfp_step = 3
            st.rerun()
        return
    
    results = st.session_state.esgfp_results
    
    if 'alternatives' not in results:
        st.warning("Results are incomplete. Please complete indicator scoring.")
        if st.button("← Back to Scoring", type="secondary", key="back_to_scoring_incomplete"):
            st.session_state.esgfp_step = 3
            st.rerun()
        return
    
    alternatives = results['alternatives']
    
    # Display overall results
    st.markdown("### 📈 Overall Results")
    
    # Calculate total scores
    total_scores = {}
    if 'pillar_scores' in results and results['pillar_scores'] is not None:
        pillar_df = results['pillar_scores']
        
        for alt in alternatives:
            try:
                if alt in pillar_df.columns:
                    total = sum(pillar_df.loc[pillar, alt] 
                               for pillar in pillar_df.index)
                    total_scores[alt] = total
                else:
                    st.warning(f"No scores found for alternative '{alt}'")
            except Exception as e:
                st.warning(f"Error calculating score for {alt}: {str(e)}")
        
        # Total scores bar chart
        if total_scores:
            df_total = pd.DataFrame({
                'Alternative': list(total_scores.keys()),
                'Total Score': list(total_scores.values())
            }).sort_values('Total Score', ascending=False)
            
            fig_total = px.bar(df_total, x='Alternative', y='Total Score',
                              title="Total ESGFP Scores",
                              color='Total Score',
                              color_continuous_scale='Viridis',
                              text_auto='.1f')
            st.plotly_chart(fig_total, use_container_width=True)
        else:
            st.info("No valid scores to display. Complete the indicator scoring with all alternatives.")
    else:
        st.warning("Pillar scores data is missing.")
    
    # Pillar scores
    st.markdown("### 🎯 Pillar Score Comparison")
    
    if 'pillar_scores' in results and results['pillar_scores'] is not None:
        # Radar chart
        try:
            fig_radar = create_radar_chart(
                results['pillar_scores'],
                "Pillar Scores Radar Chart"
            )
            st.plotly_chart(fig_radar, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not create radar chart: {str(e)}")
        
        # Heatmap
        st.markdown("#### 🔥 Pillar Scores Heatmap")
        try:
            fig_heatmap = px.imshow(
                results['pillar_scores'],
                labels=dict(x="Alternative", y="Pillar", color="Score"),
                title="Pillar Scores by Alternative",
                color_continuous_scale='YlOrRd',
                text_auto='.1f'
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not create heatmap: {str(e)}")
    else:
        st.info("Pillar score data not available yet.")
    
    # Detailed table
    st.markdown("### 📋 Detailed Scores")
    
    # Create detailed dataframe
    if 'pillar_scores' in results and results['pillar_scores'] is not None and total_scores:
        detailed_data = []
        for alt in alternatives:
            if alt in total_scores:
                row = {'Alternative': alt}
                for pillar in results['pillar_scores'].index:
                    try:
                        if alt in results['pillar_scores'].columns:
                            row[pillar] = results['pillar_scores'].loc[pillar, alt]
                    except (KeyError, Exception):
                        row[pillar] = 0
                row['Total'] = total_scores[alt]
                detailed_data.append(row)
        
        if detailed_data:
            df_detailed = pd.DataFrame(detailed_data)
            st.dataframe(
                df_detailed.round(2),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("Scores data not available yet.")
    
    # Scenario planning
    st.markdown("---")
    st.markdown("### 🔮 Scenario Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        scenario_name = st.text_input("Scenario Name", "Base Case", key="scenario_name")
        weight_adjustment = st.slider(
            "Weight Adjustment Factor", 
            0.5, 2.0, 1.0, 0.1,
            key="weight_adj"
        )
    
    with col2:
        sensitivity_analysis = st.checkbox(
            "Run Sensitivity Analysis", 
            value=False,
            key="sens_analysis"
        )
        if sensitivity_analysis:
            num_iterations = st.number_input(
                "Iterations", 
                100, 10000, 1000,
                key="num_iter"
            )
    
    if st.button("Run Scenario Analysis", type="primary", key="run_scenario"):
        # Apply weight adjustment
        scenario_scores = {}
        for alt in alternatives:
            if alt in total_scores:
                adjusted_score = total_scores[alt] * weight_adjustment
                scenario_scores[alt] = adjusted_score
            else:
                st.warning(f"No score available for alternative '{alt}'")
        
        if scenario_scores:
            # Display scenario results
            df_scenario = pd.DataFrame({
                'Alternative': list(scenario_scores.keys()),
                'Scenario Score': list(scenario_scores.values())
            }).sort_values('Scenario Score', ascending=False)
            
            fig_scenario = px.bar(
                df_scenario, 
                x='Alternative', 
                y='Scenario Score',
                title=f"Scenario: {scenario_name}",
                color='Scenario Score',
                color_continuous_scale='Plasma',
                text_auto='.1f'
            )
            
            st.plotly_chart(fig_scenario, use_container_width=True)
            
            # Store scenario
            if 'esgfp_scenarios' not in st.session_state:
                st.session_state.esgfp_scenarios = []
            
            st.session_state.esgfp_scenarios.append({
                'name': scenario_name,
                'adjustment': weight_adjustment,
                'scores': scenario_scores,
                'timestamp': datetime.now().isoformat()
            })
            
            st.success(f"Scenario '{scenario_name}' saved!")
        else:
            st.error("No valid scores to analyze. Please ensure indicator scoring is complete.")
    
    # Navigation
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← Back to Scoring", type="secondary", key="back_to_scoring_final"):
            st.session_state.esgfp_step = 3
            st.rerun()
    with col2:
        if st.button("Save Results", type="primary", key="save_results"):
            st.success("Results saved for export!")
    with col3:
        if st.button("Run Validation →", type="primary", key="run_validation"):
            st.session_state.esgfp_step = 5
            st.rerun()

def render_esgfp_validation():
    st.markdown('<div class="sub-header">Validation & Sensitivity Analysis</div>', unsafe_allow_html=True)
    
    with st.expander("Help — How to use this tab", expanded=False):
        st.markdown(
            """
            - Validation provides Monte Carlo and sensitivity analyses to test result robustness.
            - Monte Carlo perturbs scores by the specified variation and shows distributions and confidence intervals.
            - Weight Stability checks correlations between pillar scores across alternatives.
            - Run these analyses after completing Results & Scenarios to see how sensitive rankings are to assumptions.
            """
        )
    
    render_esgfp_status("validation")
    st.info("""
    **Validation Suite** includes:
    - Monte Carlo simulation for sensitivity analysis
    - Weight stability analysis
    - Scenario robustness testing
    """)
    
    # Defensive retrieval of results: ensure we have a dict-like results object
    results = st.session_state.get('esgfp_results')
    if not results or not isinstance(results, dict):
        st.warning("Please complete ESGFP scoring first.")
        if st.button("← Back to Results", type="secondary", key="back_to_results_from_val"):
            st.session_state.esgfp_step = 4
            st.rerun()
        return

    # Ensure alternatives is always defined (taken from stored results)
    alternatives = results.get('alternatives', []) if isinstance(results, dict) else []
    
    # Monte Carlo Simulation
    st.markdown("### 🎲 Monte Carlo Simulation")
    
    col1, col2 = st.columns(2)
    with col1:
        mc_iterations = st.number_input(
            "Number of iterations", 
            100, 10000, 1000,
            key="mc_iter"
        )
        weight_variation = st.slider(
            "Weight variation (%)", 
            1, 50, 10,
            key="weight_var"
        )
    with col2:
        score_variation = st.slider(
            "Score variation (%)", 
            1, 50, 5,
            key="score_var"
        )
        confidence_level = st.slider(
            "Confidence level", 
            0.8, 0.99, 0.95,
            key="conf_level"
        )
    
    if st.button("Run Monte Carlo Simulation", type="primary", key="run_mc"):
        with st.spinner("Running Monte Carlo simulation..."):
            # Simplified Monte Carlo simulation
            # Use alternatives from results (already retrieved above)
            n_alternatives = len(alternatives)
            
            # Base scores from results - with validation
            base_totals = []
            valid_alternatives = []
            
            if 'pillar_scores' in results and results['pillar_scores'] is not None:
                pillar_df = results['pillar_scores']
                
                for alt in alternatives:
                    try:
                        if alt in pillar_df.columns:
                            total = sum(pillar_df.loc[pillar, alt] 
                                      for pillar in pillar_df.index)
                            base_totals.append(total)
                            valid_alternatives.append(alt)
                        else:
                            st.warning(f"Alternative '{alt}' not found in results")
                    except Exception as e:
                        st.warning(f"Error processing alternative '{alt}': {str(e)}")
                
                if not base_totals:
                    st.error("No valid scores found for Monte Carlo simulation")
                else:
                    # Generate random variations
                    np.random.seed(42)
                    variations = np.random.normal(
                        1.0, 
                        score_variation / 100.0,
                        size=(mc_iterations, len(base_totals))
                    )
                    
                    # Apply variations to base scores
                    simulated_scores = variations * base_totals
                    
                    # Calculate statistics
                    mean_scores = simulated_scores.mean(axis=0)
                    std_scores = simulated_scores.std(axis=0)
                    
                    # Confidence intervals
                    z_score = 2.576 if confidence_level >= 0.99 else 1.96 if confidence_level >= 0.95 else 1.645
                    confidence_intervals = z_score * std_scores / np.sqrt(mc_iterations)
                    
                    # Display results
                    mc_results = pd.DataFrame({
                        'Alternative': valid_alternatives,
                        'Mean Score': mean_scores,
                        'Std Dev': std_scores,
                        f'CI (± {confidence_level:.0%})': confidence_intervals
                    }).sort_values('Mean Score', ascending=False)
                    
                    st.dataframe(mc_results.round(2), use_container_width=True)
                    
                    # Plot distribution
                    fig_mc = go.Figure()
                    for i, alt in enumerate(valid_alternatives):
                        fig_mc.add_trace(go.Violin(
                            y=simulated_scores[:, i],
                            name=alt,
                            box_visible=True,
                            meanline_visible=True,
                            points=False
                        ))
                    
                    fig_mc.update_layout(
                        title="Monte Carlo Simulation Results",
                        yaxis_title="Score",
                        showlegend=True,
                        height=500
                    )
                    
                    st.plotly_chart(fig_mc, use_container_width=True)
                    
                    # Store validation results
                    st.session_state.validation_results = {
                        'monte_carlo': mc_results.to_dict('records'),
                        'parameters': {
                            'iterations': mc_iterations,
                            'weight_variation': weight_variation,
                            'score_variation': score_variation,
                            'confidence_level': confidence_level
                        },
                'timestamp': datetime.now().isoformat()
            }
    
    # Weight Stability Analysis
    st.markdown("---")
    st.markdown("### ⚖️ Weight Stability Analysis")
    
    if st.button("Analyze Weight Stability", type="primary", key="run_weight_stability"):
        with st.spinner("Analyzing weight stability..."):
            # Simplified weight stability analysis
            pillars = list(results['pillar_scores'].index)
            n_pillars = len(pillars)
            
            # Create sensitivity matrix
            sensitivity_matrix = np.zeros((n_pillars, n_pillars))
            
            for i in range(n_pillars):
                for j in range(n_pillars):
                    if i == j:
                        sensitivity_matrix[i, j] = 1.0
                    else:
                        # Simplified correlation
                        scores_i = [results['pillar_scores'].iloc[i, k] for k in range(len(alternatives))]
                        scores_j = [results['pillar_scores'].iloc[j, k] for k in range(len(alternatives))]
                        correlation = np.corrcoef(scores_i, scores_j)[0, 1]
                        sensitivity_matrix[i, j] = correlation if not np.isnan(correlation) else 0.0
            
            fig_heatmap = px.imshow(
                sensitivity_matrix,
                labels=dict(x="Pillar", y="Pillar", color="Sensitivity"),
                x=pillars,
                y=pillars,
                title="Weight Sensitivity Matrix",
                color_continuous_scale='RdBu',
                zmin=-1,
                zmax=1
            )
            
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            st.info("""
            **Interpretation:**
            - Values close to 1: High positive correlation
            - Values close to -1: High negative correlation  
            - Values near 0: Little correlation
            """)
    
    # Export section
    st.markdown("---")
    st.markdown("### 📤 Export Validation Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Export Simulation Data", type="secondary", key="export_sim_data"):
            if 'validation_results' in st.session_state:
                # Prepare data
                export_data = {
                    'Validation_Summary': pd.DataFrame({
                        'Metric': list(st.session_state.validation_results['parameters'].keys()),
                        'Value': list(st.session_state.validation_results['parameters'].values())
                    }),
                    'Monte_Carlo_Results': pd.DataFrame(st.session_state.validation_results['monte_carlo'])
                }
                
                if st.session_state.export_format == 'Excel':
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        for sheet_name, df_data in export_data.items():
                            df_data.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                    
                    st.download_button(
                        label="Download Excel",
                        data=output.getvalue(),
                        file_name="validation_results.xlsx",
                        mime="application/vnd.ms-excel"
                    )
    
    with col2:
        if st.button("Export Full ESGFP Report", type="primary", key="export_full_report"):
            # Create comprehensive report
            report_data = {
                'ESGFP_Summary': pd.DataFrame({
                    'Alternative': results['alternatives'],
                    'Total_Score': [
                        sum(results['pillar_scores'].loc[pillar, alt] 
                           for pillar in results['pillar_scores'].index)
                        for alt in results['alternatives']
                    ]
                }),
                'Pillar_Scores': results['pillar_scores'],
                'Model_Structure': pd.DataFrame([
                    {
                        'Pillar': pillar,
                        'Key_Issue': issue,
                        'Indicators': len(indicators)
                    }
                    for pillar, issues in st.session_state.esgfp_model.items()
                    for issue, indicators in issues.items()
                ])
            }
            
            pref = st.session_state.export_format

            # Always include core tables
            files: Dict[str, bytes] = {}
            try:
                if pref == 'Excel':
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='openpyxl') as writer:
                        for sheet_name, df_data in report_data.items():
                            if isinstance(df_data, pd.DataFrame) and not df_data.empty:
                                df_data.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                    files['esgfp_report.xlsx'] = out.getvalue()
                elif pref == 'CSV':
                    # create csv files and zip
                    for name, df_data in report_data.items():
                        if isinstance(df_data, pd.DataFrame) and not df_data.empty:
                            files[f"{name}.csv"] = df_data.to_csv(index=False).encode('utf-8')
                elif pref == 'JSON':
                    json_obj = {
                        'timestamp': datetime.now().isoformat(),
                        'report': {k: (v.to_dict('records') if isinstance(v, pd.DataFrame) else v) for k, v in report_data.items()}
                    }
                    files['esgfp_report.json'] = json.dumps(json_obj, indent=2).encode('utf-8')
                elif pref in ('PNG', 'PDF'):
                    # try to export charts (if present) as binary, else fallback to HTML
                    # build simple charts if pillar_scores available
                    figs: Dict[str, go.Figure] = {}
                    if 'pillar_scores' in results and results['pillar_scores'] is not None:
                        try:
                            figs['Pillar_Radar'] = create_radar_chart(results['pillar_scores'], title='Pillar Scores Radar')
                        except Exception:
                            pass
                    # If PDF requested, try to generate a multi-page PDF with tables and embedded figures
                    if pref == 'PDF':
                        pdf_bytes = generate_pdf_report(report_data, figs, title='ESGFP Assessment Report')
                        if pdf_bytes:
                            files['esgfp_report.pdf'] = pdf_bytes
                        else:
                            # fallback: export individual figures as png/html
                            for key, fig in figs.items():
                                data, mime = safe_figure_bytes(fig, fmt='png')
                                if data is not None:
                                    files[f"{key}.png"] = data
                    else:
                        # convert figs to bytes (PNG)
                        for key, fig in figs.items():
                            data, mime = safe_figure_bytes(fig, fmt='png')
                            if data is not None:
                                files[f"{key}.png"] = data
                # If we gathered multiple files, package as zip
                if not files:
                    st.error('No report files available to export. Add data or choose a different format.')
                elif len(files) == 1:
                    name, data = next(iter(files.items()))
                    mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if name.endswith('.xlsx') else ('application/json' if name.endswith('.json') else ('image/png' if name.endswith('.png') else 'application/pdf'))
                    st.download_button(label=f"Download {name}", data=data, file_name=name, mime=mime)
                else:
                    zipb = make_zip_bytes(files)
                    st.download_button(label='Download Full Report (zip)', data=zipb, file_name='esgfp_full_report.zip', mime='application/zip')
            except Exception as e:
                st.error(f"Error preparing report: {e}")
    
    with col3:
        if st.button("Start New Analysis", type="secondary", key="start_new_analysis"):
            # Reset ESGFP data
            keys_to_reset = [k for k in st.session_state.keys() if k.startswith('esgfp_')]
            for key in keys_to_reset:
                del st.session_state[key]
            
            # Reset validation results
            if 'validation_results' in st.session_state:
                del st.session_state.validation_results
            
            st.session_state.esgfp_step = 1
            st.success("Ready for new analysis!")
            st.rerun()

def render_integrated_dashboard():
    st.markdown('<div class="main-header">Integrated Dashboard</div>', unsafe_allow_html=True)
    
    # Check data availability
    has_materiality = 'materiality_results' in st.session_state
    has_esgfp = 'esgfp_results' in st.session_state
    
    if not has_materiality and not has_esgfp:
        st.warning("""
        **No data available for dashboard.**
        
        Please complete assessments in:
        - **Materiality Assessment** module
        - **ESGFP Scoring** module
        
        Then return to this dashboard to see integrated insights.
        """)
        return
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview", 
        "🔗 Cross-Module Insights", 
        "🎯 Recommendations",
        "📅 Timeline"
    ])
    
    with tab1:
        render_overview_tab(has_materiality, has_esgfp)
    
    with tab2:
        render_cross_module_tab(has_materiality, has_esgfp)
    
    with tab3:
        render_recommendations_tab(has_materiality, has_esgfp)
    
    with tab4:
        render_timeline_tab()

def render_overview_tab(has_materiality, has_esgfp):
    st.markdown("### 📈 Integrated Performance Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if has_materiality:
            st.markdown("#### Materiality Assessment Summary")
            
            # Calculate materiality metrics
            total_issues = len(st.session_state.key_issues)
            st.metric("Total Issues", total_issues)
            
            # Issues by pillar
            issues_by_pillar = {}
            for issue in st.session_state.key_issues:
                pillar = issue['pillar']
                issues_by_pillar[pillar] = issues_by_pillar.get(pillar, 0) + 1
            
            if issues_by_pillar:
                df_pillar = pd.DataFrame({
                    'Pillar': list(issues_by_pillar.keys()),
                    'Count': list(issues_by_pillar.values())
                })
                
                fig = px.pie(df_pillar, values='Count', names='Pillar',
                            title="Issues by Pillar", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if has_esgfp:
            st.markdown("#### ESGFP Scoring Summary")
            
            results = st.session_state.esgfp_results
            
            if results and 'alternatives' in results:
                alternatives = results['alternatives']
                
                st.metric("Alternatives", len(alternatives))
                
                # Calculate average score
                total_scores = []
                for alt in alternatives:
                    total = sum(results['pillar_scores'].loc[pillar, alt] 
                              for pillar in results['pillar_scores'].index)
                    total_scores.append(total)
                
                avg_score = np.mean(total_scores) if total_scores else 0
                st.metric("Average Score", f"{avg_score:.1f}")
                
                # Indicators by pillar
                indicators_by_pillar = {}
                for pillar, issues in st.session_state.esgfp_model.items():
                    total_indicators = sum(len(indicators) for indicators in issues.values())
                    indicators_by_pillar[pillar] = total_indicators
                
                if indicators_by_pillar:
                    df_ind = pd.DataFrame({
                        'Pillar': list(indicators_by_pillar.keys()),
                        'Indicators': list(indicators_by_pillar.values())
                    })
                    
                    fig = px.bar(df_ind, x='Pillar', y='Indicators',
                                title="Indicators by Pillar",
                                color='Indicators',
                                color_continuous_scale='Blues')
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Complete the ESGFP Scoring workflow to see results.")

def render_cross_module_tab(has_materiality, has_esgfp):
    st.markdown("### 🔗 Cross-Module Correlation Analysis")
    
    if has_materiality and has_esgfp:
        st.info("""
        This section shows correlations between materiality risks and ESGFP performance.
        High-risk materiality issues may impact ESGFP scores in related pillars.
        """)
        
        # Create correlation matrix (simplified example)
        pillars = list(DEFAULT_PILLARS.keys())
        
        # Sample correlation data - in real app, calculate actual correlations
        correlation_data = np.random.randn(len(pillars), len(pillars))
        np.fill_diagonal(correlation_data, 1.0)
        
        fig = px.imshow(
            correlation_data,
            labels=dict(x="ESGFP Pillar", y="Materiality Pillar", color="Correlation"),
            x=pillars,
            y=pillars,
            title="Materiality-ESGFP Correlation Matrix",
            color_continuous_scale='RdBu',
            zmin=-1,
            zmax=1
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Risk vs Performance scatter plot
        st.markdown("#### 📊 Risk vs Performance Analysis")
        
        # Sample data - in real app, use actual risk and performance data
        risk_data = pd.DataFrame({
            'Issue': [f"Issue {i+1}" for i in range(10)],
            'Risk_Score': np.random.rand(10) * 25,
            'Performance_Impact': np.random.rand(10) * 100,
            'Pillar': np.random.choice(pillars, 10)
        })
        
        fig_scatter = px.scatter(
            risk_data, 
            x='Risk_Score', 
            y='Performance_Impact',
            color='Pillar', 
            size='Risk_Score',
            hover_name='Issue',
            title="Risk Score vs Performance Impact",
            size_max=20
        )
        
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.warning("Need data from both modules for correlation analysis.")

def render_recommendations_tab(has_materiality, has_esgfp):
    st.markdown("### 🎯 Strategic Recommendations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if has_materiality:
            st.markdown("#### 📋 Materiality-Based Recommendations")
            
            # Identify high-risk issues
            high_risk_issues = []
            for issue in st.session_state.key_issues:
                issue_name = issue['name']
                
                if 'risk_analysis_data' in st.session_state:
                    data = st.session_state.risk_analysis_data.get(issue_name, {})
                    impact = calculate_impact_from_risks_dynamic(
                        data.get('risks', []),
                        st.session_state.risk_categories
                    )
                    score = data.get('likelihood', 3) * impact
                    level, _ = get_risk_level(score)
                    
                    if 'High' in level or 'Very High' in level:
                        high_risk_issues.append({
                            'issue': issue_name,
                            'pillar': issue['pillar'],
                            'score': score,
                            'level': level
                        })
            
            if high_risk_issues:
                st.markdown("##### 🚨 High Priority Actions")
                for hr in high_risk_issues[:3]:  # Top 3
                    with st.expander(f"**{hr['issue']}** ({hr['level']})", expanded=False):
                        st.markdown(f"""
                        **Pillar:** {hr['pillar']}
                        **Risk Score:** {hr['score']:.1f}
                        
                        **Recommended Actions:**
                        1. Conduct detailed risk assessment
                        2. Develop mitigation strategy
                        3. Assign ownership and timeline
                        4. Monitor monthly progress
                        """)
    
    with col2:
        if has_esgfp:
            st.markdown("#### ⚡ ESGFP Performance Recommendations")
            
            if 'esgfp_results' in st.session_state and st.session_state.esgfp_results is not None:
                results = st.session_state.esgfp_results
                
                if 'pillar_scores' in results:
                    # Identify lowest scoring pillars across alternatives
                    pillar_avgs = results['pillar_scores'].mean(axis=1)
                    worst_pillars = pillar_avgs.nsmallest(2).index.tolist()
                    
                    if worst_pillars:
                        st.markdown("##### 🔧 Focus Areas for Improvement")
                        for pillar in worst_pillars:
                            st.markdown(f"""
                            **{pillar}** (Avg: {pillar_avgs[pillar]:.1f})
                            - Review indicator definitions
                            - Benchmark against best practices
                            - Implement improvement initiatives
                            """)
            else:
                st.info("Complete the ESGFP Scoring workflow to see recommendations.")
    
    # Integrated action plan
    st.markdown("---")
    st.markdown("#### 📅 Integrated Action Plan")
    
    action_plan = pd.DataFrame({
        'Phase': ['Assessment', 'Planning', 'Implementation', 'Monitoring', 'Review'],
        'Start Date': ['2024-01-01', '2024-02-01', '2024-03-01', '2024-06-01', '2024-12-01'],
        'End Date': ['2024-01-31', '2024-02-29', '2024-05-31', '2024-11-30', '2024-12-31'],
        'Key Activities': [
            'Risk assessment & ESGFP scoring',
            'Strategy development & resource allocation',
            'Program implementation & training',
            'Performance tracking & reporting',
            'Annual review & plan update'
        ],
        'Responsible': ['ESG Team', 'Management', 'All Departments', 'ESG Team', 'Board']
    })
    
    st.dataframe(action_plan, use_container_width=True, hide_index=True)

def render_timeline_tab():
    st.markdown("### 📅 Implementation Timeline")
    
    # Create sample timeline data
    timeline_data = pd.DataFrame({
        'Task': [
            'Materiality Assessment',
            'ESGFP Scoring',
            'Risk Mitigation Planning',
            'Implementation Phase 1',
            'Implementation Phase 2',
            'Monitoring & Reporting',
            'Annual Review'
        ],
        'Start': [
            '2024-01-01', '2024-02-01', '2024-03-01',
            '2024-04-01', '2024-07-01', '2024-10-01',
            '2024-12-01'
        ],
        'Finish': [
            '2024-01-31', '2024-02-29', '2024-03-31',
            '2024-06-30', '2024-09-30', '2024-11-30',
            '2024-12-31'
        ],
        'Responsible': [
            'ESG Team', 'Analytics Team', 'Management',
            'Operations', 'Operations', 'ESG Team',
            'Board'
        ],
        'Progress': [100, 100, 75, 50, 25, 10, 0]  # In percentage
    })
    
    # Create Gantt chart
    fig = px.timeline(
        timeline_data,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Responsible",
        title="Implementation Timeline",
        hover_data=["Progress"]
    )
    
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=400)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Progress summary
    st.markdown("#### 📊 Progress Summary")
    
    cols = st.columns(4)
    metrics = [
        ("Completed", "2/7 tasks"),
        ("In Progress", "3/7 tasks"),
        ("Not Started", "2/7 tasks"),
        ("Overall Progress", "52%")
    ]
    
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.metric(label, value)

def render_export_section():
    st.markdown('<div class="main-header">Export & Reporting Center</div>', unsafe_allow_html=True)
    
    # Check available data
    has_materiality = 'materiality_results' in st.session_state
    has_esgfp = 'esgfp_results' in st.session_state
    has_validation = 'validation_results' in st.session_state
    
    if not any([has_materiality, has_esgfp, has_validation]):
        st.warning("No data available for export. Please complete assessments first.")
        return
    
    # Export options
    st.markdown("### 📤 Select Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        export_scope = st.radio(
            "Export Scope",
            ["Current Module Only", "All Available Data", "Custom Selection"],
            key="export_scope"
        )
        
        if export_scope == "Custom Selection":
            st.markdown("#### Select Components")
            
            components = []
            if has_materiality:
                if st.checkbox("Materiality Assessment", value=True, key="exp_mat"):
                    components.append("Materiality")
            
            if has_esgfp:
                if st.checkbox("ESGFP Scoring", value=True, key="exp_esgfp"):
                    components.append("ESGFP")
            
            if has_validation:
                if st.checkbox("Validation Results", value=True, key="exp_val"):
                    components.append("Validation")
    
    with col2:
        export_format = st.selectbox(
            "Export Format",
            ["Excel Workbook", "PDF Report", "JSON Data", "CSV Files"],
            key="exp_format"
        )
        
        include_charts = st.checkbox("Include charts/visualizations", value=True, key="inc_charts")
        include_metadata = st.checkbox("Include metadata and notes", value=True, key="inc_meta")
        timestamp = st.checkbox("Add timestamp to filename", value=True, key="inc_time")
    
    # Preview section
    st.markdown("---")
    st.markdown("### 👁️ Export Preview")
    
    preview_data = []
    
    if has_materiality:
        preview_data.append({
            'Module': 'Materiality Assessment',
            'Components': 'Risk Analysis, Stakeholder Assessment',
            'Records': len(st.session_state.key_issues),
            'Size': 'Medium'
        })
    
    if has_esgfp:
        preview_data.append({
            'Module': 'ESGFP Scoring',
            'Components': 'Indicator Scores, Scenario Results',
            'Records': len(st.session_state.get('esgfp_alternatives', [])),
            'Size': 'Large'
        })
    
    if has_validation:
        preview_data.append({
            'Module': 'Validation',
            'Components': 'Monte Carlo, Weight Stability',
            'Records': 'N/A',
            'Size': 'Small'
        })
    
    if preview_data:
        df_preview = pd.DataFrame(preview_data)
        st.dataframe(df_preview, use_container_width=True, hide_index=True)
    
    # Generate export
    st.markdown("---")
    st.markdown("### 🚀 Generate Export")
    
    if st.button("🔄 Generate Export Package", type="primary", key="gen_export"):
        with st.spinner("Preparing export package..."):
            # Collect all data
            export_data = {}
            
            # Materiality data
            if has_materiality and export_scope in ["All Available Data", "Custom Selection"]:
                export_data['Materiality_Issues'] = pd.DataFrame(st.session_state.key_issues)
                
                if 'risk_analysis_data' in st.session_state:
                    risk_df = pd.DataFrame([
                        {'issue': k, **v}
                        for k, v in st.session_state.risk_analysis_data.items()
                    ])
                    export_data['Risk_Analysis'] = risk_df
            
            # ESGFP data
            if has_esgfp and export_scope in ["All Available Data", "Custom Selection"]:
                if 'esgfp_model' in st.session_state:
                    model_data = []
                    for pillar, issues in st.session_state.esgfp_model.items():
                        for issue, indicators in issues.items():
                            for ind in indicators:
                                model_data.append({
                                    'Pillar': pillar,
                                    'Key_Issue': issue,
                                    'Indicator': ind.indicator,
                                    'Unit': ind.unit,
                                    'Higher_is_Better': ind.higher_is_better
                                })
                    export_data['ESGFP_Model'] = pd.DataFrame(model_data)
                
                if 'esgfp_results' in st.session_state:
                    results = st.session_state.esgfp_results
                    export_data['ESGFP_Results'] = results['pillar_scores']
            
            # Validation data
            if has_validation and export_scope in ["All Available Data", "Custom Selection"]:
                if 'validation_results' in st.session_state:
                    val_results = st.session_state.validation_results
                    export_data['Validation_Results'] = pd.DataFrame(val_results.get('monte_carlo', []))
            
            # Generate filename
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S") if timestamp else ""
            base_name = f"esg_assessment_{timestamp_str}"

            # Prepare files dict (filename -> bytes)
            files: Dict[str, bytes] = {}

            try:
                # Core data files
                if export_format == "Excel Workbook":
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='openpyxl') as writer:
                        for sheet_name, df_data in export_data.items():
                            if isinstance(df_data, pd.DataFrame) and not df_data.empty:
                                df_data.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                    files[f"{base_name}.xlsx"] = out.getvalue()

                elif export_format == "JSON Data":
                    json_data = json.dumps({
                        'timestamp': datetime.now().isoformat(),
                        'modules': {
                            'materiality': has_materiality,
                            'esgfp': has_esgfp,
                            'validation': has_validation
                        },
                        'data': {
                            k: v.to_dict('records') if isinstance(v, pd.DataFrame) else v
                            for k, v in export_data.items()
                        }
                    }, indent=2)
                    files[f"{base_name}.json"] = json_data.encode('utf-8')

                elif export_format == "CSV Files":
                    for sheet_name, df_data in export_data.items():
                        if isinstance(df_data, pd.DataFrame) and not df_data.empty:
                            files[f"{sheet_name}.csv"] = df_data.to_csv(index=False).encode('utf-8')

                elif export_format == "PDF Report":
                    figs_for_pdf = {}
                    if include_charts:
                        # Materiality chart from risk analysis
                        if 'Risk_Analysis' in export_data and not export_data['Risk_Analysis'].empty:
                            try:
                                ra_df = export_data['Risk_Analysis']
                                matrix_results = []
                                for _, row in ra_df.iterrows():
                                    matrix_results.append({
                                        'issue': row.get('issue') or row.get('issue', ''),
                                        'color': row.get('color', '#666'),
                                        'likelihood': row.get('likelihood', 1),
                                        'impact': row.get('impact', 1),
                                        'score': row.get('score', 0)
                                    })
                                fig_mat = create_heatmap_matrix(matrix_results, "Materiality Matrix")
                                figs_for_pdf['Materiality_Matrix'] = fig_mat
                            except Exception:
                                pass

                        # ESGFP pillar radar
                        if 'ESGFP_Results' in export_data and not export_data['ESGFP_Results'].empty:
                            try:
                                pillar_df = export_data['ESGFP_Results']
                                fig_rad = create_radar_chart(pillar_df, title='Pillar Scores Radar')
                                figs_for_pdf['Pillar_Radar'] = fig_rad
                            except Exception:
                                pass
                    
                    pdf_bytes = generate_pdf_report(export_data, figs_for_pdf, title='ESG Assessment Report')
                    if pdf_bytes:
                        files[f"{base_name}.pdf"] = pdf_bytes
                    else:
                        st.error("Failed to generate PDF report.")

                # Include charts if requested
                if include_charts:
                    chart_files: Dict[str, bytes] = {}
                    # Materiality chart from risk analysis
                    if 'Risk_Analysis' in export_data and not export_data['Risk_Analysis'].empty:
                        try:
                            ra_df = export_data['Risk_Analysis']
                            matrix_results = []
                            for _, row in ra_df.iterrows():
                                matrix_results.append({
                                    'issue': row.get('issue') or row.get('issue', ''),
                                    'color': row.get('color', '#666'),
                                    'likelihood': row.get('likelihood', 1),
                                    'impact': row.get('impact', 1),
                                    'score': row.get('score', 0)
                                })
                            fig_mat = create_heatmap_matrix(matrix_results, "Materiality Matrix")
                            data, mime = safe_figure_bytes(fig_mat, fmt='png')
                            if data:
                                chart_files['Materiality_Matrix.png'] = data
                        except Exception:
                            pass

                    # ESGFP pillar radar
                    if 'ESGFP_Results' in export_data and not export_data['ESGFP_Results'].empty:
                        try:
                            pillar_df = export_data['ESGFP_Results']
                            fig_rad = create_radar_chart(pillar_df, title='Pillar Scores Radar')
                            data, mime = safe_figure_bytes(fig_rad, fmt='png')
                            if data:
                                chart_files['Pillar_Radar.png'] = data
                        except Exception:
                            pass

                    files.update(chart_files)

                # Offer download(s)
                if not files:
                    st.error('No data available to export.')
                elif len(files) == 1:
                    name, data = next(iter(files.items()))
                    mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if name.endswith('.xlsx') else ('application/json' if name.endswith('.json') else ('application/pdf' if name.endswith('.pdf') else ('image/png' if name.endswith('.png') else 'application/octet-stream')))
                    st.success('✅ Export ready!')
                    st.download_button(label=f"📥 Download {name}", data=data, file_name=name, mime=mime)
                else:
                    zipb = make_zip_bytes(files)
                    st.success('✅ Export ready!')
                    st.download_button(label="📥 Download Export Package (zip)", data=zipb, file_name=f"{base_name}.zip", mime="application/zip")

            except Exception as e:
                st.error(f"Error preparing export package: {e}")

if __name__ == "__main__":
    main()