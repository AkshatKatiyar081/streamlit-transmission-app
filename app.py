import re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

# Load Data
try:
    df = pd.read_csv("Transmission_Media_Comparison.csv", encoding="utf-8-sig")
except UnicodeDecodeError:
    df = pd.read_csv("Transmission_Media_Comparison.csv", encoding="latin-1")

# ---------------------------
# Simple column normalization
# ---------------------------
df.columns = df.columns.str.strip().str.lower()

# Map column names to standard names
column_mapping = {}
for col in df.columns:
    if 'media' in col or 'type' in col:
        column_mapping[col] = 'media_type'
    elif 'speed' in col or 'mbps' in col or 'gbps' in col:
        column_mapping[col] = 'speed'
    elif 'cost_usd' in col:
        column_mapping[col] = 'cost_usd'
    elif 'cost' in col:
        column_mapping[col] = 'cost'
    elif 'reliability' in col:
        column_mapping[col] = 'reliability'
    elif 'distance' in col or 'coverage' in col:
        column_mapping[col] = 'coverage'
    elif 'interference' in col:
        column_mapping[col] = 'interference'
    elif 'notes' in col or 'use' in col:
        column_mapping[col] = 'notes'
    else:
        column_mapping[col] = col

# Rename columns
df = df.rename(columns=column_mapping)

# Ensure we have the required columns, if not, use the first available columns
available_columns = df.columns.tolist()
if 'media_type' not in available_columns and len(available_columns) > 0:
    df = df.rename(columns={available_columns[0]: 'media_type'})
if 'speed' not in available_columns and len(available_columns) > 1:
    df = df.rename(columns={available_columns[1]: 'speed'})
if 'cost' not in available_columns and len(available_columns) > 2:
    df = df.rename(columns={available_columns[2]: 'cost'})
if 'reliability' not in available_columns and len(available_columns) > 3:
    df = df.rename(columns={available_columns[3]: 'reliability'})
if 'interference' not in available_columns and len(available_columns) > 4:
    df = df.rename(columns={available_columns[4]: 'interference'})
if 'coverage' not in available_columns and len(available_columns) > 5:
    df = df.rename(columns={available_columns[5]: 'coverage'})

# ---------------------------
# IMPROVED Speed parser
# ---------------------------
def parse_speed_to_mbps(s):
    if pd.isna(s):
        return np.nan
    text = str(s).strip()
    if text == "":
        return np.nan
    
    # Clean the text - fix common issues
    text = (text.replace("~", "")
              .replace(",", "")
              .replace("B", "-")  # Fix "B" used as dash
              .replace(" ", ""))   # Remove spaces for better parsing
    text = re.sub(r"(?i)up to", "", text)
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    
    # Handle Kbps first
    if "kbps" in text.lower():
        match = re.search(r'(\d+(?:\.\d+)?)\s*kbps', text, re.IGNORECASE)
        if match:
            return float(match.group(1)) / 1000
    
    # Handle ranges with "-"
    if "-" in text:
        numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
        if numbers:
            numbers = [float(num) for num in numbers]
            max_num = max(numbers)
            
            if "gbps" in text.lower() or max_num < 10:
                return max_num * 1000
            elif "mbps" in text.lower() or max_num > 100:
                return max_num
            else:
                return max_num * 1000 if max_num < 100 else max_num
    
    # Handle single values with explicit units
    gbps_match = re.search(r'(\d+(?:\.\d+)?)\s*gbps', text, re.IGNORECASE)
    if gbps_match:
        return float(gbps_match.group(1)) * 1000
    
    mbps_match = re.search(r'(\d+(?:\.\d+)?)\s*mbps', text, re.IGNORECASE)
    if mbps_match:
        return float(mbps_match.group(1))
    
    # Extract any remaining numbers as fallback
    numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
    if numbers:
        max_num = max(map(float, numbers))
        if max_num < 10:
            return max_num * 1000
        elif max_num > 1000:
            return max_num
        else:
            return max_num
    
    return np.nan

# Apply speed parsing if speed column exists
if 'speed' in df.columns:
    df["parsed_speed_mbps"] = df["speed"].apply(parse_speed_to_mbps)
    df["parsed_speed_gbps"] = df["parsed_speed_mbps"] / 1000.0

# ---------------------------
# Fix specific known issues
# ---------------------------
def fix_media_type_names(name):
    fixes = {
        "Twisted Pair (Cn15/6)": "Twisted Pair (Cat5/6)",
        "WIFI (802.11ac/aa)": "WiFi (802.11ac/ax)",
        "LoBOWAN": "LoRaWAN"
    }
    return fixes.get(name, name)

