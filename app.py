import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="PAIR Pricing Simulator", layout="wide")
st.title("PAIR Pricing Simulator")
st.caption("Research prototype. User-entered rates are assumptions unless independently validated.")
st.warning("Every formula has required inputs. Missing inputs are not silently replaced with market rates.")

VEHICLES = {
    "Small sedan": 4,
    "Comfort sedan": 4,
    "SUV / crossover": 4,
    "Minivan": 6,
    "Other / custom": None,
}

with st.sidebar:
    st.header("Shared trip inputs")
    vehicle = st.selectbox("Vehicle class", list(VEHICLES), help="Vehicle class can affect seat capacity and eventually class-specific rates.")
    default_seats = VEHICLES[vehicle] or 4
    seats = st.number_input("Verified passenger seats (excluding driver)", min_value=1, max_value=12, value=default_seats,
                            help="Enter the verified legal and usable capacity of this particular vehicle.")
    distance = st.number_input("Trip distance (km)", min_value=0.1, value=36.0, step=1.0,
                               help="Estimated route distance for the passenger-serving trip.")
    duration = st.number_input("Trip duration (minutes)", min_value=1.0, value=70.0, step=5.0,
                               help="Estimated journey time. Use one consistent rule for expected traffic and pickup time.")
    passengers = st.number_input("Expected paying passengers", min_value=1, max_value=int(seats), value=min(2, int(seats)),
                                 help="Number of paying passengers expected. Cannot exceed verified passenger-seat capacity.")
    scenario = st.selectbox("Scenario", [
        "Shared trip — driver is serving passengers",
        "Private ride / ride-hailing benchmark",
        "Passenger joins a driver already travelling"
    ])
    detour = st.number_input("Additional detour (km)", min_value=0.0, value=0.0, step=0.5,
                             help="Extra distance caused by pickup/drop-off.")
    st.divider()
    st.subheader("Platform accounting assumptions")
    commission_pct = st.number_input("PAIR commission (% of fare pool)", min_value=0.0, max_value=99.0, value=0.0, step=0.5,
                                     help="PAIR's percentage fee. Use 0 only if no commission is being tested.")
    fee_mode = st.radio("Commission treatment", ["Deduct from driver fare pool", "Charge on top to passengers"],
                        help="Deduct: commission reduces driver payout. On top: the driver receives the fare pool and the fee is charged separately.")
    txn_pct = st.number_input("Payment transaction cost (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1,
                              help="Use a provider tariff or explicitly labelled assumption.")
    txn_fixed = st.number_input("Fixed transaction cost per booking (₦)", min_value=0.0, value=0.0, step=10.0,
                                help="Fixed provider charge allocated to this booking.")

st.subheader("Formula-specific inputs")
st.write("Complete all required fields for each formula you want calculated. Help text explains what each value means.")
tabs = st.tabs(["A · Ride-hailing baseline", "B · Driver target allocation", "C · Route segments", "D · Already travelling"])

with tabs[0]:
    st.markdown("### Formula A — base + distance + time")
    st.latex(r"P_A=\\max(P_{min}, B+r_dD+r_tT+A)")
    st.caption("A conventional benchmark structure, not a reproduction of Uber, Bolt or Yango's proprietary algorithm.")
    a_base = st.number_input("Base fare (₦)", min_value=0.0, value=None, placeholder="Required", key="a_base",
                             help="Starting charge before distance and time components. Record the source or rationale.")
    a_km = st.number_input("Distance rate (₦/km)", min_value=0.0, value=None, placeholder="Required", key="a_km",
                           help="Fare contribution per kilometre. Enter a tested assumption or researched local rate.")
    a_minute = st.number_input("Time rate (₦/minute)", min_value=0.0, value=None, placeholder="Required", key="a_minute",
                               help="Fare contribution per minute. Avoid double-counting time if already included elsewhere.")
    a_floor = st.number_input("Minimum fare (₦)", min_value=0.0, value=None, placeholder="Required", key="a_floor",
                              help="Minimum fare allowed even if the distance/time calculation is lower.")
    a_adjust = st.number_input("Other disclosed adjustments (₦)", value=None, placeholder="Required", key="a_adjust",
                               help="Combined adjustment for permitted items such as tolls or a defined demand adjustment. Enter 0 if none.")
