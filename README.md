# Forex Project

This repository contains all documents, datasets and code files used and developed during the Forex AI research.

First install Metatrader 5: https://www.metatrader5.com/en/download

Drag and drop all files contained in directory MQL5_2020_06_15/Include into the same directory in MT5. 

The main file is located inside MQL5_2020_06_15/Experts/Advisors/EA_istoch_BB_v08. Drag and drop the file EA_istoch_BB_v08.ex5 located into /Experts/Advisors/ in the same directory of MT5. The extension ex5 is the executable version of the source code contained in the file with extension mq5.  You can open the source code using the Metatrader Editor, otherwise we can directly use the executable and experiment that in MT5. 

Link to the paper: https://ieeexplore.ieee.org/document/9612217

To cite our work

@ARTICLE{9612217,
  author={Fisichella, Marco and Garolla, Filippo},
  journal={IEEE Access}, 
  title={Can Deep Learning improve technical analysis of Forex data to predict future price movements?}, 
  year={2021},
  volume={},
  number={},
  pages={1-1},
  doi={10.1109/ACCESS.2021.3127570}}

## Gold strategy (XAUUSD)

`MQL5_2020_06_15/Experts/Advisors/EA_Gold_TrendBreakout.mq5` is a self-contained gold EA: a 200-bar Donchian
breakout on H1 with an ATR stop, an ATR trailing stop, and volatility-regime position sizing mined from 10 years of gold data. It only needs the standard `Trade\Trade.mqh`.
Backtested 2012–2022 with tuning/unseen-data checks: see [Backtest/RESULTS.md](Backtest/RESULTS.md) and
[docs/GOLD_STRATEGY.md](docs/GOLD_STRATEGY.md).
