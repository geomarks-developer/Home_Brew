from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from market_data import get_market_data


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.header("🔥 Dividend Aristocrat Heatmap")
st.caption(
    "Compare Dividend Aristocrats visually by MarketScope scores, dividend "
    "yield, dividend growth, and market performance."
)


# ---------------------------------------------------------
# Load shared data
# ---------------------------------------------------------

try:
    data = get_market_data(show_progress=False)
except Exception as exc:
    st.error(f"Unable to load MarketScope Dividend data: {exc}")
    st.stop()


df = data.get("dividend_df", pd.DataFrame()).copy()

if df.empty:
    st.warning("No Dividend Aristocrat data is currently available.")
    st.stop()

numeric_columns = [
    "Market Cap",
    "Dividend Yield",
    "Dividend Growth 5Y",
    "Return 1Y",
    "Dividend Score",
    "Quality Score",
    "Value Score",
    "Momentum Score",
    "Risk Score",
    "Overall Score",
]

for column in numeric_columns:
    if column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

if "Sector" in df.columns:
    df["Sector"] = df["Sector"].fillna("Unknown")
else:
    df["Sector"] = "Unknown"


# ---------------------------------------------------------
# Controls
# ---------------------------------------------------------

st.subheader("Heatmap Controls")

metric_options = {
    "Overall Score": "Overall Score",
    "Dividend Score": "Dividend Score",
    "Quality Score": "Quality Score",
    "Value Score": "Value Score",
    "Momentum Score": "Momentum Score",
    "Risk Score": "Risk Score",
    "Dividend Yield": "Dividend Yield",
    "5Y Dividend Growth": "Dividend Growth 5Y",
    "1Y Return": "Return 1Y",
}

control_1, control_2, control_3 = st.columns([1.2, 1.5, 1])

with control_1:
    selected_label = st.selectbox(
        "Color tiles by",
        options=list(metric_options.keys()),
        index=0,
    )

selected_metric = metric_options[selected_label]

sectors = sorted(df["Sector"].astype(str).unique())

with control_2:
    selected_sectors = st.multiselect(
        "Sector",
        options=sectors,
        default=sectors,
    )

with control_3:
    group_by_sector = st.checkbox(
        "Group by sector",
        value=True,
    )

filtered = df[df["Sector"].isin(selected_sectors)].copy()
filtered = filtered.dropna(subset=[selected_metric])

if filtered.empty:
    st.info("No stocks match the current heatmap settings.")
    st.stop()


# ---------------------------------------------------------
# Heatmap formatting
# ---------------------------------------------------------

score_metrics = {
    "Overall Score",
    "Dividend Score",
    "Quality Score",
    "Value Score",
    "Momentum Score",
    "Risk Score",
}

percent_metrics = {
    "Dividend Yield",
    "Dividend Growth 5Y",
    "Return 1Y",
}

if selected_metric in score_metrics:
    color_scale = [
        [0.00, "#b2182b"],
        [0.35, "#ef8a62"],
        [0.50, "#d9d9d9"],
        [0.65, "#67a9cf"],
        [1.00, "#2166ac"],
    ]
    range_color = [0, 100]
    color_midpoint = None
    metric_format = ".1f"

elif selected_metric in percent_metrics:
    color_scale = "RdYlGn"
    low = filtered[selected_metric].quantile(0.05)
    high = filtered[selected_metric].quantile(0.95)

    if pd.isna(low) or pd.isna(high) or low == high:
        low = filtered[selected_metric].min()
        high = filtered[selected_metric].max()

    range_color = None
    color_midpoint = 0 if low < 0 < high else None
    metric_format = "%.2f%%"

else:
    color_scale = "RdYlGn"
    range_color = None
    color_midpoint = None
    metric_format = ".2f"


# ---------------------------------------------------------
# Treemap
# ---------------------------------------------------------

st.divider()
st.subheader(f"{selected_label} Heatmap")

# Use equal-sized tiles. This keeps the visual focused on the selected
# metric instead of allowing market capitalization to dominate tile size.
filtered["Tile Size"] = 1.0

path = ["Sector", "Ticker"] if group_by_sector else ["Ticker"]

custom_data = [
    column
    for column in [
        "Company",
        "Dividend Yield",
        "Dividend Growth 5Y",
        "Overall Score",
        "Dividend Score",
        "Quality Score",
        "Value Score",
        "Momentum Score",
        "Risk Score",
        "Return 1Y",
    ]
    if column in filtered.columns
]

fig = px.treemap(
    filtered,
    path=path,
    values="Tile Size",
    color=selected_metric,
    color_continuous_scale=color_scale,
    range_color=range_color,
    color_continuous_midpoint=color_midpoint,
    custom_data=custom_data,
)

fig.update_traces(
    root_color="rgba(0,0,0,0)",
    marker=dict(line=dict(width=1, color="rgba(255,255,255,0.20)")),
)

# Build a detailed hover label from the custom-data positions.
custom_lookup = {name: index for index, name in enumerate(custom_data)}
hover_lines = ["<b>%{label}</b>"]

if "Company" in custom_lookup:
    hover_lines.append(
        f"Company: %{{customdata[{custom_lookup['Company']}]}}"
    )
