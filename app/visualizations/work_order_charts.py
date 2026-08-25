"""Plotly charts for Work Orders, Operations, and Billing/Collection."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app.visualizations.deals_charts import create_empty_figure


def chart_execution_status(ops_metrics: Dict[str, Any]) -> go.Figure:
    """Donut chart showing Work Order Execution Status distribution."""
    status_data = ops_metrics.get("status_breakdown", {})
    if not status_data:
        return create_empty_figure("Execution Status Breakdown", "No work order status data available")

    labels = list(status_data.keys())
    values = [status_data[k].get("count", 0) for k in labels]

    color_map = {
        "Completed": "#10B981",
        "In Progress": "#38BDF8",
        "Active": "#38BDF8",
        "Delayed": "#EF4444",
        "At Risk": "#F59E0B",
        "Blocked": "#DC2626",
        "Planned": "#64748B",
        "Unspecified": "#475569"
    }
    colors = [color_map.get(lbl, "#0284C7") for lbl in labels]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(colors=colors, line=dict(color="#0F172A", width=2)),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Orders: %{value}<br>Share: %{percent}<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(text="🍩 Work Order Execution Status", font=dict(size=16, color="#F8FAFC")),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        legend=dict(font=dict(color="#F8FAFC")),
        margin=dict(l=20, r=20, t=50, b=40),
        height=350
    )
    return fig


def chart_work_orders_by_sector(ops_metrics: Dict[str, Any]) -> go.Figure:
    """Horizontal bar chart of Work Orders by Sector."""
    sector_data = ops_metrics.get("work_orders_by_sector", {})
    delayed_by_sec = ops_metrics.get("delayed_by_sector", {})
    if not sector_data:
        return create_empty_figure("Work Orders by Sector", "No sector data available")

    df_list = []
    for sec, count in sector_data.items():
        del_cnt = delayed_by_sec.get(sec, 0)
        df_list.append({
            "Sector": sec,
            "Total Orders": count,
            "Delayed Orders": del_cnt,
            "Healthy Orders": count - del_cnt
        })

    df = pd.DataFrame(df_list).sort_values("Total Orders", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["Sector"],
            x=df["Healthy Orders"],
            name="On Track / Completed",
            orientation="h",
            marker_color="#10B981"
        )
    )
    fig.add_trace(
        go.Bar(
            y=df["Sector"],
            x=df["Delayed Orders"],
            name="Delayed / At Risk",
            orientation="h",
            marker_color="#EF4444"
        )
    )

    fig.update_layout(
        barmode="stack",
        title=dict(text="🏗️ Work Orders by Sector & Health", font=dict(size=16, color="#F8FAFC")),
        xaxis=dict(title="Order Count", color="#94A3B8", gridcolor="#334155"),
        yaxis=dict(title="", color="#F8FAFC"),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        legend=dict(font=dict(color="#F8FAFC"), orientation="h", y=1.05, x=0.5, xanchor="center"),
        margin=dict(l=20, r=20, t=50, b=40),
        height=350
    )
    return fig


def chart_work_order_timeline(ops_metrics: Dict[str, Any]) -> go.Figure:
    """Gantt / Timeline chart for work orders where start & end dates exist."""
    timeline_records = ops_metrics.get("timeline_data", [])
    coverage = ops_metrics.get("timeline_coverage", {})
    coverage_pct = coverage.get("coverage_pct", 0.0)

    if not timeline_records or coverage_pct < 10.0:
        return create_empty_figure(
            "Work Order Execution Timeline",
            f"Timeline unavailable: only {len(timeline_records)} orders ({coverage_pct}%) have usable date ranges."
        )

    df = pd.DataFrame(timeline_records[:20])  # limit to top 20 for readability
    df["Start"] = pd.to_datetime(df["start_date"])
    df["End"] = pd.to_datetime(df["end_date"])

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="End",
        y="deal_name",
        color="execution_status",
        color_discrete_map={"Completed": "#10B981", "In Progress": "#38BDF8", "Delayed": "#EF4444"},
        hover_data=["sector", "region"]
    )

    fig.update_layout(
        title=dict(text=f"⏱️ Work Order Timeline (Top {len(df)} Orders)", font=dict(size=16, color="#F8FAFC")),
        xaxis=dict(title="Execution Window", color="#94A3B8", gridcolor="#334155"),
        yaxis=dict(title="", color="#F8FAFC", autorange="reversed"),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        margin=dict(l=20, r=20, t=50, b=40),
        height=380
    )
    return fig


def chart_billing_collection_funnel(ops_metrics: Dict[str, Any]) -> go.Figure:
    """Financial Funnel: Billed Value -> Collected Amount -> Outstanding Receivables."""
    fin = ops_metrics.get("financial_summary", {})
    billed = fin.get("total_billed_value", 0.0)
    collected = fin.get("total_collected_amount", 0.0)
    receivables = fin.get("total_amount_receivable", 0.0)

    if billed == 0 and collected == 0 and receivables == 0:
        return create_empty_figure("Billing → Collection Flow", "No financial data populated on Work Orders")

    stages = ["Billed Value", "Collected Amount", "Outstanding Receivables"]
    values = [billed, collected, receivables]

    fig = go.Figure(
        go.Funnel(
            y=stages,
            x=values,
            textinfo="value+percent initial",
            marker=dict(color=["#38BDF8", "#10B981", "#F59E0B"]),
            hovertemplate="<b>%{y}</b><br>Amount: $%{x:,.0f}<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(text="💵 Billing → Collection Funnel", font=dict(size=16, color="#F8FAFC")),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        margin=dict(l=20, r=20, t=50, b=40),
        height=350
    )
    return fig


def chart_invoice_collection_status(ops_metrics: Dict[str, Any]) -> go.Figure:
    """Stacked bar chart showing status counts across Invoice and Collection fields."""
    inv_data = ops_metrics.get("invoice_status_breakdown", {})
    col_data = ops_metrics.get("collection_status_breakdown", {})

    if not inv_data and not col_data:
        return create_empty_figure("Invoice & Collection Status", "No status records available")

    fig = go.Figure()
    if inv_data:
        fig.add_trace(
            go.Bar(
                x=list(inv_data.keys()),
                y=list(inv_data.values()),
                name="Invoice Status",
                marker_color="#818CF8"
            )
        )
    if col_data:
        fig.add_trace(
            go.Bar(
                x=list(col_data.keys()),
                y=list(col_data.values()),
                name="Collection Status",
                marker_color="#34D399"
            )
        )

    fig.update_layout(
        title=dict(text="📑 Invoice & Collection Statuses", font=dict(size=16, color="#F8FAFC")),
        xaxis=dict(title="Status", color="#94A3B8", gridcolor="#334155"),
        yaxis=dict(title="Order Count", color="#94A3B8", gridcolor="#334155"),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        legend=dict(font=dict(color="#F8FAFC")),
        margin=dict(l=20, r=20, t=50, b=40),
        height=350
    )
    return fig

