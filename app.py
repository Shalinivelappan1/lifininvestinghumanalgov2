import streamlit as st
import pandas as pd

st.set_page_config(page_title="Classroom Trading Lab (Clean Core)", layout="wide")

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
st.title("📈 Classroom Trading Lab — Clean Core (Phase 1 + 2)")
st.caption("📰 News moves prices immediately. ▶️ Run Round applies only human trades.")

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
        qty = st.number_input("Qty", min_value=0, max_value=1000, value=0, step=10, key=f"{name}_qty")

        human_orders[name] = {
            "asset": asset,
            "action": action,
            "qty": qty
        }

# =====================================================
# RUN ROUND (APPLY HUMAN TRADES ONLY)
# =====================================================
if st.button("▶️ Run Next Round"):

    trade_log_round = []

    buy_vol = {"ABC": 0, "XYZ": 0}
    sell_vol = {"ABC": 0, "XYZ": 0}

    # -------------------------------
    # Apply human trades
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

        trade_log_round.append([
            market["round"], team, asset, action, qty, price
        ])

    # -------------------------------
    # Price impact (simple rule)
    # -------------------------------
    for asset in ["ABC", "XYZ"]:
        old_price = market["assets"][asset]["price"]
        market["assets"][asset]["history"].append(old_price)

        imbalance = buy_vol[asset] - sell_vol[asset]

        # Simple linear impact
        new_price = max(1.0, old_price + imbalance / 50.0)
        market["assets"][asset]["price"] = new_price

    # -------------------------------
    # Save logs
    # -------------------------------
    market["trade_log"].extend(trade_log_round)

    # Save P&L history
    for team, human in market["humans"].items():
        market["pnl_history"][team].append(net_worth(human))

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
st.subheader("🏆 Leaderboard (Net Worth)")

rows = []
for name, h in market["humans"].items():
    rows.append({
        "Team": name,
        "Net Worth": round(net_worth(h), 0),
        "ABC Pos": h["pos"]["ABC"],
        "XYZ Pos": h["pos"]["XYZ"]
    })

df_leader = pd.DataFrame(rows).sort_values("Net Worth", ascending=False)
st.dataframe(df_leader, use_container_width=True)

# =====================================================
# P&L SUMMARY
# =====================================================
st.subheader("📈 Team P&L Summary")

pnl_rows = []
for team, series in market["pnl_history"].items():
    start = series[0]
    current = series[-1]
    pnl_rows.append({
        "Team": team,
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
        columns=["Round", "Team", "Asset", "Action", "Qty", "Price"]
    )
    st.dataframe(log_df.tail(50), use_container_width=True)
else:
    st.write("No trades yet.")

# =====================================================
# NOTE
# =====================================================
st.info("""
This is the clean core version:

• News moves prices immediately
• ▶️ Run Round applies only human trades
• Simple price impact from order imbalance
• Trade log + P&L history + leaderboard
• No bots, no risk rules, no circuit breakers

Stable, predictable, perfect for classroom use.
""")
