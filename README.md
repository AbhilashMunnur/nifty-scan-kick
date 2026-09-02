# nifty-scan-kick

Public kicker for the private [nifty-index-trade](https://github.com/AbhilashMunnur/nifty-index-trade) scanner.

GitHub’s own `schedule` on a private repo often skips a whole morning. This
workflow sleeps until each NSE slot (09:30–15:40 IST) and then dispatches
`nifty-scan`. Because this repo is **public**, those waits do not count against
the private 2,000 Actions minutes/month.
