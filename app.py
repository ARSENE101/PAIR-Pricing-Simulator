
import io
import math
import pandas as pd
import streamlit as st

# ============================================================
# PAIR PRICING SIMULATOR — educational prototype
# ============================================================

st.set_page_config(
    page_title="PAIR Pricing Simulator",
    page_icon="🚗",
    layout="wide",
)

st.title("PAIR Pricing Simulator")
st.caption(
    "Explore how different pricing formulas affect passenger fares, "
    "driver earnings, and PAIR's revenue."
)

st.info(
    "This is a pricing experiment, not a production fare engine. "
    "All rates and cost assumptions are editable examples, not verified "
    "Nigerian market prices. Formula C is a simplified segment-allocation model."
)


# ============================================================
# HELPERS
# ============================================================

def naira(value):
    return f"₦{value:,.2f}"


def variable_help(label, meaning, purpose, distinction=None):
    """Consistent explanation format for every formula-specific input."""
    st.markdown(f"**{label}**")
    st.caption(f"What it means: {meaning}")
    st.caption(f"Why it is needed: {purpose}")
    if distinction:
        st.caption(f"How it differs from other inputs: {distinction}")


def notation_table(rows):
    st.markdown("#### Formula notation key")
    st.dataframe(
        pd.DataFrame(rows, columns=["Symbol", "Meaning", "Role in formula"]),
        hide_index=True,
        use_container_width=True,
    )


def breakdown_table(rows):
    st.markdown("#### Calculation breakdown")
    st.dataframe(
        pd.DataFrame(rows, columns=["Step", "Calculation", "Amount"]),
        hide_index=True,
        use_container_width=True,
    )


def fare_accounting(passenger_fare, commission_rate, transaction_rate,
                    transaction_fixed, commission_on="gross_fare"):
    """
    Simplified per-booking accounting.

    The transaction fee is applied to the passenger fare.
    Commission is applied according to the selected treatment.
    Actual provider fees and settlement rules must be verified later.
    """
    transaction_cost = passenger_fare * transaction_rate + transaction_fixed

    if commission_on == "gross_fare":
        commission = passenger_fare * commission_rate
    else:
        commission = max(0, passenger_fare - transaction_cost) * commission_rate

    driver_payout = passenger_fare - commission
    pair_contribution = commission - transaction_cost

    return {
        "Passenger fare": passenger_fare,
        "Driver payout (before other driver costs)": driver_payout,
        "PAIR commission / gross revenue": commission,
        "Payment transaction cost": transaction_cost,
        "PAIR contribution after transaction cost": pair_contribution,
    }


# ============================================================
# SIDEBAR — SHARED INPUTS
# These describe the journey and platform assumptions.
# They are not formula-specific pricing rates.
# ============================================================

st.sidebar.title("Shared trip inputs")
st.sidebar.caption(
    "Enter the facts about the journey once. Relevant formulas reuse them "
    "automatically; you should not need to re-enter the same trip distance "
    "or duration in each formula."
)

vehicle_class = st.sidebar.selectbox(
    "Vehicle class",
    ["Sedan", "SUV", "Minivan", "Other"],
    help="The type of vehicle being used. Vehicle class can affect capacity "
         "and operating costs, but does not itself determine a fare."
)

default_capacity = {
    "Sedan": 4,
    "SUV": 5,
    "Minivan": 7,
    "Other": 4,
}

seat_capacity = st.sidebar.number_input(
    "Passenger-seat capacity",
    min_value=1,
    max_value=20,
    value=default_capacity[vehicle_class],
    help="The number of passenger seats actually available for this trip. "
         "Do not count the driver. Use verified usable capacity, not a "
         "marketing claim about the vehicle."
)

distance_km = st.sidebar.number_input(
    "Driver's total route distance (km)",
    min_value=0.1,
    max_value=2000.0,
    value=36.0,
    step=1.0,
    help="The total route distance for the journey being simulated. "
         "This is a journey fact, not a price per kilometre."
)

duration_min = st.sidebar.number_input(
    "Estimated total route duration (minutes)",
    min_value=1,
    max_value=3000,
    value=70,
    step=5,
    help="The estimated duration of the route. A formula may multiply this "
         "by a time rate, but the duration and the rate are different things."
)

