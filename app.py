import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

#Ping to keep app and DB alive
if st.query_params.get("view") == "ping":
    st.write("Server is awake and ready! 🟢")
    st.stop()

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
    
    match_summary_lines.append(f"- **2's Comp:** {twos_payer} paid (€{twos_fee:.2f} each).")
    
    for p in players:
        if p != twos_payer:
            pairwise_debts[p][twos_payer] += twos_fee

# --- Nassau Match ---
st.subheader("Nassau Match")
base_bet = st.number_input("Base bet per leg (€)", min_value=0.0, value=2.0, step=0.5)
st.caption(f"Playing €{base_bet:.2f}-€{base_bet:.2f}-€{base_bet:.2f}. If a leg is halved, its value rolls over to the next leg.")

nassau_f9 = st.selectbox("Front 9 Winner", ["Halved"] + players)
nassau_b9 = st.selectbox("Back 9 Winner", ["Halved"] + players)
nassau_overall = st.selectbox("Overall Winner", ["Halved"] + players)

match_summary_lines.append(f"- **Nassau:** F9: {nassau_f9} | B9: {nassau_b9} | Overall: {nassau_overall}")

f9_bet = base_bet
b9_bet = base_bet
overall_bet = base_bet

if nassau_f9 == "Halved":
    b9_bet += f9_bet
    f9_bet = 0.0

if nassau_b9 == "Halved":
    overall_bet += b9_bet
    b9_bet = 0.0

if nassau_overall == "Halved":
    overall_bet = 0.0

def apply_nassau_winnings(winner, bet_amount):
    if winner != "Halved" and bet_amount > 0:
        for p in players:
            if p != winner:
                pairwise_debts[p][winner] += bet_amount

apply_nassau_winnings(nassau_f9, f9_bet)
apply_nassau_winnings(nassau_b9, b9_bet)
apply_nassau_winnings(nassau_overall, overall_bet)

# --- Side Games (Eddie vs Dale) ---
player_names_lower = [p.lower() for p in players]
eddie_playing = any("eddie" in p for p in player_names_lower)
dale_playing = any("dale" in p for p in player_names_lower)

if eddie_playing and dale_playing:
    st.subheader("Side Game (Eddie vs Dale)")
    st.caption("Birdies = €1, Eagles = €2")
    
    eddie_name = next(p for p in players if "eddie" in p.lower())
    dale_name = next(p for p in players if "dale" in p.lower())
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{eddie_name}**")
        eddie_birdies = st.number_input(f"{eddie_name}'s Birdies", min_value=0, value=0, step=1)
        eddie_eagles = st.number_input(f"{eddie_name}'s Eagles", min_value=0, value=0, step=1)
    with col2:
        st.markdown(f"**{dale_name}**")
        dale_birdies = st.number_input(f"{dale_name}'s Birdies", min_value=0, value=0, step=1)
        dale_eagles = st.number_input(f"{dale_name}'s Eagles", min_value=0, value=0, step=1)
        
    match_summary_lines.append(f"- **Side Game:** {eddie_name} ({eddie_birdies}B, {eddie_eagles}E) vs {dale_name} ({dale_birdies}B, {dale_eagles}E)")
        
    eddie_pts = (eddie_birdies * 1) + (eddie_eagles * 2)
    dale_pts = (dale_birdies * 1) + (dale_eagles * 2)
    
    net_diff = eddie_pts - dale_pts
    
    if net_diff > 0:
        pairwise_debts[dale_name][eddie_name] += net_diff
    elif net_diff < 0:
        pairwise_debts[eddie_name][dale_name] += abs(net_diff)

# Compile match details string with double newlines for correct Markdown rendering
match_details_str = "\n\n".join(match_summary_lines)

# --- Final Settlement & Netting ---
st.header("Final Settlement")

st.subheader("Individual Breakdown (Who owes who)")
has_individual_debts = False
breakdown_lines = []

for i in range(len(players)):
    for j in range(i + 1, len(players)):
        p1 = players[i]
        p2 = players[j]
        net_p1_to_p2 = pairwise_debts[p1][p2] - pairwise_debts[p2][p1]
        
        if net_p1_to_p2 > 0.01:
            line = f"{p1} owes {p2} €{net_p1_to_p2:.2f}"
            st.write(f"🔹 **{p1}** owes **{p2}** €{net_p1_to_p2:.2f}")
            breakdown_lines.append(line)
            has_individual_debts = True
        elif net_p1_to_p2 < -0.01:
            line = f"{p2} owes {p1} €{abs(net_p1_to_p2):.2f}"
            st.write(f"🔹 **{p2}** owes **{p1}** €{abs(net_p1_to_p2):.2f}")
            breakdown_lines.append(line)
            has_individual_debts = True

if not has_individual_debts:
    st.info("Nobody owes anyone anything individually.")
    breakdown_str = "All square."
else:
    breakdown_str = "\n".join(breakdown_lines)

st.divider()

balances = {p: 0.0 for p in players}
for debtor in players:
    for creditor in players:
        amount = pairwise_debts[debtor][creditor]
        balances[debtor] -= amount
        balances[creditor] += amount

debtors = []
creditors = []

for p, b in balances.items():
    if b < -0.01:
        debtors.append({"name": p, "amount": abs(b)})
    elif b > 0.01:
        creditors.append({"name": p, "amount": b})

debtors.sort(key=lambda x: x["amount"], reverse=True)
creditors.sort(key=lambda x: x["amount"], reverse=True)

transactions = []
i, j = 0, 0

while i < len(debtors) and j < len(creditors):
    debtor = debtors[i]
    creditor = creditors[j]
    amount = min(debtor["amount"], creditor["amount"])
    
    transactions.append(f"✅ {debtor['name']} pays {creditor['name']} €{amount:.2f}")
    
    debtor["amount"] -= amount
    creditor["amount"] -= amount
    
    if debtor["amount"] < 0.01:
        i += 1
    if creditor["amount"] < 0.01:
        j += 1

st.subheader("Optimized Settlement")
if transactions:
    for t in transactions:
        st.success(t)
    settlement_str = "\n".join(transactions)
else:
    st.info("All square! No payments needed.")
    settlement_str = "No payments needed."

# --- Save & Overwrite Google Sheets ---
st.divider()
if st.button("💾 Save & Overwrite Results"):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Create a single-row dataframe (this replaces the history entirely)
        new_row = pd.DataFrame([{
            "Date": str(date_played),
            "Players": ", ".join(players),
            "Match Details": match_details_str,
            "Individual Breakdown": breakdown_str,
            "Optimized Settlement": settlement_str
        }])
        
        # Overwrite whatever was there previously
        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=new_row)
        
        # Clear Streamlit's cache to ensure the read at the top of the app gets this new row
        st.cache_data.clear()
        
        st.success(f"Results successfully updated!")
        
        # Automatically refresh the app so the new results appear at the top immediately
        st.rerun()
        
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {e}")
