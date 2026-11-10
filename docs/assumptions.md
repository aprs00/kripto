# Standing assumptions (the part of self-improvement that fixes foundations, not symptoms)

Why this file exists (2026-11-10): the owner asked three questions in a row that the system should have asked itself: why is
it not always live, why only daily data, why only hourly reactions. Each was a design choice from day 1 that nobody had tested.
The weekly retro audited recent CHANGES; nothing audited what had never changed. This ledger lists every assumption the
system rests on, the evidence for it, and when it was last tested. **Sunday retro: test or challenge the two rows with the
weakest or oldest evidence, and add any assumption you notice you are relying on.** A row without evidence is a to-do.
"Owner-set" rows can only be changed by the owner (say so in STATUS.md if the evidence argues for a change).

| # | assumption | set by | evidence | last tested | verdict / next |
|---|---|---|---|---|---|
| 1 | **Backtest cost model** (fee 4.5 bp + slippage 3 bp·√($50M/volume), 1.5–25 bp, "deliberately conservative") | day 1 | 234 live fills (median $49): slippage 0.9 bp on both venues; the model charged 5.1 bp for the same HL fills (9.9 bp vs 1.5 bp live in the thinnest bucket). Total ≈ 9.6 bp modelled vs 5.4 bp live on HL (×0.56); Binance about right. Only 2 calm days. | 2026-11-10 | **OPEN, most important.** At ×0.56: flow-on-HL 0.23 → 0.54, xsmom HL 0.00 → 0.31, fspread −0.25 → 0.89, blend 1.56 → 1.73. Backlog C1: calibrate on ≥ 14 days of fills incl. a volatile day, then change the model with a design.md entry (never in a session that promotes). |
| 2 | Decisions once a day are enough | day 1 | Decision-frequency study (BN-82 5.7 y, HL 2.2 y): deciding every 4h / 1h raises return BEFORE costs by 3–6%/yr but doubles to 6× the turnover; net Sharpe falls (tsmom 0.92 → 0.78 → 0.58, xsmom 0.45 → 0.22 → −0.20). | 2026-11-10 | Holds at modelled costs. Re-run after C1 (cheaper costs move the optimum toward faster). |
| 3 | Daily / 4h bars are fine enough for signals | day 1 (bnall was downloaded as daily for convenience) | Same study: 4h or 1h bars with daily decisions: tsmom 0.76 → 0.92 / 0.82, xsmom 0.49 → 0.45 / 0.55. Hourly cross-sectional effects are real (t ≈ 8) but 2–5 bp. | 2026-11-10 | Mixed, small. Full-universe intraday data (bnall at 4h) would let this be tested without survivor bias: backlog D1, low priority until C1. |
| 4 | Positions need watching only hourly | day 1 | None: it was never a decision, just the timer. | 2026-11-10 | **Was wrong. Fixed:** kripto-live.service values every book and enforces the kill switch every 20 s. |
| 5 | Taker orders only | day 1 | T9 (2026-11-10): post-only fills on hourly OHLC lose as much alpha as they save in fees over 6 y. A paper book cannot know its queue position. | 2026-11-10 | Holds on paper. Only real fills could settle it (owner's decision). |
| 6 | HL data by polling /info at ≥ 3 s, no websocket | owner (HARD RULES 1–2, shared server IP) | One call returns every mark, so 20 s monitoring fits. Order-book and trade data stay sparse (top-10 coins hourly). | 2026-11-10 | Owner-set. Costs us: intraday order-flow research on HL. |
| 7 | Signals from price, volume, funding only | day 1 | Positioning + L2 collected since 11-09 (not yet analysable); owner raised Telegram (listing announcements, mention counts) 11-10. | never | OPEN: T6b ≈ 12-07; Telegram export test when the owner supplies channels. |
| 8 | Venues: Hyperliquid + Binance perps | owner | Binance added 11-09; blend/flow/xsmom stronger there, costs lower. | 2026-11-09 | Holds. Untested: spot legs, other perp venues. |
| 9 | Walk-forward: 240 d train, 60 d test, pick by in-sample Sharpe | day 1 | tsmom picks worse than its grid median (0.08 vs 0.58): the selection rule itself adds noise. | never | OPEN: compare "pick the best" with "trade the grid average" (one study, all strategies). |
| 10 | Gate: OOS > 0.8 on the venue traded, DSR > 0.9 on bnall, worst stress > 0 | day 1, revised 11-09 | Nothing passes; three candidates at DSR 0.81–0.88. | 2026-11-09 | Holds. Do not loosen. The forward ledger is the tie-breaker from ≈ 12-09. |
| 11 | Account sizes $1,000 and $200; 25–30% vol target; 3× max gross; 25% kill | owner | $200 vs $1,000 comparison 11-10. | 2026-11-10 | Owner-set. |
| 12 | Research cadence Tue/Thu + Sun retro; daily review; hourly watchdog | 11-09 | First day under it: one research session produced 3 results. | 2026-11-10 | Review at the 11-23 retro. |
