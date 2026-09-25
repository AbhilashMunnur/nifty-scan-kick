# nifty-scan-kick

Public kicker for the [nifty-index-scan](https://github.com/AbhilashMunnur/nifty-index-scan) scanner.

GitHub’s own `schedule` often skips a whole morning. This workflow sleeps until
each slot, then dispatches `nifty-scan`. Tuesday and Thursday are every 15
minutes, including 15:10 and 15:15. Monday, Wednesday, and Friday are every 30
minutes, with no 15:10 or 15:15. Every weekday also runs the 15:40 close.
After 15:40 it keeps waiting overnight so the next session does not depend on
GitHub’s timer.
