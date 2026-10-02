"""Build results/equity_300.png and print yearly table from results/risk*/ outputs."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
SERIES = [("v2_risk3", "v2 flat 3%", "#2a78d6"), ("v3_risk2", "v3 data-mined 2%", "#eb6834"), ("v3_risk3", "v3 data-mined 3%", "#1baf7a")]

fig, ax = plt.subplots(figsize=(10, 5.2), dpi=150, facecolor=SURF)
ax.set_facecolor(SURF)
for d, label, col in SERIES:
    eq = pd.read_csv(f"results/{d}/equity.csv", index_col=0, parse_dates=True).iloc[:, 0]
    ax.plot(eq.index, eq.values, color=col, lw=2, label=label)
    ax.annotate(f"{label}  ${eq.iloc[-1]:,.0f}", (eq.index[-1], eq.iloc[-1]), xytext=(6, 0),
                textcoords="offset points", va="center", color=INK, fontsize=9)
ax.axhline(5000, color=INK2, lw=1, ls=(0, (4, 3)))
ax.text(pd.Timestamp("2012-07-01"), 5600, "$5,000 target", color=INK2, fontsize=9)
ax.axvline(pd.Timestamp("2019-01-01"), color=INK2, lw=1, ls=(0, (1, 3)))
ax.text(pd.Timestamp("2019-02-01"), 150, "unseen data (2019+)", color=INK2, fontsize=9)
ax.set_yscale("log")
ax.set_yticks([100, 300, 1000, 3000, 10000, 30000])
ax.set_yticklabels(["$100", "$300", "$1k", "$3k", "$10k", "$30k"])
ax.set_title("Gold Trend Breakout EA v2 vs v3: $300 start, XAUUSD 2012-2022 (log scale)", color=INK, loc="left", fontsize=12)
ax.tick_params(colors=INK2, labelsize=9)
for s in ax.spines.values():
    s.set_visible(False)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="upper left", labelcolor=INK, fontsize=9)
ax.set_xlim(right=pd.Timestamp("2024-06-01"))
fig.tight_layout()
fig.savefig("results/equity_300.png", facecolor=SURF)

rows = []
for d, label, _ in SERIES:
    eq = pd.read_csv(f"results/{d}/equity.csv", index_col=0, parse_dates=True).iloc[:, 0]
    y = eq.resample("YE").last()
    prev = pd.concat([pd.Series([300.0]), y.iloc[:-1]]).values
    rows.append(((y.values / prev - 1) * 100).round(0))
tbl = pd.DataFrame(rows, index=[s[1] for s in SERIES], columns=y.index.year)
print(tbl.to_markdown())
for d, label, _ in SERIES:
    eq = pd.read_csv(f"results/{d}/equity.csv", index_col=0, parse_dates=True).iloc[:, 0]
    o = eq[eq.index >= "2019-01-01"]
    print(label, "OOS 2019-2022:", f"x{o.iloc[-1]/o.iloc[0]:.2f}", f"maxDD {((o/o.cummax())-1).min()*100:.1f}%")