passenger_count = st.sidebar.number_input(
    "Passengers paying for this trip",
    min_value=1,
    max_value=int(seat_capacity),
    value=min(2, int(seat_capacity)),
    step=1,
    help="Number of paying passengers included in the simulated trip. "
         "The driver is excluded. This is not necessarily the maximum "
         "number of seats the vehicle has."
)

scenario = st.sidebar.selectbox(
    "Trip scenario",
    [
        "Private / dedicated ride",
        "Shared trip arranged for passengers",
        "Passenger joins driver's existing route",
    ],
    help="Choose how the trip comes about. An existing-route passenger "
         "should generally pay for incremental burden and the service "
         "received, not automatically the whole original trip."
)

detour_km = st.sidebar.number_input(
    "Additional distance caused by pickup/drop-off (km)",
    min_value=0.0,
    max_value=500.0,
    value=0.0,
    step=0.5,
    help="Extra distance the driver must travel because of the passenger. "
         "This is additional distance, not the entire route distance."
)

detour_minutes = st.sidebar.number_input(
    "Additional time caused by pickup/drop-off (minutes)",
    min_value=0.0,
    max_value=1000.0,
    value=0.0,
    step=5.0,
    help="Extra time caused by collecting, dropping off, or coordinating "
         "the passenger. It is separate from total route duration."
)

st.sidebar.divider()
st.sidebar.subheader("Platform assumptions")

commission_pct = st.sidebar.number_input(
    "PAIR commission (%)",
    min_value=0.0,
    max_value=100.0,
    value=15.0,
    step=1.0,
    help="The percentage PAIR retains as commission under this simulation. "
         "This is an editable assumption, not a validated market rate."
)

commission_treatment = st.sidebar.radio(
    "Commission calculated on",
    ["Gross passenger fare", "Fare after transaction cost"],
    help="Choose whether commission is calculated on the full passenger "
         "fare or after deducting the payment-processing cost."
)

transaction_pct = st.sidebar.number_input(
    "Payment transaction fee (%)",
    min_value=0.0,
    max_value=30.0,
    value=1.5,
    step=0.1,
    help="Assumed payment-provider fee as a percentage of the passenger fare."
)

transaction_fixed = st.sidebar.number_input(
    "Fixed payment fee per booking (₦)",
    min_value=0.0,
    max_value=10000.0,
    value=0.0,
    step=10.0,
    help="Any fixed payment fee charged per booking, in addition to the "
         "percentage fee. Check the actual provider's pricing before launch."
)

commission_rate = commission_pct / 100
transaction_rate = transaction_pct / 100
commission_on = (
    "gross_fare"
    if commission_treatment == "Gross passenger fare"
    else "after_transaction"
)

st.sidebar.divider()
st.sidebar.caption(
    "Reminder: a driver's target earnings, passenger fare, operating cost, "
    "PAIR commission and PAIR contribution are different quantities."
)


# ============================================================
# FORMULA PANELS
# ============================================================

tab_a, tab_b, tab_c, tab_d = st.tabs([
    "Formula A — Baseline",
    "Formula B — Driver target",
    "Formula C — Route segments",
    "Formula D — Existing route",
])

results = {}
formula_notes = {}


# ------------------------------------------------------------
# FORMULA A
# F = max(F_min, B + d*r_d + t*r_t + adjustments)
# ------------------------------------------------------------

