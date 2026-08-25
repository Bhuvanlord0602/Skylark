"""Plotly charts for Cross-Board Executive Intelligence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app.visualizations.deals_charts import create_empty_figure


def chart_sector_health_matrix(cross_metrics: Dict[str, Any]) -> go.Figure:
    """⭐ Sector Health Matrix: Opportunity Value vs Operational Load vs Execution Risk."""
    matrix_data = cross_metrics.get("sector_health_matrix", [])
    if not matrix_data:
        return create_empty_figure("⭐ Sector Health Matrix", "No cross-board sector metrics available")

    df = pd.DataFrame(matrix_data)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Pipeline Value ($)",
            x=df["sector"],
            y=df["pipeline_value"],
            marker_color="#38BDF8",
            yaxis="y",
            hovertemplate="<b>%{x}</b><br>Pipeline: $%{y:,.0f}<extra></extra>"
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Work Order Count",
            x=df["sector"],
            y=df["work_order_count"],
            mode="lines+markers",
            marker=dict(size=8, color="#10B981"),
            line=dict(width=2, color="#10B981"),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Work Orders: %{y}<extra></extra>"
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Delayed Orders",
            x=df["sector"],
            y=df["delayed_work_orders"],
            mode="markers",
            marker=dict(size=12, symbol="triangle-up", color="#EF4444"),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Delayed: %{y}<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(text="⭐ Sector Health Matrix (Opportunity vs. Ops Load vs. Delay Risk)", font=dict(size=16, color="#F8FAFC")),
        xaxis=dict(title="Sector", color="#94A3B8", tickangle=-25),
        yaxis=dict(title="Pipeline Value ($)", color="#38BDF8", gridcolor="#334155"),
        yaxis2=dict(title="Order Count", color="#10B981", overlaying="y", side="right", showgrid=False),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#F8FAFC")),
        margin=dict(l=20, r=20, t=60, b=60),
        height=380
    )
    return fig


def chart_pipeline_vs_operational_load(cross_metrics: Dict[str, Any]) -> go.Figure:
    """Scatter plot correlating Sales Opportunity vs Operational Load."""
    scatter_data = cross_metrics.get("pipeline_vs_ops_scatter", [])
    if not scatter_data:
        return create_empty_figure("Pipeline vs Operational Load", "No cross-board records to correlate")

    df = pd.DataFrame(scatter_data)

    fig = px.scatter(
        df,
        x="pipeline_value",
        y="work_order_count",
        size="delayed_count",
        color="sector",
        hover_name="sector",
        hover_data=["execution_risk"],
        size_max=30,
        labels={
            "pipeline_value": "Pipeline Value ($)",
            "work_order_count": "Active Work Orders",
            "delayed_count": "Delayed Orders"
        }
    )

    fig.update_layout(
        title=dict(text="⚖️ Pipeline Opportunity vs. Execution Workload", font=dict(size=16, color="#F8FAFC")),
        xaxis=dict(title="Pipeline Value ($)", color="#94A3B8", gridcolor="#334155"),
        yaxis=dict(title="Work Orders", color="#94A3B8", gridcolor="#334155"),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        margin=dict(l=20, r=20, t=50, b=40),
        height=360
    )
    return fig

