# Funnel Optimizer

AI-powered optimization for a home renovation call center. Analyzes GoHighLevel CRM data to improve lead quality, funnel conversion, and meeting booking rates.

## Goals

- **Lead profiling** — Understand top-of-funnel demographics to improve ad targeting
- **Funnel analysis** — Map stage-by-stage conversion and find drop-off points
- **Customer profiling** — Compare converting leads vs. overall population
- **ML insights** — Feature importance, clustering, classification for actionable recommendations

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Data

Place GHL CRM exports in `data/`:
- `contacts_jan_2026.csv`
- `Opportunities (1).csv`

Data files are gitignored and not committed to the repository.

## Usage

Analysis is done primarily in Jupyter notebooks:

```bash
jupyter lab notebooks/
```

### Claude Commands

| Command | Description |
|---------|-------------|
| `/plan` | Orchestrate a high-level analysis goal |
| `/explore-data` | Open-ended data exploration |
| `/funnel` | Funnel conversion analysis |
| `/profile-customers` | Converter vs. population profiling |
| `/ask` | Quick data question |
| `/model` | ML-based analysis |

## Project Structure

```
├── data/               # CRM exports (gitignored)
├── notebooks/          # Jupyter exploration & analysis
├── src/funnel_optimizer/  # Reusable code (promoted from notebooks)
├── docs/plans/         # Design documents
└── .claude/            # Agents, commands, skills
```