with tab_a:
    st.subheader("Formula A — Conventional ride-hailing baseline")
    st.write(
        "This estimates a fare from a starting charge, distance charge, "
        "and time charge. It provides a useful baseline against which "
        "the sharing models can be compared."
    )

    notation_table([
        ("F", "Calculated passenger fare (₦)", "Final fare produced by this model."),
        ("B", "Base fare (₦)", "Starting charge before distance and time."),
        ("d", "Total route distance (km)", "Reused from the sidebar."),
        ("r_d", "Distance rate (₦/km)", "Amount charged for each kilometre."),
        ("t", "Total route duration (minutes)", "Reused from the sidebar."),
        ("r_t", "Time rate (₦/minute)", "Amount charged for each minute."),
        ("F_min", "Minimum fare (₦)", "Lower bound for the calculated fare."),
        ("A", "Additional adjustment (₦)", "Optional positive or negative adjustment."),
    ])

    st.markdown("#### Formula-specific pricing assumptions")
    st.caption(
        "These values define the pricing rule. They are not extra details "
        "about the journey."
    )

    c1, c2 = st.columns(2)
    with c1:
        variable_help(
            "Base fare B (₦)",
            "The starting charge for accepting and providing the ride.",
            "It represents a fixed component that does not grow with each "
            "additional kilometre or minute.",
            "Unlike distance and duration, this is a pricing parameter."
        )
        base_fare = st.number_input(
            "Base fare (₦)",
            min_value=0.0,
            value=500.0,
            step=100.0,
            key="a_base",
        )

        variable_help(
            "Distance rate r_d (₦/km)",
            "The amount charged for each kilometre travelled.",
            "Multiplying it by total route distance produces the distance charge.",
            "The sidebar's distance is measured in km; this rate is measured "
            "in naira per km."
        )
        distance_rate = st.number_input(
            "Distance rate (₦/km)",
            min_value=0.0,
            value=150.0,
            step=10.0,
            key="a_distance_rate",
        )

    with c2:
        variable_help(
            "Time rate r_t (₦/minute)",
            "The amount charged for each minute of route duration.",
            "It adds a time-based component, which can represent time-related "
            "service or operating costs.",
            "The sidebar's duration is minutes; this is the price per minute."
        )
        time_rate = st.number_input(
            "Time rate (₦/minute)",
            min_value=0.0,
            value=10.0,
            step=1.0,
            key="a_time_rate",
        )

        variable_help(
            "Minimum fare F_min (₦)",
            "The lowest fare the model is allowed to return.",
            "It prevents very short trips from producing an uneconomically "
            "small fare.",
            "It is a floor, not an extra charge automatically added to the fare."
        )
        min_fare = st.number_input(
            "Minimum fare (₦)",
            min_value=0.0,
            value=1000.0,
            step=100.0,
            key="a_min_fare",
        )

    variable_help(
        "Additional adjustment A (₦)",
        "An optional net adjustment to the fare, positive or negative.",
        "It lets you test an additional charge or discount without changing "
        "the underlying base, distance, and time rates.",
        "It is a fixed adjustment for this simulation, not the detour distance "
        "or detour time entered in the sidebar."
    )
    adjustment = st.number_input(
        "Additional adjustment (₦)",
        min_value=-100000.0,
        max_value=100000.0,
        value=0.0,
        step=100.0,
        key="a_adjustment",
    )

    raw_fare_a = (
        base_fare
        + distance_km * distance_rate
        + duration_min * time_rate
        + adjustment
    )
    fare_a = max(min_fare, raw_fare_a)

    results["A — Baseline"] = fare_a
    formula_notes["A — Baseline"] = (
        f"Raw fare = {naira(base_fare)} + "
        f"({distance_km:.1f} km × {naira(distance_rate)}/km) + "
        f"({duration_min:.0f} min × {naira(time_rate)}/min) + "
        f"{naira(adjustment)}"
    )

    st.markdown("#### Formula")
    st.latex(
        r"F = \max\left(F_{\min}, B + d r_d + t r_t + A\right)"
    )

    breakdown_table([
        ("Base fare", "B", naira(base_fare)),
        ("Distance charge", f"{distance_km:.1f} × {distance_rate:.2f}",
         naira(distance_km * distance_rate)),
        ("Time charge", f"{duration_min:.0f} × {time_rate:.2f}",
         naira(duration_min * time_rate)),
        ("Adjustment", "A", naira(adjustment)),
        ("Raw fare", "Sum of the above", naira(raw_fare_a)),
        ("Minimum fare check", f"max({naira(min_fare)}, raw fare)", naira(fare_a)),
    ])

    st.metric("Formula A passenger fare", naira(fare_a))


# ------------------------------------------------------------
# FORMULA B
# Required fare pool = target payout / (1 - commission)
# Fare per passenger = required fare pool / passenger count
# ------------------------------------------------------------

