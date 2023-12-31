import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from calendar import monthrange
import matplotlib.pyplot as plt
from io import BytesIO
from lifelines import WeibullFitter
import altair as alt


def print_about():
    """
    Print the app background and assumptions.
    """

    about_txt = """ 
    <p>This Streamlit app helps to analyse the effect of different preventive maintenance intervals on reliability metrics. 
    Consider many assets of the same type deployed at various times.  
    We can determine the failure distribution of the asset class 
    and use the same to determine the effect of various preventive maintenance intervals. 
    We are focusing on the first failure here while selecting the failure distribution 
    since we assume that the asset will become as good as new whenever there is a work order.
    Thus the current implementation uses <a href="https://www.weibull.com/hotwire/issue14/relbasics14.htm">Weibull distribution</a>.</p> 
    <p>The present asset hierarchy assumption is that a system consists of multiple subsystems, and every subsystem has many asset classes. 
    For example, an asset class name 'SIG/ATC/OBU' will denote 'SIG' as the system name and 'ATC' as the subsystem name for the asset class 'OBU'. 
    All our analyses are at asset class level.</p>
    <p> For more info about this Streamlit app, 
    Please visit <a href="https://github.com/Msundarv/Rel_PM#readme">this</a> page. 
    <br> Author: <a href="https://github.com/Msundarv">msundarv</a> </p>
    """

    about_expander = st.expander(label="About", expanded=False)
    with about_expander:
        st.markdown(about_txt, unsafe_allow_html=True)

    return None


def load_data(file):
    """
    Load input work order data excel file.
    """
    instll_date_df = pd.read_excel(file, sheet_name="sheet0", engine="openpyxl")
    wo_df = pd.read_excel(file, sheet_name="sheet1", engine="openpyxl")

    ip_data_expander = st.expander(label="Uploaded Input Data", expanded=False)
    with ip_data_expander:
        st_col1, st_col2 = st.columns(2)
        st_col2.text("Uploaded Installation Details")
        st_col2.dataframe(instll_date_df)
        st_col1.text("Uploaded Work Order Details")
        st_col1.dataframe(wo_df)

    return wo_df, instll_date_df


def attach_ttf(wo_df, instll_date_df):
    """
    Calc. ttf for work orders.
    """
    res_dfs = []
    grouped_wo = wo_df.groupby(["asset_num"])
    for asset, asset_wo in grouped_wo:
        # Get the installation date from previous work order by default
        asset_wo = asset_wo.sort_values(by="wo_date", ascending=True)
        asset_wo["instll_date"] = asset_wo["wo_date"].shift(1)
        # Get the installation date for the first work order
        initial_instll_date = list(
            instll_date_df[instll_date_df["asset_num"] == asset]["instll_date"]
        )[0]
        asset_wo.loc[
            asset_wo["instll_date"].isna(), "instll_date"
        ] = initial_instll_date
        # Get ttf
        asset_wo["ttf"] = (
            (asset_wo["wo_date"] - asset_wo["instll_date"]).dt.total_seconds() / 60 / 60
        )
        res_dfs.append(asset_wo)

    res_df = pd.concat(res_dfs, ignore_index=True)

    # Keep only work orders with ttf > 1 day
    res_df = res_df[res_df["ttf"] > 24]

    return res_df


def get_hist_dates(start_date):
    """
    Create a range of dates from start date's month till current month.
    """
    start_hist = datetime(
        start_date.year,
        start_date.month,
        monthrange(start_date.year, start_date.month)[1],
    )
    end_hist = datetime(
        datetime.now().year,
        datetime.now().month,
        monthrange(datetime.now().year, datetime.now().month)[1],
    )
    historical_dates = pd.date_range(start=start_hist, end=end_hist, freq="M")

    return historical_dates


# TODO: Function to get FPMH based on historical dates
def get_fpmh(wo_df):
    """
    Calc. historical FPMH from work order data.
    """
    hist_dates = get_hist_dates(wo_df["instll_date"].min())
    # print(hist_dates)

    return None


def get_discretized_fpmh(ttf_lt, n_bins=50):
    """
    Calc. historical FPMH from ttf data.
    """
    fcount, bins = np.histogram(ttf_lt, bins=n_bins)
    bin_end = bins[1:]
    fpmh = 1e6 * fcount.cumsum() / bin_end
    fpmh = pd.Series(fpmh, index=bin_end)
    return fpmh


