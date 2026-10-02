//+------------------------------------------------------------------+
//|                                       EA_Gold_SessionMomentum.mq5 |
//|                 XAUUSD trend-filtered session breakout + pullback |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "AI_forex_fisichella_garolla"
#property version   "1.00"
#property description "Gold (XAUUSD) Session Momentum: H1 trend filter, Asian-range breakout"
#property description "and EMA pullback entries, ATR stops, partial take-profit, break-even,"
#property description "ATR trailing, daily-loss and max-drawdown circuit breakers."

/*
 STRATEGY SUMMARY (see docs/GOLD_STRATEGY.md for full details)

 1. Trend filter (H1): EMA(50) vs EMA(200), price on the right side of EMA(200),
    ADX(14) above a threshold. Only trade in the direction of that trend.
 2. Setup A - Asian range breakout: build the high/low of the Asian session,
    then during London/New York hours buy a close above the range high
    (sell a close below the range low) in the trend direction. One per side per day.
 3. Setup B - Trend pullback: price dips into EMA(21) on the entry timeframe
    and closes back in the trend direction with RSI confirmation.
 4. Exits: ATR-based stop, fixed R-multiple target, 50% partial at +1R with
    stop moved to break-even, then ATR trailing stop on the remainder.
 5. Risk: fixed % of equity per trade, max spread filter, max trades per day,
    daily loss limit, equity max-drawdown kill switch, Friday flat.

 Trading involves substantial risk. Backtest and forward-test on a demo
 account before using real money. No result is guaranteed.
*/

#include <Trade\Trade.mqh>
CTrade Trade;

//+------------------------------------------------------------------+
//| Input variables                                                  |
//+------------------------------------------------------------------+
sinput string GEN;                          // GENERAL
input ulong  MagicNumber       = 777001;    // Magic Number
input ENUM_TIMEFRAMES EntryTF  = PERIOD_M15;// Entry timeframe
input ENUM_TIMEFRAMES TrendTF  = PERIOD_H1; // Trend timeframe
input ulong  Slippage          = 30;        // Max deviation (points)
input int    MaxOpenPositions  = 1;         // Max simultaneous positions
input int    MaxTradesPerDay   = 3;         // Max new trades per day

sinput string RISK;                         // RISK MANAGEMENT
input double RiskPercent       = 1.0;       // Risk per trade (% of equity)
input double MaxDailyLossPct   = 3.0;       // Daily loss limit (% of day-start equity)
input double MaxDrawdownPct    = 15.0;      // Equity drawdown kill switch (% from peak)
input double MaxSpreadPrice    = 0.60;      // Max spread in price units (USD)
input double MaxRiskAtMinLot   = 4.0;       // Small accounts: allow min lot if its risk <= this %

sinput string TREND;                        // TREND FILTER
input int    TrendFastEMA      = 50;        // Trend fast EMA
input int    TrendSlowEMA      = 200;       // Trend slow EMA
input int    ADXPeriod         = 14;        // ADX period
input double ADXMin            = 20.0;      // Minimum ADX to trade

sinput string SESS;                         // SESSIONS (broker server hours)
input int    AsianStartHour    = 0;         // Asian range start hour
input int    AsianEndHour      = 7;         // Asian range end hour
input int    TradeStartHour    = 8;         // Trading window start hour
input int    TradeEndHour      = 18;        // Trading window end hour
input bool   CloseOnFriday     = true;      // Close all positions on Friday
input int    FridayCloseHour   = 20;        // Friday close hour

sinput string SETA;                         // SETUP A: ASIAN RANGE BREAKOUT
input bool   UseBreakout       = true;      // Enable breakout setup
input double BreakoutBufferATR = 0.10;      // Close must exceed range by x ATR
input double MinRangeATR       = 1.5;       // Min Asian range size (x ATR)
input double MaxRangeATR       = 10.0;      // Max Asian range size (x ATR)

sinput string SETB;                         // SETUP B: TREND PULLBACK
input bool   UsePullback       = true;      // Enable pullback setup
input int    PullbackEMA       = 21;        // Pullback EMA (entry TF)
input int    RSIPeriod         = 14;        // RSI period
input double RSIBuyMin         = 45.0;      // RSI min for buys
input double RSIBuyMax         = 70.0;      // RSI max for buys
input double RSISellMin        = 30.0;      // RSI min for sells
input double RSISellMax        = 55.0;      // RSI max for sells