with tab_b:
    st.subheader("Formula B — Driver target earnings")
    st.write(
        "Start with the amount the driver wants to earn. Calculate the "
        "passenger fare pool needed to deliver that payout after commission, "
        "then divide it among the paying passengers assumed to share that pool."
    )

    st.warning(
        "This model assumes all paying passengers contribute equally to one "
        "fare pool. It does not yet allocate different prices by passenger "
        "distance or route segment."
    )

    notation_table([
        ("T", "Driver target payout (₦)", "Desired amount the driver receives."),
        ("c", "PAIR commission rate", "Reused from the sidebar."),
        ("P", "Required total passenger fare pool (₦)", "Gross fare required to fund the target payout."),
        ("n", "Paying passenger count", "Reused from the sidebar."),
        ("f", "Fare per passenger (₦)", "Equal share of the required fare pool."),
    ])

    variable_help(
        "Driver target payout T (₦)",
        "The total amount the driver wants to receive for this trip.",
        "It sets the earnings goal that the fare pool must support.",
        "It is not fuel cost, passenger fare, or PAIR revenue."
    )
    target_payout = st.number_input(
        "Driver's target payout (₦)",
        min_value=0.0,
        value=6000.0,
        step=500.0,
        key="b_target",
    )

    variable_help(
        "Additional fare-pool adjustment (₦)",
        "An optional extra amount added to the gross passenger fare pool.",
        "It lets you test whether a reserve or other explicit fare-pool "
        "requirement changes the passenger price.",
        "This is not the driver's target payout. It is added to the required "
        "pool after accounting for the target."
    )
    pool_adjustment = st.number_input(
        "Additional fare-pool adjustment (₦)",
        min_value=0.0,
        value=0.0,
        step=100.0,
        key="b_pool_adjustment",
    )

    st.caption(
        f"Shared inputs used: {passenger_count} paying passenger(s), "
        f"{commission_pct:.1f}% commission, and the commission treatment "
        "selected in the sidebar."
    )

    if commission_rate >= 1:
        st.error(
            "Formula B cannot calculate a finite fare pool when commission "
            "is 100%. Reduce the commission rate."
        )
        fare_b = 0.0
        pool_b = 0.0
    else:
        # In this simple model, commission is calculated on gross fare.
        # The sidebar option is displayed for transparency, but the gross
        # target formula uses gross commission so that the target can be solved.
        pool_b = (
            target_payout / (1 - commission_rate)
            if target_payout > 0 else 0.0
        ) + pool_adjustment
        fare_b = pool_b / passenger_count

    results["B — Driver target"] = fare_b
    formula_notes["B — Driver target"] = (
        "Fare pool = target payout / (1 − commission); "
        "fare per passenger = fare pool / paying passengers."
    )

    st.markdown("#### Formula")
    st.latex(
        r"P = \frac{T}{1-c} + R"
    )
    st.latex(
        r"f = \frac{P}{n}"
    )

    breakdown_table([
        ("Driver target payout", "T", naira(target_payout)),
        ("Commission rate", "c", f"{commission_pct:.1f}%"),
        ("Required pool before adjustment", "T / (1 − c)",
         naira(target_payout / (1 - commission_rate)
               if commission_rate < 1 else 0)),
        ("Pool adjustment", "R", naira(pool_adjustment)),
        ("Required passenger fare pool", "P", naira(pool_b)),
        ("Paying passengers", "n", str(passenger_count)),
        ("Fare per passenger", "P / n", naira(fare_b)),
    ])

    st.metric("Formula B fare per passenger", naira(fare_b))
    st.caption(
        "Simplification: the target-payout equation assumes commission is "
        "charged on gross fare. If you select commission after transaction "
        "cost in the sidebar, the actual accounting result may differ from "
        "this target calculation."
    )


# ------------------------------------------------------------
# FORMULA C — SIMPLIFIED ROUTE SEGMENT ALLOCATION
# Fare = exclusive distance * exclusive rate
#      + shared distance * shared rate
# ------------------------------------------------------------

