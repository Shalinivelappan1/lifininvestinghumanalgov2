import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Human vs Algo Market Lab", layout="wide")

# =====================================================
# INITIALIZE STATE (RUNS ONLY ONCE)
# =====================================================
if "market" not in st.session_state:

    market = {
        "round": 1,
        "liquidity_freeze": False,

        "assets": {
            "ABC": {"price": 100.0, "history": [], "halted": False, "cb_ref": 100.0, "pending_shock": 0.0},
            "XYZ": {"price": 200.0, "history": [], "halted": False, "cb_ref": 200.0, "pending_shock": 0.0},
        },

        # Risk controls
        "position_limit": 500,      # shares
        "risk_budget_pct": 0.25,     # 25% of net worth

        "humans": {},
        "bots": {},

        "trade_log": []
    }

    # 10 humans
    for i in range(1, 11):
        market["humans"][f"Human_{i}"] = {
            "cash": 100000.0,
            "pos": {"ABC": 50, "XYZ": 25}
        }

    # Bots
    bot_names = ["Momentum Bot", "MeanReversion Bot", "Panic Bot", "Random Bot", "Trend Bot"]
    for b in bot_names:
        market["bots"][b] = {
            "cash": 200000.0,
            "pos": {"ABC": 100, "XYZ": 50}
        }

    # Reckless hedge fund 😈
    market["bots"]["😈 Reckless Hedge Fund"] = {
        "cash": 500000.0,
        "pos": {"ABC": 0, "XYZ": 0}
    }

    st.session_state.market = market

market = st.session_state.market

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def net_worth(agent):
    return (
        agent["cash"]
        + agent["pos"]["ABC"] * market["assets"]["ABC"]["price"]
        + agent["pos"]["XYZ"] * market["assets"]["XYZ"]["price"]
    )

def risk_used(agent):
    return (
        abs(agent["pos"]["ABC"] * market["assets"]["ABC"]["price"])
        + abs(agent["pos"]["XYZ"] * market["assets"]["XYZ"]["price"])
    )

# =====================================================
# TITLE
# =====================================================
st.title("🤖📈 Human vs Algorithm Market Lab — Risk Controlled")
st.caption("Developed by Prof.Shalini Velappan, IIM Trichy.")

# =====================================================
# SIDEBAR — POLICY & RISK CONTROLS
# =====================================================
st.sidebar.header("🏛️ Policy & Shock Controls")

selected_asset = st.sidebar.selectbox("Select Asset", ["ABC", "XYZ"])

if st.sidebar.button("🚨 Bad News (-10%)"):
    market["assets"][selected_asset]["pending_shock"] = -0.10

if st.sidebar.button("✅ Good News (+10%)"):
    market["assets"][selected_asset]["pending_shock"] = +0.10

if st.sidebar.button("💣 Flash Crash (-25%)"):
    market["assets"][selected_asset]["pending_shock"] = -0.25

st.sidebar.divider()

if st.sidebar.button("🧊 Toggle Liquidity Freeze"):
    market["liquidity_freeze"] = not market["liquidity_freeze"]

if st.sidebar.button("🏦 Central Bank Intervention (+15% ALL)"):
    for a in market["assets"]:
        market["assets"][a]["price"] *= 1.15
        market["assets"][a]["halted"] = False
        market["assets"][a]["cb_ref"] = market["assets"][a]["price"]

st.sidebar.divider()

if st.sidebar.button("🟢 Resume All Trading"):
    for a in market["assets"]:
        market["assets"][a]["halted"] = False
        market["assets"][a]["cb_ref"] = market["assets"][a]["price"]

st.sidebar.divider()

st.sidebar.header("🧠 Risk Controls")

market["position_limit"] = st.sidebar.slider(
    "Position Limit (shares per asset)",
    min_value=100, max_value=2000, value=market["position_limit"], step=100
)

market["risk_budget_pct"] = st.sidebar.slider(
    "Risk Budget (% of Net Worth)",
    min_value=0.05, max_value=0.80, value=market["risk_budget_pct"], step=0.05
)

st.sidebar.divider()

