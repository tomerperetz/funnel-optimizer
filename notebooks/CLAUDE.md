# Notebooks Directory

Jupyter notebooks for exploration and analysis. This is the primary workspace.

## Conventions

- **Naming:** `XX-description.ipynb` (e.g., `01-data-exploration.ipynb`)
- **First cell:** Always import pandas and load data using the pattern from `data/CLAUDE.md`
- **Structure:** One clear question per notebook. Split into sections with markdown headers.
- **Output:** Keep outputs in the notebook for reference. Clear only when re-running from scratch.

## Visualization Style

- Use seaborn for statistical plots, matplotlib for custom charts
- Always label axes and add titles
- Use consistent color palette across notebooks
- For funnel charts: vertical bar charts with conversion % annotations

## Promotion to src/

When a notebook produces reusable logic (data loading, transformations, plotting utilities), extract it to `src/funnel_optimizer/`. Only promote code that has been used in 2+ notebooks or is clearly reusable.