with tab_c:
    st.subheader("Formula C — Route-segment sharing")
    st.write(
        "This model assigns a price to the passenger's exclusive route "
        "portion and their portion of a shared route segment. It is a "
        "simplified starting point, not a complete multi-passenger routing "
        "and allocation algorithm."
    )

    notation_table([
        ("d_e", "Passenger-exclusive distance (km)", "Distance travelled for this passenger outside the shared segment."),
        ("r_e", "Exclusive distance rate (₦/km)", "Rate for the exclusive segment."),
        ("d_s", "Shared segment distance (km)", "Distance covered together with other passengers."),
        ("r_s", "Shared segment rate (₦/km)", "Rate assigned to the shared segment for this passenger."),
        ("F_min", "Minimum passenger fare (₦)", "Lower bound for the calculated fare."),
        ("f", "Passenger fare (₦)", "Exclusive allocation plus shared allocation, subject to minimum."),
    ])

    st.warning(
        "For this simplified model, the exclusive distance plus shared "
        "distance cannot exceed the driver's total route distance in the "
        "sidebar. A production model would represent each passenger's pickup "
        "and drop-off points and calculate every route segment explicitly."
    )

    c1, c2 = st.columns(2)
    with c1:
        variable_help(
            "Passenger-exclusive distance d_e (km)",
            "The portion of the passenger's journey that is not shared with "
            "the other passengers represented in this simplified calculation.",
            "It lets the formula assign a different price to the part of the "
            "route that serves this passenger specifically.",
            "This is not necessarily the driver's total route distance in the "
            "sidebar; it is a passenger-specific segment input."
        )
        exclusive_km = st.number_input(
            "Passenger-exclusive distance (km)",
            min_value=0.0,
            max_value=float(distance_km),
            value=min(10.0, float(distance_km)),
            step=1.0,
            key="c_exclusive_km",
        )

        variable_help(
            "Exclusive distance rate r_e (₦/km)",
            "The price per kilometre assigned to the exclusive segment.",
            "It converts the exclusive segment distance into a fare component.",
            "The sidebar gives the distance; this parameter sets its price."
        )
        exclusive_rate = st.number_input(
            "Exclusive distance rate (₦/km)",
            min_value=0.0,
            value=150.0,
            step=10.0,
            key="c_exclusive_rate",
        )

    with c2:
        max_shared_km = max(0.0, float(distance_km) - exclusive_km)

        variable_help(
            "Shared segment distance d_s (km)",
            "The portion of the route covered together with other passengers.",
            "It allows the model to assign a price to the common segment.",
            "It is a segment of the total route, not the whole journey distance."
        )
        shared_km = st.number_input(
            "Shared segment distance (km)",
            min_value=0.0,
            max_value=float(max_shared_km),
            value=min(20.0, float(max_shared_km)),
            step=1.0,
            key="c_shared_km",
        )

        variable_help(
            "Shared segment rate r_s (₦/km)",
            "The rate assigned to each kilometre of the shared segment for "
            "this passenger.",
            "It lets you test whether shared travel receives a lower per-km "
            "allocation than exclusive travel.",
            "It is not automatically the same as the exclusive rate or the "
            "driver's full-trip target."
        )
        shared_rate = st.number_input(
            "Shared segment rate (₦/km)",
            min_value=0.0,
            value=75.0,
            step=5.0,
            key="c_shared_rate",
        )

    variable_help(
        "Minimum passenger fare F_min (₦)",
        "The minimum amount a passenger pays even if segment allocation is low.",
        "It protects against a very low result when the passenger travels only "
        "a short segment.",
        "It is a lower bound rather than an additional segment charge."
    )
    min_fare_c = st.number_input(
        "Minimum passenger fare (₦)",
        min_value=0.0,
        value=500.0,
        step=100.0,
        key="c_min_fare",
    )

    raw_fare_c = exclusive_km * exclusive_rate + shared_km * shared_rate
    fare_c = max(min_fare_c, raw_fare_c)

    results["C — Route segments"] = fare_c
    formula_notes["C — Route segments"] = (
        "Fare = exclusive distance × exclusive rate + "
        "shared distance × shared rate, subject to minimum fare."
    )

    st.markdown("#### Formula")
    st.latex(
        r"f = \max\left(F_{\min}, d_e r_e + d_s r_s\right)"
    )

    breakdown_table([
        ("Exclusive segment allocation",
         f"{exclusive_km:.1f} × {exclusive_rate:.2f}",
         naira(exclusive_km * exclusive_rate)),
        ("Shared segment allocation",
         f"{shared_km:.1f} × {shared_rate:.2f}",
         naira(shared_km * shared_rate)),
        ("Raw segment fare", "Exclusive + shared",
         naira(raw_fare_c)),
        ("Minimum fare check", f"max({naira(min_fare_c)}, raw fare)",
         naira(fare_c)),
        ("Distance represented by these segments",
         "Exclusive + shared",
         f"{exclusive_km + shared_km:.1f} km"),
        ("Driver's total route distance", "Sidebar input",
         f"{distance_km:.1f} km"),
    ])

    st.metric("Formula C passenger fare", naira(fare_c))