with tabs[1]:
    st.markdown("### Formula B — driver target allocation")
    st.latex(r"F_i=\\frac{G_{driver}}{N(1-c)}")
    st.caption("Treats the driver target as desired payout after a commission deducted from the fare pool.")
    b_target = st.number_input("Driver whole-trip payout target (₦)", min_value=0.0, value=None, placeholder="Required", key="b_target",
                               help="Amount the driver should receive after PAIR commission if commission is deducted. Separate this from operating costs.")
    b_floor = st.number_input("Minimum total passenger fare (₦)", min_value=0.0, value=None, placeholder="Required", key="b_floor",
                              help="Minimum total fare pool for the trip. Enter 0 if you are testing no minimum.")
with tabs[2]:
    st.markdown("### Formula C — simplified route-segment sharing")
    st.latex(r"F_i=E_i+\\frac{S_i}{N_i}")
    st.caption("A simplified model: exclusive segment allocation plus a share of the value assigned to shared segments.")
    c_exclusive = st.number_input("Passenger's exclusive-segment allocation (₦)", min_value=0.0, value=None, placeholder="Required", key="c_exclusive",
                                  help="Fare value allocated to route segments used only by this passenger. Enter 0 if there are none.")
    c_shared = st.number_input("Total allocation for shared segments (₦)", min_value=0.0, value=None, placeholder="Required", key="c_shared",
                               help="Total fare value allocated to segments shared with other passengers; not automatically the driver's target.")
    c_n = st.number_input("Passengers sharing these segments", min_value=1, max_value=int(seats), value=None, placeholder="Required", key="c_n",
                          help="Number of paying passengers using these shared segments.")
    c_floor = st.number_input("Minimum fare per passenger (₦)", min_value=0.0, value=None, placeholder="Required", key="c_floor",
                              help="Lowest fare allowed for an individual passenger under this model.")
with tabs[3]:
    st.markdown("### Formula D — joining an existing route")
    st.latex(r"F_D=C_{incremental}+V_{time}+S_{seat}")
    st.caption("For a passenger joining a trip the driver was already making, not the main model for a driver making a trip specifically to serve passengers.")
    d_cost = st.number_input("Incremental operating cost (₦)", min_value=0.0, value=None, placeholder="Required", key="d_cost",
                             help="Extra fuel, wear and other costs caused by carrying this passenger, including detour costs. Do not include the whole original trip cost without justification.")
    d_time = st.number_input("Extra time / coordination value (₦)", min_value=0.0, value=None, placeholder="Required", key="d_time",
                             help="Value assigned to additional waiting, pickup, drop-off and coordination.")
    d_seat = st.number_input("Seat / service contribution (₦)", min_value=0.0, value=None, placeholder="Required", key="d_seat",
                             help="Contribution for making the seat and service available. This is a testing input, not a validated market rate.")
    d_floor = st.number_input("Minimum passenger fare (₦)", min_value=0.0, value=None, placeholder="Required", key="d_floor",
                              help="Minimum fare allowed for this passenger.")

def money(x):
    return f"₦{x:,.2f}"

def accounting(total_fares):
    c = commission_pct / 100
    commission = total_fares * c
    if fee_mode == "Deduct from driver fare pool":
        driver = total_fares - commission
        added_fee = 0.0
    else:
        driver = total_fares
        added_fee = commission
    processed = total_fares + added_fee
    txn = processed * txn_pct / 100 + txn_fixed
    return driver, commission, txn, commission - txn, added_fee