def plot_hist_data(ttf_lt, hist_fpmh):
    """
    Plot historical ttf, fpmh data.
    """
    fig = plt.figure()
    fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(12, 4))

    # Plot TTF
    ax1.hist(ttf_lt, bins=25)
    ax1.set_xlabel("Time (hrs)")
    ax1.set_ylabel("No. of failures")
    ax1.title.set_text("TTF Histogram")

    # Plot FPMH
    hist_fpmh.plot(ax=ax2)
    ax2.ticklabel_format(axis="y", scilimits=(1, 3))
    ax2.set_xlabel("Time (hrs)")
    ax2.set_ylabel("FPMH")
    ax2.title.set_text("Failure Rate")

    fig.tight_layout()
    fig_buf = BytesIO()
    fig.savefig(fig_buf, format="png")

    st_col1, st_col2, st_col3 = st.columns([1, 6, 1])
    st_col1.text("")
    st_col2.image(fig_buf)
    st_col3.text("")

    return None


def plot_lifeline_weibull(wbf):
    """
    Plot cdf, pdf, survival and hazard functions using lifeline package weibull fitter.
    """
    fig_bufs = [0] * 4

    # Plot cdf function
    fig = plt.figure(figsize=(6, 4))
    wbf.plot_cumulative_density()
    fig.suptitle("Cumulative Density Function")
    fig_bufs[1] = BytesIO()
    fig.savefig(fig_bufs[1], format="png")

    # Plot pdf function
    fig = plt.figure(figsize=(6, 4))
    wbf.plot_density()
    fig.suptitle("Density Function")
    fig_bufs[0] = BytesIO()
    fig.savefig(fig_bufs[0], format="png")

    # Plot survival function
    fig = plt.figure(figsize=(6, 4))
    wbf.plot_survival_function()
    fig.suptitle("Survival Function")
    fig_bufs[2] = BytesIO()
    fig.savefig(fig_bufs[2], format="png")

    # Plot hazard function
    fig = plt.figure(figsize=(6, 4))
    wbf.plot_hazard()
    plt.ylim(ymin=0)
    fig.suptitle("Hazard Function")
    fig_bufs[3] = BytesIO()
    fig.savefig(fig_bufs[3], format="png")

    return fig_bufs


def fit_weibull(wo_df):
    """
    Fit Weibull distribution to the work order data.
    """
    wo_df["indicator"] = 1

    wbf = WeibullFitter()
    wbf.fit(wo_df["ttf"], wo_df["indicator"])
    # wbf.print_summary()
    # print(wbf.lambda_, wbf.rho_)

    fig_bufs = plot_lifeline_weibull(wbf)

    st.text(
        "Shape: "
        + "{:.2f}".format(wbf.rho_)
        + ",  Scale: "
        + "{:.2f}".format(wbf.lambda_)
    )
    st_col1, st_col2, st_col3, st_col4 = st.columns([3, 3, 3, 3])
    st_col1.image(fig_bufs[0])
    st_col2.image(fig_bufs[1])
    st_col3.image(fig_bufs[2])
    st_col4.image(fig_bufs[3])

    return wbf


def get_fpmh_by_intervals(wbf, intervals=range(1, 46)):
    """
    Calc. FPMH for different time interval using the given weibull fitter object.
    """

    # Every month is considered to have 30 days
    monthly_hrs = 30 * 24

    # Get interval length in terms of hours
    interval_lengths = [i * monthly_hrs for i in intervals]

    # FPMH by interval
    fpmh_intervals = wbf.cumulative_hazard_at_times(interval_lengths)
    fpmh_intervals = (fpmh_intervals.values * 1e6) / interval_lengths
    fpmh_intervals = pd.DataFrame(fpmh_intervals, index=intervals, columns=["FPMH"])

    # Plot Interval FPMH
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(12, 4))
    fpmh_intervals.plot.bar(
        ax=ax, xlabel="PM Interval (No. of months)", ylabel="Exp. FPMH"
    )
    ax.set_ylim(
        ((fpmh_intervals.min() * 0.8).values[0], (fpmh_intervals.max() * 1.2).values[0])
    )
    fig.suptitle("FPMH vs PM Interval Length")
    fig.tight_layout()
    fig_buf = BytesIO()
    fig.savefig(fig_buf, format="png")

    st_col1, st_col2, st_col3 = st.columns([1, 8, 1])
    st_col1.text("")
    st_col2.image(fig_buf)
    st_col3.text("")

    return fpmh_intervals


def print_summary_table(wbf, asset_class, fpmh_intervals):
    """
    Print summary table with information such as model params, and other key metrics.
    """
    shape = float("{:.2f}".format(wbf.rho_))
    scale = float("{:.2f}".format(wbf.lambda_))
    fr = "Random" if shape == 1 else "Increasing" if shape > 1 else "Decreasing"
    exp_failures = "{:.2f}".format(fpmh_intervals.iloc[12]["FPMH"])

    summary_df = pd.DataFrame(
        [
            [
                asset_class,
                "{:.2f}".format(shape),
                "{:.2f}".format(scale),
                fr,
                exp_failures,
            ]
        ],
        columns=[
            "Asset Class",
            "Shape",
            "Scale",
            "Failure Rate",
            "Exp. Failures (1Yr)",
        ],
    )

    hide_table_row_index = """
            <style>
            tbody th {display:none}
            .blank {display:none}
            </style>
            """
    st.markdown(hide_table_row_index, unsafe_allow_html=True)
    st.table(summary_df)

    return None


