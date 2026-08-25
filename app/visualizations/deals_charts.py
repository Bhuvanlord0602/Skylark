"""Plotly charts for Deals and Sales Pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def create_empty_figure(title: str, message: str = "No data available") -> go.Figure:
    """Create a graceful empty-state chart."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="#94A3B8")
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#F8FAFC")),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        margin=dict(l=40, r=40, t=50, b=40),
        height=320
    )
    return fig


def chart_pipeline_by_sector(deals_metrics: Dict[str, Any]) -> go.Figure:
    """Horizontal bar chart showing Total Pipeline Value by Sector."""
    sector_data = deals_metrics.get("pipeline_by_sector", {})
    if not sector_data:
        return create_empty_figure("Pipeline Value by Sector", "No sector pipeline data available")

    df_list = []
    for sec, stats in sector_data.items():
        df_list.append({
            "Sector": sec,
            "Total Value": stats.get("total_value", 0.0),
            "Deal Count": stats.get("deal_count", 0),
            "Win Rate": f"{stats.get('win_rate_pct')}%" if stats.get("win_rate_pct") is not None else "N/A"
        })

    df = pd.DataFrame(df_list).sort_values("Total Value", ascending=True)

    fig = go.Figure(
        go.Bar(
            x=df["Total Value"],
            y=df["Sector"],
            orientation="h",
            marker=dict(
                color=df["Total Value"],
                colorscale="Blues",
                line=dict(color="#38BDF8", width=1)
            ),
            customdata=df[["Deal Count", "Win Rate"]],
            hovertemplate="<b>%{y}</b><br>Pipeline Value: $%{x:,.0f}<br>Deals: %{customdata[0]}<br>Win Rate: %{customdata[1]}<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(text="📊 Pipeline Value by Sector", font=dict(size=16, color="#F8FAFC")),
        xaxis=dict(title="Pipeline Value ($)", color="#94A3B8", gridcolor="#334155"),
        yaxis=dict(title="", color="#F8FAFC"),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        margin=dict(l=20, r=20, t=50, b=40),
        height=350
    )
    return fig


def chart_pipeline_by_stage(deals_metrics: Dict[str, Any]) -> go.Figure:
    """Funnel / Bar chart showing Stage Distribution and Pipeline Values."""
    stage_data = deals_metrics.get("pipeline_by_stage", {})
    if not stage_data:
        return create_empty_figure("Pipeline Funnel by Stage", "No stage data available")

    df_list = []
    for stg, stats in stage_data.items():
        df_list.append({
            "Stage": stg,
            "Deal Count": stats.get("deal_count", 0),
            "Total Value": stats.get("total_value", 0.0),
            "Pct Value": stats.get("pct_of_value", 0.0)
        })

    df = pd.DataFrame(df_list).sort_values("Total Value", ascending=False)

    fig = go.Figure(
        go.Funnel(
            y=df["Stage"],
            x=df["Total Value"],
            textinfo="value+percent initial",
            marker=dict(color=["#38BDF8", "#0284C7", "#0369A1", "#075985", "#0C4A6E", "#64748B"]),
            customdata=df["Deal Count"],
            hovertemplate="<b>%{y}</b><br>Value: $%{x:,.0f}<br>Deals: %{customdata}<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(text="🌪️ Sales Pipeline Funnel by Stage", font=dict(size=16, color="#F8FAFC")),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        margin=dict(l=20, r=20, t=50, b=40),
        height=350
    )
    return fig


def chart_close_date_trend(deals_metrics: Dict[str, Any]) -> go.Figure:
    """Monthly bar and trend chart showing Expected Close Date velocity."""
    monthly_data = deals_metrics.get("close_date_distribution", {})
    if not monthly_data:
        return create_empty_figure("Pipeline by Expected Close Date", "No close date projections available")

    months = list(monthly_data.keys())
    values = [monthly_data[m].get("total_value", 0.0) for m in months]
    counts = [monthly_data[m].get("count", 0) for m in months]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=months,
            y=values,
            name="Pipeline Value",
            marker_color="#38BDF8",
            hovertemplate="<b>%{x}</b><br>Value: $%{y:,.0f}<extra></extra>"
        )
    )
    fig.add_trace(
        go.Scatter(
            x=months,
            y=counts,
            name="Deal Count",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color="#F59E0B", width=2),
            marker=dict(size=6),
            hovertemplate="<b>%{x}</b><br>Deals: %{y}<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(text="📅 Expected Close Date Distribution", font=dict(size=16, color="#F8FAFC")),
        xaxis=dict(title="Close Month", color="#94A3B8", gridcolor="#334155"),
        yaxis=dict(title="Pipeline Value ($)", color="#38BDF8", gridcolor="#334155"),
        yaxis2=dict(title="Deal Count", color="#F59E0B", overlaying="y", side="right", showgrid=False),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#F8FAFC")),
        margin=dict(l=20, r=20, t=60, b=40),
        height=350
    )
    return fig


def chart_deal_value_distribution(deals_records: List[Dict[str, Any]]) -> go.Figure:
    """Histogram / Box plot showing deal size distribution and concentration."""
    values = [d["deal_value"] for d in deals_records if d.get("deal_value") is not None]
    if not values:
        return create_empty_figure("Deal Value Distribution", "No numeric deal values to plot")

    fig = go.Figure(
        go.Box(
            y=values,
            name="Deal Value",
            marker_color="#818CF8",
            boxpoints="all",
            jitter=0.3,
            pointpos=-1.8,
            hovertemplate="Value: $%{y:,.0f}<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(text="📦 Deal Size & Distribution Spread", font=dict(size=16, color="#F8FAFC")),
        yaxis=dict(title="Deal Value ($)", color="#94A3B8", gridcolor="#334155"),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        margin=dict(l=20, r=20, t=50, b=40),
        height=350
    )
    return fig


def chart_sector_stage_heatmap(deals_records: List[Dict[str, Any]]) -> go.Figure:
    """Sector × Stage Matrix Heatmap showing opportunity concentration."""
    if not deals_records:
        return create_empty_figure("Sector × Stage Matrix", "No records available")

    df_list = []
    for d in deals_records:
        sec = d.get("sector_service") or d.get("sector") or "Unspecified"
        stg = d.get("stage") or "Unspecified"
        val = d.get("deal_value") or 0.0
        df_list.append({"Sector": sec, "Stage": stg, "Value": val})

    df = pd.DataFrame(df_list)
    pivot = df.pivot_table(index="Sector", columns="Stage", values="Value", aggfunc="sum", fill_value=0)

    if pivot.empty:
        return create_empty_figure("Sector × Stage Matrix", "Insufficient data for matrix")

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=list(pivot.columns),
            y=list(pivot.index),
            colorscale="Viridis",
            hovertemplate="Sector: %{y}<br>Stage: %{x}<br>Pipeline: $%{z:,.0f}<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(text="🔥 Sector × Stage Value Matrix", font=dict(size=16, color="#F8FAFC")),
        xaxis=dict(title="Stage", color="#94A3B8"),
        yaxis=dict(title="Sector", color="#94A3B8"),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        margin=dict(l=20, r=20, t=50, b=40),
        height=350
    )
    return fig

