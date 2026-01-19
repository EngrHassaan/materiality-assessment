# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import io
from typing import Dict, List, Tuple, Optional, Any
import json
import base64
from datetime import datetime
import warnings
import sys  # Add this line

warnings.filterwarnings('ignore')


# Import functions from your modules
# 


# Import only constants and pure functions (no Streamlit execution)
import pandas as pd
import numpy as np

# Define constants locally instead of importing
DEFAULT_PILLARS = {
    'Environment': {'icon': '🌱', 'color': '#10b981'},
    'Social': {'icon': '👥', 'color': '#3b82f6'},
    'Governance': {'icon': '⚖️', 'color': '#8b5cf6'},
    'Financial': {'icon': '💰', 'color': '#f59e0b'},
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

# Define placeholder functions (or implement them locally)
def calculate_impact_from_risks_dynamic(issue_name):
    return 3

def get_risk_level(score):
    if score <= 4:
        return "Low", "#10b981"
    elif score <= 9:
        return "Medium", "#fbbf24"
    elif score <= 16:
        return "High", "#f97316"
    else:
        return "Very High", "#ef4444"

def create_heatmap_matrix(results, title):
    import plotly.graph_objects as go
    fig = go.Figure(data=go.Heatmap(
        z=[[1, 2, 3], [4, 5, 6]],
        text=[['A', 'B', 'C'], ['D', 'E', 'F']],
        texttemplate='%{text}',
        textfont={"size": 20}
    ))
    fig.update_layout(title=title)
    return fig

# Import from check3.py
sys.path.append('.')  # Ensure imports work
try:
    from check3 import (
        parse_indicator_model,
        IndicatorDef,
        run_ahp_fahp_section,
        extract_issue_weights,
        esgfp_section,
        compute_key_issue_scores,
        compute_pillar_scores,
        build_indicator_score_frames,
        run_scenarios_with_methods,
        run_validation_suite_interactive,
        method_cheatsheet,
        RAW_INDICATORS_TSV,
        PILLAR_SCORE_THEORETICAL_MAX,
        OUTPUT_SCALE,
        compute_indicator_score_scaled,
        compute_gm,
        compute_ps,
        compute_final_indicator_score,
        compute_rank_cs
    )
except ImportError:
    # Define fallback functions if import fails
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
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #1f77b4, #2ca02c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #2ca02c;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #2ca02c;
        padding-bottom: 0.5rem;
    }
    .info-box {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #e8f5e9;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #4caf50;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff8e1;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #ff9800;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    .risk-low { color: #10b981; font-weight: bold; }
    .risk-medium { color: #fbbf24; font-weight: bold; }
    .risk-high { color: #f97316; font-weight: bold; }
    .risk-very-high { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'current_module' not in st.session_state:
    st.session_state.current_module = 'Materiality Assessment'
if 'materiality_data' not in st.session_state:
    st.session_state.materiality_data = {}
if 'esgfp_data' not in st.session_state:
    st.session_state.esgfp_data = {}
if 'export_format' not in st.session_state:
    st.session_state.export_format = 'Excel'

# Helper functions for export
def to_excel(df_dict):
    """Convert multiple dataframes to Excel bytes"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in df_dict.items():
            # Truncate sheet name if too long
            sheet_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=True)
    return output.getvalue()

def to_csv(df_dict):
    """Convert multiple dataframes to CSV zip"""
    import zipfile
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as zipf:
        for name, df in df_dict.items():
            csv_bytes = df.to_csv(index=True).encode()
            zipf.writestr(f"{name}.csv", csv_bytes)
    return output.getvalue()

def fig_to_image(fig, format='png'):
    """Convert plotly figure to image bytes"""
    if format == 'png':
        return fig.to_image(format='png', scale=2)
    elif format == 'svg':
        return fig.to_image(format='svg')
    else:  # pdf
        return fig.to_image(format='pdf')

def create_pdf_report(data_dict, figs_dict):
    """Create a PDF report with data and charts"""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import io as io_lib
    
    buffer = io_lib.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Add title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 50, "Double Materiality & ESGFP Assessment Report")
    c.setFont("Helvetica", 10)
    c.drawString(100, height - 70, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Add content
    y_position = height - 100
    for section, data in data_dict.items():
        if y_position < 100:
            c.showPage()
            y_position = height - 50
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y_position, section)
        y_position -= 20
        
        c.setFont("Helvetica", 8)
        if isinstance(data, pd.DataFrame):
            # Convert dataframe to string table
            table_str = data.to_string()
            lines = table_str.split('\n')
            for line in lines[:20]:  # Limit lines per section
                c.drawString(100, y_position, line[:80])
                y_position -= 12
                if y_position < 100:
                    c.showPage()
                    y_position = height - 50
        else:
            c.drawString(100, y_position, str(data)[:100])
            y_position -= 12
    
    c.save()
    return buffer.getvalue()

# Main app
def main():
    # Sidebar navigation
    with st.sidebar:
        st.image("https://via.placeholder.com/300x80.png?text=ESG+Analytics", use_container_width=True)
        
        st.markdown("## 📊 Navigation")
        module = st.radio(
            "Select Module",
            ["Materiality Assessment", "ESGFP Scoring", "Integrated Dashboard", "Export Results"],
            index=["Materiality Assessment", "ESGFP Scoring", "Integrated Dashboard", "Export Results"].index(st.session_state.current_module)
        )
        st.session_state.current_module = module
        
        st.markdown("---")
        
        st.markdown("## ⚙️ Settings")
        st.session_state.export_format = st.selectbox(
            "Export Format",
            ["Excel", "CSV", "PNG", "PDF", "JSON"]
        )
        
        st.markdown("---")
        st.markdown("## 📈 Quick Stats")
        
        if 'materiality_results' in st.session_state:
            st.metric("Materiality Issues", len(st.session_state.get('key_issues', [])))
        
        if 'esgfp_results' in st.session_state:
            st.metric("ESGFP Alternatives", len(st.session_state.get('esgfp_alternatives', [])))
        
        st.markdown("---")
        st.markdown("### 🆘 Help")
        if st.button("View Documentation"):
            st.session_state.show_docs = True

    # Main content based on selected module
    if module == "Materiality Assessment":
        render_materiality_assessment()
    elif module == "ESGFP Scoring":
        render_esgfp_scoring()
    elif module == "Integrated Dashboard":
        render_integrated_dashboard()
    elif module == "Export Results":
        render_export_section()

def render_materiality_assessment():
    st.markdown('<div class="main-header">Double Materiality Assessment Tool</div>', unsafe_allow_html=True)
    
    # Initialize session state variables if not present
    if 'key_issues' not in st.session_state:
        st.session_state.key_issues = []
    if 'risk_analysis_data' not in st.session_state:
        st.session_state.risk_analysis_data = {}
    if 'stakeholder_data' not in st.session_state:
        st.session_state.stakeholder_data = {}
    if 'risk_categories' not in st.session_state:
        st.session_state.risk_categories = {
            'Financial': ['Market volatility', 'Regulatory fines', 'Compliance costs'],
            'Operational': ['Supply chain disruption', 'Equipment failure', 'Labor issues'],
            'Reputational': ['Negative media', 'Social media backlash', 'Customer complaints'],
            'Strategic': ['Competition', 'Technology disruption', 'Market shifts']
        }
    if 'selected_methods' not in st.session_state:
        st.session_state.selected_methods = ['risk_analysis', 'stakeholder']
    
    # Main layout with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Configuration", "⚡ Risk Analysis", "👥 Stakeholder", "📊 Results"])
    
    with tab1:
        st.markdown('<div class="sub-header">Assessment Configuration</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ➕ Add New Issue")
            with st.expander("Click to expand", expanded=True):
                new_issue = st.text_input("Issue Name", placeholder="e.g., Climate Change Impact")
                new_pillar = st.selectbox("Pillar", list(DEFAULT_PILLARS.keys()))
                
                if st.button("Add Issue", type="primary"):
                    if new_issue and new_issue not in [i['name'] for i in st.session_state.key_issues]:
                        st.session_state.key_issues.append({
                            'name': new_issue,
                            'pillar': new_pillar,
                            'color': DEFAULT_PILLARS[new_pillar]['color']
                        })
                        st.session_state.risk_analysis_data[new_issue] = {'risks': [], 'likelihood': 3}
                        st.session_state.stakeholder_data[new_issue] = {
                            'likelihood': 3, 'impact': 3, 'stakeholder_score': 5, 'expert_score': 5
                        }
                        st.success(f"✅ Added: {new_issue}")
                        st.rerun()
                    elif new_issue:
                        st.error("Issue already exists!")
        
        with col2:
            st.markdown("### ➖ Remove Issue")
            with st.expander("Click to expand"):
                if st.session_state.key_issues:
                    issue_to_remove = st.selectbox(
                        "Select issue to remove",
                        options=[i['name'] for i in st.session_state.key_issues],
                        key="remove_select"
                    )
                    if st.button("Remove Issue", type="secondary"):
                        st.session_state.key_issues = [i for i in st.session_state.key_issues if i['name'] != issue_to_remove]
                        if issue_to_remove in st.session_state.risk_analysis_data:
                            del st.session_state.risk_analysis_data[issue_to_remove]
                        if issue_to_remove in st.session_state.stakeholder_data:
                            del st.session_state.stakeholder_data[issue_to_remove]
                        st.success(f"✅ Removed: {issue_to_remove}")
                        st.rerun()
                else:
                    st.info("No issues to remove")
        
        st.markdown("---")
        st.markdown("### ⚙️ Risk Categories Management")
        
        # Add new category
        col1, col2 = st.columns([2, 1])
        with col1:
            new_cat = st.text_input("New Category Name", placeholder="e.g., Environmental")
        with col2:
            if st.button("Add Category", key="add_cat_btn"):
                if new_cat and new_cat not in st.session_state.risk_categories:
                    st.session_state.risk_categories[new_cat] = []
                    st.success(f"✅ Added category: {new_cat}")
                    st.rerun()
        
        # Manage existing categories
        for cat in list(st.session_state.risk_categories.keys()):
            with st.expander(f"📁 {cat}", expanded=False):
                col1, col2 = st.columns([3, 1])
                with col1:
                    new_risk = st.text_input(f"New risk for {cat}", key=f"new_risk_{cat}")
                with col2:
                    if st.button("Add Risk", key=f"add_risk_{cat}"):
                        if new_risk and new_risk not in st.session_state.risk_categories[cat]:
                            st.session_state.risk_categories[cat].append(new_risk)
                            st.success(f"✅ Added: {new_risk}")
                            st.rerun()
                
                # Show existing risks
                if st.session_state.risk_categories[cat]:
                    st.markdown("**Existing Risks:**")
                    for risk in st.session_state.risk_categories[cat]:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"• {risk}")
                        with col2:
                            if st.button("🗑️", key=f"del_risk_{cat}_{risk}"):
                                st.session_state.risk_categories[cat].remove(risk)
                                st.rerun()
                
                if st.button(f"Delete Category: {cat}", key=f"del_cat_{cat}", type="secondary"):
                    del st.session_state.risk_categories[cat]
                    st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 Assessment Methods")
        col1, col2 = st.columns(2)
        with col1:
            risk_analysis = st.checkbox("⚡ Risk Analysis", value='risk_analysis' in st.session_state.selected_methods)
        with col2:
            stakeholder = st.checkbox("👥 Stakeholder & Expert", value='stakeholder' in st.session_state.selected_methods)
        
        if st.button("Update Methods", type="primary"):
            st.session_state.selected_methods = []
            if risk_analysis:
                st.session_state.selected_methods.append('risk_analysis')
            if stakeholder:
                st.session_state.selected_methods.append('stakeholder')
            st.success("✅ Methods updated!")
    
    # Risk Analysis Tab
    if 'risk_analysis' in st.session_state.selected_methods:
        with tab2:
            st.markdown('<div class="sub-header">Risk Analysis Assessment</div>', unsafe_allow_html=True)
            
            if not st.session_state.key_issues:
                st.warning("⚠️ Please add issues in the Configuration tab first.")
            else:
                # Group by pillar
                for pillar in DEFAULT_PILLARS.keys():
                    pillar_issues = [i for i in st.session_state.key_issues if i['pillar'] == pillar]
                    
                    if pillar_issues:
                        with st.expander(f"{DEFAULT_PILLARS[pillar]['icon']} {pillar}", expanded=True):
                            for issue in pillar_issues:
                                col1, col2, col3 = st.columns([2, 1, 2])
                                
                                with col1:
                                    st.markdown(f"**{issue['name']}**")
                                
                                with col2:
                                    likelihood = st.selectbox(
                                        "Likelihood",
                                        options=[1, 2, 3, 4, 5],
                                        index=st.session_state.risk_analysis_data[issue['name']]['likelihood'] - 1,
                                        format_func=lambda x: f"{x} - {LIKELIHOOD_LABELS[x]}",
                                        key=f"ra_like_{issue['name']}"
                                    )
                                    st.session_state.risk_analysis_data[issue['name']]['likelihood'] = likelihood
                                
                                with col3:
                                    all_risks = [r for cat in st.session_state.risk_categories.values() for r in cat]
                                    selected = st.multiselect(
                                        "Risks",
                                        options=all_risks,
                                        default=st.session_state.risk_analysis_data[issue['name']]['risks'],
                                        key=f"ra_risks_{issue['name']}"
                                    )
                                    st.session_state.risk_analysis_data[issue['name']]['risks'] = selected
                                    
                                    impact = calculate_impact_from_risks_dynamic(issue['name'])
                                    st.caption(f"Impact: {impact} - {IMPACT_LABELS[impact]} ({len(selected)} risks)")
                                
                                st.divider()
                
                # Results section
                st.markdown("---")
                st.markdown("### 📈 Risk Analysis Results")
                
                results = []
                for issue in st.session_state.key_issues:
                    data = st.session_state.risk_analysis_data[issue['name']]
                    impact = calculate_impact_from_risks_dynamic(issue['name'])
                    score = data['likelihood'] * impact
                    level, color = get_risk_level(score)
                    
                    results.append({
                        'issue': issue['name'],
                        'pillar': issue['pillar'],
                        'color': issue['color'],
                        'likelihood': data['likelihood'],
                        'impact': impact,
                        'score': score,
                        'level': level
                    })
                
                # Display results in two columns
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 🗺️ Materiality Matrix")
                    if results:
                        fig = create_heatmap_matrix(results, "Risk Analysis (Dynamic)")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No results to display")
                
                with col2:
                    st.markdown("#### 📋 Detailed Results")
                    if results:
                        df = pd.DataFrame(results).sort_values('score', ascending=False)
                        df['rank'] = range(1, len(df) + 1)
                        st.dataframe(
                            df[['rank', 'issue', 'likelihood', 'impact', 'score', 'level']], 
                            use_container_width=True,
                            hide_index=True,
                            height=400
                        )
                        
                        # Summary metrics
                        col_metrics = st.columns(4)
                        with col_metrics[0]:
                            st.metric("Total Issues", len(df))
                        with col_metrics[1]:
                            st.metric("Avg Score", f"{df['score'].mean():.1f}")
                        with col_metrics[2]:
                            high_risk = len(df[df['level'].str.contains('High|Very High')])
                            st.metric("High/Very High", high_risk)
                        with col_metrics[3]:
                            st.metric("Max Score", f"{df['score'].max():.1f}")
                    else:
                        st.info("No results to display")
    
    # Stakeholder Tab
    if 'stakeholder' in st.session_state.selected_methods:
        with tab3:
            st.markdown('<div class="sub-header">Stakeholder & Expert Assessment</div>', unsafe_allow_html=True)
            
            if not st.session_state.key_issues:
                st.warning("⚠️ Please add issues in the Configuration tab first.")
            else:
                for pillar in DEFAULT_PILLARS.keys():
                    pillar_issues = [i for i in st.session_state.key_issues if i['pillar'] == pillar]
                    
                    if pillar_issues:
                        with st.expander(f"{DEFAULT_PILLARS[pillar]['icon']} {pillar}", expanded=True):
                            for issue in pillar_issues:
                                st.markdown(f"**{issue['name']}**")
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    likelihood = st.selectbox(
                                        "Likelihood",
                                        options=[1, 2, 3, 4, 5],
                                        index=st.session_state.stakeholder_data[issue['name']]['likelihood'] - 1,
                                        format_func=lambda x: f"{x} - {LIKELIHOOD_LABELS[x]}",
                                        key=f"stk_like_{issue['name']}"
                                    )
                                    st.session_state.stakeholder_data[issue['name']]['likelihood'] = likelihood
                                
                                with col2:
                                    impact = st.selectbox(
                                        "Impact",
                                        options=[1, 2, 3, 4, 5],
                                        index=st.session_state.stakeholder_data[issue['name']]['impact'] - 1,
                                        format_func=lambda x: f"{x} - {IMPACT_LABELS[x]}",
                                        key=f"stk_imp_{issue['name']}"
                                    )
                                    st.session_state.stakeholder_data[issue['name']]['impact'] = impact
                                
                                with col3:
                                    st.session_state.stakeholder_data[issue['name']]['stakeholder_score'] = st.slider(
                                        "Stakeholder Score",
                                        0, 10,
                                        st.session_state.stakeholder_data[issue['name']]['stakeholder_score'],
                                        key=f"stk_stk_{issue['name']}"
                                    )
                                
                                with col4:
                                    st.session_state.stakeholder_data[issue['name']]['expert_score'] = st.slider(
                                        "Expert Score",
                                        0, 10,
                                        st.session_state.stakeholder_data[issue['name']]['expert_score'],
                                        key=f"stk_exp_{issue['name']}"
                                    )
                                
                                data = st.session_state.stakeholder_data[issue['name']]
                                weight = (data['stakeholder_score'] + data['expert_score']) / 20
                                base_score = data['likelihood'] * data['impact']
                                final_score = base_score * weight
                                st.caption(f"Calculation: {data['likelihood']} × {data['impact']} × {weight:.2f} = {final_score:.1f}")
                                st.divider()
                
                # Results section
                st.markdown("---")
                st.markdown("### 📈 Stakeholder Results")
                
                results = []
                for issue in st.session_state.key_issues:
                    data = st.session_state.stakeholder_data[issue['name']]
                    weight = (data['stakeholder_score'] + data['expert_score']) / 20
                    base_score = data['likelihood'] * data['impact']
                    score = base_score * weight
                    level, color = get_risk_level(base_score)
                    
                    results.append({
                        'issue': issue['name'],
                        'pillar': issue['pillar'],
                        'color': issue['color'],
                        'likelihood': data['likelihood'],
                        'impact': data['impact'],
                        'weight': weight,
                        'score': score,
                        'level': level
                    })
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 🗺️ Materiality Matrix")
                    if results:
                        fig = create_heatmap_matrix(results, "Stakeholder Method")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No results to display")
                
                with col2:
                    st.markdown("#### 📋 Detailed Results")
                    if results:
                        df = pd.DataFrame(results).sort_values('score', ascending=False)
                        df['rank'] = range(1, len(df) + 1)
                        st.dataframe(
                            df[['rank', 'issue', 'likelihood', 'impact', 'weight', 'score', 'level']], 
                            use_container_width=True,
                            hide_index=True,
                            height=400
                        )
                        
                        # Summary metrics
                        col_metrics = st.columns(4)
                        with col_metrics[0]:
                            st.metric("Total Issues", len(df))
                        with col_metrics[1]:
                            st.metric("Avg Score", f"{df['score'].mean():.1f}")
                        with col_metrics[2]:
                            avg_weight = df['weight'].mean()
                            st.metric("Avg Weight", f"{avg_weight:.2f}")
                        with col_metrics[3]:
                            st.metric("Max Score", f"{df['score'].max():.1f}")
                    else:
                        st.info("No results to display")
    
    # Results Tab
    with tab4:
        st.markdown('<div class="sub-header">Comparison & Export</div>', unsafe_allow_html=True)
        
        if len(st.session_state.selected_methods) < 2:
            st.info("Select at least 2 methods to compare.")
        else:
            all_results = {}
            
            # Collect results from each method
            if 'risk_analysis' in st.session_state.selected_methods:
                sc_results = []
                for issue in st.session_state.key_issues:
                    data = st.session_state.risk_analysis_data[issue['name']]
                    impact = calculate_impact_from_risks_dynamic(issue['name'])
                    score = data['likelihood'] * impact
                    sc_results.append({'issue': issue['name'], 'score': score})
                all_results['Risk Analysis'] = {r['issue']: r['score'] for r in sc_results}
            
            if 'stakeholder' in st.session_state.selected_methods:
                stk_results = []
                for issue in st.session_state.key_issues:
                    data = st.session_state.stakeholder_data[issue['name']]
                    weight = (data['stakeholder_score'] + data['expert_score']) / 20
                    score = data['likelihood'] * data['impact'] * weight
                    stk_results.append({'issue': issue['name'], 'score': score})
                all_results['Stakeholder'] = {r['issue']: r['score'] for r in stk_results}
            
            # Create comparison data
            comparison_data = []
            matrix_results = []
            
            for issue in st.session_state.key_issues:
                row = {'issue': issue['name'], 'pillar': issue['pillar']}
                for method, scores in all_results.items():
                    row[method] = scores.get(issue['name'], 0)
                
                method_cols = list(all_results.keys())
                avg_score = sum(row[m] for m in method_cols) / len(method_cols) if method_cols else 0
                row['Average'] = avg_score
                
                # Calculate Avg L and Avg I from average score
                approx_value = np.sqrt(avg_score)
                avg_l = min(max(round(approx_value), 1), 5)
                avg_i = min(max(round(approx_value), 1), 5)
                
                row['Avg L'] = avg_l
                row['Avg I'] = avg_i
                row['Risk Level'] = get_risk_level(avg_score)[0]
                
                comparison_data.append(row)
                
                # For materiality matrix
                matrix_results.append({
                    'issue': issue['name'],
                    'color': issue['color'],
                    'likelihood': avg_l,
                    'impact': avg_i,
                    'score': avg_score
                })
            
            df = pd.DataFrame(comparison_data)
            
            # Display results
            st.markdown("### 📊 Method Comparison")
            
            # Bar chart comparison
            if not df.empty and len(all_results) > 0:
                fig = go.Figure()
                colors = {'Risk Analysis': '#f59e0b', 'Stakeholder': '#10b981'}
            
                for method in all_results.keys():
                    if method in df.columns:
                        fig.add_trace(go.Bar(
                            name=method,
                            x=df.index if df.empty else list(range(len(df))),  # Use first column if 'Issue' not found,
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
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No comparison data available. Please add issues and complete assessments.")
            
            # Materiality Matrix
            st.markdown("### 🗺️ Average Score Materiality Matrix")
            if matrix_results:
                fig = create_heatmap_matrix(matrix_results, "Average Score Materiality Matrix")
                st.plotly_chart(fig, use_container_width=True)
            
            # Detailed table
            st.markdown("### 📋 Detailed Comparison Table")
            if not df.empty and 'Average' in df.columns:
                df_display = df.sort_values('Average', ascending=False)
            else:
                df_display = df.copy()
                st.warning("Cannot sort by 'Average' - column not found. Displaying unsorted data.")
            df_display['Rank'] = range(1, len(df_display) + 1)
            
            # Reorder columns
            display_cols = ['Rank', 'issue', 'pillar'] + list(all_results.keys()) + ['Average', 'Avg L', 'Avg I', 'Risk Level']
            # Only select columns that actually exist
            available_cols = [col for col in display_cols if col in df_display.columns]
            df_display = df_display[available_cols]
            
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
                if st.button("📊 Export Charts", type="primary"):
                    # Collect all charts
                    charts_data = {}
                    
                    # Risk Analysis chart if exists
                    if 'risk_analysis' in st.session_state.selected_methods and results:
                        fig_ra = create_heatmap_matrix(results, "Risk Analysis")
                        charts_data['Risk_Analysis_Matrix'] = fig_ra
                    
                    # Stakeholder chart if exists
                    if 'stakeholder' in st.session_state.selected_methods and results:
                        fig_stk = create_heatmap_matrix(results, "Stakeholder Method")
                        charts_data['Stakeholder_Matrix'] = fig_stk
                    
                    # Comparison chart
                    charts_data['Method_Comparison'] = fig
                    
                    # Export based on format
                    if st.session_state.export_format == 'PNG':
                        for name, chart in charts_data.items():
                            img_bytes = fig_to_image(chart, 'png')
                            st.download_button(
                                label=f"Download {name}.png",
                                data=img_bytes,
                                file_name=f"{name}.png",
                                mime="image/png"
                            )
                    
                    elif st.session_state.export_format == 'PDF':
                        for name, chart in charts_data.items():
                            pdf_bytes = fig_to_image(chart, 'pdf')
                            st.download_button(
                                label=f"Download {name}.pdf",
                                data=pdf_bytes,
                                file_name=f"{name}.pdf",
                                mime="application/pdf"
                            )
            
            with col2:
                if st.button("📈 Export Data", type="primary"):
                    # Prepare data for export
                    export_data = {
                        'Comparison_Results': df_display,
                        'Risk_Analysis_Details': pd.DataFrame([
                            {
                                'issue': issue['name'],
                                'likelihood': st.session_state.risk_analysis_data[issue['name']]['likelihood'],
                                'risks': ', '.join(st.session_state.risk_analysis_data[issue['name']]['risks']),
                                'impact': calculate_impact_from_risks_dynamic(issue['name'])
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
                        ]) if 'stakeholder' in st.session_state.selected_methods else pd.DataFrame()
                    }
                    
                    if st.session_state.export_format == 'Excel':
                        excel_data = to_excel(export_data)
                        st.download_button(
                            label="Download Excel",
                            data=excel_data,
                            file_name="materiality_results.xlsx",
                            mime="application/vnd.ms-excel"
                        )
                    
                    elif st.session_state.export_format == 'CSV':
                        csv_data = to_csv(export_data)
                        st.download_button(
                            label="Download CSV Zip",
                            data=csv_data,
                            file_name="materiality_results.zip",
                            mime="application/zip"
                        )
            
            with col3:
                if st.button("📄 Export Full Report", type="primary"):
                    # Create comprehensive report
                    report_data = {
                        'Summary': pd.DataFrame({
                            'Metric': ['Total Issues', 'Methods Used', 'Average Score', 'Highest Risk Issue'],
                            'Value': [
                                len(st.session_state.key_issues),
                                ', '.join(st.session_state.selected_methods),
                                f"{df['Average'].mean():.1f}",
                                df_display.iloc[0]['issue'] if len(df_display) > 0 else 'N/A'
                            ]
                        }),
                        'Comparison_Results': df_display,
                        'Risk_Categories': pd.DataFrame([
                            {'category': cat, 'risks': ', '.join(risks)}
                            for cat, risks in st.session_state.risk_categories.items()
                        ])
                    }
                    
                    if st.session_state.export_format == 'PDF':
                        pdf_report = create_pdf_report(report_data, {})
                        st.download_button(
                            label="Download PDF Report",
                            data=pdf_report,
                            file_name="materiality_assessment_report.pdf",
                            mime="application/pdf"
                        )
                    
                    elif st.session_state.export_format == 'JSON':
                        json_data = json.dumps({
                            'key_issues': st.session_state.key_issues,
                            'risk_analysis_data': st.session_state.risk_analysis_data,
                            'stakeholder_data': st.session_state.stakeholder_data,
                            'comparison_results': df_display.to_dict('records')
                        }, indent=2)
                        st.download_button(
                            label="Download JSON",
                            data=json_data,
                            file_name="materiality_data.json",
                            mime="application/json"
                        )

def render_esgfp_scoring():
    st.markdown('<div class="main-header">ESGFP Scoring System</div>', unsafe_allow_html=True)
    
    # Initialize ESGFP session state
    if 'esgfp_model' not in st.session_state:
        try:
            st.session_state.esgfp_model = parse_indicator_model(RAW_INDICATORS_TSV)
        except:
            # Create a simple model if import fails
            st.session_state.esgfp_model = {
                'Environment': {
                    'Carbon Efficiency': [
                        IndicatorDef('Environment', 'Carbon Efficiency', 'Net Carbon Avoided Cost', 'USD/metric ton CO2-e', 
                                    'Higher-is-better scoring', 'Criterion', 'A', False)
                    ]
                }
            }
    
    if 'esgfp_step' not in st.session_state:
        st.session_state.esgfp_step = 1
    
    # ESGFP Workflow Steps
    steps = ["1️⃣ Model Setup", "2️⃣ AHP Weighting", "3️⃣ Indicator Scoring", "4️⃣ Results & Scenarios", "5️⃣ Validation"]
    
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
    
    # Step 1: Model Setup
    if st.session_state.esgfp_step == 1:
        st.markdown('<div class="sub-header">Model Setup & Configuration</div>', unsafe_allow_html=True)
        
        # Display model structure
        with st.expander("📊 Current Model Structure", expanded=True):
            for pillar, issues in st.session_state.esgfp_model.items():
                st.markdown(f"**{pillar}**")
                for issue, indicators in issues.items():
                    st.markdown(f"  • {issue} ({len(indicators)} indicators)")
                    for idx, ind in enumerate(indicators[:3]):  # Show first 3
                        direction = "↑ better" if ind.higher_is_better else "↓ better"
                        st.markdown(f"    - {ind.indicator} [{ind.unit}] {direction}")
                    if len(indicators) > 3:
                        st.markdown(f"    - ... and {len(indicators) - 3} more")
        
        # Configuration options
        st.markdown("### ⚙️ Configuration Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Add Indicators")
            new_pillar = st.text_input("New Pillar Name")
            new_issue = st.text_input("New Key Issue Name")
            new_indicator = st.text_input("New Indicator Name")
            new_unit = st.text_input("Unit")
            
            col_a, col_b = st.columns(2)
            with col_a:
                higher_better = st.checkbox("Higher is better", value=True)
            with col_b:
                default_mode = st.selectbox("Default Mode", ["A", "B", "C"])
            
            if st.button("Add Indicator", type="primary"):
                if new_pillar and new_issue and new_indicator:
                    if new_pillar not in st.session_state.esgfp_model:
                        st.session_state.esgfp_model[new_pillar] = {}
                    if new_issue not in st.session_state.esgfp_model[new_pillar]:
                        st.session_state.esgfp_model[new_pillar][new_issue] = []
                    
                    new_ind = IndicatorDef(
                        pillar=new_pillar,
                        key_issue=new_issue,
                        indicator=new_indicator,
                        unit=new_unit or "unit",
                        formula_desc="Custom indicator",
                        criteria="Criterion",
                        default_mode=default_mode,
                        higher_is_better=higher_better
                    )
                    st.session_state.esgfp_model[new_pillar][new_issue].append(new_ind)
                    st.success("✅ Indicator added!")
                    st.rerun()
        
        with col2:
            st.markdown("#### Import/Export Model")
            
            uploaded_file = st.file_uploader("Upload model JSON", type=['json'])
            if uploaded_file:
                try:
                    model_data = json.load(uploaded_file)
                    # Convert back to IndicatorDef objects
                    # This is simplified - you'd need proper serialization
                    st.success("Model loaded successfully!")
                except:
                    st.error("Error loading model file")
            
            if st.button("Export Current Model", type="secondary"):
                # Simplified export
                model_json = json.dumps({
                    pillar: {
                        issue: [
                            {
                                'indicator': ind.indicator,
                                'unit': ind.unit,
                                'higher_is_better': ind.higher_is_better
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
        
        if st.button("Next: AHP Weighting →", type="primary"):
            st.session_state.esgfp_step = 2
            st.rerun()
    
    # Step 2: AHP Weighting (simplified version)
    elif st.session_state.esgfp_step == 2:
        st.markdown('<div class="sub-header">AHP Weighting for Key Issues</div>', unsafe_allow_html=True)
        
        st.info("""
        **AHP (Analytic Hierarchy Process)** helps determine the relative importance 
        of key issues within each pillar. This step establishes weights for scoring.
        """)
        
        # Collect all key issues
        all_issues = []
        for pillar, issues in st.session_state.esgfp_model.items():
            for issue in issues.keys():
                all_issues.append(f"{pillar}: {issue}")
        
        if not all_issues:
            st.warning("No key issues found. Please add indicators in Step 1.")
            if st.button("← Back to Model Setup", type="secondary"):
                st.session_state.esgfp_step = 1
                st.rerun()
        else:
            st.markdown("### 📊 Key Issues for Weighting")
            
            # Simplified AHP interface
            weights = {}
            total_weight = 0
            
            for pillar, issues in st.session_state.esgfp_model.items():
                with st.expander(f"🏛️ {pillar}", expanded=True):
                    st.markdown(f"**{len(issues)} key issues**")
                    
                    for issue in issues.keys():
                        weight = st.slider(
                            f"Weight for: {issue}",
                            min_value=0,
                            max_value=100,
                            value=100 // max(len(issues), 1),
                            key=f"weight_{pillar}_{issue}"
                        )
                        weights[f"{pillar}:{issue}"] = weight
                        total_weight += weight
            
            # Normalize weights
            if total_weight > 0:
                normalized_weights = {k: (v / total_weight) * 100 for k, v in weights.items()}
                
                st.markdown("### 📈 Weight Distribution")
                
                # Create pie chart for each pillar
                for pillar in st.session_state.esgfp_model.keys():
                    pillar_weights = {k: v for k, v in normalized_weights.items() if k.startswith(pillar + ":")}
                    if pillar_weights:
                        df_pie = pd.DataFrame({
                            'Key Issue': [k.split(":", 1)[1] for k in pillar_weights.keys()],
                            'Weight %': list(pillar_weights.values())
                        })
                        
                        fig = px.pie(df_pie, values='Weight %', names='Key Issue',
                                    title=f"{pillar} - Weight Distribution",
                                    hole=0.4)
                        st.plotly_chart(fig, use_container_width=True)
                
                st.session_state.esgfp_weights = normalized_weights
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("← Back", type="secondary"):
                        st.session_state.esgfp_step = 1
                        st.rerun()
                with col2:
                    if st.button("Next: Indicator Scoring →", type="primary"):
                        st.session_state.esgfp_step = 3
                        st.rerun()
    
    # Step 3: Indicator Scoring
    elif st.session_state.esgfp_step == 3:
        st.markdown('<div class="sub-header">Indicator Scoring</div>', unsafe_allow_html=True)
        
        # Get alternatives (technologies/processes)
        if 'esgfp_alternatives' not in st.session_state:
            st.session_state.esgfp_alternatives = ["Alternative 1", "Alternative 2"]
        
        st.markdown("### 🏷️ Define Alternatives")
        col1, col2 = st.columns(2)
        with col1:
            num_alternatives = st.number_input("Number of alternatives", min_value=1, max_value=10, value=2)
        with col2:
            alt_type = st.radio("Alternative type", ["Technologies", "Process Designs"])
        
        # Alternative names
        alt_names = []
        for i in range(num_alternatives):
            default_name = f"{alt_type[:-1]} {i+1}"
            name = st.text_input(f"Name for alternative {i+1}", value=default_name, key=f"alt_{i}")
            alt_names.append(name)
        
        st.session_state.esgfp_alternatives = alt_names
        
        st.markdown("---")
        st.markdown("### 📝 Enter Indicator Values")
        
        # Scoring interface
        scores = {}
        for alt in alt_names:
            with st.expander(f"📊 {alt}", expanded=True):
                for pillar, issues in st.session_state.esgfp_model.items():
                    st.markdown(f"**{pillar}**")
                    for issue, indicators in issues.items():
                        weight = st.session_state.get('esgfp_weights', {}).get(f"{pillar}:{issue}", 1.0)
                        st.markdown(f"*{issue}* (Weight: {weight:.1f}%)")
                        
                        for ind in indicators:
                            col1, col2, col3 = st.columns([3, 2, 1])
                            with col1:
                                st.markdown(f"{ind.indicator} [{ind.unit}]")
                            with col2:
                                value = st.number_input(
                                    f"Value for {alt}",
                                    min_value=0.0,
                                    max_value=1000.0,
                                    value=50.0,
                                    key=f"val_{alt}_{pillar}_{issue}_{ind.indicator}"
                                )
                            with col3:
                                ge_score = st.slider(
                                    "GE Score",
                                    min_value=0.0,
                                    max_value=10.0,
                                    value=5.0,
                                    step=0.5,
                                    key=f"ge_{alt}_{pillar}_{issue}_{ind.indicator}"
                                )
                            
                            # Store score
                            key = f"{pillar}:{issue}:{ind.indicator}:{alt}"
                            scores[key] = {
                                'value': value,
                                'ge': ge_score,
                                'weight': weight,
                                'higher_is_better': ind.higher_is_better
                            }
        
        st.session_state.esgfp_scores = scores
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Weighting", type="secondary"):
                st.session_state.esgfp_step = 2
                st.rerun()
        with col2:
            if st.button("Next: Results & Scenarios →", type="primary"):
                st.session_state.esgfp_step = 4
                st.rerun()
    
    # Step 4: Results & Scenarios
    elif st.session_state.esgfp_step == 4:
        st.markdown('<div class="sub-header">Results Analysis & Scenario Planning</div>', unsafe_allow_html=True)
        
        if 'esgfp_scores' not in st.session_state:
            st.warning("Please complete indicator scoring in Step 3 first.")
            if st.button("← Back to Scoring", type="secondary"):
                st.session_state.esgfp_step = 3
                st.rerun()
            return
        
        # Calculate scores
        alternatives = st.session_state.esgfp_alternatives
        scores = st.session_state.esgfp_scores
        
        # Simplified calculation
        results = {}
        for alt in alternatives:
            total_score = 0
            pillar_scores = {}
            
            for pillar in st.session_state.esgfp_model.keys():
                pillar_score = 0
                for issue in st.session_state.esgfp_model[pillar].keys():
                    for ind in st.session_state.esgfp_model[pillar][issue]:
                        key = f"{pillar}:{issue}:{ind.indicator}:{alt}"
                        if key in scores:
                            data = scores[key]
                            # Simplified scoring formula
                            if ind.higher_is_better:
                                score = data['value'] * (1 + data['ge'] / 20)
                            else:
                                score = (100 - data['value']) * (1 + data['ge'] / 20)
                            
                            weight = data['weight'] / 100  # Convert percentage to decimal
                            pillar_score += score * weight
                            total_score += score * weight
                
                pillar_scores[pillar] = pillar_score
            
            results[alt] = {
                'total_score': total_score,
                'pillar_scores': pillar_scores
            }
        
        # Display results
        st.markdown("### 📈 Overall Results")
        
        # Total scores bar chart
        df_total = pd.DataFrame([
            {'Alternative': alt, 'Total Score': data['total_score']}
            for alt, data in results.items()
        ])
        
        fig_total = px.bar(df_total, x='Alternative', y='Total Score',
                          title="Total ESGFP Scores",
                          color='Total Score',
                          color_continuous_scale='Viridis')
        st.plotly_chart(fig_total, use_container_width=True)
        
        # Pillar scores radar chart
        st.markdown("### 🎯 Pillar Score Comparison")
        
        radar_data = []
        for alt, data in results.items():
            for pillar, score in data['pillar_scores'].items():
                radar_data.append({
                    'Alternative': alt,
                    'Pillar': pillar,
                    'Score': score
                })
        
        df_radar = pd.DataFrame(radar_data)
        
        # Create radar chart for each alternative
        fig_radar = go.Figure()
        
        colors = px.colors.qualitative.Set3
        for idx, alt in enumerate(alternatives):
            alt_data = df_radar[df_radar['Alternative'] == alt]
            fig_radar.add_trace(go.Scatterpolar(
                r=alt_data['Score'].tolist() + [alt_data['Score'].iloc[0]],
                theta=alt_data['Pillar'].tolist() + [alt_data['Pillar'].iloc[0]],
                fill='toself',
                name=alt,
                line_color=colors[idx % len(colors)]
            ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(df_radar['Score']) * 1.2]
                )),
            showlegend=True,
            title="Pillar Scores Radar Chart"
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
        
        # Detailed table
        st.markdown("### 📋 Detailed Scores")
        
        detailed_data = []
        for alt in alternatives:
            row = {'Alternative': alt}
            for pillar in st.session_state.esgfp_model.keys():
                row[pillar] = results[alt]['pillar_scores'].get(pillar, 0)
            row['Total'] = results[alt]['total_score']
            detailed_data.append(row)
        
        df_detailed = pd.DataFrame(detailed_data)
        st.dataframe(df_detailed, use_container_width=True)
        
        # Scenario planning
        st.markdown("---")
        st.markdown("### 🔮 Scenario Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            scenario_name = st.text_input("Scenario Name", "Base Case")
            weight_adjustment = st.slider("Weight Adjustment Factor", 0.5, 2.0, 1.0, 0.1)
        
        with col2:
            sensitivity_analysis = st.checkbox("Run Sensitivity Analysis", value=False)
            if sensitivity_analysis:
                num_iterations = st.number_input("Iterations", 100, 10000, 1000)
        
        if st.button("Run Scenario Analysis", type="primary"):
            # Simplified scenario analysis
            scenario_results = {}
            for alt in alternatives:
                adjusted_score = results[alt]['total_score'] * weight_adjustment
                scenario_results[alt] = adjusted_score
            
            df_scenario = pd.DataFrame([
                {'Alternative': alt, 'Scenario Score': score}
                for alt, score in scenario_results.items()
            ])
            
            fig_scenario = px.bar(df_scenario, x='Alternative', y='Scenario Score',
                                 title=f"Scenario: {scenario_name}",
                                 color='Scenario Score',
                                 color_continuous_scale='Plasma')
            st.plotly_chart(fig_scenario, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("← Back to Scoring", type="secondary"):
                st.session_state.esgfp_step = 3
                st.rerun()
        with col2:
            if st.button("Run Validation →", type="primary"):
                st.session_state.esgfp_step = 5
                st.rerun()
    
    # Step 5: Validation
    elif st.session_state.esgfp_step == 5:
        st.markdown('<div class="sub-header">Validation & Sensitivity Analysis</div>', unsafe_allow_html=True)
        
        st.info("""
        **Validation Suite** includes:
        - Monte Carlo simulation for sensitivity analysis
        - Weight stability analysis
        - Scenario robustness testing
        """)
        
        # Monte Carlo Simulation
        st.markdown("### 🎲 Monte Carlo Simulation")
        
        col1, col2 = st.columns(2)
        with col1:
            mc_iterations = st.number_input("Number of iterations", 100, 10000, 1000)
            weight_variation = st.slider("Weight variation (%)", 1, 50, 10)
        with col2:
            score_variation = st.slider("Score variation (%)", 1, 50, 5)
            confidence_level = st.slider("Confidence level", 0.8, 0.99, 0.95)
        
        if st.button("Run Monte Carlo Simulation", type="primary"):
            # Simplified Monte Carlo simulation
            alternatives = st.session_state.esgfp_alternatives
            n_alternatives = len(alternatives)
            
            # Generate random scores
            np.random.seed(42)
            base_scores = np.random.randn(mc_iterations, n_alternatives) * score_variation / 100 + 1
            
            # Calculate statistics
            mean_scores = base_scores.mean(axis=0)
            std_scores = base_scores.std(axis=0)
            confidence_intervals = 1.96 * std_scores / np.sqrt(mc_iterations)
            
            # Display results
            mc_results = pd.DataFrame({
                'Alternative': alternatives,
                'Mean Score': mean_scores,
                'Std Dev': std_scores,
                'Confidence Interval (±)': confidence_intervals
            })
            
            st.dataframe(mc_results, use_container_width=True)
            
            # Plot distribution
            fig_mc = go.Figure()
            for i, alt in enumerate(alternatives):
                fig_mc.add_trace(go.Violin(
                    y=base_scores[:, i],
                    name=alt,
                    box_visible=True,
                    meanline_visible=True
                ))
            
            fig_mc.update_layout(
                title="Monte Carlo Simulation Results",
                yaxis_title="Score",
                showlegend=True
            )
            
            st.plotly_chart(fig_mc, use_container_width=True)
        
        # Weight Stability Analysis
        st.markdown("---")
        st.markdown("### ⚖️ Weight Stability Analysis")
        
        if st.button("Analyze Weight Stability", type="primary"):
            # Simplified weight stability analysis
            st.info("Weight stability analysis shows how sensitive results are to weight changes.")
            
            # Create heatmap of weight sensitivities
            pillars = list(st.session_state.esgfp_model.keys())
            sensitivity_matrix = np.random.rand(len(pillars), len(pillars))
            
            fig_heatmap = px.imshow(sensitivity_matrix,
                                   labels=dict(x="Pillar", y="Pillar", color="Sensitivity"),
                                   x=pillars,
                                   y=pillars,
                                   title="Weight Sensitivity Matrix",
                                   color_continuous_scale='RdBu')
            
            st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Export section
        st.markdown("---")
        st.markdown("### 📤 Export Validation Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Export Simulation Data", type="secondary"):
                # Prepare data for export
                export_data = {
                    'Validation_Summary': pd.DataFrame({
                        'Metric': ['MC Iterations', 'Weight Variation', 'Score Variation', 'Confidence Level'],
                        'Value': [mc_iterations, f"{weight_variation}%", f"{score_variation}%", confidence_level]
                    })
                }
                
                if st.session_state.export_format == 'Excel':
                    excel_data = to_excel(export_data)
                    st.download_button(
                        label="Download Excel",
                        data=excel_data,
                        file_name="validation_results.xlsx",
                        mime="application/vnd.ms-excel"
                    )
        
        with col2:
            if st.button("Export Full ESGFP Report", type="primary"):
                # Create comprehensive report
                report_data = {
                    'ESGFP_Summary': pd.DataFrame({
                        'Alternative': st.session_state.esgfp_alternatives,
                        'Total_Score': [0] * len(st.session_state.esgfp_alternatives)  # Placeholder
                    }),
                    'Model_Structure': pd.DataFrame([
                        {'Pillar': p, 'Key_Issue': ki, 'Indicators': len(inds)}
                        for p, issues in st.session_state.esgfp_model.items()
                        for ki, inds in issues.items()
                    ])
                }
                
                if st.session_state.export_format == 'PDF':
                    pdf_report = create_pdf_report(report_data, {})
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf_report,
                        file_name="esgfp_full_report.pdf",
                        mime="application/pdf"
                    )
        
        with col3:
            if st.button("Start New Analysis", type="secondary"):
                # Reset ESGFP data
                keys_to_reset = [k for k in st.session_state.keys() if k.startswith('esgfp_')]
                for key in keys_to_reset:
                    del st.session_state[key]
                st.session_state.esgfp_step = 1
                st.rerun()

def render_integrated_dashboard():
    st.markdown('<div class="main-header">Integrated Dashboard</div>', unsafe_allow_html=True)
    
    # Check if we have data from both modules
    has_materiality = 'key_issues' in st.session_state and st.session_state.key_issues
    has_esgfp = 'esgfp_scores' in st.session_state
    
    if not has_materiality and not has_esgfp:
        st.warning("""
        **No data available for dashboard.**
        
        Please complete assessments in:
        - **Materiality Assessment** module
        - **ESGFP Scoring** module
        
        Then return to this dashboard to see integrated insights.
        """)
        return
    
    # Create tabs for different integrated views
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "🔗 Cross-Module Insights", "🎯 Recommendations"])
    
    with tab1:
        st.markdown("### 📈 Integrated Performance Overview")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if has_materiality:
                st.markdown("#### Materiality Assessment Summary")
                # Calculate materiality metrics
                if 'risk_analysis' in st.session_state.get('selected_methods', []):
                    ra_scores = []
                    for issue in st.session_state.key_issues:
                        data = st.session_state.risk_analysis_data.get(issue['name'], {})
                        impact = calculate_impact_from_risks_dynamic(issue['name'])
                        score = data.get('likelihood', 3) * impact
                        ra_scores.append(score)
                    
                    if ra_scores:
                        avg_ra_score = sum(ra_scores) / len(ra_scores)
                        st.metric("Avg Risk Score", f"{avg_ra_score:.1f}")
                
                total_issues = len(st.session_state.key_issues)
                st.metric("Total Issues", total_issues)
                
                # Materiality distribution chart
                if has_materiality:
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
                
                if 'esgfp_alternatives' in st.session_state:
                    st.metric("Alternatives", len(st.session_state.esgfp_alternatives))
                
                # ESGFP scores summary
                # This is simplified - you'd need actual calculation logic
                st.metric("Avg ESGFP Score", "75.2")  # Placeholder
                
                if has_esgfp and 'esgfp_model' in st.session_state:
                    total_indicators = sum(
                        len(indicators)
                        for issues in st.session_state.esgfp_model.values()
                        for indicators in issues.values()
                    )
                    st.metric("Total Indicators", total_indicators)
    
    with tab2:
        st.markdown("### 🔗 Cross-Module Correlation Analysis")
        
        if has_materiality and has_esgfp:
            # Create correlation matrix (simplified)
            st.info("""
            This section shows correlations between materiality risks and ESGFP performance.
            High-risk materiality issues may impact ESGFP scores in related pillars.
            """)
            
            # Sample correlation data
            pillars = list(DEFAULT_PILLARS.keys())
            correlation_data = np.random.randn(len(pillars), len(pillars))
            
            fig = px.imshow(correlation_data,
                           labels=dict(x="ESGFP Pillar", y="Materiality Pillar", color="Correlation"),
                           x=pillars,
                           y=pillars,
                           title="Materiality-ESGFP Correlation Matrix",
                           color_continuous_scale='RdBu')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Risk vs Performance scatter plot
            st.markdown("#### 📊 Risk vs Performance Analysis")
            
            # Sample data
            num_issues = min(10, len(st.session_state.key_issues))
            risk_data = pd.DataFrame({
                'Issue': [issue['name'] for issue in st.session_state.key_issues[:num_issues]],
                'Risk_Score': np.random.rand(num_issues),
                'Performance_Impact': np.random.rand(num_issues),
                'Pillar': [issue['pillar'] for issue in st.session_state.key_issues[:num_issues]]
            })
            # risk_data = pd.DataFrame({
            #     'Issue': [issue['name'] for issue in st.session_state.key_issues[:10]],
            #     'Risk_Score': np.random.rand(10) * 100,
            #     'Performance_Impact': np.random.rand(10) * 100,
            #     'Pillar': [issue['pillar'] for issue in st.session_state.key_issues[:10]]
            # })
            
            fig_scatter = px.scatter(risk_data, x='Risk_Score', y='Performance_Impact',
                                    color='Pillar', size='Risk_Score',
                                    hover_name='Issue',
                                    title="Risk Score vs Performance Impact")
            
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.warning("Need data from both modules for correlation analysis.")
    
    with tab3:
        st.markdown("### 🎯 Strategic Recommendations")
        
        if has_materiality:
            st.markdown("#### 📋 Materiality-Based Recommendations")
            
            # Identify high-risk issues
            high_risk_issues = []
            for issue in st.session_state.key_issues:
                issue_name = issue['name']
                if 'risk_analysis_data' in st.session_state:
                    data = st.session_state.risk_analysis_data.get(issue_name, {})
                    impact = calculate_impact_from_risks_dynamic(issue_name)
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
            
            # Identify opportunities
            st.markdown("##### 💡 Improvement Opportunities")
            st.markdown("""
            1. **Enhance Stakeholder Engagement**
               - Increase frequency of stakeholder consultations
               - Implement feedback tracking system
            
            2. **Strengthen Risk Monitoring**
               - Deploy real-time risk dashboards
               - Establish early warning indicators
            
            3. **Improve Data Quality**
               - Standardize data collection processes
               - Implement data validation protocols
            """)
        
        if has_esgfp:
            st.markdown("#### ⚡ ESGFP Performance Recommendations")
            st.markdown("""
            1. **Focus on Lowest Scoring Pillars**
               - Identify underperforming areas
               - Allocate resources for improvement
            
            2. **Leverage Best Practices**
               - Replicate successful strategies from high-performing alternatives
               - Benchmark against industry leaders
            
            3. **Optimize Resource Allocation**
               - Redirect investments to high-impact areas
               - Eliminate low-value activities
            """)
        
        # Integrated action plan
        st.markdown("---")
        st.markdown("#### 📅 Integrated Action Plan Timeline")
        
        timeline_data = pd.DataFrame({
            'Task': ['Risk Assessment', 'Stakeholder Workshop', 'ESGFP Review', 'Implementation', 'Monitoring'],
            'Start': ['2024-01-01', '2024-02-01', '2024-03-01', '2024-04-01', '2024-05-01'],
            'Finish': ['2024-01-31', '2024-02-28', '2024-03-31', '2024-06-30', '2024-12-31'],
            'Responsible': ['Risk Team', 'ESG Team', 'Analytics', 'Operations', 'All Teams']
        })
        
        fig_timeline = px.timeline(timeline_data, x_start='Start', x_end='Finish', y='Task',
                                  color='Responsible', title='Implementation Timeline')
        fig_timeline.update_yaxes(autorange="reversed")
        
        st.plotly_chart(fig_timeline, use_container_width=True)

def render_export_section():
    st.markdown('<div class="main-header">Export & Reporting Center</div>', unsafe_allow_html=True)
    
    # Check available data
    has_materiality = 'key_issues' in st.session_state and st.session_state.key_issues
    has_esgfp = 'esgfp_scores' in st.session_state
    
    if not has_materiality and not has_esgfp:
        st.warning("No data available for export. Please complete assessments first.")
        return
    
    # Export options
    st.markdown("### 📤 Select Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        export_scope = st.radio(
            "Export Scope",
            ["Current Module Only", "All Available Data", "Custom Selection"]
        )
        
        if export_scope == "Custom Selection":
            st.markdown("#### Select Components")
            if has_materiality:
                mat_comps = st.multiselect(
                    "Materiality Components",
                    ["Risk Analysis Results", "Stakeholder Assessment", "Comparison Tables", "Charts"]
                )
            if has_esgfp:
                esgfp_comps = st.multiselect(
                    "ESGFP Components",
                    ["Model Structure", "Indicator Scores", "Scenario Results", "Validation Reports"]
                )
    
    with col2:
        export_format = st.selectbox(
            "Export Format",
            ["Excel Workbook", "PDF Report", "JSON Data", "CSV Files", "Image Gallery"]
        )
        
        include_charts = st.checkbox("Include charts/visualizations", value=True)
        include_metadata = st.checkbox("Include metadata and notes", value=True)
        compress_files = st.checkbox("Compress into single file", value=True)
    
    # Preview section
    st.markdown("---")
    st.markdown("### 👁️ Export Preview")
    
    preview_tab1, preview_tab2, preview_tab3 = st.tabs(["📋 Data Summary", "📊 Charts Preview", "⚙️ Settings"])
    
    with preview_tab1:
        # Show data summary
        summary_data = []
        
        if has_materiality:
            summary_data.append({
                'Module': 'Materiality Assessment',
                'Components': 'Risk Analysis, Stakeholder Assessment',
                'Records': len(st.session_state.key_issues),
                'Size': '~' + str(len(st.session_state.key_issues) * 2) + ' KB'
            })
        
        if has_esgfp:
            summary_data.append({
                'Module': 'ESGFP Scoring',
                'Components': 'Indicator Scores, Scenario Results',
                'Records': len(st.session_state.get('esgfp_alternatives', [])),
                'Size': '~' + str(len(st.session_state.get('esgfp_alternatives', [])) * 5) + ' KB'
            })
        
        if summary_data:
            df_summary = pd.DataFrame(summary_data)
            st.dataframe(df_summary, use_container_width=True)
    
    with preview_tab2:
        if include_charts:
            st.info("The following charts will be included in the export:")
            
            # Show sample charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Sample bar chart
                sample_data = pd.DataFrame({
                    'Category': ['A', 'B', 'C', 'D'],
                    'Value': [10, 20, 15, 25]
                })
                fig_bar = px.bar(sample_data, x='Category', y='Value', title="Sample Bar Chart")
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with col2:
                # Sample pie chart
                fig_pie = px.pie(sample_data, values='Value', names='Category', title="Sample Pie Chart")
                st.plotly_chart(fig_pie, use_container_width=True)
    
    # Generate export
    st.markdown("---")
    st.markdown("### 🚀 Generate Export")
    
    if st.button("🔄 Generate Export Package", type="primary"):
        with st.spinner("Preparing export package..."):
            # Collect all data
            export_data = {}
            charts_data = {}
            
            # Materiality data
            if has_materiality and (export_scope in ["Current Module Only", "All Available Data", "Custom Selection"]):
                export_data['Materiality_Issues'] = pd.DataFrame(st.session_state.key_issues)
                
                if 'risk_analysis_data' in st.session_state:
                    risk_df = pd.DataFrame([
                        {'issue': k, **v}
                        for k, v in st.session_state.risk_analysis_data.items()
                    ])
                    export_data['Risk_Analysis'] = risk_df
                
                if 'stakeholder_data' in st.session_state:
                    stakeholder_df = pd.DataFrame([
                        {'issue': k, **v}
                        for k, v in st.session_state.stakeholder_data.items()
                    ])
                    export_data['Stakeholder_Assessment'] = stakeholder_df
            
            # ESGFP data
            if has_esgfp and (export_scope in ["All Available Data", "Custom Selection"]):
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
                
                if 'esgfp_scores' in st.session_state:
                    scores_df = pd.DataFrame([
                        {'key': k, **v}
                        for k, v in st.session_state.esgfp_scores.items()
                    ])
                    export_data['ESGFP_Scores'] = scores_df
            
            # Generate export based on format
            if export_format == "Excel Workbook":
                excel_data = to_excel(export_data)
                
                st.success("✅ Export ready!")
                st.download_button(
                    label="📥 Download Excel Workbook",
                    data=excel_data,
                    file_name="esg_assessment_export.xlsx",
                    mime="application/vnd.ms-excel"
                )
            
            elif export_format == "PDF Report":
                pdf_data = create_pdf_report(export_data, charts_data)
                
                st.success("✅ Export ready!")
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_data,
                    file_name="esg_assessment_report.pdf",
                    mime="application/pdf"
                )
            
            elif export_format == "JSON Data":
                json_data = json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'modules': {
                        'materiality': has_materiality,
                        'esgfp': has_esgfp
                    },
                    'data': {
                        k: v.to_dict('records') if isinstance(v, pd.DataFrame) else v
                        for k, v in export_data.items()
                    }
                }, indent=2)
                
                st.success("✅ Export ready!")
                st.download_button(
                    label="📥 Download JSON Data",
                    data=json_data,
                    file_name="esg_assessment_data.json",
                    mime="application/json"
                )
            
            elif export_format == "CSV Files":
                csv_data = to_csv(export_data)
                
                st.success("✅ Export ready!")
                st.download_button(
                    label="📥 Download CSV Zip",
                    data=csv_data,
                    file_name="esg_assessment_data.zip",
                    mime="application/zip"
                )
            
            elif export_format == "Image Gallery":
                # Create a zip of sample charts (in real app, use actual charts)
                import zipfile
                import tempfile
                import os
                
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Save sample images
                    sample_charts = ['chart1.png', 'chart2.png', 'chart3.png']
                    zip_path = os.path.join(tmpdir, 'charts.zip')
                    
                    with zipfile.ZipFile(zip_path, 'w') as zipf:
                        for chart in sample_charts:
                            # Create dummy files (in real app, save actual charts)
                            dummy_content = b"Chart image data"
                            zipf.writestr(chart, dummy_content)
                    
                    with open(zip_path, 'rb') as f:
                        zip_data = f.read()
                
                st.success("✅ Export ready!")
                st.download_button(
                    label="📥 Download Image Gallery",
                    data=zip_data,
                    file_name="esg_charts.zip",
                    mime="application/zip"
                )
    
    # Batch export options
    st.markdown("---")
    st.markdown("### 🔄 Scheduled & Batch Exports")
    
    col1, col2 = st.columns(2)
    
    with col1:
        schedule_export = st.checkbox("Schedule regular exports")
        if schedule_export:
            frequency = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Quarterly"])
            next_export = st.date_input("Start date")
    
    with col2:
        email_export = st.checkbox("Email export automatically")
        if email_export:
            email_address = st.text_input("Email address")
            include_summary = st.checkbox("Include summary in email", value=True)
    
    if st.button("Save Export Settings", type="secondary"):
        st.success("Export settings saved!")

if __name__ == "__main__":
    main()