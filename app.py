import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Final Amazon Audit", page_icon="📊", layout="wide")

# Brand Configuration
BRAND_MAP = {
    'MA': 'Maison de l’Avenir',
    'CL': 'Creation Lamis',
    'JPD': 'Jean Paul Dupont',
    'PC': 'Paris Collection',
    'DC': 'Dorall Collection',
    'CPT': 'CP Trendies'
}

def clean_numeric(val):
    """Safely converts currency strings to numbers for analysis."""
    if isinstance(val, str):
        cleaned = val.replace('AED', '').replace('$', '').replace('\xa0', '').replace(',', '').strip()
        try: return pd.to_numeric(cleaned)
        except: return val
    return val

def get_brand_robust(name):
    """Resilient mapping for both campaign prefixes and product titles."""
    if pd.isna(name): return "Unmapped"
    n = str(name).upper().replace('’', "'").replace('LAVENIR', "L'AVENIR").strip()
    for prefix, full_name in BRAND_MAP.items():
        if any(n.startswith(f"{prefix}{sep}") for sep in ["_", " ", "-", " |", " -"]):
            return full_name
        if full_name.upper().replace('’', "'") in n:
            return full_name
    return "Unmapped"

def find_robust_col(df, keywords, exclude=['acos', 'roas', 'cpc', 'ctr', 'rate']):
    """Dynamically finds metric columns."""
    for col in df.columns:
        col_clean = str(col).strip().lower()
        if any(kw.lower() in col_clean for kw in keywords):
            if not any(ex.lower() in col_clean for ex in exclude):
                return col
    return None

def calculate_audit_kpis(df):
    """Calculates all performance ratios."""
    df['CTR'] = (df['Clicks'] / df['Impressions']).replace([np.inf, -np.inf], 0).fillna(0)
    df['CVR'] = (df['Orders'] / df['Clicks']).replace([np.inf, -np.inf], 0).fillna(0)
    df['ROAS'] = (df['Ad Sales'] / df['Spend']).replace([np.inf, -np.inf], 0).fillna(0)
    df['ACOS'] = (df['Spend'] / df['Ad Sales']).replace([np.inf, -np.inf], 0).fillna(0)
    df['TACOS'] = (df['Spend'] / df['Total Sales']).replace([np.inf, -np.inf], 0).fillna(0)
    df['Organic Sales'] = df['Total Sales'] - df['Ad Sales']
    df['Paid Contrib'] = (df['Ad Sales'] / df['Total Sales']).replace([np.inf, -np.inf], 0).fillna(0)
    df['Organic Contrib'] = (df['Organic Sales'] / df['Total Sales']).replace([np.inf, -np.inf], 0).fillna(0)
    df['CPC'] = (df['Spend'] / df['Clicks']).replace([np.inf, -np.inf], 0).fillna(0)
    return df

st.title("📊 Final Amazon Audit")
st.info("Verified Historical Audit: Sponsored Products + Sponsored Brands + Business Report")

st.sidebar.header("Upload Files")
sp_file = st.sidebar.file_uploader("1. Sponsored Products Report", type=["csv", "xlsx"])
sb_file = st.sidebar.file_uploader("2. Sponsored Brands Report", type=["csv", "xlsx"])
biz_file = st.sidebar.file_uploader("3. Business Report (Total Sales)", type=["csv", "xlsx"])

