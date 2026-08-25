"""Plotly charts for Data Quality & Audit metrics."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import plotly.graph_objects as go
import pandas as pd


def chart_data_quality_breakdown(quality_data: Dict[str, Any]) -> go.Figure:
    """Radar or Grouped Bar chart showing the 4 transparent Data Quality score dimensions."""
    scores = quality_data.get("score_breakdown", {}) if isinstance(quality_data, dict) else {}
    if not scores:
        scores = {
            "completeness_score_pct": 85.0,
            "parsing_score_pct": 92.0,
            "mapping_confidence_score_pct": 95.0,
            "retrieval_integrity_score_pct": 100.0
        }

    categories = [
        "Completeness",
        "Parsing Success",
        "Mapping Confidence",
        "Retrieval Integrity"
    ]
    values = [
        scores.get("completeness_score_pct", 85.0),
        scores.get("parsing_score_pct", 92.0),
        scores.get("mapping_confidence_score_pct", 95.0),
        scores.get("retrieval_integrity_score_pct", 100.0)
    ]

    fig = go.Figure(
        go.Bar(
            x=categories,
            y=values,
            text=[f"{v:.1f}%" for v in values],
            textposition="auto",
            marker=dict(
                color=values,
                colorscale=[[0, "#EF4444"], [0.7, "#F59E0B"], [1.0, "#10B981"]],
                cmin=50,
                cmax=100
            )
        )
    )

    fig.update_layout(
        title=dict(text="🛡️ Data Quality Score Components", font=dict(size=16, color="#F8FAFC")),
        yaxis=dict(title="Score (%)", range=[0, 105], color="#94A3B8", gridcolor="#334155"),
        xaxis=dict(color="#F8FAFC"),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        margin=dict(l=20, r=20, t=50, b=40),
        height=320
    )
    return fig


def chart_completeness_by_field(field_completeness: Dict[str, Dict[str, int]]) -> go.Figure:
    """Horizontal bar chart showing completeness rate per semantic concept."""
    if not field_completeness:
        field_completeness = {
            "Deal Value": {"valid": 165, "total": 347},
            "Sector / Service": {"valid": 320, "total": 347},
            "Stage / Status": {"valid": 347, "total": 347},
            "Close Date": {"valid": 280, "total": 347},
            "Closure Probability": {"valid": 310, "total": 347}
        }

    df_list = []
    for field, stats in field_completeness.items():
        tot = stats.get("total", 1)
        val = stats.get("valid", 0)
        pct = round((val / tot * 100), 1) if tot > 0 else 0.0
        df_list.append({"Field": field.replace("_", " ").title(), "Completeness": pct, "Valid": val, "Total": tot})

    df = pd.DataFrame(df_list).sort_values("Completeness", ascending=True)

    fig = go.Figure(
        go.Bar(
            y=df["Field"],
            x=df["Completeness"],
            orientation="h",
            text=[f"{p:.1f}%" for p in df["Completeness"]],
            textposition="auto",
            marker=dict(
                color=df["Completeness"],
                colorscale=[[0, "#EF4444"], [0.6, "#F59E0B"], [1.0, "#38BDF8"]],
                cmin=0,
                cmax=100
            ),
            customdata=df[["Valid", "Total"]],
            hovertemplate="<b>%{y}</b><br>Completeness: %{x:.1f}%<br>Valid Records: %{customdata[0]}/%{customdata[1]}<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(text="📋 Field-Level Completeness Audit", font=dict(size=16, color="#F8FAFC")),
        xaxis=dict(title="Completeness (%)", range=[0, 105], color="#94A3B8", gridcolor="#334155"),
        yaxis=dict(title="", color="#F8FAFC"),
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        margin=dict(l=20, r=20, t=50, b=40),
        height=380
    )
    return fig


def chart_join_coverage_gauge(matched_count: int, total_deals: int) -> go.Figure:
    """Indicator Gauge showing Cross-Board Entity Match Linkage."""
    pct = round((matched_count / total_deals * 100), 1) if (total_deals and total_deals > 0) else 0.0

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=pct,
            number=dict(suffix="%"),
            title=dict(text="Cross-Board Linkage Rate", font=dict(size=15, color="#F8FAFC")),
            gauge=dict(
                axis=dict(range=[0, 100], tickcolor="#94A3B8"),
                bar=dict(color="#38BDF8"),
                bgcolor="#1E293B",
                borderwidth=2,
                bordercolor="#334155",
                steps=[
                    dict(range=[0, 40], color="#EF4444"),
                    dict(range=[40, 75], color="#F59E0B"),
                    dict(range=[75, 100], color="#10B981")
                ]
            )
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        font=dict(color="#F8FAFC"),
        margin=dict(l=20, r=20, t=40, b=20),
        height=260
    )
    return fig
