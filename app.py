import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Golf Bet Settler", page_icon="⛳", layout="centered")

st.title("⛳ Golf Bet Settler")
st.markdown("Calculate and net off all golf bets to leave the fewest payments possible.")

# The URL you provided
SHEET_URL = "https://docs.google.com/spreadsheets/d/1JFo65TUfuRE4WKK4YTrIi0M92yGrm-vwvC6fLTmnky8/edit?gid=0#gid=0"

# --- 1. Display Persistent Latest Results ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # ttl=0 forces Streamlit to fetch the live sheet, bypassing the cache
    df = conn.read(spreadsheet=SHEET_URL, ttl=0)
    
    if not df.empty and "Date" in df.columns:
        df = df.dropna(subset=['Date'])
        if not df.empty:
            # Get the single row of data
            latest_row = df.iloc[-1]
            
            with st.container(border=True):
                st.subheader("📌 Latest Saved Round Details")
                st.write(f"**Date:** {latest_row['Date']} | **Players:** {latest_row['Players']}")
                
                # Show the match details if they exist in the sheet
                if "Match Details" in df.columns and pd.notna(latest_row['Match Details']):
                    st.markdown("**How it played out:**")
                    # Replace single newlines with double to force markdown rendering for older saved data
                    display_details = str(latest_row['Match Details']).replace('\n', '\n\n')
                    st.info(display_details)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Individual Breakdown:**")
                    st.text(latest_row['Individual Breakdown'])
                with col2:
                    st.markdown("**Optimized Settlement:**")
                    st.text(latest_row['Optimized Settlement'])
                    
            st.divider()
except Exception as e:
    # If the sheet is completely empty or fails to load, just silently continue
    pass


# --- 2. Record New Round ---
st.header("🏌️ Record New Round")

date_played = st.date_input("Date of Round", datetime.date.today())
num_players = st.radio("How many players?", [2, 3, 4], index=2, horizontal=True)

players = []
cols = st.columns(num_players)
default_names = ["Eddie", "Ronan", "Dale", "Chris"]

for i in range(num_players):
    default_val = default_names[i] if i < len(default_names) else f"Player {i+1}"
    name = cols[i].text_input(f"Player {i+1} Name", value=default_val).strip()
    players.append(name)

if len(set(players)) != num_players or "" in players:
    st.warning("Please ensure all players have unique, non-empty names.")
    st.stop()

pairwise_debts = {p1: {p2: 0.0 for p2 in players} for p1 in players}
match_summary_lines = []

# --- 2's Competition ---
st.subheader("2's Competition")
play_twos = st.checkbox("Include 2's competition?", value=True)

if play_twos:
    col1, col2 = st.columns(2)
    with col1:
        twos_fee = st.number_input("Cost per person (€)", min_value=0.0, value=2.0, step=1.0)
    with col2:
        twos_payer = st.selectbox("Who paid for the 2's?", players)
    
    match_summary_lines.append(f"- **2's Comp:** {twos_payer} paid (€{twos_fee} each).")
    
    for p in players:
        if p != twos_payer:
            pairwise_debts[p][twos_payer] += twos_fee

# --- Nassau Match ---
st.subheader("Nassau Match (€2-€2-€2)")
st.caption("If a leg is halved, its value rolls over to the next leg.")

nassau_f9 = st.selectbox("Front 9 Winner", ["Halved
