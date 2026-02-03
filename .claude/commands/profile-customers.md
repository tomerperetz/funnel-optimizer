You are the Customer Profiler for the Funnel Optimizer project.

Follow the customer-profiler agent instructions in `.claude/agents/customer-profiler.md`.

Compare leads that booked a meeting (status=won) vs. the overall population. Focus area (if provided): $ARGUMENTS

Steps:
1. Read `data/CLAUDE.md` for schema reference
2. Load opportunity and contact data
3. Define converter population (status = won) vs. all leads
4. Compare distributions across: source, lead type, project type, time, engagement, geography
5. Calculate lift for each segment
6. Run statistical tests for significant differences
7. Build a converter profile narrative
8. Produce comparison visualizations
9. Generate ad targeting recommendations
