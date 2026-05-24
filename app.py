import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Golf Bet Settler", page_icon="⛳", layout="centered")

st.title("⛳ Golf Bet Settler")

# The URL you provided
SHEET_URL = "https://docs.google.com/spreadsheets/d/1JFo65TUfuRE4WKK4YTrIi0M92yGrm-vwvC6fLTmnky8/edit?gid=0#gid=0"

tab1, tab2 = st.tabs(["🏌️ Record New Round", "📅 View Historical Results"])

with tab1:
    st.markdown("Calculate and net off all golf bets to leave the fewest payments possible.")
    
    # --- 1. Player & Date Setup ---
    st.header("1. Round Details")
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
    
    # --- 2. 2's Competition ---
    st.header("2. 2's Competition")
    play_twos = st.checkbox("Include 2's competition?", value=True)
    
    if play_twos:
        col1, col2 = st.columns(2)
        with col1:
            twos_fee = st.number_input("Cost per person (€)", min_value=0.0, value=2.0, step=1.0)
        with col2:
            twos_payer = st.selectbox("Who paid for the 2's?", players)
        
        for p in players:
            if p != twos_payer:
                pairwise_debts[p][twos_payer] += twos_fee
    
    # --- 3. Nassau Match ---
    st.header("3. Nassau Match (€2-€2-€2)")
    st.caption("If a leg is halved, its value rolls over to the next leg.")
    
    nassau_f9 = st.selectbox("Front 9 Winner", ["Halved"] + players)
    nassau_b9 = st.selectbox("Back 9 Winner", ["Halved"] + players)
    nassau_overall = st.selectbox("Overall Winner", ["Halved"] + players)
    
    base_bet = 2.0
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
    
    # --- 4. Side Games (Eddie vs Dale) ---
    player_names_lower = [p.lower() for p in players]
    eddie_playing = any("eddie" in p for p in player_names_lower)
    dale_playing = any("dale" in p for p in player_names_lower)
    
    if eddie_playing and dale_playing:
        st.header("4. Side Game (Eddie vs Dale)")
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
            
        eddie_pts = (eddie_birdies * 1) + (eddie_eagles * 2)
        dale_pts = (dale_birdies * 1) + (dale_eagles * 2)
        
        net_diff = eddie_pts - dale_pts
        
        if net_diff > 0:
            pairwise_debts[dale_name][eddie_name] += net_diff
        elif net_diff < 0:
            pairwise_debts[eddie_name][dale_name] += abs(net_diff)
    
    # --- 5. Final Settlement & Netting ---
    st.header("5. Final Settlement")
    
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

    # --- 6. Save to Google Sheets ---
    st.divider()
    if st.button("💾 Save Results to Google Sheet"):
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            
            # Create the new row
            new_row = pd.DataFrame([{
                "Date": str(date_played),
                "Players": ", ".join(players),
                "Individual Breakdown": breakdown_str,
                "Optimized Settlement": settlement_str
            }])
            
            # Fetch existing data
            existing_data = conn.read(spreadsheet=SHEET_URL, usecols=[0, 1, 2, 3])
            
            # Append new row
            updated_data = pd.concat([existing_data, new_row], ignore_index=True)
            
            # Write back to sheet (FIXED: added spreadsheet=SHEET_URL here)
            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_data)
            st.success(f"Results for {date_played} successfully saved to Google Sheets!")
            
        except Exception as e:
            st.error(f"Error saving to Google Sheets: {e}")
            st.caption("Did you configure your `secrets.toml` and share the sheet with your service account?")

with tab2:
    st.header("📅 Historical Results")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=SHEET_URL, usecols=[0, 1, 2, 3])
        
        if df.empty or "Date" not in df.columns:
            st.info("No historical data found. Make sure you have saved a round and your Google Sheet has the correct headers (Date, Players, Individual Breakdown, Optimized Settlement).")
        else:
            # Drop empty rows that might have been fetched
            df = df.dropna(subset=['Date'])
            df['Date'] = df['Date'].astype(str)
            
            available_dates = df['Date'].unique().tolist()
            # Sort dates descending (newest first)
            available_dates.sort(reverse=True)
            
            selected_date = st.selectbox("Select Date to View", available_dates)
            
            if selected_date:
                filtered_df = df[df['Date'] == selected_date]
                for index, row in filtered_df.iterrows():
                    with st.container(border=True):
                        st.subheader(f"Round on {row['Date']}")
                        st.write(f"**Players:** {row['Players']}")
                        st.markdown("**Individual Breakdown:**")
                        st.text(row['Individual Breakdown'])
                        st.markdown("**Optimized Settlement:**")
                        st.text(row['Optimized Settlement'])
    except Exception as e:
        st.error(f"Error reading from Google Sheets: {e}")