# ------------------------------------------------------------
# FORMULA D — EXISTING ROUTE CONTRIBUTION
# Fare = incremental cost + extra-time value + coordination + seat value
# ------------------------------------------------------------

with tab_d:
    st.subheader("Formula D — Passenger joins an existing route")
    st.write(
        "This model is designed for the case where a driver is already "
        "travelling in the passenger's direction and has an empty seat. "
        "The fare estimates the additional burden and value of serving "
        "that passenger, rather than automatically charging for the whole trip."
    )

    st.info(
        "Use this formula primarily for the 'Passenger joins driver's "
        "existing route' scenario. You can still explore it under other "
        "scenarios to see how its output behaves."
    )

    notation_table([
        ("d_x", "Additional distance (km)", "Reused from sidebar detour distance."),
        ("c_k", "Operating cost per additional km (₦/km)", "Estimated cost of additional distance."),
        ("t_x", "Additional time (minutes)", "Reused from sidebar detour time."),
        ("v_t", "Value per additional minute (₦/minute)", "Value assigned to extra driver time."),
        ("C_coord", "Coordination value (₦)", "Value assigned to pickup, communication and coordination effort."),
        ("C_seat", "Seat/service contribution (₦)", "Contribution for providing access to an available seat and service."),
        ("F_min", "Minimum fare (₦)", "Lower bound for the passenger fare."),
        ("f", "Passenger fare (₦)", "Sum of incremental components, subject to minimum."),
    ])

    c1, c2 = st.columns(2)
    with c1:
        variable_help(
            "Operating cost per additional km c_k (₦/km)",
            "An estimate of the driver's additional operating cost for each "
            "extra kilometre, including the fuel and wear assumptions you "
            "choose to represent.",
            "It converts the additional distance caused by serving the "
            "passenger into an estimated incremental operating cost.",
            "This is not the driver's entire fuel bill or the price charged "
            "to the passenger per kilometre."
        )
        cost_per_km = st.number_input(
            "Operating cost per additional km (₦/km)",
            min_value=0.0,
            value=80.0,
            step=5.0,
            key="d_cost_km",
        )

        variable_help(
            "Value of extra time v_t (₦/minute)",
            "The value assigned to each extra minute the driver spends serving "
            "the passenger.",
            "It accounts for time lost to detours, waiting, coordination or "
            "other additional service time.",
            "It is not the full-route time rate used in Formula A."
        )
        extra_time_value = st.number_input(
            "Value per additional minute (₦/minute)",
            min_value=0.0,
            value=10.0,
            step=1.0,
            key="d_time_value",
        )

    with c2:
        variable_help(
            "Coordination value C_coord (₦)",
            "A fixed amount representing the effort of arranging pickup, "
            "communicating and coordinating the passenger.",
            "It allows the simulation to represent work that may not appear "
            "as extra kilometres.",
            "It is a service-value assumption, not the detour distance or "
            "a verified operating expense."
        )
        coordination_value = st.number_input(
            "Coordination value (₦)",
            min_value=0.0,
            value=100.0,
            step=50.0,
            key="d_coordination",
        )

        variable_help(
            "Seat/service contribution C_seat (₦)",
            "An additional contribution for making an available seat useful "
            "to a passenger.",
            "It lets you test a contribution beyond the measured incremental "
            "distance and time costs.",
            "It is not the driver's total-trip earnings target. It should be "
            "tested against what passengers will actually pay."
        )
        seat_contribution = st.number_input(
            "Seat/service contribution (₦)",
            min_value=0.0,
            value=300.0,
            step=50.0,
            key="d_seat_contribution",
        )

    variable_help(
        "Minimum fare F_min (₦)",
        "The lowest fare the existing-route model can return.",
        "It protects against fares that are too small to justify serving "
        "the passenger.",
        "It is a floor, not an extra amount automatically added."
    )
    min_fare_d = st.number_input(
        "Minimum fare (₦)",
        min_value=0.0,
        value=300.0,
        step=50.0,
        key="d_min_fare",
    )

    incremental_distance_cost = detour_km * cost_per_km
    incremental_time_cost = detour_minutes * extra_time_value
    raw_fare_d = (
        incremental_distance_cost
        + incremental_time_cost
        + coordination_value
        + seat_contribution
    )
    fare_d = max(min_fare_d, raw_fare_d)

    results["D — Existing route"] = fare_d
    formula_notes["D — Existing route"] = (
        "Fare = incremental distance cost + extra-time value + "
        "coordination value + seat/service contribution, subject to minimum."
    )

    st.markdown("#### Formula")
    st.latex(
        r"f = \max\left("
        r"F_{\min}, d_x c_k + t_x v_t + C_{\mathrm{coord}} + C_{\mathrm{seat}}"
        r"\right)"
    )

    breakdown_table([
        ("Incremental distance cost",
         f"{detour_km:.1f} × {cost_per_km:.2f}",
         naira(incremental_distance_cost)),
        ("Extra-time value",
         f"{detour_minutes:.1f} × {extra_time_value:.2f}",
         naira(incremental_time_cost)),
        ("Coordination value", "C_coord", naira(coordination_value)),
        ("Seat/service contribution", "C_seat", naira(seat_contribution)),
        ("Raw fare", "Sum of incremental components", naira(raw_fare_d)),
        ("Minimum fare check", f"max({naira(min_fare_d)}, raw fare)",
         naira(fare_d)),
    ])

    st.metric("Formula D passenger fare", naira(fare_d))


