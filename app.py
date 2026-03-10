from flask import Flask, render_template, request, jsonify
import yfinance as yf

app = Flask(__name__)


def get_verdict(score):
    if score >= 6:
        return "BUY", "#22c55e"
    elif score >= 3:
        return "HOLD", "#f59e0b"
    else:
        return "SELL", "#ef4444"


def fmt(val, prefix="", suffix="", decimals=2):
    if val is None:
        return "N/A"
    try:
        return f"{prefix}{val:,.{decimals}f}{suffix}"
    except:
        return "N/A"


def fmt_big(val):
    if val is None:
        return "N/A"
    try:
        if abs(val) >= 1e12:
            return f"${val/1e12:.2f}T"
        elif abs(val) >= 1e9:
            return f"${val/1e9:.2f}B"
        elif abs(val) >= 1e6:
            return f"${val/1e6:.2f}M"
        else:
            return f"${val:,.0f}"
    except:
        return "N/A"


def analyze(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info

    # Basic info
    name = info.get("longName") or info.get("shortName", ticker_symbol)
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    description = info.get("longBusinessSummary", "No description available.")
    if len(description) > 400:
        description = description[:400] + "..."

    # Price info
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    week_high = info.get("fiftyTwoWeekHigh")
    week_low = info.get("fiftyTwoWeekLow")
    market_cap = info.get("marketCap")

    # Valuation
    pe_ratio = info.get("trailingPE")
    forward_pe = info.get("forwardPE")
    pb_ratio = info.get("priceToBook")
    div_yield = info.get("dividendYield")

    # Income statement
    revenue = info.get("totalRevenue")
    revenue_growth = info.get("revenueGrowth")
    profit_margin = info.get("profitMargins")
    ebitda_margins = info.get("ebitdaMargins")
    eps = info.get("trailingEps")

    # Balance sheet
    debt_to_equity = info.get("debtToEquity")
    current_ratio = info.get("currentRatio")
    return_on_equity = info.get("returnOnEquity")

    # Cash flow
    free_cashflow = info.get("freeCashflow")
    operating_cashflow = info.get("operatingCashflow")

    # Macro / market
    beta = info.get("beta")
    short_ratio = info.get("shortRatio")
    analyst_target = info.get("targetMeanPrice")
    rec = info.get("recommendationKey", "").upper()

    # --- Scoring (0–10 points, higher = more bullish) ---
    score = 5  # start neutral
    reasons_bull = []
    reasons_bear = []

    # PE ratio
    if pe_ratio:
        if pe_ratio < 15:
            score += 1
            reasons_bull.append(f"P/E of {pe_ratio:.1f} is low — stock may be undervalued relative to earnings.")
        elif pe_ratio > 35:
            score -= 1
            reasons_bear.append(f"P/E of {pe_ratio:.1f} is high — investors are paying a premium, leaving less margin for error.")

    # Revenue growth
    if revenue_growth:
        if revenue_growth > 0.10:
            score += 1
            reasons_bull.append(f"Revenue growing at {revenue_growth*100:.1f}% — strong top-line momentum.")
        elif revenue_growth < 0:
            score -= 1
            reasons_bear.append(f"Revenue declining at {revenue_growth*100:.1f}% — business is shrinking.")

    # Profit margin
    if profit_margin:
        if profit_margin > 0.15:
            score += 1
            reasons_bull.append(f"Profit margin of {profit_margin*100:.1f}% — company keeps good earnings from each dollar of revenue.")
        elif profit_margin < 0:
            score -= 1
            reasons_bear.append(f"Negative profit margin ({profit_margin*100:.1f}%) — company is losing money.")

    # Debt to equity
    if debt_to_equity:
        if debt_to_equity < 50:
            score += 1
            reasons_bull.append(f"Low debt-to-equity ({debt_to_equity:.0f}) — financially healthy balance sheet.")
        elif debt_to_equity > 150:
            score -= 1
            reasons_bear.append(f"High debt-to-equity ({debt_to_equity:.0f}) — company carries significant debt.")

    # Free cash flow
    if free_cashflow:
        if free_cashflow > 0:
            score += 1
            reasons_bull.append(f"Positive free cash flow ({fmt_big(free_cashflow)}) — company generates real cash.")
        else:
            score -= 1
            reasons_bear.append(f"Negative free cash flow — company is burning more cash than it brings in.")

    # Price vs analyst target
    if analyst_target and price:
        upside = (analyst_target - price) / price
        if upside > 0.10:
            score += 1
            reasons_bull.append(f"Analyst consensus target of ${analyst_target:.2f} implies {upside*100:.0f}% upside from current price.")
        elif upside < -0.05:
            score -= 1
            reasons_bear.append(f"Analyst consensus target of ${analyst_target:.2f} is below current price — analysts see limited upside.")

    # Beta
    if beta:
        if beta > 1.5:
            reasons_bear.append(f"High beta ({beta:.2f}) — this stock moves more than the market, increasing risk.")
        elif beta < 0.8:
            reasons_bull.append(f"Low beta ({beta:.2f}) — relatively stable compared to the broader market.")

    score = max(0, min(10, score))
    verdict, verdict_color = get_verdict(score)

    # Price position in 52-week range
    price_position = None
    if week_high and week_low and price:
        price_position = (price - week_low) / (week_high - week_low) * 100

    return {
        "name": name,
        "ticker": ticker_symbol.upper(),
        "sector": sector,
        "industry": industry,
        "description": description,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "score": score,
        "reasons_bull": reasons_bull,
        "reasons_bear": reasons_bear,
        "price": fmt(price, "$"),
        "week_high": fmt(week_high, "$"),
        "week_low": fmt(week_low, "$"),
        "price_position": round(price_position) if price_position is not None else None,
        "market_cap": fmt_big(market_cap),
        "pe_ratio": fmt(pe_ratio, decimals=1),
        "forward_pe": fmt(forward_pe, decimals=1),
        "pb_ratio": fmt(pb_ratio, decimals=2),
        "div_yield": fmt(div_yield * 100, suffix="%", decimals=2) if div_yield else "None",
        "revenue": fmt_big(revenue),
        "revenue_growth": fmt((revenue_growth or 0) * 100, suffix="%", decimals=1) if revenue_growth is not None else "N/A",
        "profit_margin": fmt((profit_margin or 0) * 100, suffix="%", decimals=1) if profit_margin is not None else "N/A",
        "ebitda_margin": fmt((ebitda_margins or 0) * 100, suffix="%", decimals=1) if ebitda_margins is not None else "N/A",
        "eps": fmt(eps, "$"),
        "debt_to_equity": fmt(debt_to_equity, decimals=1) if debt_to_equity else "N/A",
        "current_ratio": fmt(current_ratio, decimals=2),
        "return_on_equity": fmt((return_on_equity or 0) * 100, suffix="%", decimals=1) if return_on_equity is not None else "N/A",
        "free_cashflow": fmt_big(free_cashflow),
        "operating_cashflow": fmt_big(operating_cashflow),
        "beta": fmt(beta, decimals=2),
        "short_ratio": fmt(short_ratio, decimals=1),
        "analyst_target": fmt(analyst_target, "$"),
        "analyst_rec": rec if rec else "N/A",
    }


@app.route("/")
def index():
    return render_template("index.html")


def resolve_ticker(query):
    """Try to resolve a company name or ticker to a valid ticker symbol."""
    # 1. Try yf.Search (may fail on some hosting environments)
    try:
        search = yf.Search(query, max_results=5)
        results = search.quotes
        if results:
            return results[0]["symbol"]
    except Exception:
        pass

    # 2. Try the query directly as a ticker
    candidate = query.upper().strip()
    try:
        info = yf.Ticker(candidate).info
        if info.get("regularMarketPrice") or info.get("currentPrice") or info.get("longName"):
            return candidate
    except Exception:
        pass

    return None


@app.route("/analyze")
def analyze_route():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Please enter a company name or ticker."})
    try:
        ticker_symbol = resolve_ticker(query)
        if not ticker_symbol:
            return jsonify({"error": f"Could not find '{query}'. Try using the ticker symbol (e.g. AAPL, TSLA)."})
        data = analyze(ticker_symbol)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Could not find data for '{query}'. Try using the ticker symbol (e.g. AAPL, TSLA)."})


if __name__ == "__main__":
    app.run(debug=True, port=5050)
