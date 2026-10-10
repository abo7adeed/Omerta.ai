"""Dynamic Matplotlib Visualization Engine for Omerta.ai Agentic RAG.

Design Standards:
- Corporate Sapphire/Gold design system:
  Sapphire (#002D72), Gold (#F9A825), Emerald (#10B981), Royal Blue (#1E88E5).
- High-resolution (300 DPI or 150 DPI balanced) crisp rendering with clear axes,
  currency formatting, titles, and legends.
- Secure artifact storage with unguessable artifact IDs.
- Deterministic rendering from validated ChartSpecification models.
- Graceful error handling (returns None if rendering fails, leaving text response intact).
"""

import logging
from pathlib import Path
from uuid import uuid4

from domain.agentic_rag.schemas import ChartArtifactReference, ChartSpecification, ChartType

logger = logging.getLogger(__name__)

# Primary Corporate Palette
PALETTE = ["#002D72", "#F9A825", "#10B981", "#1E88E5", "#7C3AED", "#EF4444", "#0D9488"]
BG_COLOR = "#FFFFFF"
GRID_COLOR = "#E2E8F0"
TEXT_COLOR = "#0A192F"

# Ensure storage directory exists
ARTIFACTS_DIR = Path("apps/api/static/artifacts/charts").resolve()
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


