# Gold (XAUUSD) Trend Breakout Strategy (v4)

* EA: `Code/MQL5_2020_06_15/Experts/Advisors/EA_Gold_TrendBreakout.mq5`
* Presets: `Code/MQL5_2020_06_15/Presets/GTB_*.set`
* Backtest + full results: [`Backtest/RESULTS.md`](../Backtest/RESULTS.md)

> **Risk warning:** No strategy guarantees profit. Every trade has a stop loss. Without one,
> a single gold move of $30–$100 can wipe a small account. Test on demo first.

## Rules (chart: XAUUSD H1)
| | |
|---|---|
| **Buy** | The last closed H1 candle closes **above the highest high of the previous 200 candles**, and the candle before did not (fresh breakout). |
| **Sell** | The last closed H1 candle closes **below the lowest low of the previous 200 candles** (fresh breakout). |
| **Stop loss** | 1.5 × ATR(14) from entry. Always set. (Tighter than v3: ~900 variants tested, 1.25–1.5 ATR is the best region and 1.5 is the one that survives wider spreads.) |
| **Trailing stop** | 5 × ATR(14) behind price; it only moves in your favour. |
| **Take profit** | None: let trends run. Trades of +10R to +19R pay for the many small losses. |
| **Positions** | One at a time. Signals during an open trade are ignored. |
| **Size (data-mined)** | Risk % of equity per trade, from the stop distance. **Doubled** when weekly volatility is below 0.8× its 1-year median: these quiet-market breakouts were 2–4× more profitable in the data. |

Expect a **~30% win rate**. Most trades are small losses; a few huge winners make the profit.
Losing streaks of 10–12 trades happened in the backtest. Do not switch the EA off during one.

## $300 → $5,000 plan
1. Open a **cent account** (or start with $1,000+ on a standard account), raw/ECN spread under $0.40.
2. Load `GTB_Balanced_1.5pct.set` (1.5% risk, 3% in quiet markets). Backtest: $300 → $14,368, max drawdown −36%,
   $5k after ~7.5 years. For faster growth, `GTB_Aggressive_2pct.set`: $300 → $32,381 and $5k in ~5.5 years,
   **but expect drawdowns near 50%**.
3. Do not raise risk further. Monte Carlo at 2% already gives a 95th-percentile drawdown of about −60%.
4. After reaching $5,000, switch to `GTB_Conservative_1pct.set` to keep it.
5. **Spread matters more with the tighter stop.** The EA refuses to open above $0.60 spread. On a broker whose
   gold spread is usually above $0.8, use `SL_ATR=2.0 Trail_ATR=4.0` (the v3 settings) instead.

## Installation
1. Copy `EA_Gold_TrendBreakout.mq5` to `MQL5/Experts/` and compile it in MetaEditor (F7).
2. Open an **XAUUSD H1** chart and attach the EA. Enable Algo Trading.
3. Inputs → Load → choose a preset from `Presets/`.
4. Make sure at least **one year of H1 history** (~6,200 bars) is loaded: scroll the H1 chart back until it
   stops loading, and set Tools → Options → Charts → "Max bars in chart" to 100,000 or more. Without it the
   EA prints a warning and trades at base risk only (no volatility sizing).
5. Keep the terminal running 24/5 (VPS recommended). The trailing stop is updated by the EA.
6. Verify in the MT5 Strategy Tester (XAUUSD, H1, "Every tick based on real ticks", your broker's data).
