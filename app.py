import streamlit as st

st.set_page_config(page_title="Golf Bet Settler", page_icon="⛳", layout="centered")

st.title("⛳ Golf Bet Settler")
st.markdown("Calculate and net off all golf bets to leave the fewest payments possible.")

# --- 1. Player Setup ---
st.header("1. Players")
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

# Initialize balance sheet
balances = {p: 0.0 for p in players}

# --- 2. 2's Competition ---
st.header("2. 2's Competition")
play_twos = st.checkbox("Include 2's competition?", value=True)

if play_twos:
    col1, col2 = st.columns(2)
    with col1:
        twos_fee = st.number_input("Cost per person (€)", min_value=0.0, value=2.0, step=1.0)
    with col2:
        twos_payer = st.selectbox("Who paid for the 2's?", players)
    
    # Calculate 2's balances
    for p in players:
        if p == twos_payer:
            # Payer gets owed the fee by everyone else
            balances[p] += twos_fee * (num_players - 1)
        else:
            # Everyone else owes the fee
            balances[p] -= twos_fee

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
    overall_bet = 0.0 # Nobody wins the final rollover pot

def apply_nassau_winnings(winner, bet_amount):
    """If a player wins a leg, everyone else pays them the bet amount."""
    if winner != "Halved" and bet_amount > 0:
        for p in players:
            if p == winner:
                balances[p] += bet_amount * (num_players - 1)
            else:
                balances[p] -= bet_amount

apply_nassau_winnings(nassau_f9, f9_bet)
apply_nassau_winnings(nassau_b9, b9_bet)
apply_nassau_winnings(nassau_overall, overall_bet)

# --- 4. Side Games (Eddie vs Dale) ---
# Check if both Eddie and Dale are currently playing (case-insensitive)
player_names_lower = [p.lower() for p in players]
eddie_playing = any("eddie" in p for p in player_names_lower)
dale_playing = any("dale" in p for p in player_names_lower)

if eddie_playing and dale_playing:
    st.header("4. Side Game (Eddie vs Dale)")
    st.caption("Birdies = €1, Eagles = €2")
    
    # Extract exact typed names to update the balance dict correctly
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
        
    # Net side game results
    eddie_pts = (eddie_birdies * 1) + (eddie_eagles * 2)
    dale_pts = (dale_birdies * 1) + (dale_eagles * 2)
    
    eddie_net_side_game = eddie_pts - dale_pts
    balances[eddie_name] += eddie_net_side_game
    balances[dale_name] -= eddie_net_side_game


# --- 5. Final Settlement & Netting ---
st.header("5. Final Settlement")

with st.expander("Show Gross Balances Before Netting"):
    st.json({k: f"€{v:.2f}" for k, v in balances.items()})

# Separate into who owes money (debtors) and who is owed money (creditors)
debtors = []
creditors = []

for p, b in balances.items():
    if b < -0.01: # Use 0.01 to avoid float precision issues
        debtors.append({"name": p, "amount": abs(b)})
    elif b > 0.01:
        creditors.append({"name": p, "amount": b})

# Sort descending: largest debtors pay largest creditors first (greedy algorithm to minimize transactions)
debtors.sort(key=lambda x: x["amount"], reverse=True)
creditors.sort(key=lambda x: x["amount"], reverse=True)

transactions = []
i, j = 0, 0

while i < len(debtors) and j < len(creditors):
    debtor = debtors[i]
    creditor = creditors[j]
    
    # The transaction amount is the smaller of the debt or the credit
    amount = min(debtor["amount"], creditor["amount"])
    
    transactions.append(f"**{debtor['name']}** pays **{creditor['name']}** €{amount:.2f}")
    
    # Adjust balances
    debtor["amount"] -= amount
    creditor["amount"] -= amount
    
    # Move to the next person if they are settled
    if debtor["amount"] < 0.01:
        i += 1
    if creditor["amount"] < 0.01:
        j += 1

st.subheader("Fewest Payments to Settle Up:")
if transactions:
    for t in transactions:
        st.success(t)
else:
    st.info("All square! No payments needed.")