sinput string EXIT;                         // EXITS
input int    ATRPeriod         = 14;        // ATR period (entry TF)
input double SL_ATR            = 1.5;       // Stop loss (x ATR)
input double TP_R              = 2.5;       // Take profit (x initial risk), 0 = none
input bool   UsePartialClose   = true;      // Close part at +1R
input double PartialPercent    = 50.0;      // % of volume closed at +1R
input double PartialAtR        = 1.0;       // R multiple for partial + break-even
input double BE_BufferATR      = 0.10;      // Break-even lock (x ATR) beyond entry
input bool   UseTrailing       = true;      // ATR trailing after break-even
input double Trail_ATR         = 2.0;       // Trailing distance (x ATR)

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
int hTrendFast = INVALID_HANDLE, hTrendSlow = INVALID_HANDLE, hADX = INVALID_HANDLE;
int hATR = INVALID_HANDLE, hPullEMA = INVALID_HANDLE, hRSI = INVALID_HANDLE;

datetime lastBarTime    = 0;
datetime currentDay     = 0;
double   dayStartEquity = 0;
double   peakEquity     = 0;
bool     dailyHalt      = false;
bool     killSwitch     = false;
int      tradesToday    = 0;
datetime lastBreakoutBuyDay  = 0;
datetime lastBreakoutSellDay = 0;

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   if(TrendFastEMA >= TrendSlowEMA || RiskPercent <= 0 || SL_ATR <= 0 ||
      AsianEndHour <= AsianStartHour || TradeEndHour <= TradeStartHour)
   {
      Print("Invalid input parameters");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(RiskPercent > 3.0)
      Print("WARNING: RiskPercent ", RiskPercent, "% is very aggressive for gold");

   hTrendFast = iMA(_Symbol, TrendTF, TrendFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   hTrendSlow = iMA(_Symbol, TrendTF, TrendSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   hADX       = iADX(_Symbol, TrendTF, ADXPeriod);
   hATR       = iATR(_Symbol, EntryTF, ATRPeriod);
   hPullEMA   = iMA(_Symbol, EntryTF, PullbackEMA, 0, MODE_EMA, PRICE_CLOSE);
   hRSI       = iRSI(_Symbol, EntryTF, RSIPeriod, PRICE_CLOSE);

   if(hTrendFast == INVALID_HANDLE || hTrendSlow == INVALID_HANDLE || hADX == INVALID_HANDLE ||
      hATR == INVALID_HANDLE || hPullEMA == INVALID_HANDLE || hRSI == INVALID_HANDLE)
   {
      Print("Failed to create indicator handles");
      return(INIT_FAILED);
   }

   Trade.SetExpertMagicNumber(MagicNumber);
   Trade.SetDeviationInPoints(Slippage);
   Trade.SetTypeFillingBySymbol(_Symbol);

   peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   ResetDay();
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(hTrendFast);
   IndicatorRelease(hTrendSlow);
   IndicatorRelease(hADX);
   IndicatorRelease(hATR);
   IndicatorRelease(hPullEMA);
   IndicatorRelease(hRSI);
}

//+------------------------------------------------------------------+
//| Expert tick                                                      |
//+------------------------------------------------------------------+
void OnTick()
{
   // New day bookkeeping
   datetime today = iTime(_Symbol, PERIOD_D1, 0);
   if(today != currentDay) ResetDay();

   // Circuit breakers
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > peakEquity) peakEquity = equity;

   if(!killSwitch && MaxDrawdownPct > 0 && equity <= peakEquity * (1.0 - MaxDrawdownPct / 100.0))
   {
      killSwitch = true;
      CloseAll("max drawdown kill switch");
      Print("KILL SWITCH: equity drawdown exceeded ", MaxDrawdownPct, "%. EA stopped trading.");
   }
   if(!dailyHalt && MaxDailyLossPct > 0 && equity <= dayStartEquity * (1.0 - MaxDailyLossPct / 100.0))
   {
      dailyHalt = true;
      CloseAll("daily loss limit");
      Print("Daily loss limit hit. No more trades today.");
   }

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(CloseOnFriday && dt.day_of_week == 5 && dt.hour >= FridayCloseHour)
   {
      CloseAll("Friday close");
      return;
   }

   // Manage open positions every tick
   ManagePositions();

   // Entries only on a new bar of the entry timeframe
   datetime barTime = iTime(_Symbol, EntryTF, 0);
   if(barTime == lastBarTime) return;
   lastBarTime = barTime;

   if(killSwitch || dailyHalt) return;
   if(tradesToday >= MaxTradesPerDay) return;
   if(CountPositions() >= MaxOpenPositions) return;
   if(dt.hour < TradeStartHour || dt.hour >= TradeEndHour) return;
   if(dt.day_of_week == 5 && CloseOnFriday && dt.hour >= FridayCloseHour - 2) return;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask - bid > MaxSpreadPrice) return;

   int trend = TrendDirection();
   if(trend == 0) return;

   double atr = GetValue(hATR, 0, 1);
   if(atr <= 0) return;

   int signal = 0;
   string tag = "";

   if(UseBreakout)
   {
      signal = BreakoutSignal(trend, atr, today);
      if(signal != 0) tag = "GSM-Breakout";
   }
   if(signal == 0 && UsePullback)
   {
      signal = PullbackSignal(trend);
      if(signal != 0) tag = "GSM-Pullback";
   }
   if(signal == 0) return;

   if(OpenTrade(signal, atr, tag))
   {
      tradesToday++;
      if(tag == "GSM-Breakout")
      {
         if(signal > 0) lastBreakoutBuyDay = today;
         else           lastBreakoutSellDay = today;
      }
   }
}

