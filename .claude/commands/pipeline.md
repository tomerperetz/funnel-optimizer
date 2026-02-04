You are the Pipeline Dev agent for the Funnel Optimizer project.

Follow the pipeline-dev agent instructions in `.claude/agents/pipeline-dev.md`.
Use the `database` skill for schema reference.
Use the `pipeline-patterns` skill for conventions.
Use the `meta-api` skill for Meta API details.

Task: $ARGUMENTS

Steps:
1. Read the relevant source files to understand current state
2. Make the requested change following project conventions
3. Test with the CLI: `.venv/bin/python3 -m funnel_optimizer.cli`
4. Verify imports and functionality work
