"""Print the H4 nested-blend component choices per refit (latest last) for a dataset, so the live `blend_nested` entry
(config/strategies.json, which runs `blend` with explicit components) can be updated at each 60-day refit.

    nice -n 19 .venv/bin/python -m scripts.nested_choice hl      # or bnall
"""
import sys

from kripto import data, strategies as st

if __name__ == "__main__":
    ds = sys.argv[1] if len(sys.argv) > 1 else "hl"
    _, _, log = st.nested_selection(data.load_panel(ds, "1d"))
    for t, ch in log[-6:]:
        print(t.date(), ch)
    print("next refit:", (log[-1][0] + __import__("pandas").Timedelta(days=60)).date())