# ============================================================
# COMPARISON AND FINANCIAL BREAKDOWN
# ============================================================

st.divider()
st.header("Compare the pricing formulas")
st.write(
    "The comparison below uses the same shared trip assumptions wherever "
    "the selected formula uses them. A lower fare is not automatically a "
    "better fare: check driver payout, transaction cost, and whether the "
    "assumptions describe the actual trip."
)

# Keep results in a consistent order
ordered_names = [
    "A — Baseline",
    "B — Driver target",
    "C — Route segments",
    "D — Existing route",
]

comparison_rows = []
accounting_rows = []

for name in ordered_names:
    fare = float(results.get(name, 0.0))
    accounting = fare_accounting(
        fare,
        commission_rate,
        transaction_rate,
        transaction_fixed,
        commission_on,
    )

    comparison_rows.append({
        "Formula": name,
        "Passenger fare (₦)": fare,
        "Driver payout before other costs (₦)": accounting["Driver payout (before other driver costs)"],
        "PAIR commission (₦)": accounting["PAIR commission / gross revenue"],
        "Transaction cost (₦)": accounting["Payment transaction cost"],
        "PAIR contribution after transaction cost (₦)": accounting["PAIR contribution after transaction cost"],
    })

    accounting_rows.append({
        "Formula": name,
        **accounting,
    })

comparison_df = pd.DataFrame(comparison_rows)
accounting_df = pd.DataFrame(accounting_rows)

lowest_fare = min(results.values()) if results else 0.0

metric_cols = st.columns(4)
for col, name in zip(metric_cols, ordered_names):
    fare = results.get(name, 0.0)
    with col:
        st.metric(
            name,
            naira(fare),
            delta=(
                f"{((fare - lowest_fare) / lowest_fare * 100):+.1f}% vs lowest"
                if lowest_fare > 0 else None
            ),
        )

st.subheader("Fare and revenue comparison")
st.dataframe(
    comparison_df.style.format({
        "Passenger fare (₦)": "₦{:,.2f}",
        "Driver payout before other costs (₦)": "₦{:,.2f}",
        "PAIR commission (₦)": "₦{:,.2f}",
        "Transaction cost (₦)": "₦{:,.2f}",
        "PAIR contribution after transaction cost (₦)": "₦{:,.2f}",
    }),
    hide_index=True,
    use_container_width=True,
)