if "Dividend Yield" in custom_lookup:
    hover_lines.append(
        f"Dividend Yield: %{{customdata[{custom_lookup['Dividend Yield']}]:.2f}}%"
    )
if "Dividend Growth 5Y" in custom_lookup:
    hover_lines.append(
        f"5Y Dividend Growth: %{{customdata[{custom_lookup['Dividend Growth 5Y']}]:.2%}}"
    )
if "Overall Score" in custom_lookup:
    hover_lines.append(
        f"Overall Score: %{{customdata[{custom_lookup['Overall Score']}]:.1f}}"
    )
if "Dividend Score" in custom_lookup:
    hover_lines.append(
        f"Dividend Score: %{{customdata[{custom_lookup['Dividend Score']}]:.1f}}"
    )
if "Quality Score" in custom_lookup:
    hover_lines.append(
        f"Quality Score: %{{customdata[{custom_lookup['Quality Score']}]:.1f}}"
    )
if "Value Score" in custom_lookup:
    hover_lines.append(
        f"Value Score: %{{customdata[{custom_lookup['Value Score']}]:.1f}}"
    )
if "Momentum Score" in custom_lookup:
    hover_lines.append(
        f"Momentum Score: %{{customdata[{custom_lookup['Momentum Score']}]:.1f}}"
    )
if "Risk Score" in custom_lookup:
    hover_lines.append(
        f"Risk Score: %{{customdata[{custom_lookup['Risk Score']}]:.1f}}"
    )
if "Return 1Y" in custom_lookup:
    hover_lines.append(
        f"1Y Return: %{{customdata[{custom_lookup['Return 1Y']}]:.2%}}"
    )

hover_lines.append("<extra></extra>")
fig.update_traces(hovertemplate="<br>".join(hover_lines))

fig.update_layout(
    height=720,
    margin=dict(t=20, l=5, r=5, b=5),
    coloraxis_colorbar=dict(title=selected_label),
)

st.plotly_chart(
    fig,
    use_container_width=True,
    config={"displayModeBar": True, "displaylogo": False},
)


# ---------------------------------------------------------
# Leaders and laggards
# ---------------------------------------------------------

st.divider()

left, right = st.columns(2)

ascending_for_best = selected_metric in {
    # No current selected metrics are intrinsically lower-is-better.
}

with left:
    st.subheader(f"🟢 Highest {selected_label}")

    leaders = filtered.sort_values(
        selected_metric,
        ascending=ascending_for_best,
    ).head(10)

    leader_columns = [
        column
        for column in dict.fromkeys([
            "Ticker",
            "Company",
            "Sector",
            selected_metric,
            "Overall Score",
        ])
        if column in leaders.columns
    ]

    leaders_display = leaders[leader_columns].copy()
    # Values are already on the desired display scale here.

    st.dataframe(
        leaders_display,
        hide_index=True,
        use_container_width=True,
        column_config={
            selected_metric: st.column_config.NumberColumn(
                selected_label,
                format=metric_format,
            ),
            "Overall Score": st.column_config.NumberColumn(
                "Overall Score",
                format="%.1f",
            ),
        },
    )

with right:
    st.subheader(f"🔴 Lowest {selected_label}")

    laggards = filtered.sort_values(
        selected_metric,
        ascending=not ascending_for_best,
    ).head(10)

    laggard_columns = [
        column
        for column in dict.fromkeys([
            "Ticker",
            "Company",
            "Sector",
            selected_metric,
            "Overall Score",
        ])
        if column in laggards.columns
    ]

    laggards_display = laggards[laggard_columns].copy()
    # Values are already on the desired display scale here.

    st.dataframe(
        laggards_display,
        hide_index=True,
        use_container_width=True,
        column_config={
            selected_metric: st.column_config.NumberColumn(
                selected_label,
                format=metric_format,
            ),
            "Overall Score": st.column_config.NumberColumn(
                "Overall Score",
                format="%.1f",
            ),
        },
    )


# ---------------------------------------------------------
# Sector comparison
# ---------------------------------------------------------

st.divider()
st.subheader(f"Sector Median: {selected_label}")

sector_summary = (
    filtered.groupby("Sector", as_index=False)
    .agg(
        Stocks=("Ticker", "count"),
        Median=(selected_metric, "median"),
    )
    .sort_values("Median", ascending=False)
)

sector_fig = px.bar(
    sector_summary,
    x="Sector",
    y="Median",
    color="Median",
    color_continuous_scale=color_scale,
    range_color=range_color,
    color_continuous_midpoint=color_midpoint,
    hover_data={"Stocks": True},
    labels={"Median": f"Median {selected_label}"},
)

sector_fig.update_layout(
    height=450,
    xaxis_title=None,
    yaxis_title=f"Median {selected_label}",
    coloraxis_colorbar_title=selected_label,
    margin=dict(l=10, r=10, t=20, b=10),
)

if selected_metric in percent_metrics:
    sector_fig.update_yaxes(tickformat=".1f", ticksuffix="%")

st.plotly_chart(
    sector_fig,
    use_container_width=True,
    config={"displaylogo": False},
)


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.caption(
    "Each stock uses an equal-sized heatmap tile so color drives the comparison. "
    "MarketScope scores are research indicators, not investment recommendations."
)