class VisualizationEngine:
    """Matplotlib rendering service for authorized financial analytics."""

    @staticmethod
    def render_chart(spec: ChartSpecification) -> ChartArtifactReference | None:
        """Render a ChartSpecification into an isolated PNG artifact."""
        try:
            import matplotlib
            matplotlib.use("Agg")  # Non-interactive backend
            import matplotlib.pyplot as plt
            import matplotlib.ticker as ticker
        except ImportError as exc:
            logger.warning("Matplotlib is not installed: %s. Visualization will be skipped gracefully.", exc)
            return None

        artifact_id = f"chart-{uuid4().hex[:12]}"
        output_path = ARTIFACTS_DIR / f"{artifact_id}.png"

        try:
            plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
            fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150, facecolor=BG_COLOR)
            ax.set_facecolor(BG_COLOR)

            # Title & Axis labels
            ax.set_title(spec.title, fontsize=13, fontweight="bold", color=TEXT_COLOR, pad=14)
            if spec.x_axis_label:
                ax.set_xlabel(spec.x_axis_label, fontsize=10, fontweight="medium", color="#475569", labelpad=8)
            if spec.y_axis_label:
                ax.set_ylabel(spec.y_axis_label, fontsize=10, fontweight="medium", color="#475569", labelpad=8)

            ax.grid(True, linestyle="--", alpha=0.5, color=GRID_COLOR)

            colors = spec.palette or PALETTE

            # Render by chart type
            if spec.chart_type == ChartType.LINE:
                for idx, s in enumerate(spec.series):
                    color = s.color or colors[idx % len(colors)]
                    x_vals = spec.categories if spec.categories else list(range(len(s.data)))
                    ax.plot(x_vals, s.data, marker="o", linewidth=2.4, markersize=5, label=s.name, color=color)
                if len(spec.series) > 1 or (spec.series and spec.series[0].name != "Values"):
                    ax.legend(frameon=True, facecolor="#F8FAFC", edgecolor=GRID_COLOR, fontsize=9)

            elif spec.chart_type == ChartType.BAR:
                import numpy as np
                x = np.arange(len(spec.categories))
                width = 0.8 / max(len(spec.series), 1)
                for idx, s in enumerate(spec.series):
                    color = s.color or colors[idx % len(colors)]
                    offset = (idx - (len(spec.series) - 1) / 2) * width
                    ax.bar(x + offset, s.data, width, label=s.name, color=color, edgecolor="#CBD5E1", linewidth=0.5)
                ax.set_xticks(x)
                ax.set_xticklabels(spec.categories, rotation=25 if len(spec.categories) > 5 else 0, ha="right" if len(spec.categories) > 5 else "center")
                if len(spec.series) > 1:
                    ax.legend(frameon=True, facecolor="#F8FAFC", edgecolor=GRID_COLOR, fontsize=9)

            elif spec.chart_type == ChartType.AREA:
                import numpy as np
                x_vals = spec.categories if spec.categories else [f"T{i+1}" for i in range(len(spec.series[0].data if spec.series else []))]
                for idx, s in enumerate(spec.series):
                    color = s.color or colors[idx % len(colors)]
                    x_indices = np.arange(len(x_vals))
                    ax.plot(x_indices, s.data, marker="o", markersize=4, linewidth=2.2, label=s.name, color=color)
                    ax.fill_between(x_indices, s.data, color=color, alpha=0.25)
                ax.set_xticks(range(len(x_vals)))
                ax.set_xticklabels(x_vals, rotation=20 if len(x_vals) > 5 else 0, ha="right" if len(x_vals) > 5 else "center")
                if len(spec.series) > 1 or (spec.series and spec.series[0].name != "Values"):
                    ax.legend(frameon=True, facecolor="#F8FAFC", edgecolor=GRID_COLOR, fontsize=9)

            elif spec.chart_type == ChartType.HORIZONTAL_BAR:
                import numpy as np
                y = np.arange(len(spec.categories))
                s = spec.series[0] if spec.series else None
                if s:
                    color = s.color or colors[0]
                    bars = ax.barh(y, s.data, color=color, edgecolor="#CBD5E1", height=0.55)
                    # Add data labels
                    for bar in bars:
                        w = bar.get_width()
                        ax.text(w + (max(s.data) * 0.02 if s.data else 1), bar.get_y() + bar.get_height() / 2, f"{w:,.0f}", va="center", ha="left", fontsize=9, fontweight="bold", color="#1E293B")
                ax.set_yticks(y)
                ax.set_yticklabels(spec.categories)
                ax.invert_yaxis()

            elif spec.chart_type in (ChartType.PIE, ChartType.DONUT):
                s = spec.series[0] if spec.series else None
                if s and s.data:
                    wedges, texts, autotexts = ax.pie(
                        s.data,
                        labels=spec.categories if spec.categories else None,
                        colors=colors[:len(s.data)],
                        autopct="%1.1f%%",
                        pctdistance=0.75 if spec.chart_type == ChartType.DONUT else 0.6,
                        startangle=140,
                        wedgeprops=dict(width=0.45 if spec.chart_type == ChartType.DONUT else 1.0, edgecolor="#FFFFFF", linewidth=1.8),
                    )
                    for at in autotexts:
                        at.set_fontsize(9)
                        at.set_fontweight("bold")
                        at.set_color("#1E293B")
                    for t in texts:
                        t.set_fontsize(9)
                        t.set_color("#334155")

            elif spec.chart_type == ChartType.HISTOGRAM:
                s = spec.series[0] if spec.series else None
                if s and s.data:
                    color = s.color or colors[0]
                    ax.hist(s.data, bins=min(len(s.data), 10), color=color, edgecolor="#FFFFFF", alpha=0.85)

            elif spec.chart_type == ChartType.SCATTER:
                s = spec.series[0] if spec.series else None
                if s and s.data:
                    x_vals = spec.categories if spec.categories else list(range(len(s.data)))
                    color = s.color or colors[0]
                    ax.scatter(x_vals, s.data, color=color, s=40, alpha=0.8, edgecolors="#1E293B")

            plt.tight_layout()
            fig.savefig(str(output_path), format="png", bbox_inches="tight", facecolor=BG_COLOR)
            plt.close(fig)

            summary = f"{spec.title} ({spec.chart_type.value.upper()}) over {len(spec.categories)} categories"
            return ChartArtifactReference(
                chart_id=f"cht-{uuid4().hex[:8]}",
                chart_type=spec.chart_type,
                title=spec.title,
                artifact_id=artifact_id,
                artifact_url=f"/api/v1/agentic-rag/artifacts/{artifact_id}",
                data_summary=summary,
                citations=[],
            )

        except Exception as exc:
            logger.exception("Failed to render chart: %s", exc)
            return None
