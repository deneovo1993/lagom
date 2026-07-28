import os
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Lagom Market Dashboard", layout="wide")

FOLDER = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def load_data():
    master = pd.read_csv(os.path.join(FOLDER, "master_counties.csv"), low_memory=False)
    target = pd.read_csv(os.path.join(FOLDER, "target_counties.csv"), low_memory=False)
    for df in [master, target]:
        df["state"] = df["geographic_area_name"].str.split(",").str[-1].str.strip()
        for col in ["median_listing_price", "absorption_rate", "hotness_score",
                    "demand_score", "supply_score", "median_days_on_market_x",
                    "homes_sold", "active_listings", "median_household_income"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return master, target

master, target = load_data()

# SIDEBAR
st.sidebar.title("Filters")
all_states = ["All States"] + sorted(target["state"].dropna().unique())
selected_state = st.sidebar.selectbox("State", all_states)
price_min, price_max = st.sidebar.slider(
    "Listing Price Range ($)",
    min_value=200000,
    max_value=300000,
    value=(200000, 300000),
    step=5000,
    format="$%d"
)

filtered = target[target["median_listing_price"].between(price_min, price_max)].copy()
if selected_state != "All States":
    filtered = filtered[filtered["state"] == selected_state]

# HEADER
st.title("Lagom Development — Market Prioritization Dashboard")
st.caption("County Selection for $200K–$300K Housing Development")
st.markdown("---")

# TOP STATS
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Counties Analyzed", f"{len(master):,}")
col2.metric("Target Counties ($200K–$300K)", f"{len(target):,}")
col3.metric("Filtered Counties", f"{len(filtered):,}")
col4.metric("Avg Absorption Rate", f"{filtered['absorption_rate'].mean():.1f}%")
st.markdown("---")

# TOP COUNTIES TABLE
st.subheader("Top Recommended Counties")
st.caption("Ranked by absorption rate, hotness score, demand score, and days on market.")

rank_data = filtered.dropna(subset=["absorption_rate", "hotness_score",
                                     "demand_score", "median_days_on_market_x"]).copy()
if len(rank_data) > 0:
    rank_data["score"] = (
        rank_data["absorption_rate"].rank(pct=True)
        + rank_data["hotness_score"].rank(pct=True)
        + rank_data["demand_score"].rank(pct=True)
        - rank_data["median_days_on_market_x"].rank(pct=True)
    )
    top_n = st.slider("Number of counties to show", 5, 50, 20)
    top = rank_data.sort_values("score", ascending=False).head(top_n)

    display_cols = {
        "geographic_area_name": "County",
        "state": "State",
        "median_listing_price": "Median Price",
        "absorption_rate": "Absorption Rate (%)",
        "hotness_score": "Hotness Score",
        "demand_score": "Demand Score",
        "supply_score": "Supply Score",
        "median_days_on_market_x": "Days on Market"
    }
    display = top[[c for c in display_cols if c in top.columns]].rename(columns=display_cols)
    display["Median Price"] = display["Median Price"].apply(lambda x: f"${x:,.0f}")
    display["Absorption Rate (%)"] = display["Absorption Rate (%)"].apply(lambda x: f"{x:.1f}")
    display["Hotness Score"] = display["Hotness Score"].apply(lambda x: f"{x:.1f}")
    display["Demand Score"] = display["Demand Score"].apply(lambda x: f"{x:.1f}")
    display["Supply Score"] = display["Supply Score"].apply(lambda x: f"{x:.1f}")
    display["Days on Market"] = display["Days on Market"].apply(lambda x: f"{x:.0f}")
    st.dataframe(display.reset_index(drop=True), use_container_width=True)
else:
    st.warning("No counties match the current filters.")

st.markdown("---")

# ROW 1: ABSORPTION + HOTNESS
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Top 20 by Absorption Rate")
    top_abs = filtered.dropna(subset=["absorption_rate"]).nlargest(20, "absorption_rate")
    fig = px.bar(
        top_abs.sort_values("absorption_rate"),
        x="absorption_rate",
        y="geographic_area_name",
        orientation="h",
        color_discrete_sequence=["#4C7A5B"],
        labels={"absorption_rate": "Absorption Rate (%)", "geographic_area_name": ""}
    )
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.subheader("Top 20 by Hotness Score")
    top_hot = filtered.dropna(subset=["hotness_score"]).nlargest(20, "hotness_score")
    fig = px.bar(
        top_hot.sort_values("hotness_score"),
        x="hotness_score",
        y="geographic_area_name",
        orientation="h",
        color_discrete_sequence=["#A87B50"],
        labels={"hotness_score": "Hotness Score", "geographic_area_name": ""}
    )
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ROW 2: AFFORDABILITY SCATTER + STATE COUNTS
col_l2, col_r2 = st.columns(2)

with col_l2:
    st.subheader("Affordability vs. Absorption Rate")
    scatter_data = filtered.dropna(subset=["median_listing_price", "absorption_rate"]).copy()
    if len(scatter_data) > 0:
        fig = px.scatter(
            scatter_data,
            x="median_listing_price",
            y="absorption_rate",
            color="hotness_score",
            hover_name="geographic_area_name",
            hover_data={"median_listing_price": ":$,.0f", "absorption_rate": ":.1f"},
            color_continuous_scale=["#1D5E6A", "#A87B50"],
            labels={
                "median_listing_price": "Median Listing Price ($)",
                "absorption_rate": "Absorption Rate (%)",
                "hotness_score": "Hotness Score"
            }
        )
        median_abs = scatter_data["absorption_rate"].median()
        fig.add_hline(y=median_abs, line_dash="dash", line_color="gray",
                      annotation_text=f"Median {median_abs:.1f}%")
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

with col_r2:
    st.subheader("Target Counties by State")
    state_counts = filtered["state"].value_counts().head(15).reset_index()
    state_counts.columns = ["State", "Count"]
    fig = px.bar(
        state_counts.sort_values("Count"),
        x="Count",
        y="State",
        orientation="h",
        color_discrete_sequence=["#1D5E6A"],
        labels={"Count": "Number of Target Counties", "State": ""}
    )
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ROW 3: SUPPLY VS DOM + DEMAND VS SUPPLY
col_l3, col_r3 = st.columns(2)

with col_l3:
    st.subheader("Supply Score vs. Days on Market")
    st.caption("Lower supply = more days on market. This is the key regression finding.")
    sd = filtered.dropna(subset=["supply_score", "median_days_on_market_x"]).copy()
    if len(sd) > 0:
        fig = px.scatter(
            sd,
            x="supply_score",
            y="median_days_on_market_x",
            color="absorption_rate",
            hover_name="geographic_area_name",
            color_continuous_scale=["#A87B50", "#1D5E6A"],
            labels={
                "supply_score": "Supply Score",
                "median_days_on_market_x": "Days on Market",
                "absorption_rate": "Absorption Rate (%)"
            }
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

with col_r3:
    st.subheader("Demand vs. Supply Score")
    st.caption("Counties in the top-left (high demand, low supply) are the strongest opportunities.")
    ds = filtered.dropna(subset=["demand_score", "supply_score"]).copy()
    if len(ds) > 0:
        fig = px.scatter(
            ds,
            x="demand_score",
            y="supply_score",
            color="median_days_on_market_x",
            hover_name="geographic_area_name",
            color_continuous_scale=["#4C7A5B", "#A87B50"],
            labels={
                "demand_score": "Demand Score",
                "supply_score": "Supply Score",
                "median_days_on_market_x": "Days on Market"
            }
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)