def analyse_pm_effect(asset_class, wo_df, instll_date_df):
    """
    Perform the analysis to understand the effect of various preventive maintenance interval.
    Analysis is done at asset class level, so the input is expected to contain only records for one asset class.
    """

    # Get ttf data
    wo_df = attach_ttf(wo_df, instll_date_df)
    ttf_lt = list(wo_df["ttf"])
    # st.dataframe(wo_df)

    # Get FPMH data
    # hist_fpmh = get_fpmh(wo_df)
    hist_fpmh = get_discretized_fpmh(ttf_lt)
    # st.dataframe(hist_fpmh)

    # Plot hist. metrics
    st.subheader("[" + asset_class + "] Historical Reliability Metrics")
    plot_hist_data(ttf_lt, hist_fpmh)
    st.markdown("---")

    # Fit Weibull Distribution
    st.subheader("[" + asset_class + "] Fitted Weibull Distribution")
    wbf = fit_weibull(wo_df)
    st.markdown("---")

    # Calc. FPMH for different PM Intervals
    st.subheader("[" + asset_class + "] Plan Preventive Maintenance")
    fpmh_intervals = get_fpmh_by_intervals(wbf, range(1, 24))
    st.markdown("---")

    # Display summary table
    st.subheader("[" + asset_class + "] Summary")
    print_summary_table(wbf, wo_df["asset_class"][0], fpmh_intervals)
    st.markdown("---")

    return None


def get_hist_failure_count(wo_df):
    """
    Calc. the monthly number of failures for every asset class.
    """
    res_df = wo_df.copy()

    # Calc. the daily number of work orders for every asset class
    res_df = res_df.groupby("asset_class")["wo_date"].value_counts()
    res_df = res_df.sort_index().unstack(0)
    res_df = res_df.fillna(0)

    # Calc. the monthly number of work orders for every asset class
    res_df.index = pd.DatetimeIndex(res_df.index)
    res_df = res_df.resample("1M").sum().fillna(0)
    res_df = res_df.astype(int)

    # Add sys, subsys details
    res_df = res_df.unstack().reset_index()
    res_df = res_df.rename(columns={"wo_date": "Date", 0: "Failure Count"})
    res_df["Date"] = pd.to_datetime(res_df["Date"]).dt.date
    res_df["Sys"] = [x.split("/")[0] for x in res_df["asset_class"]]
    res_df["Subsys"] = [x.split("/")[1] for x in res_df["asset_class"]]

    return res_df


def plot_failure_count(wo_count_df, level):
    """
    Plot failure count data as stacked bar graph based on the asset hierarchy level given.
    """

    if level in wo_count_df["Sys"].unique():
        # Plot at system level
        bar_chart = (
            alt.Chart(wo_count_df[wo_count_df["Sys"] == level])
            .mark_bar()
            .encode(x="Date:T", y="Failure Count:Q", color="Subsys:N")
            .interactive()
        )
        st.altair_chart(bar_chart, use_container_width=True)
    else:
        # Plot at sub system level
        bar_chart = (
            alt.Chart(wo_count_df[wo_count_df["Subsys"] == level])
            .mark_bar()
            .encode(x="Date:T", y="Failure Count:Q", color="asset_class:N")
            .interactive()
        )
        st.altair_chart(bar_chart, use_container_width=True)

    return None


# Config Streamlit
st.set_page_config(page_title="Rel PM", layout="wide")
st.title("Reliability Based Preventive Maintenance")
print_about()
st.markdown("---")

st.subheader("Upload Work Order Data")
uploaded_file = st.file_uploader("Choose a WO XLSX file", type="xlsx")
if uploaded_file:

    try:
        # Load work order data
        wo_df, instll_date_df = load_data(uploaded_file)
        st.markdown("---")

        # Overall summary
        st.header("Overall Summary")
        wo_count_df = get_hist_failure_count(wo_df)
        wo_count_lvl = st.selectbox(
            "Please select a sys/subsys: ",
            np.concatenate(
                (wo_count_df["Sys"].unique(), wo_count_df["Subsys"].unique()), axis=0
            ),
        )
        plot_failure_count(wo_count_df, wo_count_lvl)
        st.markdown("---")

        # Select an asset class
        st.header("Asset Class Level Report")
        asset_class = st.selectbox(
            "Please select an asset class: ", wo_df["asset_class"].unique()
        )
        st.markdown("---")

        # Perform asset level analysis
        analyse_pm_effect(
            asset_class,
            wo_df[wo_df["asset_class"] == asset_class],
            instll_date_df[instll_date_df["asset_class"] == asset_class],
        )

    except ValueError:
        st.error("Please upload a valid WO XLSX file")

else:
    st.text("Work order data not yet uploaded")
