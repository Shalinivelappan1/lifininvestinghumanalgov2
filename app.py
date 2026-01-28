import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Classroom Trading Lab (Humans vs Bots)", layout="wide")

# =====================================================
# INIT STATE
# =====================================================
if "market" not in st.session_state:

    market = {
        "round": 1,

        "assets": {
            "ABC": {"price": 100.0, "history": []},
            "XYZ": {"price": 200.0, "history": []},
        },

        "humans": {},
        "bots": {},

        "trade_log": [],
        "pnl_history": {}
    }

    # 10 human teams
    for i in range(1, 11):
        name = f"Team_{i}"
        market["humans"][name] = {
            "cash": 100000.0,
            "pos": {"ABC": 0, "XYZ": 0}
        }
        market["pnl_history"][name] = [100000.0]

    # Normal bots
    bot_names = ["Momentum Bot", "MeanReversion Bot", "Panic Bot", "Random Bot"]
    for b in bot_names:
        market["bots"][b] = {
            "cash": 200000.0,
            "pos": {"ABC": 0, "XYZ": 0}
        }
        market["pnl_history"][b] = [200000.0]

    # Reckless hedge fund 😈
    market["bots"]["😈 Reckless Hedge Fund"] = {
        "cash": 1000000.0,
        "pos": {"ABC": 0, "XYZ": 0}
    }
    market["pnl_history"]["😈 Reckless Hedge Fund"] = [1000000.0]

    st.session_state.market = market

market = st.session_state.market

# =====================================================
# HELPERS
# =====================================================
def net_worth(agent):
    return (
        agent["cash"]
        + agent["pos"]["ABC"] * market["assets"]["ABC"]["price"]
        + agent["pos"]["XYZ"] * market["assets"]["XYZ"]["price"]
    )

# =====================================================
# TITLE
# =====================================================
st.title("🤖📈 Classroom Trading Lab — Humans vs Bots (+ Reckless Fund)")
st.caption("📰 News moves prices immediately. ▶️ Run Round = humans + bots trade.")

# =====================================================
# SIDEBAR — NEWS
# =====================================================
st.sidebar.header("📰 News Shocks (Immediate)")

selected_asset = st.sidebar.selectbox(
    "Select Asset",
    ["ABC", "XYZ"],
    key="news_asset"
)

if st.sidebar.button("🚨 Bad News (-10%)"):
    a = market["assets"][selected_asset]
    a["history"].append(a["price"])
    a["price"] *= 0.90

if st.sidebar.button("✅ Good News (+10%)"):
    a = market["assets"][selected_asset]
    a["history"].append(a["price"])
    a["price"] *= 1.10

if st.sidebar.button("💣 Crash (-25%)"):
    a = market["assets"][selected_asset]
    a["history"].append(a["price"])
    a["price"] *= 0.75

st.sidebar.divider()