if sp_file and sb_file and biz_file:
    def load_and_standardize(file):
        df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]
        for col in df.columns:
            if not any(x in col.lower() for x in ['name', 'title', 'term', 'brand', 'asin']):
                df[col] = df[col].apply(clean_numeric)
        return df

    sp_df, sb_df, biz_df = load_and_standardize(sp_file), load_and_standardize(sb_file), load_and_standardize(biz_file)

    # Mapping
    sp_df['Brand'] = sp_df['Campaign Name'].apply(get_brand_robust)
    sb_df['Brand'] = sb_df['Campaign Name'].apply(get_brand_robust)
    title_col = find_robust_col(biz_df, ['Title', 'Product Name'])
    biz_df['Brand'] = biz_df[title_col].apply(get_brand_robust)

    # Column Detection
    sp_sales_col = find_robust_col(sp_df, ['Sales'])
    sb_sales_col = find_robust_col(sb_df, ['Sales'])
    sp_orders_col = find_robust_col(sp_df, ['Orders'])
    sb_orders_col = find_robust_col(sb_df, ['Orders'])
    biz_sales_col = find_robust_col(biz_df, ['Ordered Product Sales', 'Sales'])
    search_col = find_robust_col(sp_df, ['Customer Search Term', 'Search Term'])

    # Aggregation
    metrics_map = {'Spend': 'sum', 'Clicks': 'sum', 'Impressions': 'sum'}
    sp_grouped = sp_df.groupby('Brand').agg({**metrics_map, sp_sales_col: 'sum', sp_orders_col: 'sum'}).rename(columns={sp_sales_col: 'Ad Sales', sp_orders_col: 'Orders'})
    sb_grouped = sb_df.groupby('Brand').agg({**metrics_map, sb_sales_col: 'sum', sb_orders_col: 'sum'}).rename(columns={sb_sales_col: 'Ad Sales', sb_orders_col: 'Orders'})
    total_ads = sp_grouped.add(sb_grouped, fill_value=0).reset_index()

    total_biz = biz_df.groupby('Brand')[biz_sales_col].sum().reset_index().rename(columns={biz_sales_col: 'Total Sales'})
    final_df = calculate_audit_kpis(pd.merge(total_ads, total_biz, on='Brand', how='outer').fillna(0))
    final_df = final_df[final_df['Brand'] != "Unmapped"]

    tabs = st.tabs(["🌍 Portfolio Overview"] + sorted(list(BRAND_MAP.values())))

    def display_two_row_metrics(row_data):
        st.markdown("#### 💰 Sales & Contribution")
        r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns(5)
        r1_c1.metric("Total Sales", f"{row_data['Total Sales']:,.2f}")
        r1_c2.metric("Ad Sales", f"{row_data['Ad Sales']:,.2f}")
        r1_c3.metric("Organic Sales", f"{row_data['Organic Sales']:,.2f}")
        r1_c4.metric("Paid Contrib %", f"{row_data['Paid Contrib']:.1%}")
        r1_c5.metric("Organic Contrib %", f"{row_data['Organic Contrib']:.1%}")

        st.markdown("#### ⚡ Ad Efficiency & Traffic")
        r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns(5)
        r2_c1.metric("Ad Spend", f"{row_data['Spend']:,.2f}")
        r2_c2.metric("ROAS", f"{row_data['ROAS']:.2f}")
        r2_c3.metric("TACOS", f"{row_data['TACOS']:.1%}")
        r2_c4.metric("CTR", f"{row_data['CTR']:.2%}")
        r2_c5.metric("CVR", f"{row_data['CVR']:.2%}")

    with tabs[0]:
        t_row = final_df.select_dtypes(include=[np.number]).sum()
        # Rates
        t_row['CTR'] = t_row['Clicks'] / t_row['Impressions'] if t_row['Impressions'] > 0 else 0
        t_row['CVR'] = t_row['Orders'] / t_row['Clicks'] if t_row['Clicks'] > 0 else 0
        t_row['ROAS'] = t_row['Ad Sales'] / t_row['Spend'] if t_row['Spend'] > 0 else 0
        t_row['ACOS'] = t_row['Spend'] / t_row['Ad Sales'] if t_row['Ad Sales'] > 0 else 0
        t_row['TACOS'] = t_row['Spend'] / t_row['Total Sales'] if t_row['Total Sales'] > 0 else 0
        t_row['Paid Contrib'] = t_row['Ad Sales'] / t_row['Total Sales'] if t_row['Total Sales'] > 0 else 0
        t_row['Organic Contrib'] = 1 - t_row['Paid Contrib']
        t_row['Organic Sales'] = t_row['Total Sales'] - t_row['Ad Sales']
        
        display_two_row_metrics(t_row)
        st.divider()
        st.subheader("🏢 Brand-Wise Performance Breakdown")
        st.dataframe(final_df.sort_values(by='Total Sales', ascending=False), hide_index=True, use_container_width=True)

    for i, brand_name in enumerate(sorted(BRAND_MAP.values())):
        with tabs[i+1]:
            b_data = final_df[final_df['Brand'] == brand_name].iloc[0]
            display_two_row_metrics(b_data)
            
            st.divider()
            # Campaign Overview section
            st.subheader(f"📈 {brand_name} Campaign Overview")
            b_sp_camp = sp_df[sp_df['Brand'] == brand_name].groupby('Campaign Name').agg({
                'Impressions': 'sum', 'Clicks': 'sum', 'Spend': 'sum', sp_sales_col: 'sum', sp_orders_col: 'sum'
            }).rename(columns={sp_sales_col: 'Sales', sp_orders_col: 'Orders'}).reset_index()
            
            b_sb_camp = sb_df[sb_df['Brand'] == brand_name].groupby('Campaign Name').agg({
                'Impressions': 'sum', 'Clicks': 'sum', 'Spend': 'sum', sb_sales_col: 'sum', sb_orders_col: 'sum'
            }).rename(columns={sb_sales_col: 'Sales', sb_orders_col: 'Orders'}).reset_index()
            
            camp_overview = pd.concat([b_sp_camp, b_sb_camp]).sort_values(by='Sales', ascending=False)
            st.dataframe(camp_overview, use_container_width=True, hide_index=True)
            
            st.divider()
            # Search Term Drilldown section
            st.subheader(f"🔍 {brand_name} Search Term & Keyword Performance")
            b_sp_drill = sp_df[sp_df['Brand'] == brand_name][['Campaign Name', search_col, 'Impressions', 'Clicks', 'Spend', sp_sales_col, sp_orders_col]]
            b_sp_drill.rename(columns={sp_sales_col: 'Sales', sp_orders_col: 'Orders'}, inplace=True)
            
            b_sb_drill = sb_df[sb_df['Brand'] == brand_name][['Campaign Name', search_col, 'Impressions', 'Clicks', 'Spend', sb_sales_col, sb_orders_col]]
            b_sb_drill.rename(columns={sb_sales_col: 'Sales', sb_orders_col: 'Orders'}, inplace=True)
            
            drill_df = pd.concat([b_sp_drill, b_sb_drill])
            # Calculate metrics for search terms
            drill_df['ROAS'] = (drill_df['Sales'] / drill_df['Spend']).replace([np.inf, -np.inf], 0).fillna(0)
            drill_df['CTR'] = (drill_df['Clicks'] / drill_df['Impressions']).replace([np.inf, -np.inf], 0).fillna(0)
            drill_df['CVR'] = (drill_df['Orders'] / drill_df['Clicks']).replace([np.inf, -np.inf], 0).fillna(0)
            
            st.dataframe(drill_df.sort_values(by='Sales', ascending=False), hide_index=True, use_container_width=True)

    # Export
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_df.to_excel(writer, sheet_name='PORTFOLIO_AUDIT', index=False)
    st.sidebar.download_button("📥 Download Master Report", data=output.getvalue(), file_name="Amazon_Portfolio_Audit.xlsx", use_container_width=True)
else:
    st.info("Upload reports to generate the Final Amazon Audit.")