def fix_speed_values(speed_text):
    fixes = {
        "100 Mbps B 10 Gbps": "100 Mbps - 10 Gbps",
        "300 Mbps B 9.6 Gbps": "300 Mbps - 9.6 Gbps", 
        "1810 Gbps": "1-10 Gbps",
        "2810 Mbps": "2-10 Mbps",
        "108100 Mbps": "10-100 Mbps",
        "10820 Gbps": "10-20 Gbps",
        "0.3850 Kbps": "0.3-50 Kbps"
    }
    return fixes.get(str(speed_text), speed_text)

# Apply fixes
if 'media_type' in df.columns:
    df["media_type"] = df["media_type"].apply(fix_media_type_names)

if 'speed' in df.columns:
    df["speed"] = df["speed"].apply(fix_speed_values)
    # Re-parse speeds after fixing
    df["parsed_speed_mbps"] = df["speed"].apply(parse_speed_to_mbps)
    df["parsed_speed_gbps"] = df["parsed_speed_mbps"] / 1000.0

# Ensure numeric columns
for col in ['cost', 'reliability', 'interference', 'cost_usd']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# ---------------------------
# Dashboard
# ---------------------------
st.title("📡 Transmission Media Comparison Dashboard")
st.markdown("Interactive dashboard comparing different transmission media types.")

# Sidebar Navigation
st.sidebar.title("Navigation")
app_mode = st.sidebar.selectbox(
    "Choose Dashboard Mode:",
    ["Main Dashboard", "Cost Analysis", "Data Overview"]
)

# MAIN DASHBOARD
if app_mode == "Main Dashboard":
    st.header("Comprehensive Comparison Dashboard")
    
    options = []
    if 'parsed_speed_gbps' in df.columns:
        options.append("Speed")
    if 'reliability' in df.columns and 'interference' in df.columns:
        options.append("Reliability vs Interference")
    if 'coverage' in df.columns:
        options.append("Coverage")
    
    if not options:
        st.error("No compatible data columns found. Please check your CSV file.")
        st.write("Available columns:", df.columns.tolist())
    else:
        option = st.sidebar.selectbox("Choose what to compare:", options)

        if option == "Speed" and 'parsed_speed_gbps' in df.columns:
            col1, col2 = st.columns([3, 1])
            with col1:
                fig = px.bar(df, x="media_type", y="parsed_speed_gbps",
                             title="Speed Comparison (Gbps)", 
                             text=df["parsed_speed_gbps"].apply(lambda x: f"{x:.2f} Gbps"),
                             color="parsed_speed_gbps")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.metric("Fastest", f"{df['parsed_speed_gbps'].max():.2f} Gbps")

        elif option == "Reliability vs Interference" and 'reliability' in df.columns and 'interference' in df.columns:
            grouped = df.groupby(["interference", "reliability"]).agg({
                "media_type": lambda x: ", ".join(x),
                "reliability": "first",
                "interference": "first"
            }).reset_index(drop=True)

            fig = px.scatter(grouped, x="interference",  y="reliability",size="reliability",text="media_type",color="interference",
                             title="Reliability vs Interference ")
            
            fig.update_traces(textposition='top center', textfont=dict(size=11))
            st.plotly_chart(fig, use_container_width=True)

        elif option == "Coverage" and 'coverage' in df.columns:
            st.dataframe(df[["media_type", "coverage"]], use_container_width=True)

# COST ANALYSIS
elif app_mode == "Cost Analysis" and ('cost' in df.columns or 'cost_usd' in df.columns):
    st.header("Cost Analysis")

    if "cost" in df.columns:
        fig_line = px.line(df, x="media_type", y="cost", markers=True,
                           title="Relative Cost (1-5)")
        st.plotly_chart(fig_line, use_container_width=True)
        st.metric("Average Relative Cost", f"{df['cost'].mean():.1f}/5")

    if "cost_usd" in df.columns:
        fig_bar = px.bar(df, x="media_type", y="cost_usd", text="cost_usd", color="cost_usd",
                         title="Cost (USD)")
        fig_bar.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
        st.plotly_chart(fig_bar, use_container_width=True)
        st.metric("Average Cost (USD)", f"${df['cost_usd'].mean():.2f}")

    st.markdown("*Note: Costs are approximate and may vary by vendor, region, and installation.*")

# SPEED ANALYSIS
elif app_mode == "Speed Analysis" and 'parsed_speed_gbps' in df.columns:
    st.header("Speed Analysis")
    fig = px.bar(df, x="media_type", y="parsed_speed_gbps", color="parsed_speed_gbps")
    st.plotly_chart(fig, use_container_width=True)

# DATA OVERVIEW
elif app_mode == "Data Overview":
    st.header("Data Overview")
    st.dataframe(df, use_container_width=True)

else:
    st.error("Required data not available for this mode.")
    st.write("Available columns:", df.columns.tolist())