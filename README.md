# MacroIntel agent

A command-line macro/markets analyst that runs on Claude. It pulls US data from FRED, searches the web for central-bank news and market pricing, and gives a sourced view of the growth/inflation regime along with the bias that follows for equities, duration, credit, the dollar and commodities.

## Run

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # or run `ant auth login`
export FRED_API_KEY=...        # free: https://fred.stlouisfed.org/docs/api/api_key.html
python -m macro_agent.agent "What regime are we in, and what does it mean for bonds?"
```

After the first answer you can keep asking follow-ups in the same session. Ctrl-D quits.

## How it works

- `macro_agent/agent.py` runs a manual tool-use loop on `claude-opus-5-5`. It streams the answer, uses adaptive thinking at `high` effort, and handles `pause_turn` for long web searches. It also sets `fallbacks: "default"`, so if the safety classifiers decline a request, another model answers it instead of the request failing.
- `macro_agent/tools.py` defines three client-side tools:
  - `regime_snapshot`: a fixed dashboard of 10 FRED series with each one's latest value and 6-month change.
  - `fred_series`: fetches any single series, with transforms such as year-over-year change.
  - `fred_search`: finds series IDs by keyword.

  Web search runs on Anthropic's servers.
- To add a tool, write a function, add its schema to `TOOLS`, and register it in `HANDLERS`.

## Test

`pytest` runs offline. FRED and the Claude API are both stubbed.
