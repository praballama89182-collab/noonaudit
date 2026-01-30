import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Final Noon Audit", page_icon="🚀", layout="wide")

# Brand Configuration
BRAND_MAP = {
    'MA': 'Maison de l’Avenir',
    'CL': 'Creation Lamis',
    'JPD': 'Jean Paul Dupont',
    'PC': 'Paris Collection',
    'DC': 'Dorall Collection',
    'CPT': 'CP Trendies'
}

# Mapping for Noon Sales Export brand_code
NOON_BRAND_CODE_MAP = {
    'maison_de_lavenir': 'Maison de l’Avenir',
    'creation_lamis': 'Creation Lamis',
    'jean_paul_dupont': 'Jean Paul Dupont',
    'paris_collection': 'Paris Collection',
    'dorall_collection': 'Dorall Collection',
    'cp_trendies': 'CP Trendies'
}

def clean_numeric(val):
    """Clean currency strings and non-breaking spaces."""
    if isinstance(val, str):
        cleaned = val.replace('AED', '').replace('$', '').replace('\xa0', '').replace(',', '').strip()
        try: return pd.to_numeric(cleaned)
        except: return val
    return val

def get_brand_robust(name):
    """Resilient mapping for Noon campaign prefixes."""
    if pd.isna(name): return "Unmapped"
    n = str(name).upper().strip()
    for prefix, full_name in BRAND_MAP.items():
        if any(n.startswith(f"{prefix}{sep}") for sep in ["_", " ", "-", " |", " -"]):
            return full_name
    return "Unmapped"

def calculate_audit_kpis(df):
    """Calculates all performance ratios for Noon."""
    df['CTR'] = (df['Clicks'] / df['Impressions']).replace([np.inf, -np.inf], 0).fillna(0)
    df['CVR'] = (df['Orders'] / df['Clicks']).replace([np.inf, -np.inf], 0).fillna(0)
    df['ROAS'] = (df['Ad Sales'] / df['Spend']).replace([np.inf, -np.inf], 0).fillna(0)
    df['ACOS'] = (df['Spend'] / df['Ad Sales']).replace([np.inf, -np.inf], 0).fillna(0)
    df['TACOS'] = (df['Spend'] / df['Total Sales']).replace([np.inf, -np.inf], 0).fillna(0)
    df['Organic Sales'] = df['Total Sales'] - df['Ad Sales']
    df['Paid Contrib'] = (df['Ad Sales'] / df['Total Sales']).replace([np.inf, -np.inf], 0).fillna(0)
    df['Organic Contrib'] = (df['Organic Sales'] / df['Total Sales']).replace([np.inf, -np.inf], 0).fillna(0)
    return df

st.title("📊 Final Noon Audit")
st.info("Verified Historical Audit: Noon Ad Campaign Report + Sales Export")

st.sidebar.header("Upload Files")
ad_file = st.sidebar.file_uploader("1. Ad Overview (Campaign Report)", type=["csv", "xlsx"])
sales_file = st.sidebar.file_uploader("2. Sales Export (Overall Sales)", type=["csv", "xlsx"])

