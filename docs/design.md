# kripto — design & research philosophy

_Written 2026-11-08 at project start. The autonomous agent may append to this file but must not
silently rewrite history; changes of direction are recorded in `journal/`._

## 1. Objective and honest framing

Goal: a **paper-traded** Hyperliquid perps strategy, starting with $200 of virtual capital, that makes
money **after all costs**, with a research loop that keeps improving it without a human.

What "profitable" has to mean to be worth anything:

* Net of taker fees (4.5 bp), slippage, and hourly funding.
* Measured **out-of-sample**: on data the strategy's parameters never saw, and then live on paper.
* Big enough to beat the noise from how many ideas we tried (deflated Sharpe, §4).

What we will *not* do: show a beautiful in-sample backtest and call it an edge. Most retail bots die
because of exactly that: overfitting plus ignored costs. Our infrastructure exists to stop that.

## 2. Where can a $200, minutes-to-hours-latency bot have an edge?

Think like a prop desk: **who is on the other side of the trade, and why are they willing to lose?**

| Edge type | Can we compete? | Why |
|---|---|---|
| Latency arbitrage, market making, queue position | **No** | HFT firms colocate; our loop is minutes. Paper fills couldn't even validate it honestly. |
| **Risk premia** (being paid to hold risk others want to shed) | **Yes** | Funding carry: leveraged longs pay to keep crowded bets on. We get paid to take the other side, neutralising price risk. |
| **Behavioural / flow** (predictable, non-informational order flow) | **Yes** | Retail chases trends (time-series momentum), over-reacts short term (reversal), crowds into hype listings that then bleed. |
| **Structural / information** specific to Hyperliquid | **Yes, the most interesting part** | HL is an on-chain exchange: every account's positions, leverage and liquidation price are public. CEX traders cannot see this. |

Capacity is a non-issue at $200: we can trade things too small for a fund. That's a real advantage.
The minimum order is $10, which allows roughly 10–20 positions at modest leverage.

## 3. Hypothesis pipeline

**Tier 1, documented anomalies (testable now on price + funding history):**

1. `tsmom`: time-series trend, multi-horizon, volatility-targeted. The most robust crypto effect historically.
2. `xsmom`: cross-sectional momentum, beta-hedged.
3. `xsrev`: short-term cross-sectional reversal (likely killed by fees; we check).
4. `carry`: short high-funding / long low-funding, dollar and beta neutral. Earns the funding spread.
5. `lowvol`: betting against volatility (the lottery-ticket alts underperform).
6. `funding_contra`: a funding spike against an asset's own history is a crowding signal, so fade it.

**Tier 2, Hyperliquid-specific (need data we start collecting now, since HL has no history API for it):**

7. **Positioning transparency.** Snapshot open interest, funding, premium and the positions of the
   largest/most-profitable public addresses every hour. Test whether "smart" accounts lead and
   "dumb", highly levered accounts lag.
8. **Liquidation maps.** Estimate where clusters of liquidation prices sit and whether price is
   drawn to them (cascade risk). Use as a risk filter first, a signal second.
9. **HL vs Binance funding/premium spread.** HL retail flow is distinct. When HL funding is far above
   Binance funding for the same coin, HL longs are uniquely crowded. Test this as a reversal signal.
10. **New-listing decay.** Newly listed perps (airdrop/unlock tokens) tend to bleed after the hype.
    Testable now on daily candles of all 235 perps, including delisted ones (avoids survivorship bias).
11. **Token unlocks.** Short ahead of large scheduled unlocks, using public calendars.

**Tier 3, portfolio level:** combine surviving signals with risk-parity weighting and volatility
targeting, and switch regimes only if evidence supports it.

## 4. Research protocol (anti-self-deception)

* **Causality tests.** Every strategy is unit-tested to give identical weights whether or not future data exists.
* **Realistic costs.** Taker fee + liquidity-scaled slippage (1.5–25 bp) + hourly funding, with the position drifting between rebalances, and a no-trade band to cut churn.
* **Walk-forward.** At each fold, parameters are chosen on past data only and evaluated on the next 60 days. Only the stitched out-of-sample record counts.
* **Grid robustness.** A real effect is positive across most of its parameter grid, not at one magic point.
* **Two venues.** Signals must hold on HL (≈2.3 y of 4h data) **and** Binance (2020→now).
* **Trial registry.** Every backtest config and every walk-forward experiment is appended to `research/registry.jsonl`. A walk-forward OOS Sharpe is deflated by the number of walk-forward experiments ever run (in-sample single-config Sharpes by the number of single-config backtests), so more ideas tried means a higher bar.
* **Cost stress.** The edge must survive 2× costs.