if st.sidebar.button("🔁 Reset Simulation"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# =====================================================
# MARKET STATUS
# =====================================================
st.subheader("📊 Market Status")

c1, c2, c3 = st.columns(3)
c1.metric("Round", market["round"])
c2.metric("ABC Price", f"₹ {market['assets']['ABC']['price']:.2f}")
c3.metric("XYZ Price", f"₹ {market['assets']['XYZ']['price']:.2f}")

# =====================================================
# HUMAN DECISIONS
# =====================================================
st.subheader("👩‍🏫 Team Decisions")

human_orders = {}

cols = st.columns(5)
for i, name in enumerate(market["humans"].keys()):
    with cols[i % 5]:
        st.markdown(f"**{name}**")
        asset = st.selectbox("Asset", ["ABC", "XYZ"], key=f"{name}_asset")
        action = st.radio("Action", ["HOLD", "BUY", "SELL"], horizontal=True, key=f"{name}_action")
        qty = st.number_input("Qty", min_value=0, max_value=2000, value=0, step=20, key=f"{name}_qty")

        human_orders[name] = {"asset": asset, "action": action, "qty": qty}

# =====================================================
# RUN ROUND (HUMANS + BOTS)
# =====================================================
if st.button("▶️ Run Next Round"):

    trade_log_round = []

    buy_vol = {"ABC": 0, "XYZ": 0}
    sell_vol = {"ABC": 0, "XYZ": 0}

    # -------------------------------
    # 1. HUMAN TRADES
    # -------------------------------
    for team, order in human_orders.items():
        human = market["humans"][team]
        asset = order["asset"]
        action = order["action"]
        qty = order["qty"]
        price = market["assets"][asset]["price"]

        if action == "HOLD" or qty <= 0:
            continue

        if action == "BUY":
            human["pos"][asset] += qty
            human["cash"] -= qty * price
            buy_vol[asset] += qty

        elif action == "SELL":
            human["pos"][asset] -= qty
            human["cash"] += qty * price
            sell_vol[asset] += qty

        trade_log_round.append([market["round"], team, asset, action, qty, price])

    # -------------------------------
    # 2. BOT TRADES
    # -------------------------------
    for bname, bot in market["bots"].items():
        for asset in ["ABC", "XYZ"]:

            price = market["assets"][asset]["price"]
            hist = market["assets"][asset]["history"]

            action = None
            qty = 0

            # 😈 Reckless hedge fund (two-sided, destabilizing)
            if "Reckless" in bname:
                base_qty = 300

                if len(hist) > 0:
                    if price > hist[-1]:
                        action = "BUY"
                        qty = base_qty
                    else:
                        action = "SELL"
                        qty = base_qty * 2
                else:
                    action = "BUY"
                    qty = base_qty

            else:
                # Momentum bot
                if "Momentum" in bname and len(hist) > 0:
                    if price > hist[-1]:
                        action = "BUY"
                    else:
                        action = "SELL"
                    qty = 50

                # Mean reversion bot
                if "MeanReversion" in bname:
                    ref = 100 if asset == "ABC" else 200
                    if price > 1.1 * ref:
                        action = "SELL"; qty = 40
                    elif price < 0.9 * ref:
                        action = "BUY"; qty = 40

                # Panic bot
                if "Panic" in bname and len(hist) > 0:
                    if price < 0.95 * hist[-1]:
                        action = "SELL"; qty = 80

                # Random bot
                if "Random" in bname:
                    if np.random.rand() > 0.5:
                        action = "BUY"; qty = 30
                    else:
                        action = "SELL"; qty = 30

            if action is None or qty == 0:
                continue

            if action == "BUY":
                bot["pos"][asset] += qty
                bot["cash"] -= qty * price
                buy_vol[asset] += qty
            else:
                bot["pos"][asset] -= qty
                bot["cash"] += qty * price
                sell_vol[asset] += qty

            trade_log_round.append([market["round"], bname, asset, action, qty, price])

    # -------------------------------
    # 3. PRICE IMPACT
    # -------------------------------
    for asset in ["ABC", "XYZ"]:
        old_price = market["assets"][asset]["price"]
        market["assets"][asset]["history"].append(old_price)

        imbalance = buy_vol[asset] - sell_vol[asset]
        new_price = max(1.0, old_price + imbalance / 40.0)
        market["assets"][asset]["price"] = new_price

    # -------------------------------
    # 4. SAVE LOGS & P&L
    # -------------------------------
    market["trade_log"].extend(trade_log_round)

    for name, h in market["humans"].items():
        market["pnl_history"][name].append(net_worth(h))

    for name, b in market["bots"].items():
        market["pnl_history"][name].append(net_worth(b))

    market["round"] += 1

# =====================================================
# PRICE CHARTS
# =====================================================
st.subheader("📈 Price History")

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
st.subheader("🏆 Leaderboard (Humans vs Bots)")

rows = []
for name, h in market["humans"].items():
    rows.append({"Agent": name, "Type": "Human", "Net Worth": round(net_worth(h), 0)})
for name, b in market["bots"].items():
    rows.append({"Agent": name, "Type": "Bot", "Net Worth": round(net_worth(b), 0)})

df_leader = pd.DataFrame(rows).sort_values("Net Worth", ascending=False)
st.dataframe(df_leader, use_container_width=True)

# =====================================================
# P&L SUMMARY
# =====================================================
st.subheader("📈 P&L Summary")

pnl_rows = []
for name, series in market["pnl_history"].items():
    start = series[0]
    current = series[-1]
    pnl_rows.append({
        "Agent": name,
        "Net Worth": round(current, 0),
        "P&L": round(current - start, 0),
        "Return %": round(100 * (current - start) / start, 2)
    })

st.dataframe(pd.DataFrame(pnl_rows), use_container_width=True)

# =====================================================
# TRADE LOG
# =====================================================
st.subheader("🧾 Trade Log (Last 50 Trades)")

if len(market["trade_log"]) > 0:
    log_df = pd.DataFrame(
        market["trade_log"],
        columns=["Round", "Agent", "Asset", "Action", "Qty", "Price"]
    )
    st.dataframe(log_df.tail(50), use_container_width=True)
else:
    st.write("No trades yet.")

# =====================================================
# NOTE
# =====================================================
st.info("""
😈 The Reckless Hedge Fund:
• Buys aggressively in rising markets (FOMO)
• Sells violently in falling markets (panic)
• Amplifies both bubbles and crashes
• Sometimes wins big, sometimes self-destructs

This creates realistic instability and reflexivity.
""")
