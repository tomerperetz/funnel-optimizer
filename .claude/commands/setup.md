Initialize the Funnel Optimizer development environment.

Steps:
1. Check that `.venv/` exists, create if needed: `python3 -m venv .venv`
2. Install dependencies: `.venv/bin/pip install -e ".[dev]"`
3. Initialize the database: `.venv/bin/python3 -m funnel_optimizer.cli db init`
4. Check for `.env` file — if missing, copy from `.env.example` and warn user to fill in Meta API credentials
5. Run `.venv/bin/python3 -m funnel_optimizer.cli db status` to confirm everything works
6. Report status to user
