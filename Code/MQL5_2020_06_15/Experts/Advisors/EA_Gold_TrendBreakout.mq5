//+------------------------------------------------------------------+
//|                                         EA_Gold_TrendBreakout.mq5 |
//|                   XAUUSD Donchian trend breakout with ATR trailing |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "AI_forex_fisichella_garolla"
#property version   "2.00"
#property description "Gold (XAUUSD) trend breakout: enter on a fresh close beyond the"
#property description "N-bar Donchian channel, ATR stop, ATR trailing stop, % risk sizing."
#property description "Backtested 2012-2022 (see Backtest/RESULTS.md). High risk."

/*
 STRATEGY (validated in Backtest/gold_backtest.py, see docs/GOLD_STRATEGY.md)

 Signal timeframe H1 (default):
   BUY  when the last closed bar closes above the highest high of the previous
        DonchianPeriod bars, and the bar before it did not (fresh breakout).
   SELL mirror image on the lowest low.
 Stop loss     : SL_ATR x ATR(14) from entry.
 Trailing stop : Trail_ATR x ATR(14) behind price, only ever tightens.
 Take profit   : none by default (let the trend run), optional TP_R.
 One position at a time; signals while in a trade are ignored.

 Trading involves substantial risk. Past results do not guarantee future results.
*/

#include <Trade\Trade.mqh>
CTrade Trade;

//+------------------------------------------------------------------+
//| Input variables                                                  |
//+------------------------------------------------------------------+
sinput string GEN;                          // GENERAL
input ulong  MagicNumber       = 777002;    // Magic Number
input ENUM_TIMEFRAMES SignalTF = PERIOD_H1; // Signal timeframe
input ulong  Slippage          = 50;        // Max deviation (points)

sinput string STRAT;                        // STRATEGY
input int    DonchianPeriod    = 200;       // Donchian channel length (bars)
input int    TrendEMA          = 0;         // Optional EMA trend filter (0 = off)
input int    ATRPeriod         = 14;        // ATR period
input double SL_ATR            = 2.0;       // Initial stop (x ATR)
input double Trail_ATR         = 4.0;       // Trailing stop (x ATR), 0 = off
input double TP_R              = 0.0;       // Take profit (x initial risk), 0 = none

sinput string RISK;                         // RISK MANAGEMENT
input double RiskPercent       = 3.0;       // Risk per trade (% of equity)
input double MaxRiskAtMinLot   = 6.0;       // Allow min lot if its risk <= this % (small accounts)
input double MaxSpreadPrice    = 0.80;      // Max spread to open a trade (USD)
input double MaxDrawdownPct    = 0.0;       // Equity drawdown kill switch (% from peak), 0 = off
input bool   CloseOnFriday     = false;     // Close positions on Friday evening
input int    FridayCloseHour   = 21;        // Friday close hour (server time)

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
int      hATR = INVALID_HANDLE, hEMA = INVALID_HANDLE;
datetime lastBarTime = 0;
double   peakEquity  = 0;
bool     killSwitch  = false;

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   if(DonchianPeriod < 2 || SL_ATR <= 0 || RiskPercent <= 0)
   {
      Print("Invalid input parameters");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(RiskPercent > 5.0)
      Print("WARNING: RiskPercent ", RiskPercent, "% - backtests show >90% chance of a 50%+ drawdown");

   hATR = iATR(_Symbol, SignalTF, ATRPeriod);
   if(TrendEMA > 0) hEMA = iMA(_Symbol, SignalTF, TrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(hATR == INVALID_HANDLE || (TrendEMA > 0 && hEMA == INVALID_HANDLE))
   {
      Print("Failed to create indicator handles");
      return(INIT_FAILED);
   }

   Trade.SetExpertMagicNumber(MagicNumber);
   Trade.SetDeviationInPoints(Slippage);
   Trade.SetTypeFillingBySymbol(_Symbol);

   peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(hATR);
   if(hEMA != INVALID_HANDLE) IndicatorRelease(hEMA);
}

//+------------------------------------------------------------------+
//| Expert tick                                                      |
//+------------------------------------------------------------------+
void OnTick()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > peakEquity) peakEquity = equity;
   if(!killSwitch && MaxDrawdownPct > 0 && equity <= peakEquity * (1.0 - MaxDrawdownPct / 100.0))
   {
      killSwitch = true;
      CloseAll("max drawdown kill switch");
      Print("KILL SWITCH: equity drawdown exceeded ", MaxDrawdownPct, "%. EA stopped trading.");
   }

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   bool fridayFlat = CloseOnFriday && dt.day_of_week == 5 && dt.hour >= FridayCloseHour;
   if(fridayFlat) CloseAll("Friday close");

   double atr = GetValue(hATR, 1);
   if(atr <= 0) return;

   // Trailing stop every tick
   TrailPositions(atr);

   // Entries only on a new signal bar
   datetime barTime = iTime(_Symbol, SignalTF, 0);
   if(barTime == lastBarTime) return;
   lastBarTime = barTime;

   if(killSwitch || fridayFlat) return;
   if(CountPositions() > 0) return;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask - bid > MaxSpreadPrice) return;

   int signal = BreakoutSignal();
   if(signal != 0) OpenTrade(signal, atr);
}

//+------------------------------------------------------------------+
//| Read one indicator value                                         |
//+------------------------------------------------------------------+
double GetValue(int handle, int shift)
{
   double buf[];
   if(CopyBuffer(handle, 0, shift, 1, buf) != 1) return(0.0);
   return(buf[0]);
}

