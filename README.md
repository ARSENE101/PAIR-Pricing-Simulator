# PAIR Pricing Simulator

A Streamlit research prototype for comparing four candidate pricing models.

## Includes
- Shared inputs for vehicle class, verified passenger-seat capacity, distance, duration, passenger count, scenario, and detour.
- Explanatory help text beside each input.
- Formula-specific mandatory inputs; incomplete formulas do not calculate.
- Formula A: base + distance + time benchmark.
- Formula B: driver target allocation.
- Formula C: simplified route-segment allocation.
- Formula D: passenger joining an existing route.
- Side-by-side comparison, chart, difference in naira and percentage.
- CSV export and Excel export including trip assumptions.

## Run
Requires Python 3.10+.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Important
This is a research prototype, not production fare-setting software. User-entered rates are assumptions unless supported by evidence. Formula A is not a reproduction of Uber, Bolt or Yango's proprietary algorithms. Formula C is currently a simplified segment model.