st.subheader("Passenger fare chart")
chart_df = comparison_df.set_index("Formula")[["Passenger fare (₦)"]]
st.bar_chart(chart_df)

st.subheader("Formula explanations")
for name in ordered_names:
    with st.expander(name):
        st.write(formula_notes.get(name, "No formula explanation available."))

st.subheader("Important interpretation notes")
st.markdown(
    """
    - **Passenger fare** is what the passenger pays under the simulated formula.
    - **Driver payout** is the fare less the simulated PAIR commission. It is
      not the driver's profit after fuel, maintenance or other operating costs.
    - **PAIR commission / gross revenue** is not the same as PAIR's contribution.
    - **PAIR contribution after transaction cost** subtracts the assumed payment
      transaction fee from commission. It does not yet include all platform costs.
    - **Formula B** uses a target-payout allocation, not route-specific passenger pricing.
    - **Formula C** is simplified. A full version needs pickup/drop-off ordering,
      shared route segments, detours and passenger-specific allocation.
    - **Formula D** estimates incremental burden and seat/service contribution.
      Its cost inputs need real-world validation.
    - This prototype does not perform live maps routing, demand matching, OJO
      wallet reservations, payment collection or settlement.
    """
)

# ============================================================
# EXPORTS
# ============================================================

st.divider()
st.header("Export your simulation")

# Include sidebar inputs, formula assumptions and formula outputs.
assumptions = {
    "Vehicle class": vehicle_class,
    "Passenger-seat capacity": seat_capacity,
    "Driver's total route distance (km)": distance_km,
    "Estimated total route duration (minutes)": duration_min,
    "Paying passenger count": passenger_count,
    "Trip scenario": scenario,
    "Additional detour distance (km)": detour_km,
    "Additional detour time (minutes)": detour_minutes,
    "PAIR commission (%)": commission_pct,
    "Commission treatment": commission_treatment,
    "Payment transaction fee (%)": transaction_pct,
    "Fixed payment fee per booking (₦)": transaction_fixed,
    "A: Base fare (₦)": base_fare,
    "A: Distance rate (₦/km)": distance_rate,
    "A: Time rate (₦/minute)": time_rate,
    "A: Minimum fare (₦)": min_fare,
    "A: Additional adjustment (₦)": adjustment,
    "B: Driver target payout (₦)": target_payout,
    "B: Fare-pool adjustment (₦)": pool_adjustment,
    "C: Exclusive distance (km)": exclusive_km,
    "C: Exclusive rate (₦/km)": exclusive_rate,
    "C: Shared distance (km)": shared_km,
    "C: Shared rate (₦/km)": shared_rate,
    "C: Minimum fare (₦)": min_fare_c,
    "D: Operating cost per additional km (₦/km)": cost_per_km,
    "D: Value per additional minute (₦/minute)": extra_time_value,
    "D: Coordination value (₦)": coordination_value,
    "D: Seat/service contribution (₦)": seat_contribution,
    "D: Minimum fare (₦)": min_fare_d,
}

assumptions_df = pd.DataFrame(
    [{"Input / assumption": k, "Value": v} for k, v in assumptions.items()]
)

csv_bytes = comparison_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download fare comparison (CSV)",
    data=csv_bytes,
    file_name="pair_pricing_comparison.csv",
    mime="text/csv",
)

try:
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        comparison_df.to_excel(
            writer, sheet_name="Fare Comparison", index=False
        )
        assumptions_df.to_excel(
            writer, sheet_name="Assumptions", index=False
        )
        pd.DataFrame(
            [{"Formula": k, "Explanation": v}
             for k, v in formula_notes.items()]
        ).to_excel(
            writer, sheet_name="Formula Notes", index=False
        )

    st.download_button(
        "Download full simulation (Excel)",
        data=excel_buffer.getvalue(),
        file_name="pair_pricing_simulation.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
except ImportError:
    st.warning(
        "Excel export requires openpyxl. Install it with "
        "`pip install openpyxl`. CSV export remains available."
    )

st.caption(
    "PAIR Pricing Simulator — exploratory prototype. Validate all cost, "
    "commission, pricing and allocation assumptions with Nigerian drivers "
    "and passengers before using them in a live product."
)
