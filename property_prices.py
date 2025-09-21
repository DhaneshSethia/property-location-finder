import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
import plotly.express as px
from math import radians, sin, cos, sqrt, atan2
import streamlit.components.v1 as components
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

GA_TRACKING_ID = st.secrets["GA_TRACKING_ID"]  # <-- replace this with your ID
#GA_TRACKING_ID = ""  # <-- replace this with your ID

# --- Google Sheets setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Load service account JSON from Streamlit Secrets
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_KEY"])

# Authenticate
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

ga_code = f"""
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_TRACKING_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_TRACKING_ID}');
</script>
"""
components.html(ga_code, height=0)

def track_event(event_name, event_params=None):
    if event_params is None:
        event_params = {}
    event_script = f"""
    <script>
    gtag('event', '{event_name}', {event_params});
    </script>
    """
    components.html(event_script, height=0)

# Load dataset
#df = pd.read_csv("prices2.csv")
# Open your sheet by name (must already exist)
sheet = client.open("PropertyPrices").sheet1  # or .get_worksheet(index)

# Get all records
data = sheet.get_all_records()

# Convert to pandas DataFrame
df = pd.DataFrame(data)


st.markdown(
    """
    <style>
    /* Remove top padding/margin */
    .css-18e3th9 {  /* Main app container */
        padding-top: -100rem;
    }
    /* Optional: reduce sidebar padding */
    .css-1d391kg {  
        padding-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# Theme Colors
# -------------------------------
PRIMARY_COLOR = "#3873B2"
CARD_BG_COLOR = "#ffffff"
CARD_SHADOW = "0px 4px 8px rgba(0,0,0,0.1)"


st.set_page_config(layout="wide")
st.title("Search for the best property location")

# ==============================
# SIDEBAR FILTERS
# ==============================
st.sidebar.header("🔍 Filters")

# # City filter
# cities = ["All"] + sorted(df["city"].dropna().unique().tolist())
# selected_city = st.sidebar.selectbox("Select City", cities)

# # --- City filter with onboarding memory ---
# cities = ["All"] + sorted(df["city"].dropna().unique().tolist())

# # Ask for default city if not already set
# if "user_city" not in st.session_state:
#     st.session_state["user_city"] = st.selectbox(
#         "👋 Welcome! Please select your default city:",
#         sorted(df["city"].dropna().unique().tolist())
#     )
#     st.success(f"✅ Default city set to {st.session_state['user_city']}")
#     st.stop()  # stop app here so user sets this first

# print(st.session_state["user_city"])
# selected_city = st.sidebar.selectbox(
#     "Select City",
#     cities,
#     index=cities.index(st.session_state["user_city"]) if st.session_state["user_city"] in cities else 0
# )

# print(st.session_state["user_city"])

# 👋 Onboarding step: Ask for default city once
city_options = ["-- Select a city --"] + sorted(df["city"].dropna().unique().tolist())

if "user_city" not in st.session_state:
    selected_default = st.selectbox(
        "👋 Welcome! Please select your default city:",
        city_options,
        index=0
    )

    if selected_default != "-- Select a city --":
        st.session_state["user_city"] = selected_default
        st.success(f"✅ Default city set to {st.session_state['user_city']}")
        #st.stop()  # stop app here so user sets this first
    else:
        st.warning("⚠️ Please select a city to continue")
        st.stop()

# 📌 Sidebar city filter (with "All" option)
cities = ["All"] + sorted(df["city"].dropna().unique().tolist())
selected_city = st.sidebar.selectbox(
    "Select City",
    cities,
    index=cities.index(st.session_state["user_city"]) if st.session_state["user_city"] in cities else 0
)


# Location filter (depends on City)
if selected_city != "All":
    locations = ["All"] + sorted(df[df["city"] == selected_city]["location"].dropna().unique().tolist())
else:
    locations = ["All"] + sorted(df["location"].dropna().unique().tolist())
selected_location = st.sidebar.selectbox("Select Location", locations)

# Locality filter (depends on City & Location)
if selected_city != "All" and selected_location != "All":
    localities = ["All"] + sorted(df[(df["city"] == selected_city) & 
                                     (df["location"] == selected_location)]["locality"].dropna().unique().tolist())
elif selected_city != "All":
    localities = ["All"] + sorted(df[df["city"] == selected_city]["locality"].dropna().unique().tolist())
elif selected_location != "All":
    localities = ["All"] + sorted(df[df["location"] == selected_location]["locality"].dropna().unique().tolist())
else:
    localities = ["All"] + sorted(df["locality"].dropna().unique().tolist())
selected_locality = st.sidebar.selectbox("Select Locality", localities)

# Segment filter
segments = ["All"] + sorted(df["segment"].dropna().unique().tolist())
selected_segment = st.sidebar.selectbox("Select Segment", segments)

# Property type filter
property_types = ["All"] + sorted(df["property_type"].dropna().unique().tolist())

default_property_type = "apartment"
default_index = property_types.index(default_property_type) if default_property_type in property_types else 0

selected_property_type = st.sidebar.selectbox(
    "Select Property Type",
    property_types,
    index=default_index
)

# Metric selection
numeric_cols = ["rental_yields", "rates_per_sqft"]

# Set "rates_per_sqft" as default
default_metric_index = numeric_cols.index("rates_per_sqft")
metric = st.selectbox("Metric", numeric_cols, index=default_metric_index)

# ==============================
# APPLY FILTERS
# ==============================
filtered_df = df.copy()

if selected_city != "All":
    filtered_df = filtered_df[filtered_df["city"] == selected_city]
if selected_location != "All":
    filtered_df = filtered_df[filtered_df["location"] == selected_location]
if selected_locality != "All":
    filtered_df = filtered_df[filtered_df["locality"] == selected_locality]
if selected_segment != "All":
    filtered_df = filtered_df[filtered_df["segment"] == selected_segment]
if selected_property_type != "All":
    filtered_df = filtered_df[filtered_df["property_type"] == selected_property_type]

# -------------------------------
# SUMMARY METRICS CARDS
# -------------------------------
if not filtered_df.empty:
    avg_val, min_val, max_val = filtered_df[metric].mean(), filtered_df[metric].min(), filtered_df[metric].max()
    
    c1, c2, c3 = st.columns(3)
    
    for col, label, value, emoji in zip(
        [c1, c2, c3],
        ["Average", "Minimum", "Maximum"],
        [avg_val, min_val, max_val],
        ["⚖️", "📉", "📈"]
    ):
        # Format value based on metric
        if metric == "rates_per_sqft":
            display_value = f"₹{value:,.0f}"
        elif metric == "rental_yields":
            display_value = f"{value*100:.2f}%"
        else:
            display_value = f"{value:.2f}"
        
        col.markdown(
            f"""
            <div style="
                background-color:{CARD_BG_COLOR};
                padding:20px;
                border-radius:12px;
                box-shadow:{CARD_SHADOW};
                text-align:center;
            ">
                <h3>{emoji} {label}</h3>
                <h2>{display_value}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

else:
    st.warning("No data for selected filters.")

# ==============================
# FOLIUM MAP
# ==============================
if not filtered_df.empty:
    m = folium.Map(location=[filtered_df["Latitude"].mean(), filtered_df["Longitude"].mean()], zoom_start=11)

    metric_min, metric_max = filtered_df[metric].min(), filtered_df[metric].max()

    for _, row in filtered_df.iterrows():
        value = row[metric]

        # Normalize intensity safely
        if pd.isna(value):
            continue

        size = 5 if metric_max == metric_min else 5 + ((value - metric_min) / (metric_max - metric_min)) * 15
        intensity = 50 if metric_max == metric_min else int(50 + ((value - metric_min) / (metric_max - metric_min)) * 205)
        color = f"rgb({255-intensity},{50},{intensity})"

        # folium.CircleMarker(
        #     location=[row["Latitude"], row["Longitude"]],
        #     radius=size,
        #     popup=(
        #         f"<b>{row['locality']}</b><br>"
        #         f"City: {row['city']}<br>"
        #         f"Location: {row['location']}<br>"
        #         f"Segment: {row['segment']}<br>"
        #         f"Type: {row['property_type']}<br>"
        #         f"{metric}: {value}"
        #     ),
        #     color=color,
        #     fill=True,
        #     fill_color=color,
        #     fill_opacity=0.7
        # ).add_to(m)
        
        # Format the value based on the metric
        if metric == "rates_per_sqft":
            display_value = f"₹{value:,.0f}"
        elif metric == "rental_yields":
            display_value = f"{value*100:.2f}%"
        else:
            display_value = f"{value:.2f}"
        
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=size,
            popup=folium.Popup(
                html=f"""
                <div style="font-size:12px; line-height:1.4; padding:5px; max-width:200px;">
                    <b>{row['locality']}</b><br>
                    <span style="color:gray;">City:</span> {row['city']}<br>
                    <span style="color:gray;">Location:</span> {row['location']}<br>
                    <span style="color:gray;">Segment:</span> {row['segment']}<br>
                    <span style="color:gray;">Type:</span> {row['property_type']}<br>
                    <span style="color:darkblue;">{metric}:</span> {display_value}
                </div>
                """,
                max_width=250,
            ),
            tooltip=f"{row['locality']} – {display_value}",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7
        ).add_to(m)



    st.subheader("🗺️ Property Map")
    st_folium(m, width=1000, height=600)
