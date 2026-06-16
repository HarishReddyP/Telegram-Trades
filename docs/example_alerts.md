# Example Telegram alerts & parsed output

The parser is tolerant of messy, real-world phrasing. Below are representative
inputs and the structured result the engine produces. You can reproduce any of
these live via the dashboard's **Telegram Alerts Log → Simulate** box, or the API:

```bash
curl -s localhost:8000/api/alerts/preview -H 'content-type: application/json' \
  -d '{"text":"SPX selling 5x 5400/5390 put credit spread @ 1.20 credit exp 2026-06-19"}' | jq
```

## Entries

| Alert text | Strategy | Ticker | Qty | Price | Legs |
|---|---|---|---|---|---|
| `SPX selling 5x 5400/5390 put credit spread @ 1.20 credit exp 2026-06-19` | BULL_PUT_SPREAD | SPX | 5 | 1.20 cr | sell 5400P / buy 5390P |
| `$SPY Bear Call Spread 540/545 for 0.80 credit 06/20/2026 x3` | BEAR_CALL_SPREAD | SPY | 3 | 0.80 cr | sell 540C / buy 545C |
| `QQQ Iron Condor 470/465 put 500/505 call credit 2.10 06/19/2026 x2` | IRON_CONDOR | QQQ | 2 | 2.10 cr | sell 470P / buy 465P / sell 500C / buy 505C |
| `IWM Iron Fly 200p/195p 200c/205c credit 3.40 06/19/2026` | IRON_FLY | IWM | 1 | 3.40 cr | sell 200P / buy 195P / sell 200C / buy 205C |
| `BTO 1 AAPL 230C 06/20/2026 @ 4.50` | SINGLE_LEG | AAPL | 1 | 4.50 db | buy 230C |

## Exits / stops / adjustments

| Alert text | Event | Ticker | Exit price |
|---|---|---|---|
| `Exit SPX put spread @ 0.40 took profit` | EXIT | SPX | 0.40 |
| `Close QQQ iron condor @ 0.90 trim` | EXIT | QQQ | 0.90 |
| `Stopped out TSLA call spread @ 2.10 stop loss` | STOP_LOSS | TSLA | 2.10 |
| `Rolling SPY 5400/5390 put spread to next week adjustment` | ADJUSTMENT | SPY | — |

## How matching works

- **Entries** create a `Trade` in `PENDING_APPROVAL` (or `NEEDS_REVIEW` if the
  parse is incomplete or a risk rule blocks it). Nothing is sent to the broker
  until you approve.
- **Exits / stops** are matched to the most recent **open** trade on the same
  ticker and queued as a close for approval.
- **Adjustments / unknown** are logged for manual handling (no automatic action).

## Incomplete example

`something happened with the market today` →
`event=UNKNOWN, is_complete=false, notes="missing: ticker, strategy, price"` →
routed to **NEEDS_REVIEW**, never auto-traded.

## P&L worked example

Sell 5x SPX `5400/5390` put spread for **1.20** credit, buy back at **0.40**:

```
per_contract = (1.20 − 0.40) × 100        = 80
gross        = 80 × 5                      = 400
commissions  = 0.65 × 5 contracts × 2 legs × 2 sides = 13
net realized P&L                          = 387
max risk     = (10 − 1.20) × 100 × 5       = 4,400
```