//+------------------------------------------------------------------+
//| +1 / -1 on a fresh Donchian breakout of closed bar 1, else 0     |
//+------------------------------------------------------------------+
int BreakoutSignal()
{
   if(Bars(_Symbol, SignalTF) < DonchianPeriod + 5) return(0);

   // Channel for bar 1 = bars 2..N+1, channel for bar 2 = bars 3..N+2
   int iHi1 = iHighest(_Symbol, SignalTF, MODE_HIGH, DonchianPeriod, 2);
   int iLo1 = iLowest(_Symbol, SignalTF, MODE_LOW, DonchianPeriod, 2);
   int iHi2 = iHighest(_Symbol, SignalTF, MODE_HIGH, DonchianPeriod, 3);
   int iLo2 = iLowest(_Symbol, SignalTF, MODE_LOW, DonchianPeriod, 3);
   if(iHi1 < 0 || iLo1 < 0 || iHi2 < 0 || iLo2 < 0) return(0);

   double hh1 = iHigh(_Symbol, SignalTF, iHi1);
   double ll1 = iLow(_Symbol, SignalTF, iLo1);
   double hh2 = iHigh(_Symbol, SignalTF, iHi2);
   double ll2 = iLow(_Symbol, SignalTF, iLo2);
   double c1  = iClose(_Symbol, SignalTF, 1);
   double c2  = iClose(_Symbol, SignalTF, 2);

   int signal = 0;
   if(c1 > hh1 && !(c2 > hh2)) signal = 1;
   if(c1 < ll1 && !(c2 < ll2)) signal = -1;

   if(signal != 0 && TrendEMA > 0)
   {
      double ema = GetValue(hEMA, 1);
      if(ema <= 0 || (signal > 0 && c1 <= ema) || (signal < 0 && c1 >= ema)) return(0);
   }
   return(signal);
}

//+------------------------------------------------------------------+
//| Position size from risk % and stop distance                      |
//+------------------------------------------------------------------+
double CalcLots(double slDistance, ENUM_ORDER_TYPE type, double price)
{
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double minLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double stepLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(tickSize <= 0 || tickValue <= 0 || stepLot <= 0) return(0);

   double equity     = AccountInfoDouble(ACCOUNT_EQUITY);
   double lossPerLot = slDistance / tickSize * tickValue;
   if(lossPerLot <= 0) return(0);

   double lots = MathFloor(equity * RiskPercent / 100.0 / lossPerLot / stepLot) * stepLot;
   lots = MathMin(lots, maxLot);

   double margin = 0;
   while(lots >= minLot && OrderCalcMargin(type, _Symbol, lots, price, margin) &&
         margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.9)
      lots -= stepLot;

   // Small accounts: min lot may exceed RiskPercent; allow it only up to a hard cap
   if(lots < minLot && MaxRiskAtMinLot > 0 && minLot * lossPerLot <= equity * MaxRiskAtMinLot / 100.0 &&
      OrderCalcMargin(type, _Symbol, minLot, price, margin) && margin <= AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.9)
      lots = minLot;
   if(lots < minLot) return(0);

   int volDigits = (int)MathMax(0, MathCeil(-MathLog10(stepLot)));
   return(NormalizeDouble(lots, volDigits));
}

//+------------------------------------------------------------------+
//| Open a market order                                              |
//+------------------------------------------------------------------+
bool OpenTrade(int direction, double atr)
{
   int    digits  = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point   = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minStop = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   double slDist  = MathMax(SL_ATR * atr, minStop + 10 * point);

   ENUM_ORDER_TYPE type = (direction > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double price = (direction > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                  : SymbolInfoDouble(_Symbol, SYMBOL_BID);

   double lots = CalcLots(slDist, type, price);
   if(lots <= 0)
   {
      Print("Lot size below minimum for the configured risk; trade skipped. ",
            "Use a cent account or raise MaxRiskAtMinLot.");
      return(false);
   }

   double sl = NormalizeDouble(price - direction * slDist, digits);
   double tp = (TP_R > 0) ? NormalizeDouble(price + direction * slDist * TP_R, digits) : 0.0;

   bool ok = (direction > 0) ? Trade.Buy(lots, _Symbol, price, sl, tp, "GTB")
                             : Trade.Sell(lots, _Symbol, price, sl, tp, "GTB");
   if(!ok || (Trade.ResultRetcode() != TRADE_RETCODE_DONE && Trade.ResultRetcode() != TRADE_RETCODE_PLACED))
   {
      Print("Order failed: ", Trade.ResultRetcode(), " ", Trade.ResultRetcodeDescription());
      return(false);
   }
   PrintFormat("GTB %s %.2f lots @ %.2f SL %.2f TP %.2f", direction > 0 ? "BUY" : "SELL", lots, price, sl, tp);
   return(true);
}

//+------------------------------------------------------------------+
//| ATR trailing stop                                                |
//+------------------------------------------------------------------+
void TrailPositions(double atr)
{
   if(Trail_ATR <= 0) return;

   int    digits  = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point   = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minStop = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;

      int    dir   = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      double sl    = PositionGetDouble(POSITION_SL);
      double tp    = PositionGetDouble(POSITION_TP);
      double price = (dir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                               : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      double newSL  = NormalizeDouble(price - dir * Trail_ATR * atr, digits);
      bool   better = (sl == 0) || ((dir > 0) ? (newSL > sl + point) : (newSL < sl - point));
      if(better && MathAbs(price - newSL) > minStop)
         Trade.PositionModify(ticket, newSL, tp);
   }
}

//+------------------------------------------------------------------+
//| Count this EA's open positions                                   |
//+------------------------------------------------------------------+
int CountPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == MagicNumber)
         count++;
   }
   return(count);
}

//+------------------------------------------------------------------+
//| Close all of this EA's positions                                 |
//+------------------------------------------------------------------+
void CloseAll(string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      if(Trade.PositionClose(ticket))
         Print("Closed #", ticket, " (", reason, ")");
   }
}
//+------------------------------------------------------------------+
