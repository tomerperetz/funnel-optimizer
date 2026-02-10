---
description: Initialize a campaign from config JSON — creates DB records and generates approval report
argument: Path to campaign config JSON file (exported from the init form)
---

Run the campaign init pipeline on the provided config file:

1. Read and validate the config JSON at `$ARGUMENTS`
2. Run `funnel campaign init $ARGUMENTS`
3. Show the user the generated report path
4. Ask if they want to review and approve the content variants

If no file path is provided, check `reports/` for recent `campaign-config-*.json` files and ask which one to use.

After successful init, present the next steps:
- Open the HTML report for review
- Approve each content variant with `funnel content approve <id>`
- Create campaigns with `funnel campaign create <id>`