//+------------------------------------------------------------------+
//| Reset daily counters                                             |
//+------------------------------------------------------------------+
void ResetDay()
{
   currentDay     = iTime(_Symbol, PERIOD_D1, 0);
   dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   dailyHalt      = false;
   tradesToday    = 0;
}

//+------------------------------------------------------------------+
//| Read one indicator value                                         |
//+------------------------------------------------------------------+
double GetValue(int handle, int buffer, int shift)
{
   double buf[];
   if(CopyBuffer(handle, buffer, shift, 1, buf) != 1) return(0.0);
   return(buf[0]);
}

//+------------------------------------------------------------------+
//| +1 uptrend, -1 downtrend, 0 no trade (on last closed trend bar)  |
//+------------------------------------------------------------------+
int TrendDirection()
{
   double fast  = GetValue(hTrendFast, 0, 1);
   double slow  = GetValue(hTrendSlow, 0, 1);
   double adx   = GetValue(hADX, 0, 1);
   double close = iClose(_Symbol, TrendTF, 1);
   if(fast == 0 || slow == 0 || close == 0) return(0);
   if(adx < ADXMin) return(0);

   if(fast > slow && close > slow) return(1);
   if(fast < slow && close < slow) return(-1);
   return(0);
}

//+------------------------------------------------------------------+
//| Setup A: Asian range breakout                                    |
//+------------------------------------------------------------------+
int BreakoutSignal(int trend, double atr, datetime today)
{
   datetime from = today + AsianStartHour * 3600;
   datetime to   = today + AsianEndHour * 3600 - 1;
   if(TimeCurrent() < today + AsianEndHour * 3600) return(0);

   MqlRates rates[];
   int n = CopyRates(_Symbol, EntryTF, from, to, rates);
   if(n < 4) return(0);

   double hi = rates[0].high, lo = rates[0].low;
   for(int i = 1; i < n; i++)
   {
      if(rates[i].high > hi) hi = rates[i].high;
      if(rates[i].low  < lo) lo = rates[i].low;
   }
   double range = hi - lo;
   if(range < MinRangeATR * atr || range > MaxRangeATR * atr) return(0);

   double close1 = iClose(_Symbol, EntryTF, 1);
   double close2 = iClose(_Symbol, EntryTF, 2);
   double buffer = BreakoutBufferATR * atr;

   // Fresh breakout only: previous bar was still inside the level
   if(trend > 0 && lastBreakoutBuyDay != today &&
      close1 > hi + buffer && close2 <= hi + buffer)
      return(1);
   if(trend < 0 && lastBreakoutSellDay != today &&
      close1 < lo - buffer && close2 >= lo - buffer)
      return(-1);
   return(0);
}

