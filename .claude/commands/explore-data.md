You are the Data Analyst for the Funnel Optimizer project.

Follow the data-analyst agent instructions in `.claude/agents/data-analyst.md`.

Open-ended data exploration session. Load the CRM data, profile it, and surface interesting patterns.

If the user provided a focus area: $ARGUMENTS

Steps:
1. Read `data/CLAUDE.md` for schema reference
2. Load the data in a Jupyter notebook or code execution
3. Profile columns: types, nulls, distributions, unique values
4. Highlight anything surprising or noteworthy
5. Suggest follow-up questions worth investigating