else:
    st.info("Adjust filters to view properties on the map.")
    
# ==============================
# BAR CHART SECTION
# ==============================
st.markdown("---")
#st.subheader("📊 Locality Comparison")
st.subheader("📊 Comparison Charts")

if selected_property_type != "All" and selected_city != "All" and not filtered_df.empty:
    # Sort by metric value only (descending)
    #bar_data = filtered_df.sort_values(by=[metric], ascending=[False])
    temp_df = filtered_df.dropna(subset=["locality", metric])
    
    temp_df["location"] = temp_df["location"].fillna("Unknown")
    
    # Collapse to one row per locality (row with max metric)
    bar_data = (
        temp_df.loc[
            temp_df.groupby("locality")[metric].idxmax()
        ]
        .sort_values(by=metric, ascending=False)
    )
    # bar_data = (
    #     filtered_df.loc[
    #         filtered_df.groupby("locality")[metric].idxmax()
    #     ]
    #     .sort_values(by=metric, ascending=False)
    # )
    # Force unique order for localities
    #unique_localities = bar_data["locality"].drop_duplicates().tolist()
    unique_localities = bar_data["locality"].tolist()
    bar_data["locality"] = pd.Categorical(
        bar_data["locality"], 
        categories=unique_localities, 
        ordered=True
    )

    # Create bar chart
    fig_bar = px.bar(
        bar_data,
        x="locality",
        y=metric,
        color="location",   # just for coloring
        title=f"{metric} by Locality (sorted by {metric})"
    )

    # Force order on x-axis & rotate labels for readability
    fig_bar.update_layout(xaxis={'categoryorder':'array', 'categoryarray': unique_localities})
    fig_bar.update_xaxes(tickangle=-45)
        
    # Optional: tweak bar width individually (fraction of total width)
    fig_bar.update_traces(width=0.6)  # 0.6 means 60% of available space per bar
    
    # Format the y-axis and bar text dynamically
    if metric == "rates_per_sqft":
        fig_bar.update_yaxes(tickprefix="₹", tickformat=",")   # adds ₹ prefix with comma formatting
        fig_bar.update_traces(texttemplate="₹%{y:,.0f}")      # value on bars with ₹
    elif metric == "rental_yields":
        fig_bar.update_yaxes(ticksuffix="%", tickformat=".2f")  # add % to y-axis
        fig_bar.update_traces(texttemplate="%{y:.2f}%")         # value on bars
    else:
        fig_bar.update_traces(texttemplate="%{y:.2f}") 

    st.plotly_chart(fig_bar, use_container_width=True)

