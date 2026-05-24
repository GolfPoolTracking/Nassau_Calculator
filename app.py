import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Golf Bet Settler", page_icon="⛳", layout="centered")

# The URL to your Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1JFo65TUfuRE4WKK4YTrIi0M92yGrm-vwvC6fLTmnky8/edit?gid=0#gid=0"

st.title("⛳ Golf Bet Settler")
st.markdown("Calculate, net off golf bets, and track historical results.")

# Create tabs
tab_calc, tab_hist = st.tabs(["📊 Calculate & Save", "📅 Historical Results"])

with tab_calc:
    st.header("1. Match Details")
    col1, col2 = st.columns(2)
    with col1:
        round_date = st.date_input("Date of Round", datetime.today())
    with col2:
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

    # Initialize pairwise debt matrix (who owes who)
    pairwise_debts = {p1: {p2: 0.0 for p2 in players} for p1 in players}

    # --- 2. 2's Competition ---
    st.header("2. 2's Competition")
    play_twos = st.checkbox("Include 2's competition?", value=True)

    if play_twos:
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            twos_fee = st.number_input("Cost per person (€)", min_value=0.0, value=2.0, step=1.0)
        with col_t2:
            twos_payer = st.selectbox("Who paid for the 2's?", players)
        
        # Calculate 2's debts
        for p in players:
            if p != twos_payer:
                pairwise_debts[p][twos_payer] += twos_fee

    # --- 3. Nassau Match ---
    st.header("3. Nassau Match (€2-€2-€2)")
    st.caption("If a leg is halved, its value rolls over to the next leg.")

    nassau_f9 = st.selectbox("Front 9 Winner", ["Halved"] + players)
    nassau_b9 = st.selectbox("Back 9 Winner", ["Halved"] + players)
    nassau_overall = st.selectbox("Overall Winner", ["Halved"] + players)

    # Nassau rollover logic
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
        """If a player wins a leg, everyone else owes them the bet amount."""
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
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown(f"**{eddie_name}**")
            eddie_birdies = st.number_input(f"{eddie_name}'s Birdies", min_value=0, value=0, step=1)
            eddie_eagles = st.number_input(f"{eddie_name}'s Eagles", min_value=0, value=0, step=1)
        with col_s2:
            st.markdown(f"**{dale_name}**")
            dale_birdies = st.number_input(f"{dale_name}'s Birdies", min_value=0, value=0, step=1)
            dale_eagles = st.number_input(f"{dale_name}'s Eagles", min_value=0, value=0, step=1)
            
        # Net side game results
        eddie_pts = (eddie_birdies * 1) + (eddie_eagles * 2)
        dale_pts = (dale_birdies * 1) + (dale_eagles * 2)
        
        net_diff = eddie_pts - dale_pts
        
        if net_diff > 0:
            pairwise_debts[dale_name][eddie_name] += net_diff
        elif net_diff < 0:
            pairwise_debts[eddie_name][dale_name] += abs(net_diff)

    # --- 5. Final Settlement & Netting ---
    st.header("5. Final Settlement")

    with st.expander("Show Individual Breakdown (Who owes who)"):
        has_individual_debts = False
        for i in range(len(players)):
            for j in range(i + 1, len(players)):
                p1 = players[i]
                p2 = players[j]
                
                net_p1_to_p2 = pairwise_debts[p1][p2] - pairwise_debts[p2][p1]
                
                if net_p1_to_p2 > 0.01:
                    st.write(f"🔹 **{p1}** owes **{p2}** €{net_p1_to_p2:.2f}")
                    has_individual_debts = True
                elif net_p1_to_p2 < -0.01:
                    st.write(f"🔹 **{p2}** owes **{p1}** €{abs(net_p1_to_p2):.2f}")
                    has_individual_debts = True

        if not has_individual_debts:
            st.info("Nobody owes anyone anything individually.")

    # Calculate overall global balances
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
    structured_transactions = [] # To save to dataframe
    i, j = 0, 0

    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]
        
        amount = min(debtor["amount"], creditor["amount"])
        
        transactions.append(f"✅ **{debtor['name']}** pays **{creditor['name']}** €{amount:.2f}")
        structured_transactions.append({
            "Date": str(round_date),
            "Debtor": debtor['name'],
            "Creditor": creditor['name'],
            "Amount": amount
        })
        
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
    else:
        st.info("All square! No payments needed.")

    # --- 6. Save to Sheets ---
    st.divider()
    if st.button("💾 Save Results to Google Sheet"):
        if not structured_transactions:
            st.warning("No payments to save! Everyone is all square.")
        else:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                
                # Fetch existing data
                try:
                    existing_data = conn.read(spreadsheet=SHEET_URL)
                    # Clean up empty rows that gsheets sometimes pulls
                    existing_data = existing_data.dropna(how="all") 
                except Exception:
                    # If sheet is empty or failing, create empty dataframe
                    existing_data = pd.DataFrame(columns=["Date", "Debtor", "Creditor", "Amount"])

                # Append new data
                new_data = pd.DataFrame(structured_transactions)
                updated_data = pd.concat([existing_data, new_data], ignore_index=True)

                # Push back to sheets
                conn.update(worksheet="Sheet1", data=updated_data)
                st.success(f"Successfully saved {len(structured_transactions)} transactions for {round_date}!")
                
            except Exception as e:
                st.error(f"Failed to save to Google Sheets. Did you set up your secrets.toml and share the sheet? Error: {e}")

# --- Tab 2: Historical Results ---
with tab_hist:
    st.header("📅 Historical Settlements")
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_history = conn.read(spreadsheet=SHEET_URL)
        df_history = df_history.dropna(how="all") # remove empty rows
        
        if df_history.empty or "Date" not in df_history.columns:
            st.info("No historical data found. Save a round first!")
        else:
            # Get unique dates
            unique_dates = df_history["Date"].unique().tolist()
            # Sort dates descending if possible
            unique_dates.sort(reverse=True)
            
            selected_date = st.selectbox("Select a Date to view", unique_dates)
            
            if selected_date:
                # Filter data
                filtered_df = df_history[df_history["Date"] == selected_date]
                
                st.subheader(f"Settlements for {selected_date}")
                
                # Display beautifully
                for index, row in filtered_df.iterrows():
                    st.write(f"✅ **{row['Debtor']}** paid **{row['Creditor']}** €{float(row['Amount']):.2f}")
                    
                with st.expander("View Raw Table Data"):
                    st.dataframe(filtered_df, hide_index=True)

    except Exception as e:
         st.warning("Cannot connect to Google Sheets. Ensure your service account is configured.")
         st.caption(f"Details: {e}")
