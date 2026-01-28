import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Human vs Algo Market Lab", layout="wide")

# =====================================================
# INITIALIZE STATE (RUNS ONLY ONCE)
# =====================================================
if "market" not in st.session_state:

    market = {
        "round": 1,
        "liquidity_freeze": False,

        "assets": {
            "ABC": {"price": 100.0, "history": [], "halted": False, "cb_ref": 100.0},
            "XYZ": {"price": 200.0, "history": [], "halted": False, "cb_ref": 200.0},
        },

        # Risk & regulation
        "position_limit": 500,      # shares
        "risk_budget_pct": 0.25,     # 25% of net worth
        "short_selling_ban": False,
        "circuit_breaker_pct": 0.10,

        "humans": {},
        "bots": {},

        "trade_log": [],
        "pnl_history": {}
    }

    # 10 humans
    for i in range(1, 11):
        name = f"Human_{i}"
        market["humans"][name] = {
            "cash": 100000.0,
            "pos": {"ABC": 50, "XYZ": 25}
        }
        market["pnl_history"][name] = [100000.0]

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
st.title("🤖📈 Human vs Algorithm Market Lab — Regulation & Risk")
st.caption("📰 News moves prices immediately. ▶️ Trading reacts when you run the round.")

# =====================================================
# SIDEBAR — POLICY, SHOCKS, REGULATION
# =====================================================
st.sidebar.header("🏛️ Policy & Shock Controls")

selected_asset = st.sidebar.selectbox(
    "Select Asset for News",
    ["ABC", "XYZ"],
    key="selected_asset_for_news"
)

# -------------------------------
# NEWS SHOCKS (IMMEDIATE)
# -------------------------------
if st.sidebar.button("🚨 Bad News (-10%)"):
    a = market["assets"][selected_asset]
    a["history"].append(a["price"])
    a["price"] *= 0.90
    a["cb_ref"] = a["price"]
    a["halted"] = False

if st.sidebar.button("✅ Good News (+10%)"):
    a = market["assets"][selected_asset]
    a["history"].append(a["price"])
    a["price"] *= 1.10
    a["cb_ref"] = a["price"]
    a["halted"] = False

if st.sidebar.button("💣 Flash Crash (-25%)"):
    a = market["assets"][selected_asset]
    a["history"].append(a["price"])
    a["price"] *= 0.75
    a["cb_ref"] = a["price"]
    a["halted"] = False

st.sidebar.divider()

# Liquidity freeze
if st.sidebar.button("🧊 Toggle Liquidity Freeze"):
    market["liquidity_freeze"] = not market["liquidity_freeze"]

# Central bank (immediate)
if st.sidebar.button("🏦 Central Bank Intervention (+15% ALL)"):
    for a in market["assets"]:
        asset = market["assets"][a]
        asset["history"].append(asset["price"])
        asset["price"] *= 1.15
        asset["halted"] = False
        asset["cb_ref"] = asset["price"]

# Resume trading
if st.sidebar.button("🟢 Resume All Trading"):
    for a in market["assets"]:
        market["assets"][a]["halted"] = False
        market["assets"][a]["cb_ref"] = market["assets"][a]["price"]

st.sidebar.divider()

# -------------------------------
# REGULATIONS & RISK CONTROLS
# -------------------------------
st.sidebar.header("🧠 Regulations & Risk")

market["short_selling_ban"] = st.sidebar.checkbox(
    "🚫 Ban Short Selling",
    value=market["short_selling_ban"]
)

market["position_limit"] = st.sidebar.slider(
    "Position Limit (shares per asset)",
    min_value=100, max_value=2000, value=market["position_limit"], step=100
)

market["risk_budget_pct"] = st.sidebar.slider(
    "Risk Budget (% of Net Worth)",
    min_value=0.05, max_value=0.80, value=market["risk_budget_pct"], step=0.05
)

market["circuit_breaker_pct"] = st.sidebar.slider(
    "🚨 Circuit Breaker Threshold (%)",
    min_value=0.05, max_value=0.50, value=market["circuit_breaker_pct"], step=0.05
)

st.sidebar.divider()

# Reset
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
# RUN ROUND (TRADING)
# =====================================================
if st.button("▶️ Run Next Market Round"):

    trade_log_round = []

    buy_vol = {"ABC": 0, "XYZ": 0}
    sell_vol = {"ABC": 0, "XYZ": 0}

    # -------------------------------
    # HUMAN ORDERS
    # -------------------------------
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

            # Short selling ban
            if market["short_selling_ban"] and action == "SELL":
                if human["pos"][asset] - qty < 0:
                    trade_log_round.append([market["round"], hname, asset, action, qty, price, "BLOCKED", "SHORT BAN"])
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

    # -------------------------------
    # BOTS
    # -------------------------------
    for bname, bot in market["bots"].items():
        for asset in ["ABC", "XYZ"]:
            if market["assets"][asset]["halted"] or market["liquidity_freeze"]:
                continue

            price = market["assets"][asset]["price"]
            hist = market["assets"][asset]["history"]

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

    # -------------------------------
    # PRICE FORMATION + CIRCUIT BREAKER
    # -------------------------------
    for asset in ["ABC", "XYZ"]:
        old_price = market["assets"][asset]["price"]
        market["assets"][asset]["history"].append(old_price)

        if market["assets"][asset]["halted"]:
            continue

        imbalance = buy_vol[asset] - sell_vol[asset]
        new_price = max(1.0, old_price + imbalance / 50.0)

        ref = market["assets"][asset]["cb_ref"]
        if abs(new_price - ref) / ref > market["circuit_breaker_pct"]:
            market["assets"][asset]["halted"] = True
        else:
            market["assets"][asset]["price"] = new_price
            market["assets"][asset]["cb_ref"] = new_price

    # -------------------------------
    # SAVE TRADE LOG
    # -------------------------------
    market["trade_log"].extend(trade_log_round)

    # Save P&L history
    for hname, h in market["humans"].items():
        market["pnl_history"][hname].append(net_worth(h))

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
# P&L SUMMARY
# =====================================================
st.subheader("📈 Team P&L Summary")

pnl_rows = []
for hname, series in market["pnl_history"].items():
    start = series[0]
    current = series[-1]
    pnl_rows.append({
        "Team": hname,
        "Net Worth": round(current, 0),
        "P&L": round(current - start, 0),
        "Return %": round(100 * (current - start) / start, 2)
    })

st.dataframe(pd.DataFrame(pnl_rows), use_container_width=True)

# =====================================================
# TRADE LOG + EXPORT
# =====================================================
st.subheader("🧾 Trade History (Last 50)")

if len(market["trade_log"]) > 0:
    log_df = pd.DataFrame(
        market["trade_log"],
        columns=["Round", "Agent", "Asset", "Action", "Qty", "Price", "Status", "Reason"]
    )
    st.dataframe(log_df.tail(50), use_container_width=True)

    # Export to Excel
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        log_df.to_excel(writer, index=False, sheet_name="TradeLog")
    buffer.seek(0)

    st.download_button(
        "⬇️ Download Trade Log (Excel)",
        data=buffer,
        file_name="trade_log.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.write("No trades yet.")

# =====================================================
# TEACHING NOTE
# =====================================================
st.info("""
This simulator now includes:
• Immediate news shocks (good/bad/crash/CB)
• Liquidity freeze
• Circuit breakers (configurable)
• Short-selling ban
• Position limits
• Risk budgets
• Full trade log + Excel export
• Per-team P&L tracking

This is a complete Market Microstructure + Regulation + Risk Lab.
""")