if ad_file and sales_file:
    def load_df(file):
        df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]
        for col in df.columns:
            if not any(x in col.lower() for x in ['name', 'title', 'code', 'sku', 'nr']):
                df[col] = df[col].apply(clean_numeric)
        return df

    # Process Ads
    ads_df = load_df(ad_file)
    ads_df['Brand'] = ads_df['Campaign Name'].apply(get_brand_robust)

    ad_grouped = ads_df.groupby('Brand').agg({
        'Views': 'sum', 'Clicks': 'sum', 'Orders': 'sum', 'Spends': 'sum', 'Revenue': 'sum'
    }).rename(columns={
        'Views': 'Impressions', 'Spends': 'Spend', 'Revenue': 'Ad Sales'
    }).reset_index()

    # Process Overall Sales
    overall_df = load_df(sales_file)
    overall_df['Brand'] = overall_df['brand_code'].map(NOON_BRAND_CODE_MAP).fillna("Unmapped")
    total_sales_map = overall_df.groupby('Brand')['gmv_lcy'].sum().reset_index().rename(columns={'gmv_lcy': 'Total Sales'})

    # Final Merge & KPI Calculation
    final_df = calculate_audit_kpis(pd.merge(ad_grouped, total_sales_map, on='Brand', how='outer').fillna(0))
    final_df = final_df[final_df['Brand'] != "Unmapped"]

    tabs = st.tabs(["🌍 Portfolio Overview"] + sorted(list(BRAND_MAP.values())))

    def display_two_row_metrics(row_data):
        # Row 1: Sales & Contribution
        st.markdown("#### 💰 Sales & Contribution")
        r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns(5)
        r1_c1.metric("Total Sales", f"{row_data['Total Sales']:,.2f}")
        r1_c2.metric("Ad Sales", f"{row_data['Ad Sales']:,.2f}")
        r1_c3.metric("Organic Sales", f"{row_data['Organic Sales']:,.2f}")
        r1_c4.metric("Paid Contrib %", f"{row_data['Paid Contrib']:.1%}")
        r1_c5.metric("Organic Contrib %", f"{row_data['Organic Contrib']:.1%}")

        # Row 2: Efficiency & Traffic
        st.markdown("#### ⚡ Ad Efficiency & Traffic")
        r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns(5)
        r2_c1.metric("Ad Spend", f"{row_data['Spend']:,.2f}")
        r2_c2.metric("ROAS", f"{row_data['ROAS']:.2f}")
        r2_c3.metric("TACOS", f"{row_data['TACOS']:.1%}")
        r2_c4.metric("CTR", f"{row_data['CTR']:.2%}")
        r2_c5.metric("CVR", f"{row_data['CVR']:.2%}")

    with tabs[0]:
        t_row = final_df.select_dtypes(include=[np.number]).sum()
        # Aggregated Portfolio Rates
        t_row['CTR'] = t_row['Clicks'] / t_row['Impressions'] if t_row['Impressions'] > 0 else 0
        t_row['CVR'] = t_row['Orders'] / t_row['Clicks'] if t_row['Clicks'] > 0 else 0
        t_row['ROAS'] = t_row['Ad Sales'] / t_row['Spend'] if t_row['Spend'] > 0 else 0
        t_row['TACOS'] = t_row['Spend'] / t_row['Total Sales'] if t_row['Total Sales'] > 0 else 0
        t_row['Paid Contrib'] = t_row['Ad Sales'] / t_row['Total Sales'] if t_row['Total Sales'] > 0 else 0
        t_row['Organic Contrib'] = 1 - t_row['Paid Contrib']
        t_row['Organic Sales'] = t_row['Total Sales'] - t_row['Ad Sales']
        
        display_two_row_metrics(t_row)
        st.divider()
        st.subheader("🏢 Brand Breakdown")
        st.dataframe(final_df.sort_values(by='Total Sales', ascending=False), hide_index=True, use_container_width=True)

    for i, brand_name in enumerate(sorted(BRAND_MAP.values())):
        with tabs[i+1]:
            b_data = final_df[final_df['Brand'] == brand_name]
            if not b_data.empty:
                r = b_data.iloc[0]
                display_two_row_metrics(r)
                st.divider()
                st.subheader("📊 Campaign Performance Drilldown")
                drill_df = ads_df[ads_df['Brand'] == brand_name][['Campaign Name', 'Views', 'Clicks', 'Spends', 'Revenue', 'ROAS']]
                st.dataframe(drill_df.sort_values(by='Revenue', ascending=False), hide_index=True, use_container_width=True)
            else:
                st.warning(f"No data available for {brand_name}.")

    # Export
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_df.to_excel(writer, sheet_name='NOON_AUDIT_SUMMARY', index=False)
    st.sidebar.download_button("📥 Download Master Report", data=output.getvalue(), file_name="Noon_Portfolio_Audit.xlsx", use_container_width=True)
else:
    st.info("Upload the Campaign Report (Ads) and Sales Export (Overall) to start.")
