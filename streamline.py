import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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


# ============================================================
# SIDEBAR FILTERS
# ============================================================

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

min_absorption = st.sidebar.slider(
    "Minimum Absorption Rate (%)",
    min_value=0.0,
    max_value=float(target["absorption_rate"].max()),
    value=0.0,
    step=0.5
)

min_hotness = st.sidebar.slider(
    "Minimum Hotness Score",
    min_value=0.0,
    max_value=float(target["hotness_score"].max()),
    value=0.0,
    step=1.0
)

max_dom = st.sidebar.slider(
    "Max Days on Market",
    min_value=1,
    max_value=int(target["median_days_on_market_x"].max()),
    value=int(target["median_days_on_market_x"].max()),
    step=1
)

filtered = target[
    target["median_listing_price"].between(price_min, price_max) &
    (target["absorption_rate"] >= min_absorption) &
    (target["hotness_score"] >= min_hotness) &
    (target["median_days_on_market_x"] <= max_dom)
].copy()

if selected_state != "All States":
    filtered = filtered[filtered["state"] == selected_state]


# ============================================================
# HEADER
# ============================================================

st.title("Lagom Development — Market Prioritization Dashboard")
st.caption("Data-Driven County Selection for $200K–$300K Housing Development")
st.markdown("---")


# ============================================================
# OVERVIEW STATS
# ============================================================

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Counties Analyzed", f"{len(master):,}")
col2.metric("Target Counties ($200K–$300K)", f"{len(target):,}")
col3.metric("Filtered Counties", f"{len(filtered):,}")
col4.metric("Avg Absorption Rate", f"{filtered['absorption_rate'].mean():.1f}%")
col5.metric("Avg Days on Market", f"{filtered['median_days_on_market_x'].mean():.0f} days")

st.markdown("---")


# ============================================================
# TAB LAYOUT
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Top Counties", "County Explorer", "Market Charts", "Supply & Demand", "Regression Results"
])


# ============================================================
# TAB 1: TOP COUNTIES
# ============================================================

with tab1:
    st.subheader("Top Recommended Counties")
    st.caption("Ranked by combined absorption rate, hotness score, demand score, and days on market.")

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
            fig.update_layout(height=600)
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
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No counties match the current filters.")


# ============================================================
# TAB 2: COUNTY EXPLORER
# ============================================================

with tab2:
    st.subheader("County Explorer")

    sort_col = st.selectbox("Sort by", [
        "absorption_rate", "hotness_score", "demand_score",
        "median_listing_price", "median_days_on_market_x", "supply_score"
    ])

    sort_asc = st.radio("Order", ["Descending", "Ascending"]) == "Ascending"

    explore_cols = {
        "geographic_area_name": "County",
        "state": "State",
        "median_listing_price": "Median Price ($)",
        "absorption_rate": "Absorption Rate (%)",
        "hotness_score": "Hotness Score",
        "demand_score": "Demand Score",
        "supply_score": "Supply Score",
        "median_days_on_market_x": "Days on Market",
        "median_household_income": "Median Income ($)"
    }

    explore = filtered[[c for c in explore_cols if c in filtered.columns]].rename(columns=explore_cols)
    col_to_sort = explore_cols.get(sort_col, sort_col)
    if col_to_sort in explore.columns:
        explore = explore.sort_values(col_to_sort, ascending=sort_asc)

    st.dataframe(explore.reset_index(drop=True), use_container_width=True)
    st.caption(f"Showing {len(explore):,} counties")


# ============================================================
# TAB 3: MARKET CHARTS
# ============================================================

