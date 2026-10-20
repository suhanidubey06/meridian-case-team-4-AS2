import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import math

st.set_page_config(
    page_title="Meridian E-Portfolio",
    page_icon="📊",
    layout="wide"
)

st.title("Meridian E-Portfolio")
st.caption("Workforce planning, job design and staffing readiness")

WORKBOOK = Path(__file__).parent / "01_HCM_Session_6_AS2_Guided_Excel_Workbook_Filled.xlsx"

@st.cache_data
def load_inputs(path):
    """Read the workbook's input assumptions and role data."""
    inputs = pd.read_excel(path, sheet_name="Inputs", header=None, engine="openpyxl")
    params = {
        "window": float(inputs.iloc[5, 1]),
        "weekly_hours": float(inputs.iloc[6, 1]),
        "allowance": float(inputs.iloc[7, 1]),
        "vendor_proficiency": float(inputs.iloc[8, 1]),
        "vendor_budget": float(inputs.iloc[9, 1]),
        "vendor_limit": int(inputs.iloc[10, 1]),
        "vendor_delay": float(inputs.iloc[14, 1]),
        "extra_role_workload": float(inputs.iloc[15, 1]),
        "extra_incremental_cost": float(inputs.iloc[16, 1]),
    }
    roles = inputs.iloc[25:31, 0:9].copy()
    roles.columns = [
        "Role", "Pool people", "Legacy hours/person", "Volume",
        "Hours/unit", "Retained coordination hours",
        "Bounded coordination hours", "Vendor rate/hour", "Source"
    ]
    for col in roles.columns[1:8]:
        roles[col] = pd.to_numeric(roles[col], errors="coerce")
    roles = roles.dropna(subset=["Role"]).reset_index(drop=True)
    return params, roles

def calculate_scenario(params, roles, workflow, include_duplicate, arrangement):
    """Calculate the workbook's four-week scenario from its input assumptions."""
    employee_productive_hours = (
        params["window"] * params["weekly_hours"] * (1 - params["allowance"])
    )
    vendor_paid_hours = max(0, params["window"] - params["vendor_delay"]) * params["weekly_hours"]
    vendor_effective_hours = vendor_paid_hours * (1 - params["allowance"]) * params["vendor_proficiency"]

    data = roles.copy()
    data["Task demand h"] = data["Volume"] * data["Hours/unit"]
    data.loc[data["Role"].eq("Data preparation"), "Task demand h"] += 240 * include_duplicate
    coordination_col = "Retained coordination hours" if workflow == 1 else "Bounded coordination hours"
    data["Coordination h"] = data[coordination_col]
    data["Extra workload h"] = params["extra_role_workload"]
    data["Pilot demand h"] = data["Task demand h"] + data["Coordination h"] + data["Extra workload h"]
    data["Legacy work h"] = data["Pool people"] * data["Legacy hours/person"]
    data["Available pilot h"] = data["Pool people"] * (
        employee_productive_hours - data["Legacy hours/person"]
    ).clip(lower=0)
    data["Internal used h"] = data[["Pilot demand h", "Available pilot h"]].min(axis=1)
    data["Skill gap h"] = (data["Pilot demand h"] - data["Internal used h"]).clip(lower=0)
    if vendor_effective_hours > 0:
        data["Vendor workers"] = data["Skill gap h"].apply(
            lambda gap: math.ceil(gap / vendor_effective_hours) if gap > 0 else 0
        )
    else:
        data["Vendor workers"] = 0
    data["Vendor cost INR"] = data["Vendor workers"] * vendor_paid_hours * data["Vendor rate/hour"]
    data["Arrangement"] = arrangement
    return data

if not WORKBOOK.exists():
    st.error("The Excel workbook is missing. Upload the workbook alongside app.py in your GitHub repository.")
    st.stop()

params, roles = load_inputs(WORKBOOK)

st.sidebar.header("Portfolio sections")
section = st.sidebar.radio("Go to", ["Problem", "Solution Guide"])
st.sidebar.divider()
st.sidebar.caption("Graphs are calculated from the workbook's Inputs sheet. Scenario results are conditional estimates, not approvals.")

st.sidebar.subheader("Scenario assumptions")
workflow_label = st.sidebar.selectbox(
    "Workflow arrangement",
    ["Retained workflow", "Bounded workflow"],
    index=1
)
workflow = 1 if workflow_label == "Retained workflow" else 2
duplicate_label = st.sidebar.selectbox(
    "Duplicate data-preparation work",
    ["Include duplicate work", "Single authoritative output"],
    index=1
)
include_duplicate = 1 if duplicate_label == "Include duplicate work" else 0
params["vendor_delay"] = st.sidebar.number_input(
    "Vendor delay (weeks)", min_value=0.0, max_value=float(params["window"]), value=float(params["vendor_delay"]), step=1.0
)
params["extra_role_workload"] = st.sidebar.number_input(
    "Extra workload per role (hours)", min_value=0.0, value=float(params["extra_role_workload"]), step=8.0
)
params["extra_incremental_cost"] = st.sidebar.number_input(
    "Extra incremental cost (INR)", min_value=0.0, value=float(params["extra_incremental_cost"]), step=10000.0
)