elif selected_property_type == "All" or selected_city == "All":
    st.info("Select a specific City & Property Type to view the bar chart.")
else:
    st.warning("No data available for the selected filters.")
    


    

# ==============================
# DISTANCE CALCULATION
# ==============================
st.markdown("---")
#st.subheader("📍 Locality Distance Comparison")

def haversine(lat1, lon1, lat2, lon2):
    # convert decimal degrees to radians
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

# ==============================
# LOCALITY DISTANCE CHART
# ==============================
if selected_property_type != "All" and selected_city != "All" and not filtered_df.empty:
    
    ref_locality = st.selectbox("Select Reference Locality", sorted(df[df["city"] == selected_city]["locality"].unique()))

    if ref_locality:
        ref_row = df[(df["city"] == selected_city) & (df["locality"] == ref_locality)].iloc[0]
        ref_lat, ref_lon = ref_row["Latitude"], ref_row["Longitude"]

        # Calculate distance of all localities from reference
        df_dist = filtered_df.copy()
        df_dist = df_dist.dropna(subset=["locality", metric])

        df_dist = df_dist.loc[
            df_dist.groupby("locality")[metric].idxmax()
        ]
        df_dist["distance_km"] = df_dist.apply(
            lambda r: haversine(ref_lat, ref_lon, r["Latitude"], r["Longitude"]), axis=1
        )

        # Bucket distances
        def distance_bucket(d):
            if d < 2: return "0-2 km"
            elif d < 5: return "2-5 km"
            elif d < 10: return "5-10 km"
            else: return ">10 km"

        df_dist["distance_bucket"] = df_dist["distance_km"].apply(distance_bucket)

        # Exclude the reference locality itself (distance = 0)
        df_dist = df_dist[df_dist["locality"] != ref_locality]

        # Sort by distance
        df_dist = df_dist.sort_values("distance_km", ascending=True)

        # Plot bar chart
        fig_dist = px.bar(
            df_dist,
            x="locality",
            y=metric,
            color="distance_km",
            #category_orders={"distance_bucket": ["0-2 km", "2-5 km", "5-10 km", ">10 km"]},
            hover_data=["distance_km"],
            title=f"{metric} vs Distance from {ref_locality}"
        )
        # Increase y-axis height
        fig_dist.update_layout(
            xaxis_tickangle=-45,
            height=600  # Adjust this value as needed (e.g., 700 or 800 for taller chart)
        )
        
        # Optional: tweak bar width individually (fraction of total width)
        fig_dist.update_traces(width=0.6)
        
        # Format the y-axis and bar text dynamically
        if metric == "rates_per_sqft":
            fig_dist.update_yaxes(tickprefix="₹", tickformat=",")   # adds ₹ prefix with comma formatting
            fig_dist.update_traces(texttemplate="₹%{y:,.0f}")      # value on bars with ₹
        elif metric == "rental_yields":
            fig_dist.update_yaxes(ticksuffix="%", tickformat=".2f")  # add % to y-axis
            fig_dist.update_traces(texttemplate="%{y:.2f}%")         # value on bars
        else:
            fig_dist.update_traces(texttemplate="%{y:.2f}") 
        
        st.plotly_chart(fig_dist, use_container_width=True)
elif selected_property_type == "All" or selected_city == "All":
    st.info("Select a specific City & Property Type to view the bar chart.")
else:
    st.warning("No data available for the selected filters.")

st.markdown("---")
st.subheader("💬 Feedback")

# Embed Google Form
form_url = st.secrets["FEEDBACK_FORM_URL"] 
components.iframe(form_url, height=600, scrolling=True)

# st.markdown("---")
# st.subheader("💬 Feedback")

# # --- Google Sheets setup ---
# # --- Google Sheets setup ---
# scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# # Load JSON string from Streamlit Secrets
# service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_KEY"])

# # Authenticate using the dict instead of a file
# creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
# client = gspread.authorize(creds)

# # Open the sheet (must already exist)
# sheet = client.open("Property Finder Dashboard Feedback").sheet1  # opens first worksheet

# with st.form("feedback_form"):
#     q1 = st.text_area("1. What did you like on the dashboard?")
#     q2 = st.text_area("2. What do you want to make your property search better?")
#     q3 = st.text_area("3. Any other inputs?")
    
#     submitted = st.form_submit_button("Submit")
#     if submitted:
#         timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         sheet.append_row([timestamp, q1, q2, q3])

#         st.success("✅ Thanks! Your feedback has been recorded.")