//+------------------------------------------------------------------+
//| Setup B: pullback into EMA with rejection candle                 |
//+------------------------------------------------------------------+
int PullbackSignal(int trend)
{
   double ema = GetValue(hPullEMA, 0, 1);
   double rsi = GetValue(hRSI, 0, 1);
   if(ema == 0 || rsi == 0) return(0);

   double o = iOpen(_Symbol, EntryTF, 1);
   double h = iHigh(_Symbol, EntryTF, 1);
   double l = iLow(_Symbol, EntryTF, 1);
   double c = iClose(_Symbol, EntryTF, 1);

   if(trend > 0 && l <= ema && c > ema && c > o && rsi >= RSIBuyMin && rsi <= RSIBuyMax)
      return(1);
   if(trend < 0 && h >= ema && c < ema && c < o && rsi >= RSISellMin && rsi <= RSISellMax)
      return(-1);
   return(0);
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
   double riskMoney  = equity * RiskPercent / 100.0;
   double lossPerLot = slDistance / tickSize * tickValue;
   if(lossPerLot <= 0) return(0);

   double lots = MathFloor(riskMoney / lossPerLot / stepLot) * stepLot;
   lots = MathMin(lots, maxLot);

   // Respect free margin
   double margin = 0;
   while(lots >= minLot && OrderCalcMargin(type, _Symbol, lots, price, margin) &&
         margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.9)
      lots -= stepLot;

   // Small accounts: min lot may exceed RiskPercent; allow it only up to a hard cap
   if(lots < minLot && MaxRiskAtMinLot > 0 && minLot * lossPerLot <= equity * MaxRiskAtMinLot / 100.0 &&
      OrderCalcMargin(type, _Symbol, minLot, price, margin) && margin <= AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.9)
      lots = minLot;
   if(lots < minLot) return(0);
   return(NormalizeDouble(lots, 2));
}

//+------------------------------------------------------------------+
//| Open a market order                                              |
//+------------------------------------------------------------------+
bool OpenTrade(int direction, double atr, string tag)
{
   int    digits    = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point     = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minStop   = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   double slDist    = MathMax(SL_ATR * atr, minStop + 10 * point);

   ENUM_ORDER_TYPE type = (direction > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double price = (direction > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                  : SymbolInfoDouble(_Symbol, SYMBOL_BID);

   double lots = CalcLots(slDist, type, price);
   if(lots <= 0)
   {
      Print("Lot size below minimum for the configured risk; trade skipped");
      return(false);
   }

   double sl = NormalizeDouble(price - direction * slDist, digits);
   double tp = (TP_R > 0) ? NormalizeDouble(price + direction * slDist * TP_R, digits) : 0.0;

   bool ok = (direction > 0) ? Trade.Buy(lots, _Symbol, price, sl, tp, tag)
                             : Trade.Sell(lots, _Symbol, price, sl, tp, tag);
   if(!ok || (Trade.ResultRetcode() != TRADE_RETCODE_DONE && Trade.ResultRetcode() != TRADE_RETCODE_PLACED))
   {
      Print("Order failed: ", Trade.ResultRetcode(), " ", Trade.ResultRetcodeDescription());
      return(false);
   }
   PrintFormat("%s %s %.2f lots @ %.2f SL %.2f TP %.2f", tag, direction > 0 ? "BUY" : "SELL", lots, price, sl, tp);
   return(true);
}

//+------------------------------------------------------------------+
//| Partial close, break-even and ATR trailing                       |
//+------------------------------------------------------------------+
void ManagePositions()
{
   double atr = GetValue(hATR, 0, 1);
   if(atr <= 0) return;

   int    digits  = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point   = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minStop = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double stepLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;

      long   type   = PositionGetInteger(POSITION_TYPE);
      int    dir    = (type == POSITION_TYPE_BUY) ? 1 : -1;
      double open   = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl     = PositionGetDouble(POSITION_SL);
      double tp     = PositionGetDouble(POSITION_TP);
      double volume = PositionGetDouble(POSITION_VOLUME);
      double price  = (dir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                                : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if(sl == 0) continue;

      // Stop still on the losing side of entry => break-even not yet done
      bool beDone = (dir > 0) ? (sl >= open) : (sl <= open);

      if(!beDone)
      {
         double risk   = MathAbs(open - sl);
         double profit = (price - open) * dir;
         if(risk > 0 && profit >= PartialAtR * risk)
         {
            if(UsePartialClose && PartialPercent > 0)
            {
               double closeVol = MathFloor(volume * PartialPercent / 100.0 / stepLot) * stepLot;
               if(closeVol >= minLot && volume - closeVol >= minLot)
                  Trade.PositionClosePartial(ticket, NormalizeDouble(closeVol, 2));
            }
            double newSL = NormalizeDouble(open + dir * BE_BufferATR * atr, digits);
            if(MathAbs(price - newSL) > minStop)
               Trade.PositionModify(ticket, newSL, tp);
         }
         continue;
      }

      if(UseTrailing)
      {
         double trailSL = NormalizeDouble(price - dir * Trail_ATR * atr, digits);
         bool better = (dir > 0) ? (trailSL > sl + point) : (trailSL < sl - point);
         if(better && MathAbs(price - trailSL) > minStop)
            Trade.PositionModify(ticket, trailSL, tp);
      }
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
