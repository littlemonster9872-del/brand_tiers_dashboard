import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Brand Tiers Dashboard", page_icon="🍷", layout="wide")

from pathlib import Path

DEFAULT_FILE = Path(__file__).parent / "Copy of Brand tiers - GBB.xlsx"

@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_excel(DEFAULT_FILE)

    df.columns = [str(c).strip() for c in df.columns]

    # Clean common text fields
    text_cols = ["SPEC NUMBER", "CLIENT", "BRAND", "CULT", "PRODUCT", "TIER"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    if "VINT" in df.columns:
        df["VINT"] = pd.to_numeric(df["VINT"], errors="coerce").astype("Int64")

    return df


def multiselect_with_all(label, options, default_all=True):
    options = [o for o in options if pd.notna(o)]
    default = options if default_all else None
    return st.multiselect(label, options=options, default=default)


st.title("🍷 Brand Tiers Dashboard")
st.caption("Interactive dashboard for the Brand Tiers workbook")

with st.sidebar:
    st.header("Data source")
    uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
    st.caption(f"If no file is uploaded, the app uses: {DEFAULT_FILE}")

df = load_data(uploaded_file)

required_columns = {"SPEC NUMBER", "CLIENT", "BRAND", "CULT", "VINT", "PRODUCT", "TIER"}
missing = required_columns - set(df.columns)

if missing:
    st.error(f"The workbook is missing these expected columns: {', '.join(sorted(missing))}")
    st.stop()

# Sidebar filters
with st.sidebar:
    st.header("Filters")

    selected_tiers = multiselect_with_all("Tier", sorted(df["TIER"].dropna().unique().tolist()))
    selected_clients = multiselect_with_all("Client", sorted(df["CLIENT"].dropna().unique().tolist()))
    selected_brands = multiselect_with_all("Brand", sorted(df["BRAND"].dropna().unique().tolist()))
    selected_cults = multiselect_with_all("Cultivar code", sorted(df["CULT"].dropna().unique().tolist()))

    vint_options = sorted([int(v) for v in df["VINT"].dropna().unique().tolist()])
    selected_vints = st.multiselect("Vintage", options=vint_options, default=vint_options)

    search_text = st.text_input("Search product / spec / brand / client", placeholder="Type to search...")
    top_n = st.slider("Top N for charts", min_value=5, max_value=30, value=10, step=1)

# Apply filters
filtered = df[
    df["TIER"].isin(selected_tiers)
    & df["CLIENT"].isin(selected_clients)
    & df["BRAND"].isin(selected_brands)
    & df["CULT"].isin(selected_cults)
    & df["VINT"].isin(selected_vints)
].copy()

if search_text:
    q = search_text.strip().lower()
    mask = (
        filtered["PRODUCT"].fillna("").str.lower().str.contains(q)
        | filtered["SPEC NUMBER"].fillna("").str.lower().str.contains(q)
        | filtered["BRAND"].fillna("").str.lower().str.contains(q)
        | filtered["CLIENT"].fillna("").str.lower().str.contains(q)
    )
    filtered = filtered[mask]

# KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Filtered rows", f"{len(filtered):,}")
k2.metric("Unique brands", f"{filtered['BRAND'].nunique():,}")
k3.metric("Unique clients", f"{filtered['CLIENT'].nunique():,}")
k4.metric("Unique tier labels", f"{filtered['TIER'].nunique():,}")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Brand & Client", "Detail Table", "Quick Insights"])

with tab1:
    c1, c2 = st.columns(2)

    tier_counts = (
        filtered["TIER"]
        .value_counts()
        .reset_index()
    )
    tier_counts.columns = ["TIER", "COUNT"]

    fig_tier = px.bar(
        tier_counts,
        x="TIER",
        y="COUNT",
        title="Products by Tier",
        text="COUNT"
    )
    fig_tier.update_layout(xaxis_title="", yaxis_title="Count")

    vint_counts = (
        filtered["VINT"]
        .value_counts(dropna=True)
        .sort_index()
        .reset_index()
    )
    vint_counts.columns = ["VINT", "COUNT"]

    fig_vint = px.bar(
        vint_counts,
        x="VINT",
        y="COUNT",
        title="Products by Vintage",
        text="COUNT"
    )
    fig_vint.update_layout(xaxis_title="Vintage", yaxis_title="Count")

    c1.plotly_chart(fig_tier, use_container_width=True)
    c2.plotly_chart(fig_vint, use_container_width=True)

    cult_counts = filtered["CULT"].value_counts().head(top_n).reset_index()
    cult_counts.columns = ["CULT", "COUNT"]
    fig_cult = px.bar(
        cult_counts,
        x="COUNT",
        y="CULT",
        orientation="h",
        title=f"Top {top_n} Cultivar Codes",
        text="COUNT"
    )
    fig_cult.update_layout(yaxis_title="", xaxis_title="Count")
    st.plotly_chart(fig_cult, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)

    brand_counts = filtered["BRAND"].value_counts().head(top_n).reset_index()
    brand_counts.columns = ["BRAND", "COUNT"]
    fig_brand = px.bar(
        brand_counts,
        x="COUNT",
        y="BRAND",
        orientation="h",
        title=f"Top {top_n} Brands",
        text="COUNT"
    )
    fig_brand.update_layout(yaxis_title="", xaxis_title="Count")

    client_counts = filtered["CLIENT"].value_counts().head(top_n).reset_index()
    client_counts.columns = ["CLIENT", "COUNT"]
    fig_client = px.bar(
        client_counts,
        x="COUNT",
        y="CLIENT",
        orientation="h",
        title=f"Top {top_n} Clients",
        text="COUNT"
    )
    fig_client.update_layout(yaxis_title="", xaxis_title="Count")

    c1.plotly_chart(fig_brand, use_container_width=True)
    c2.plotly_chart(fig_client, use_container_width=True)

    heatmap_data = (
        filtered.groupby(["TIER", "VINT"])
        .size()
        .reset_index(name="COUNT")
    )

    if not heatmap_data.empty:
        fig_heat = px.density_heatmap(
            heatmap_data,
            x="VINT",
            y="TIER",
            z="COUNT",
            title="Tier vs Vintage",
            text_auto=True
        )
        fig_heat.update_layout(xaxis_title="Vintage", yaxis_title="Tier")
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("No data available for the Tier vs Vintage heatmap.")

with tab3:
    st.subheader("Filtered records")

    show_cols = ["SPEC NUMBER", "CLIENT", "BRAND", "CULT", "VINT", "PRODUCT", "TIER"]
    st.dataframe(
        filtered[show_cols].sort_values(["TIER", "BRAND", "CLIENT"], ascending=[True, True, True]),
        use_container_width=True,
        hide_index=True
    )

    csv = filtered[show_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered data as CSV",
        data=csv,
        file_name="brand_tiers_filtered.csv",
        mime="text/csv"
    )

with tab4:
    st.subheader("Quick insights")

    total_rows = len(filtered)
    top_brand = filtered["BRAND"].mode().iloc[0] if not filtered["BRAND"].mode().empty else "N/A"
    top_client = filtered["CLIENT"].mode().iloc[0] if not filtered["CLIENT"].mode().empty else "N/A"
    top_tier = filtered["TIER"].mode().iloc[0] if not filtered["TIER"].mode().empty else "N/A"

    tier_summary = filtered["TIER"].value_counts(normalize=True).mul(100).round(1)

    st.markdown(f"""
    - Total filtered records: **{total_rows:,}**
    - Most common brand: **{top_brand}**
    - Most common client: **{top_client}**
    - Most common tier: **{top_tier}**
    """)

    if not tier_summary.empty:
        st.markdown("**Tier mix**")
        for tier_name, pct in tier_summary.items():
            st.write(f"- {tier_name}: {pct}%")

st.divider()
st.caption("Built in Streamlit. Put this .py file in the same folder as your Excel workbook, then run it with: streamlit run brand_tiers_dashboard.py")
