# nifty-scan-kick

Public kicker for the private [nifty-index-trade](https://github.com/AbhilashMunnur/nifty-index-trade) scanner.

GitHub’s own `schedule` on a private repo often skips a whole morning. This
workflow sleeps until each NSE 30-minute slot (09:30, 10:00, … 15:30, plus
15:40 IST close) and then dispatches `nifty-scan`. After 15:40 it keeps
waiting overnight so the next session does not depend on GitHub’s timer.