scenario_options = [
    ("Retained + duplicate", 1, 1),
    ("Retained + single output", 1, 0),
    ("Bounded + duplicate", 2, 1),
    ("Bounded + single output", 2, 0),
]
all_scenarios = []
for name, wf, dup in scenario_options:
    calculated = calculate_scenario(params, roles, wf, dup, name)
    all_scenarios.append({
        "Arrangement": name,
        "Demand h": calculated["Pilot demand h"].sum(),
        "Available h": calculated["Available pilot h"].sum(),
        "Skill gap h": calculated["Skill gap h"].sum(),
        "Vendor workers": int(calculated["Vendor workers"].sum()),
        "Vendor INR": calculated["Vendor cost INR"].sum(),
        "Total incremental INR": calculated["Vendor cost INR"].sum() + params["extra_incremental_cost"],
        "Role details": calculated,
    })
summary = pd.DataFrame([{k: v for k, v in item.items() if k != "Role details"} for item in all_scenarios])
current = calculate_scenario(params, roles, workflow, include_duplicate, f"{workflow_label} / {duplicate_label}")

if section == "Problem":
    st.header("1. Problem")
    st.write(
        "Meridian must deliver a four-week pilot while protecting existing services. "
        "The central workforce-planning question is whether pilot demand can be met by "
        "available capacity without assuming that employees can be released automatically."
    )
    st.info(
        "The workbook distinguishes theoretical capacity from approved allocation. "
        "Use the charts to identify gaps; do not treat a numerical result as permission to release staff."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Pilot demand", f"{current['Pilot demand h'].sum():,.0f} h")
    c2.metric("Available pilot capacity", f"{current['Available pilot h'].sum():,.0f} h")
    c3.metric("Estimated skill gap", f"{current['Skill gap h'].sum():,.0f} h")

    st.subheader("Graph 1 — Pilot demand vs available capacity by role")
    demand_chart = current.melt(
        id_vars="Role",
        value_vars=["Pilot demand h", "Available pilot h"],
        var_name="Measure",
        value_name="Hours"
    )
    fig = px.bar(
        demand_chart, x="Role", y="Hours", color="Measure", barmode="group",
        title="Workforce demand compared with available capacity",
        labels={"Role": "Role", "Hours": "Hours", "Measure": "Measure"}
    )
    fig.update_layout(xaxis_tickangle=-25, legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Graph 2 — Estimated skill gap by role")
    gap_chart = current.sort_values("Skill gap h", ascending=False)
    fig_gap = px.bar(
        gap_chart, x="Role", y="Skill gap h",
        title="Roles where demand exceeds available capacity",
        labels={"Role": "Role", "Skill gap h": "Gap (hours)"}
    )
    fig_gap.update_layout(xaxis_tickangle=-25)
    st.plotly_chart(fig_gap, use_container_width=True)

    st.subheader("Role-level figures")
    st.dataframe(
        current[["Role", "Pilot demand h", "Available pilot h", "Skill gap h"]].round(1),
        use_container_width=True, hide_index=True
    )

elif section == "Solution Guide":
    st.header("2. Solution Guide")
    st.write(
        "A practical response combines work redesign, clear decision rights, protected employee release, "
        "and targeted sourcing for any remaining skill gaps. A bounded workflow and single authoritative "
        "data output may reduce work, but both depend on valid authority and receiver acceptance."
    )

    st.subheader("Graph 3 — Compare the four staffing scenarios")
    metric_choice = st.selectbox(
        "Choose a measure",
        ["Skill gap h", "Vendor workers", "Vendor INR", "Total incremental INR", "Demand h", "Available h"]
    )
    scenario_chart = px.bar(
        summary, x="Arrangement", y=metric_choice,
        title=f"Four-scenario comparison: {metric_choice}",
        labels={"Arrangement": "Staffing scenario", metric_choice: metric_choice}
    )
    scenario_chart.update_layout(xaxis_tickangle=-20)
    st.plotly_chart(scenario_chart, use_container_width=True)

    st.subheader("Graph 4 — Estimated vendor cost by role")
    role_cost = current.sort_values("Vendor cost INR", ascending=False)
    cost_chart = px.bar(
        role_cost, x="Role", y="Vendor cost INR",
        title="Estimated vendor cost for the selected assumptions",
        labels={"Role": "Role", "Vendor cost INR": "Vendor cost (INR)"}
    )
    cost_chart.update_layout(xaxis_tickangle=-25)
    st.plotly_chart(cost_chart, use_container_width=True)

    st.subheader("Scenario summary")
    st.dataframe(summary.round(1), use_container_width=True, hide_index=True)

    vendor_total = float(current["Vendor cost INR"].sum() + params["extra_incremental_cost"])
    vendor_count = int(current["Vendor workers"].sum())
    budget_left = params["vendor_budget"] - vendor_total
    people_left = params["vendor_limit"] - vendor_count
    m1, m2, m3 = st.columns(3)
    m1.metric("Estimated vendor cost", f"₹{vendor_total:,.0f}")
    m2.metric("Vendor budget remaining", f"₹{budget_left:,.0f}")
    m3.metric("Vendor limit remaining", f"{people_left} people")

    st.markdown("### Recommended action checklist")
    st.checkbox("Confirm role ownership, decision rights and escalation route.")
    st.checkbox("Obtain named employee-release approval and protect existing service commitments.")
    st.checkbox("Confirm one authoritative data-preparation output before removing duplicate work.")
    st.checkbox("Use role-specific work samples and verify access, onboarding and readiness.")
    st.checkbox("Recheck vendor budget, vendor headcount and assumptions before approval.")

    st.caption(
        "Calculation note: vendor workers are rounded up by role using effective vendor hours. "
        "Costs use paid vendor hours and the role-specific hourly rates in the workbook. "
        "Scenario calculations assume theoretical internal capacity is usable; validate employee allocations, "
        "access and service cover before relying on the result."
    )

st.divider()
st.caption("Meridian case workbook | Built with Streamlit, pandas, Plotly and openpyxl")
