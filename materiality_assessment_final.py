"""
Double Materiality Assessment Tool - COMPLETE VERSION
=====================================================
Features:
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Constants
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

# Helper functions (you need to define these or import them)
def calculate_impact_from_risks_dynamic(issue_name):
    """Calculate impact based on risks (simplified version)"""
    # This is a simplified version - replace with your actual logic
    return 3

def get_risk_level(score):
    """Determine risk level from score"""
    if score <= 4:
        return "Low", "#10b981"
    elif score <= 9:
        return "Medium", "#fbbf24"
    elif score <= 16:
        return "High", "#f97316"
    else:
        return "Very High", "#ef4444"

def create_heatmap_matrix(results, title):
    """Create a heatmap matrix visualization"""
    # Simplified version - replace with your actual Plotly code
    fig = go.Figure(data=go.Heatmap(
        z=[[1, 2, 3], [4, 5, 6]],
        text=[['A', 'B', 'C'], ['D', 'E', 'F']],
        texttemplate='%{text}',
        textfont={"size": 20}
    ))
    fig.update_layout(title=title)
    return fig

# Define the main function
# Define the materiality assessment function
def run_materiality_assessment():
    """Run the materiality assessment tool"""
    # Initialize session state
    if 'key_issues' not in st.session_state:
        st.session_state.key_issues = []
    if 'risk_analysis_data' not in st.session_state:
        st.session_state.risk_analysis_data = {}
    if 'stakeholder_data' not in st.session_state:
        st.session_state.stakeholder_data = {}
    if 'risk_categories' not in st.session_state:
        st.session_state.risk_categories = {}
    if 'selected_methods' not in st.session_state:
        st.session_state.selected_methods = []

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.subheader("Manage Data")
    
    # Add new issue
    with st.expander("➕ Add New Issue"):
        new_issue = st.text_input("Issue Name")
        new_pillar = st.selectbox("Pillar", list(DEFAULT_PILLARS.keys()))
        if st.button("Add Issue"):
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
                st.success(f"Added: {new_issue}")
                st.rerun()
            elif new_issue:
                st.error("Issue already exists!")
    
    # Remove issue
    with st.expander("➖ Remove Issue"):
        if st.session_state.key_issues:
            issue_to_remove = st.selectbox(
                "Select issue to remove",
                options=[i['name'] for i in st.session_state.key_issues]
            )
            if st.button("Remove Issue", type="secondary"):
                st.session_state.key_issues = [i for i in st.session_state.key_issues if i['name'] != issue_to_remove]
                if issue_to_remove in st.session_state.risk_analysis_data:
                    del st.session_state.risk_analysis_data[issue_to_remove]
                if issue_to_remove in st.session_state.stakeholder_data:
                    del st.session_state.stakeholder_data[issue_to_remove]
                st.success(f"Removed: {issue_to_remove}")
                st.rerun()
        else:
            st.info("No issues to remove")
    
    # Manage risks
    with st.expander("⚙️ Manage Risk Categories"):
        # Add new category
        new_cat = st.text_input("New Category Name")
        if st.button("Add Category"):
            if new_cat and new_cat not in st.session_state.risk_categories:
                st.session_state.risk_categories[new_cat] = []
                st.success(f"Added category: {new_cat}")
                st.rerun()
        
        # Add risks to categories
        for cat in list(st.session_state.risk_categories.keys()):
            st.markdown(f"**{cat}**")
            new_risk = st.text_input(f"New risk for {cat}", key=f"risk_{cat}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Add", key=f"add_{cat}"):
                    if new_risk and new_risk not in st.session_state.risk_categories[cat]:
                        st.session_state.risk_categories[cat].append(new_risk)
                        st.success(f"Added: {new_risk}")
                        st.rerun()
            with col2:
                if st.button("Delete Category", key=f"del_{cat}"):
                    del st.session_state.risk_categories[cat]
                    st.rerun()
    
    st.divider()
    
    # Method selection
    st.subheader("Select Methods")
    risk_analysis = st.checkbox("⚡ Risk Analysis", value=True)
    stakeholder = st.checkbox("👥 Stakeholder & Expert", value=True)
    
    st.session_state.selected_methods = []
    if risk_analysis:
        st.session_state.selected_methods.append('risk_analysis')
    if stakeholder:
        st.session_state.selected_methods.append('stakeholder')
    
    st.divider()
    
    # Risk level legend
    st.subheader("Risk Levels")
    st.markdown(
        "<div class='risk-low'>• Low (1-4)</div>\n"
        "<div class='risk-medium'>• Medium (5-9)</div>\n"
        "<div class='risk-high'>• High (10-16)</div>\n"
        "<div class='risk-very-high'>• Very High (17-25)</div>",
        unsafe_allow_html=True
    )

if not st.session_state.selected_methods:
    st.info("👈 Select at least one assessment method from the sidebar.")
    st.stop()

# Create tabs
tabs = []
if 'risk_analysis' in st.session_state.selected_methods:
    tabs.append("⚡ Risk Analysis")
if 'stakeholder' in st.session_state.selected_methods:
    tabs.append("👥 Stakeholder")
tabs.append("📊 Compare")

tab_objects = st.tabs(tabs)
tab_idx = 0

# SHORTCUT METHOD
if 'risk_analysis' in st.session_state.selected_methods:
    with tab_objects[tab_idx]:
        st.header("⚡ Risk Analysis")
        st.caption("Impact calculated dynamically based on maximum risks across all issues.")
        
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
                                key=f"sc_like_{issue['name']}"
                            )
                            st.session_state.risk_analysis_data[issue['name']]['likelihood'] = likelihood
                        
                        with col3:
                            all_risks = [r for cat in st.session_state.risk_categories.values() for r in cat]
                            selected = st.multiselect(
                                "Risks",
                                options=all_risks,
                                default=st.session_state.risk_analysis_data[issue['name']]['risks'],
                                key=f"sc_risks_{issue['name']}"
                            )
                            st.session_state.risk_analysis_data[issue['name']]['risks'] = selected
                            
                            impact = calculate_impact_from_risks_dynamic(issue['name'])
                            st.caption(f"Impact: {impact} - {IMPACT_LABELS[impact]} ({len(selected)} risks)")
                        
                        st.divider()
        
        st.subheader("Results")
        
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
        
        col1, col2 = st.columns(2)
        with col1:
            fig = create_heatmap_matrix(results, "Risk Analysis (Dynamic)")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            df = pd.DataFrame(results).sort_values('score', ascending=False)
            df['rank'] = range(1, len(df) + 1)
            st.dataframe(df[['rank', 'issue', 'likelihood', 'impact', 'score', 'level']], 
                       use_container_width=True, hide_index=True)
    
    tab_idx += 1

# AHP METHOD
if 'ahp' in st.session_state.selected_methods:
    with tab_objects[tab_idx]:
        st.header("⚖️ AHP Method (Analytic Hierarchy Process)")
        st.caption("Compare pairs of issues to determine relative importance using pairwise comparison")
        
        if len(st.session_state.key_issues) < 2:
            st.info("Add at least 2 issues to use AHP pairwise comparison")
        else:
            # Initialize AHP data structure
            if 'ahp_comparisons' not in st.session_state:
                st.session_state.ahp_comparisons = {}
            
            n = len(st.session_state.key_issues)
            issue_names = [i['name'] for i in st.session_state.key_issues]
            
            # Initialize comparison matrix if needed
            for i in range(n):
                for j in range(i + 1, n):
                    key = f"{i}-{j}"
                    if key not in st.session_state.ahp_comparisons:
                        st.session_state.ahp_comparisons[key] = {
                            'issue1': issue_names[i],
                            'issue2': issue_names[j],
                            'value': 1,
                            'favors': 'equal'
                        }
            
            # Display pairwise comparisons
            st.subheader("Pairwise Comparisons")
            st.markdown("**Scale:** 1=Equal, 3=Moderate, 5=Strong, 7=Very Strong, 9=Extreme")
            
            comparison_keys = sorted([k for k in st.session_state.ahp_comparisons.keys()])
            
            for idx, key in enumerate(comparison_keys):
                comp = st.session_state.ahp_comparisons[key]
                issue1 = comp['issue1']
                issue2 = comp['issue2']
                
                col1, col2, col3 = st.columns([2, 3, 2])
                
                with col1:
                    st.markdown(f"**{issue1}**")
                
                with col2:
                    # Radio buttons for comparison
                    options = [
                        f"← 9x more important",
                        f"← 7x more important",
                        f"← 5x more important", 
                        f"← 3x more important",
                        "Equal (1)",
                        f"3x more important →",
                        f"5x more important →",
                        f"7x more important →",
                        f"9x more important →"
                    ]
                    
                    # Determine current index
                    if comp['favors'] == 'issue1':
                        if comp['value'] == 9:
                            default_idx = 0
                        elif comp['value'] == 7:
                            default_idx = 1
                        elif comp['value'] == 5:
                            default_idx = 2
                        elif comp['value'] == 3:
                            default_idx = 3
                        else:
                            default_idx = 4
                    elif comp['favors'] == 'issue2':
                        if comp['value'] == 3:
                            default_idx = 5
                        elif comp['value'] == 5:
                            default_idx = 6
                        elif comp['value'] == 7:
                            default_idx = 7
                        elif comp['value'] == 9:
                            default_idx = 8
                        else:
                            default_idx = 4
                    else:
                        default_idx = 4
                    
                    selection = st.radio(
                        f"comp_{key}",
                        options,
                        index=default_idx,
                        key=f"ahp_radio_{key}",
                        label_visibility="collapsed",
                        horizontal=True
                    )
                    
                    # Update comparison based on selection
                    if "9x more important ←" in selection:
                        comp['value'] = 9
                        comp['favors'] = 'issue1'
                    elif "7x more important ←" in selection:
                        comp['value'] = 7
                        comp['favors'] = 'issue1'
                    elif "5x more important ←" in selection:
                        comp['value'] = 5
                        comp['favors'] = 'issue1'
                    elif "3x more important ←" in selection:
                        comp['value'] = 3
                        comp['favors'] = 'issue1'
                    elif "3x more important →" in selection:
                        comp['value'] = 3
                        comp['favors'] = 'issue2'
                    elif "5x more important →" in selection:
                        comp['value'] = 5
                        comp['favors'] = 'issue2'
                    elif "7x more important →" in selection:
                        comp['value'] = 7
                        comp['favors'] = 'issue2'
                    elif "9x more important →" in selection:
                        comp['value'] = 9
                        comp['favors'] = 'issue2'
                    else:
                        comp['value'] = 1
                        comp['favors'] = 'equal'
                
                with col3:
                    st.markdown(f"**{issue2}**")
                
                if idx < len(comparison_keys) - 1:
                    st.divider()
            
            # Build pairwise comparison matrix
            A = np.ones((n, n), dtype=float)
            for i in range(n):
                for j in range(i + 1, n):
                    key = f"{i}-{j}"
                    comp = st.session_state.ahp_comparisons[key]
                    
                    if comp['favors'] == 'issue1':
                        A[i, j] = comp['value']
                        A[j, i] = 1.0 / comp['value']
                    elif comp['favors'] == 'issue2':
                        A[i, j] = 1.0 / comp['value']
                        A[j, i] = comp['value']
                    else:
                        A[i, j] = 1.0
                        A[j, i] = 1.0
            
            # Calculate priorities using eigenvector method
            try:
                eigenvalues, eigenvectors = np.linalg.eig(A)
                max_index = np.argmax(eigenvalues.real)
                lambda_max = eigenvalues[max_index].real
                principal_eigenvector = np.abs(eigenvectors[:, max_index].real)
                priorities = principal_eigenvector / principal_eigenvector.sum()
                
                # Calculate Consistency Index and Ratio
                CI = (lambda_max - n) / (n - 1) if n > 1 else 0
                
                # Random Index values
                RI_values = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 
                            8: 1.41, 9: 1.45, 10: 1.49, 11: 1.51, 12: 1.48, 13: 1.56, 
                            14: 1.57, 15: 1.59}
                RI = RI_values.get(n, 1.49)
                CR = CI / RI if RI != 0 else 0
                
                # Display consistency metrics
                st.subheader("Consistency Check")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("λ max", f"{lambda_max:.4f}")
                with col2:
                    st.metric("CI", f"{CI:.4f}")
                with col3:
                    st.metric("RI", f"{RI:.2f}")
                with col4:
                    if CR < 0.10:
                        st.metric("CR", f"{CR:.4f}", delta="Excellent", delta_color="normal")
                    elif CR < 0.20:
                        st.metric("CR", f"{CR:.4f}", delta="Acceptable", delta_color="normal")
                    else:
                        st.metric("CR", f"{CR:.4f}", delta="Please revise", delta_color="inverse")
                
                st.caption("CR < 0.10: Excellent | CR 0.10-0.20: Acceptable | CR > 0.20: Inconsistent")
                
                # Store scores for comparison
                for i, issue in enumerate(issue_names):
                    if 'ahp_scores' not in st.session_state:
                        st.session_state.ahp_scores = {}
                    st.session_state.ahp_scores[issue] = float(priorities[i] * 25)  # Scale to 1-25 range
                
                # Display results
                st.subheader("Priority Weights and Scores")
                
                results = []
                for i, issue in enumerate(issue_names):
                    results.append({
                        'issue': issue,
                        'priority': priorities[i],
                        'score': priorities[i] * 25,
                        'like': np.sqrt(priorities[i] * 25),
                        'impact': np.sqrt(priorities[i] * 25)
                    })
                
                df_results = pd.DataFrame(results).sort_values('priority', ascending=False)
                df_results['rank'] = range(1, len(df_results) + 1)
                
                # Display table
                st.dataframe(
                    df_results[['rank', 'issue', 'priority', 'score']].round(4),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Visualization
                fig = create_heatmap_matrix(results, "AHP Priority Weights")
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"Error calculating AHP priorities: {e}")
                st.info("Please review your pairwise comparisons.")
    
    tab_idx += 1

# STAKEHOLDER METHOD
if 'stakeholder' in st.session_state.selected_methods:
    with tab_objects[tab_idx]:
        st.header("👥 Stakeholder & Expert Method")
        
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
                                "Stakeholder",
                                0, 10,
                                st.session_state.stakeholder_data[issue['name']]['stakeholder_score'],
                                key=f"stk_stk_{issue['name']}"
                            )
                        
                        with col4:
                            st.session_state.stakeholder_data[issue['name']]['expert_score'] = st.slider(
                                "Expert",
                                0, 10,
                                st.session_state.stakeholder_data[issue['name']]['expert_score'],
                                key=f"stk_exp_{issue['name']}"
                            )
                        
                        data = st.session_state.stakeholder_data[issue['name']]
                        weight = (data['stakeholder_score'] + data['expert_score']) / 20
                        base_score = data['likelihood'] * data['impact']
                        final_score = base_score * weight
                        st.caption(f"Calc: {data['likelihood']} × {data['impact']} × {weight:.2f} = {final_score:.1f}")
                        st.divider()
        
        st.subheader("Results")
        
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
                'like': data['likelihood'],
                'impact': data['impact'],
                'weight': weight,
                'score': score,
                'level': level
            })
        
        col1, col2 = st.columns(2)
        with col1:
            fig = create_heatmap_matrix(results, "Stakeholder Method")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            df = pd.DataFrame(results).sort_values('score', ascending=False)
            df['rank'] = range(1, len(df) + 1)
            st.dataframe(df[['rank', 'issue', 'likelihood', 'impact', 'weight', 'score', 'level']], 
                       use_container_width=True, hide_index=True)
    
    tab_idx += 1

# COMPARE
with tab_objects[-1]:
    st.header("📊 Compare Results")
    
    if len(st.session_state.selected_methods) < 2:
        st.info("Select at least 2 methods to compare.")
    else:
        all_results = {}
        
        if 'risk_analysis' in st.session_state.selected_methods:
            sc_results = []
            for issue in st.session_state.key_issues:
                data = st.session_state.risk_analysis_data[issue['name']]
                impact = calculate_impact_from_risks_dynamic(issue['name'])
                score = data['likelihood'] * impact
                sc_results.append({'issue': issue['name'], 'score': score})
            all_results['Shortcut'] = {r['issue']: r['score'] for r in sc_results}
        
        if 'stakeholder' in st.session_state.selected_methods:
            stk_results = []
            for issue in st.session_state.key_issues:
                data = st.session_state.stakeholder_data[issue['name']]
                weight = (data['stakeholder_score'] + data['expert_score']) / 20
                score = data['likelihood'] * data['impact'] * weight
                stk_results.append({'issue': issue['name'], 'score': score})
            all_results['Stakeholder'] = {r['issue']: r['score'] for r in stk_results}
        
        comparison_data = []
        matrix_results = []
        
        for issue in st.session_state.key_issues:
            row = {'issue': issue['name'], 'pillar': issue['pillar']}
            for method, scores in all_results.items():
                row[method] = scores.get(issue['name'], 0)
            
            method_cols = list(all_results.keys())
            avg_score = sum(row[m] for m in method_cols) / len(method_cols)
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
        
        # Calculate normalized scores per pillar (sum-based: each score / pillar total)
        # This gives 0-1 scale where all issues in a pillar sum to 1.0
        normalized_scores = []
        pillar_sums = df.groupby('pillar')['Average'].sum().to_dict()
        
        for idx, row in df.iterrows():
            pillar = row['pillar']
            pillar_sum = pillar_sums[pillar]
            normalized = row['Average'] / pillar_sum if pillar_sum > 0 else 0
            normalized_scores.append(normalized)
        
        df['Normalized'] = normalized_scores
        
        # Pillar-wise normalized breakdown with charts
        st.subheader("Normalized Scores by Pillar")
        st.caption("Each pillar's scores sum to 1.0. Shows relative weight of each issue within its pillar.")
        
        # Create pie charts for each pillar
        pillar_list = df['pillar'].unique()
        
        # Use columns for side-by-side display
        num_cols = min(len(pillar_list), 3)
        cols = st.columns(num_cols)
        
        for idx, pillar in enumerate(pillar_list):
            with cols[idx % num_cols]:
                pillar_df = df[df['pillar'] == pillar].copy()
                pillar_sum = pillar_sums[pillar]
                
                # Create pie chart for this pillar
                fig_pie = go.Figure(data=[go.Pie(
                    labels=pillar_df['issue'],
                    values=pillar_df['Normalized'],
                    marker=dict(colors=pillar_df['Average'].apply(lambda x: 
                        '#10b981' if x < 8 else '#fbbf24' if x < 15 else '#f97316' if x < 20 else '#ef4444'
                    )),
                    textinfo='label+percent',
                    textfont=dict(size=10),
                    hovertemplate='<b>%{label}</b><br>Normalized: %{value:.3f}<br>Percentage: %{percent}<extra></extra>',
                    hole=0.4
                )])
                
                fig_pie.update_layout(
                    title=dict(text=f"{pillar}<br><sub>Total: {pillar_sum:.1f}</sub>", font=dict(size=14)),
                    showlegend=False,
                    height=300,
                    margin=dict(l=20, r=20, t=60, b=20)
                )
                
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # Show breakdown
                st.markdown(f"**Issues in {pillar}:**")
                for _, row in pillar_df.iterrows():
                    percentage = row['Normalized'] * 100
                    st.markdown(f"• {row['issue']}: **{row['Normalized']:.3f}** ({percentage:.1f}%)")
                
                sum_normalized = pillar_df['Normalized'].sum()
                st.caption(f"Sum: {sum_normalized:.3f}")
                
                if idx < len(pillar_list) - 1:
                    st.divider()
        
        # Materiality Matrix
        st.subheader("Average Score Materiality Matrix")
        st.caption("Combined assessment across all selected methods. Position shows approximate likelihood and impact based on average score.")
        fig = create_heatmap_matrix(matrix_results, "Average Score Materiality Matrix")
        st.plotly_chart(fig, use_container_width=True)
        
        # Bar chart
        st.subheader("Score Comparison by Method")
        fig = go.Figure()
        colors = {'Shortcut': '#f59e0b', 'AHP': '#3b82f6', 'Stakeholder': '#10b981'}
        
        for method in method_cols:
            fig.add_trace(go.Bar(
                name=method,
                x=df['issue'],
                y=df[method],
                marker_color=colors.get(method, '#666')
            ))
        
        fig.update_layout(
            title="Score Comparison",
            barmode='group',
            xaxis_tickangle=-45,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Table
        st.subheader("Detailed Comparison Table")
        st.caption("**Normalized**: Each issue's score divided by pillar total (0-1 scale, sum per pillar = 1.0). **Avg L** (Likelihood) & **Avg I** (Impact) are calculated from √(Average Score).")
        df = df.sort_values('Average', ascending=False)
        df['Rank'] = range(1, len(df) + 1)
        
        # Reorder columns to show Normalized, Avg L and Avg I
        display_cols = ['Rank', 'issue', 'pillar'] + method_cols + ['Average', 'Normalized', 'Avg L', 'Avg I', 'Risk Level']
        
        # Format numbers in display
        df_display = df[display_cols].copy()
        for col in method_cols + ['Average']:
            df_display[col] = df_display[col].round(1)
        # Format normalized to 3 decimal places
        df_display['Normalized'] = df_display['Normalized'].apply(lambda x: f"{x:.3f}")
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Export
        if st.button("📥 Export to CSV"):
            csv = df.to_csv(index=False)
            st.download_button("Download", csv, "materiality_results.csv", "text/csv")

if __name__ == "__main__":
    run_materiality_assessment()