if st.sidebar.button("🔁 Reset Simulation"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# =====================================================
# MARKET STATUS
# =====================================================
st.subheader("📊 Market Status")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Round", market["round"])
c2.metric("ABC", f"₹ {market['assets']['ABC']['price']:.2f}", "HALTED" if market["assets"]["ABC"]["halted"] else "LIVE")
c3.metric("XYZ", f"₹ {market['assets']['XYZ']['price']:.2f}", "HALTED" if market["assets"]["XYZ"]["halted"] else "LIVE")
c4.metric("Liquidity", "FROZEN" if market["liquidity_freeze"] else "NORMAL")

# =====================================================
# HUMAN DECISIONS
# =====================================================
st.subheader("👩‍🏫 Human Traders Decisions (Exact Quantity)")

human_orders = {}

cols = st.columns(5)
for i, name in enumerate(market["humans"].keys()):
    with cols[i % 5]:
        st.markdown(f"**{name}**")
        asset = st.selectbox("Asset", ["ABC", "XYZ"], key=f"{name}_asset")
        action = st.radio("Action", ["HOLD", "BUY", "SELL"], horizontal=True, key=f"{name}_action")
        qty = st.number_input("Qty", min_value=0, max_value=2000, value=0, step=50, key=f"{name}_qty")
        human_orders[name] = {"asset": asset, "action": action, "qty": qty}

# =====================================================
# RUN ROUND
# =====================================================
if st.button("▶️ Run Next Market Round"):

    trade_log_round = []

    # ----------------------------------
    # 1. APPLY NEWS SHOCKS (DOMINANT)
    # ----------------------------------
    news_applied = {"ABC": False, "XYZ": False}

    for a in market["assets"]:
        shock = market["assets"][a]["pending_shock"]
        if shock != 0:
            # Save history
            market["assets"][a]["history"].append(market["assets"][a]["price"])

            # Apply shock
            market["assets"][a]["price"] *= (1 + shock)

            # Reset CB reference
            market["assets"][a]["cb_ref"] = market["assets"][a]["price"]

            # Mark news applied
            news_applied[a] = True

            # Reset shock
            market["assets"][a]["pending_shock"] = 0.0

    # ----------------------------------
    # 2. COLLECT ORDER FLOW
    # ----------------------------------
    buy_vol = {"ABC": 0, "XYZ": 0}
    sell_vol = {"ABC": 0, "XYZ": 0}

    # ----------------------------------
    # 3. HUMAN ORDERS (WITH HARD LIMITS)
    # ----------------------------------
    if not market["liquidity_freeze"]:

        for hname, order in human_orders.items():
            human = market["humans"][hname]
            asset = order["asset"]
            action = order["action"]
            qty = order["qty"]
            price = market["assets"][asset]["price"]

            if qty <= 0 or action == "HOLD":
                continue

            if market["assets"][asset]["halted"]:
                trade_log_round.append([market["round"], hname, asset, action, qty, price, "BLOCKED", "HALTED"])
                continue

            # Position limit
            new_pos = human["pos"][asset] + (qty if action == "BUY" else -qty)
            if abs(new_pos) > market["position_limit"]:
                trade_log_round.append([market["round"], hname, asset, action, qty, price, "BLOCKED", "POS LIMIT"])
                continue

            # Risk limit (only for BUY)
            if action == "BUY":
                tmp = {"cash": human["cash"], "pos": human["pos"].copy()}
                tmp["pos"][asset] += qty
                new_risk = risk_used(tmp)
                limit = market["risk_budget_pct"] * net_worth(human)
                if new_risk > limit:
                    trade_log_round.append([market["round"], hname, asset, action, qty, price, "BLOCKED", "RISK LIMIT"])
                    continue

            # Execute
            if action == "BUY":
                buy_vol[asset] += qty
                human["pos"][asset] += qty
                human["cash"] -= qty * price
            else:
                sell_vol[asset] += qty
                human["pos"][asset] -= qty
                human["cash"] += qty * price

            trade_log_round.append([market["round"], hname, asset, action, qty, price, "EXECUTED", "OK"])

    # ----------------------------------
    # 4. BOTS
    # ----------------------------------
    for bname, bot in market["bots"].items():
        for asset in ["ABC", "XYZ"]:
            if market["assets"][asset]["halted"] or market["liquidity_freeze"]:
                continue

            price = market["assets"][asset]["price"]
            hist = market["assets"][asset]["history"]
            qty = 0

            # Reckless 😈
            if "Reckless" in bname:
                qty = 200
                if len(hist) > 0 and price < hist[-1]:
                    qty = 400
                buy_vol[asset] += qty
                bot["pos"][asset] += qty
                bot["cash"] -= qty * price
                trade_log_round.append([market["round"], bname, asset, "BUY", qty, price, "EXECUTED", "RECKLESS"])
                continue

            # Momentum
            if "Momentum" in bname and len(hist) > 0:
                if price > hist[-1]:
                    qty = 20; buy_vol[asset] += qty; bot["pos"][asset] += qty; bot["cash"] -= qty * price
                    trade_log_round.append([market["round"], bname, asset, "BUY", qty, price, "EXECUTED", "MOM"])
                else:
                    qty = 20; sell_vol[asset] += qty; bot["pos"][asset] -= qty; bot["cash"] += qty * price
                    trade_log_round.append([market["round"], bname, asset, "SELL", qty, price, "EXECUTED", "MOM"])

            # Mean reversion
            if "MeanReversion" in bname:
                ref = 100 if asset == "ABC" else 200
                if price > 1.2 * ref:
                    qty = 15; sell_vol[asset] += qty; bot["pos"][asset] -= qty; bot["cash"] += qty * price
                    trade_log_round.append([market["round"], bname, asset, "SELL", qty, price, "EXECUTED", "MEANREV"])
                elif price < 0.8 * ref:
                    qty = 15; buy_vol[asset] += qty; bot["pos"][asset] += qty; bot["cash"] -= qty * price
                    trade_log_round.append([market["round"], bname, asset, "BUY", qty, price, "EXECUTED", "MEANREV"])

            # Panic
            if "Panic" in bname and len(hist) > 0:
                if price < 0.95 * hist[-1]:
                    qty = 40; sell_vol[asset] += qty; bot["pos"][asset] -= qty; bot["cash"] += qty * price
                    trade_log_round.append([market["round"], bname, asset, "SELL", qty, price, "EXECUTED", "PANIC"])

            # Random
            if "Random" in bname:
                if np.random.rand() > 0.5:
                    qty = 10; buy_vol[asset] += qty; bot["pos"][asset] += qty; bot["cash"] -= qty * price
                    trade_log_round.append([market["round"], bname, asset, "BUY", qty, price, "EXECUTED", "RAND"])
                else:
                    qty = 10; sell_vol[asset] += qty; bot["pos"][asset] -= qty; bot["cash"] += qty * price
                    trade_log_round.append([market["round"], bname, asset, "SELL", qty, price, "EXECUTED", "RAND"])

            # Trend
            if "Trend" in bname and len(hist) > 1:
                if hist[-1] > hist[-2]:
                    qty = 20; buy_vol[asset] += qty; bot["pos"][asset] += qty; bot["cash"] -= qty * price
                    trade_log_round.append([market["round"], bname, asset, "BUY", qty, price, "EXECUTED", "TREND"])

    # ----------------------------------
    # 5. PRICE FORMATION (ONLY IF NO NEWS)
    # ----------------------------------
    for asset in ["ABC", "XYZ"]:

        if news_applied.get(asset, False):
            continue

        old_price = market["assets"][asset]["price"]
        market["assets"][asset]["history"].append(old_price)

        if market["assets"][asset]["halted"]:
            continue

        imbalance = buy_vol[asset] - sell_vol[asset]
        new_price = max(1.0, old_price + imbalance / 50.0)

        ref = market["assets"][asset]["cb_ref"]
        if abs(new_price - ref) / ref > 0.10:
            market["assets"][asset]["halted"] = True
        else:
            market["assets"][asset]["price"] = new_price
            market["assets"][asset]["cb_ref"] = new_price

    # ----------------------------------
    # 6. SAVE TRADE LOG
    # ----------------------------------
    market["trade_log"].extend(trade_log_round)

    market["round"] += 1

# =====================================================
# CHARTS
# =====================================================
st.subheader("📈 Price Evolution")

c1, c2 = st.columns(2)
with c1:
    if len(market["assets"]["ABC"]["history"]) > 0:
        st.line_chart(pd.DataFrame({"ABC": market["assets"]["ABC"]["history"]}))
with c2:
    if len(market["assets"]["XYZ"]["history"]) > 0:
        st.line_chart(pd.DataFrame({"XYZ": market["assets"]["XYZ"]["history"]}))

# =====================================================
# LEADERBOARD
# =====================================================
st.subheader("🏆 Leaderboard (Real Portfolios)")

rows = []
for name, h in market["humans"].items():
    rows.append({"Agent": name, "Type": "Human", "NetWorth": round(net_worth(h), 0)})
for name, b in market["bots"].items():
    rows.append({"Agent": name, "Type": "Bot", "NetWorth": round(net_worth(b), 0)})

df = pd.DataFrame(rows).sort_values("NetWorth", ascending=False)
st.dataframe(df, use_container_width=True)

# =====================================================
# TRADE LOG
# =====================================================
st.subheader("🧾 Trade History (Last 50)")

if len(market["trade_log"]) > 0:
    log_df = pd.DataFrame(
        market["trade_log"],
        columns=["Round", "Agent", "Asset", "Action", "Qty", "Price", "Status", "Reason"]
    )
    st.dataframe(log_df.tail(50), use_container_width=True)
else:
    st.write("No trades yet.")

# =====================================================
# TEACHING NOTE
# =====================================================
st.info("""
Guaranteed behavior:
• Good news → price up that round
• Bad news → price down that round
• Flash crash → big down move
• Trading reacts NEXT round
• Liquidity freeze → no trading
• Circuit breaker → halts
• Risk & position limits → hard blocked trades
""")