### Promotion gates
| Stage | Requirement |
|---|---|
| candidate → **incubation** (paper, small weight) | WF out-of-sample Sharpe > 0.8 net on HL; positive on Binance; DSR > 0.9 of the WF OOS record on the longest survivorship-free venue that has the signal (bnall if a Binance analogue exists, else HL); survives 2× costs; grid median Sharpe > 0 |
| incubation → **active** | ≥ 21 days live paper, live Sharpe not significantly below backtest (live return inside the backtest's 90% band), no operational errors |
| active → **retired** | live drawdown > 2× backtest max DD, or 60-day live Sharpe < 0 with backtest-inconsistent behaviour |

## 5. Architecture

```
server (Hetzner, user `kripto`, no docker/root access)
├── kripto-trader.service   24/7 paper trading engine (python, hourly loop)
│     • every hour: refresh data → run each enabled strategy → target weights
│     • simulated taker fills by walking the LIVE L2 order book + fees; hourly funding accrual
│     • one virtual book per strategy (shadow books) + the combined "main" $200 book
│     • risk: max gross leverage, per-asset cap, drawdown kill-switch (flatten + halt)
├── kripto-collector        hourly snapshots: asset contexts (OI/funding/premium), top-address positions
└── claude (headless) on timers
      • review   every 4h: health, P&L vs expectations, anomalies → STATUS.md, journal
      • research daily: one research task from the backlog, gates, promote/demote → commit & push
```

State: SQLite (`state/paper.db`). Code and research history: git → GitHub. Data: parquet (not in git).

## 6. Risk policy (main book)
* Starting equity $200 (virtual). Max gross leverage 3×, max 35% of equity in any single asset.
* Volatility target ~25–30% annualised for the combined book.
* Kill switch: −25% from peak flattens and halts everything until a review re-enables it.
* Paper only. No exchange keys exist on the server. Going live is a **human decision**, requiring the
  owner's explicit instruction plus ≥ 60 days of paper results that match expectations.

## 7. Hard rules for the autonomous agent
See `CLAUDE.md`. Summary: paper only; public data only; respect API rate limits; no manipulation
(spoofing, wash trading, etc.), even simulated; never touch anything outside `/home/kripto` (the
`crypto-scanner` stack on the same server is a separate project and off-limits).

## Changelog (protocol/gate changes only; each needs a general rationale independent of any strategy's results)
* 2026-11-08: initial version. Backtest no-trade band set to 0.05 to mirror the $10 min order on a $200 book.
  Shadow books run at $2,000 virtual equity so signal quality isn't distorted by the min order.
* 2026-11-08: clarified the role of live paper (general statistical reason, not tied to any strategy): over weeks, the
  SE of a live Sharpe is ±3–4, so incubation→active is judged mainly on **tracking**. Live behaviour (positions, costs,
  slippage, funding) must match a backtest replay of the same period, with no operational errors, and returns must not be
  significantly worse than expected. Edge itself is judged on the backtest evidence plus accumulating live months.
  Ideas rejected on HL evidence alone are re-tested once HL history has grown ≥ 6 months.
* 2026-11-09 (interactive session with the owner): **DSR trial count and venue.** General rationale, independent of any
  strategy: (1) `n_trials` was the raw registry line count, which adds ~150 per research day from cost-stress reruns,
  re-runs of identical grids, venues and per-config lines of a walk-forward. The DSR bar therefore rose without limit
  (HL, 1.6 y OOS: annual SR ≈ 3.4 needed at 484 lines) and penalised running cost stresses and re-checks, which are
  exactly the checks we want. Inside a walk-forward the parameters are already picked on past data only, so the
  remaining selection bias is choosing which *experiment* to believe → a WF OOS DSR now uses the number of
  walk-forward experiments ever run (all 40 so far, the 11-08 invalid ones included, which is conservative).
  (2) DSR is now measured on the longest survivorship-free venue. 1.6 y of HL cannot make any plausible Sharpe
  significant (even with 1 trial, PSR 0.9 needs SR ≈ 1.0), so on HL the DSR clause silently overrode everything
  else. HL keeps its own requirement: OOS > 0.8 net of HL costs plus 2× costs. With 41 experiments, bnall
  (6 y, daily) needs OOS SR ≈ 1.4. Check at the time of the change: **no current strategy passes** (tsmom/xsmom/listing_short
  all fail HL > 0.8, and none reaches bnall SR 1.4). Effective from the 2026-11-10 research session, not before.