if st.button("Calculate and compare formulas", type="primary", use_container_width=True):
    rows, missing = [], []
    def add_result(name, fare_each, total, note):
        driver, pair_rev, txn, contribution, added_fee = accounting(total)
        rows.append({
            "Formula": name,
            "Fare per passenger (₦)": fare_each,
            "Total fare pool (₦)": total,
            "Driver payout (₦)": driver,
            "PAIR gross revenue (₦)": pair_rev,
            "Transaction costs (₦)": txn,
            "PAIR contribution after transaction costs (₦)": contribution,
            "Added-on PAIR fee (₦)": added_fee,
            "Notes": note,
        })

    if all(v is not None for v in [a_base, a_km, a_minute, a_floor, a_adjust]):
        total = max(a_floor, a_base + a_km * distance + a_minute * duration + a_adjust)
        if scenario == "Shared trip — driver is serving passengers":
            add_result("A — Ride-hailing baseline", total / passengers, total, "Ride total split equally for shared scenario")
        else:
            add_result("A — Ride-hailing baseline", total, total, "Calculated as one ride fare")
    else:
        missing.append("Formula A needs base fare, distance rate, time rate, minimum fare, and other adjustments.")

    if all(v is not None for v in [b_target, b_floor]):
        c = commission_pct / 100
        if fee_mode == "Deduct from driver fare pool":
            total = max(b_floor, b_target / (1 - c))
        else:
            total = max(b_floor, b_target)
        add_result("B — Driver target allocation", total / passengers, total,
                   "Driver target is treated as payout after commission when commission is deducted.")
    else:
        missing.append("Formula B needs driver payout target and minimum total passenger fare.")

    if all(v is not None for v in [c_exclusive, c_shared, c_n, c_floor]):
        each = max(c_floor, c_exclusive + c_shared / c_n)
        add_result("C — Route-segment sharing", each, each * passengers,
                   "Simplified allocation; entered per-passenger segment structure is applied to each passenger.")
    else:
        missing.append("Formula C needs exclusive allocation, shared allocation, shared-segment passenger count, and minimum fare.")

    if all(v is not None for v in [d_cost, d_time, d_seat, d_floor]):
        each = max(d_floor, d_cost + d_time + d_seat)
        add_result("D — Already travelling", each, each * passengers,
                   "Contribution model for passenger(s) joining an existing route.")
    else:
        missing.append("Formula D needs incremental cost, extra time value, seat contribution, and minimum fare.")

    if missing:
        st.error("Some formulas were not calculated because required inputs are missing.")
        for m in missing:
            st.write(f"- {m}")
    if rows:
        df = pd.DataFrame(rows)
        st.subheader("Side-by-side results")
        formatted = df.copy()
        for col in [c for c in formatted.columns if "(₦)" in c]:
            formatted[col] = formatted[col].map(money)
        st.dataframe(formatted, use_container_width=True, hide_index=True)
        st.subheader("Passenger fare comparison")
        st.bar_chart(df.set_index("Formula")[["Fare per passenger (₦)"]])
        if len(df) > 1:
            low = df["Fare per passenger (₦)"].min()
            diff = df[["Formula", "Fare per passenger (₦)"]].copy()
            diff["Difference from lowest (₦)"] = diff["Fare per passenger (₦)"] - low
            diff["Difference from lowest (%)"] = diff["Difference from lowest (₦)"] / low * 100 if low else 0
            st.dataframe(diff.style.format({
                "Fare per passenger (₦)": "₦{:,.2f}",
                "Difference from lowest (₦)": "₦{:,.2f}",
                "Difference from lowest (%)": "{:.2f}%"
            }), use_container_width=True, hide_index=True)
        st.download_button("Download results as CSV", df.to_csv(index=False).encode("utf-8-sig"),
                           file_name="pair_pricing_comparison.csv", mime="text/csv")
        assumptions = pd.DataFrame([
            {"Input": "Vehicle class", "Value": vehicle},
            {"Input": "Verified passenger seats", "Value": int(seats)},
            {"Input": "Distance (km)", "Value": distance},
            {"Input": "Duration (minutes)", "Value": duration},
            {"Input": "Paying passengers", "Value": int(passengers)},
            {"Input": "Scenario", "Value": scenario},
            {"Input": "Detour (km)", "Value": detour},
            {"Input": "PAIR commission (%)", "Value": commission_pct},
            {"Input": "Commission treatment", "Value": fee_mode},
            {"Input": "Transaction cost (%)", "Value": txn_pct},
            {"Input": "Fixed transaction cost (₦)", "Value": txn_fixed},
        ])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Formula Results")
            assumptions.to_excel(writer, index=False, sheet_name="Trip Assumptions")
        st.download_button("Download results + assumptions as Excel", output.getvalue(),
                           file_name="pair_pricing_comparison.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.divider()
st.subheader("Interpretation notes")
st.markdown("""
- Formula A is a configurable benchmark, not a reproduction of any ride-hailing company's proprietary engine.
- Formula B assumes passengers share the same route and the driver's target is a payout target.
- Formula C is a simplified segment-allocation model, not a full route optimiser.
- Formula D is for a passenger joining a journey already planned by the driver.
- Revenue, driver payout and transaction costs are separated. Confirm the accounting policy before using these values for real settlement.
- No input is represented as a validated Nigerian market rate.
""")