with tab3:
    col_left, col_right = st.columns(2)

    with col_left:
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
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Top States by Target County Count")
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
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.subheader("Days on Market Distribution")
        dom_data = filtered.dropna(subset=["median_days_on_market_x"])
        fig = px.histogram(
            dom_data,
            x="median_days_on_market_x",
            nbins=30,
            color_discrete_sequence=["#1D5E6A"],
            labels={"median_days_on_market_x": "Median Days on Market"}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col_right2:
        st.subheader("Listing Price Distribution")
        price_data = filtered.dropna(subset=["median_listing_price"])
        fig = px.histogram(
            price_data,
            x="median_listing_price",
            nbins=30,
            color_discrete_sequence=["#A87B50"],
            labels={"median_listing_price": "Median Listing Price ($)"}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Market Screening Funnel")
    county_rows = int(master["geographic_area_name"].str.contains("County", case=False, na=False).sum())
    target_with_absorption = int(target["absorption_rate"].notna().sum())

    funnel_labels = ["Master Records", "County Records", "$200K–$300K Target Counties", "Targets with Absorption Rate"]
    funnel_values = [len(master), county_rows, len(target), target_with_absorption]

    fig = go.Figure(go.Bar(
        x=funnel_labels,
        y=funnel_values,
        marker_color=["#6B7280", "#1D5E6A", "#A87B50", "#4C7A5B"],
        text=[f"{v:,}" for v in funnel_values],
        textposition="outside"
    ))
    fig.update_layout(height=400, yaxis_title="Number of Records")
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# TAB 4: SUPPLY & DEMAND
# ============================================================

with tab4:
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Demand vs. Supply Score")
        sd_data = filtered.dropna(subset=["demand_score", "supply_score"]).copy()
        if len(sd_data) > 0:
            fig = px.scatter(
                sd_data,
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
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Supply Score vs. Days on Market")
        sd2 = filtered.dropna(subset=["supply_score", "median_days_on_market_x"]).copy()
        if len(sd2) > 0:
            fig = px.scatter(
                sd2,
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
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Average Metrics by State")
    state_avg = filtered.groupby("state").agg(
        avg_absorption=("absorption_rate", "mean"),
        avg_hotness=("hotness_score", "mean"),
        avg_dom=("median_days_on_market_x", "mean"),
        avg_supply=("supply_score", "mean"),
        avg_demand=("demand_score", "mean"),
        county_count=("geographic_area_name", "count")
    ).round(1).reset_index().sort_values("avg_absorption", ascending=False)

    state_avg.columns = ["State", "Avg Absorption (%)", "Avg Hotness",
                         "Avg Days on Market", "Avg Supply Score",
                         "Avg Demand Score", "County Count"]
    st.dataframe(state_avg.reset_index(drop=True), use_container_width=True)


# ============================================================
# TAB 5: REGRESSION RESULTS
# ============================================================

with tab5:
    st.subheader("Regression Model Results")

    model_results = pd.DataFrame({
        "Model": ["OLS", "Ridge", "Lasso", "Random Forest"],
        "MSE":   [51.96, 52.09, 52.06, 0.01],
        "RMSE":  [7.21,  7.22,  7.22,  0.11],
        "R²":    [0.893, 0.892, 0.892, 0.9995]
    })
    st.dataframe(model_results, use_container_width=True, hide_index=True)
    st.caption("Random Forest R² of 0.9995 is cross-validated (CV). Training R² was 1.0 due to overfitting.")

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Feature Importance (Random Forest)")
        importance = pd.DataFrame({
            "Feature": ["supply_score", "demand_score", "median_listing_price",
                        "median_household_income", "total_households"],
            "Importance": [0.9998, 0.0001, 0.0001, 0.0000, 0.0000]
        }).sort_values("Importance")

        fig = px.bar(
            importance,
            x="Importance",
            y="Feature",
            orientation="h",
            color_discrete_sequence=["#1D5E6A"],
            labels={"Importance": "Importance Score", "Feature": ""}
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Model RMSE Comparison")
        fig = px.bar(
            model_results,
            x="Model",
            y="RMSE",
            color_discrete_sequence=["#1D5E6A"],
            text="RMSE"
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Key Finding")
    st.info(
        "Supply score accounts for over 99% of feature importance in the Random Forest model. "
        "Counties with low housing supply relative to demand sell homes significantly faster. "
        "Price and income do not statistically predict sale speed at the county level."
    )
