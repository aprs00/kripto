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
* **No verdict on one formulation (2026-11-12).** The clauses above guard against believing a false edge; this one guards against
  burying a real one. Before testing, write the mechanism and at least three materially different formulations of the idea
  (definition, bar type/horizon, universe/venue, stand-alone vs filter for an existing book, alone vs combined). Explore them with
  descriptive studies on an exploration sample, with the confirmation sample (later period and/or unused instruments) named in
  writing first; walk-forward only the best one or two on the confirmation sample. Every failure gets a diagnosed reason. A single
  failed formulation is recorded OPEN (one form failed); DEAD requires three failed formulations and the reason.

* **No unwritten hold-backs (2026-11-26).** The gate is sufficient as well as necessary. A strategy that passes every clause below is set to
  `incubation` and given its equal-risk share of its venue's main book in the session that sees it pass; "more evidence first", "prove it live",
  "let's wait" are not clauses. Holding back a passer is an error of the same size as promoting a failure. Any extra condition is a gate change
  (general rationale, changelog, not applied in the session it is made), never a judgement call. `scripts/held_back.py` applies the written
  clauses mechanically; the watchdog WARNs on a passer that is not trading. Live tracking (incubation → active / retired) is the check after entry.

### Promotion gates
| Stage | Requirement |
|---|---|
| candidate → **incubation** (paper, small weight) | WF out-of-sample Sharpe > 0.8 net (from 2026-11-19: min(pick, grid average), changelog 2026-11-17) on the **venue the strategy trades** (HL, or Binance = bnall); positive on the other venue where the signal is testable there; DSR > 0.9 of the WF OOS record on the longest survivorship-free venue that has the signal (bnall if a Binance analogue exists, else HL); robustness block of the WF-chosen config (`robust.worst` = the lowest full-sample Sharpe among: base, 2× costs, one bar of execution delay, first 6 and first 12 months dropped) > 0; grid median Sharpe > 0. Schedules slower than daily are run as staggered tranches (the average over every start day), never as one start day |
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
      • research twice daily (06:40, 13:40 UTC): hypotheses from the backlog, gates, promote/demote → commit & push
```

State: SQLite (`state/paper.db`). Code and research history: git → GitHub. Data: parquet (not in git).

## 6. Risk policy (main book)
* Starting equity $1,000 (virtual; $200 until 2026-11-10, see changelog). Max gross leverage 3×, max 35% of equity in any single asset.
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
* 2026-11-09 (owner direction, interactive): **Binance USDT-M perps become a second paper venue.** Paper only, public
  market data only (fapi klines/depth/premiumIndex/exchangeInfo), no keys, no orders, same as HL. General rationale: an
  edge should be judged where it is traded, with that venue's costs, and the other venue serves as a robustness check.
  Binance has 6 y of survivorship-free history (vs HL ≈ 1.6–3 y), a $5 min order (vs HL $10; BTC $50, ETH $20), so it allows
  ~2× the breadth at $200, and taker buy volume in live klines. The gate's "> 0.8 net on HL" therefore becomes "> 0.8 net on the
  venue it trades". Each venue gets its own $200 main book (realistic: one account per exchange). Effective once the Binance
  paper venue is built and tested, and never in the session that builds it.
* 2026-11-09 (owner direction, interactive; effective from the next research session, and not used to promote anything in
  the session that made it; nothing passes anyway). The owner reviewed the project, said the earnings a $200 account can produce
  are not worth having, set a **$1,000** reference account size, and chose the **steady** risk mode (the existing
  25–30% volatility target, no extra leverage). Changes, each with a rationale that does not depend on any strategy's result:
  (1) **Main paper books are $1,000 per venue** (HL and Binance are alternative homes for the same $1,000, not $2,000 together).
  A paper account must mirror the capital that would really be deployed, otherwise executability is tested at the wrong scale.
  The backtest no-trade band follows mechanically: min order / equity = $10 / $1,000 = **0.01** (was 0.05). Registry lines now
  record `band`. Shadow books stay at $2,000.
  (2) **Staggered tranches.** Every schedule was anchored at the epoch, so a config that rebalances every n days was tested on one
  of its n possible start days. The start day is arbitrary, yet it moved full-sample Sharpe from 0.26 to 1.46 for one config.
  A result may not depend on an arbitrary choice, so a schedule of n days is now n tranches rebalanced on consecutive days
  (research and live use the same function, `strategies.scheduled`). Single start days remain available as a diagnostic (`phase`).
  (3) **Robustness block in the gate.** "Survives 2× costs" becomes `robust.worst > 0` (2× costs, one bar of execution delay,
  first 6/12 months dropped), computed automatically for every walk-forward. This only makes the gate stricter.
  (4) **Forward ledger** (`scripts/forward_score.py`, weekly): every experiment's frozen choice scored only on bars after it was
  registered. Reported in the weekly retro and STATUS. It is the evidence stream that does not wear out with re-use; it becomes a
  gate clause only after it has run long enough to know its noise (decide no earlier than 2027-02, with a general rationale).
  (5) **Cadence.** ~25 walk-forward experiments a day on a fixed history push the DSR bar from 1.44 (N=49) to 1.76 (N=500) within
  weeks without adding information. Research runs Tue + Thu, the retro on Sun; the 4-hourly Claude review became an hourly
  deterministic watchdog (`scripts/health.py`) plus one Claude review a day, with an extra review started on any new problem.
  Consequence for old numbers: every result before this entry used band 0.05 and one start day. The candidates' pre-registered
  grids were re-measured the same day (batches 2026-11-09-h1-recheck-*); findings.md carries the new numbers.
* 2026-11-10 (owner direction, interactive): **"test also with $200, not only with $1,000."** The owner may fund either amount, and
  what a strategy can hold depends on the account: at $200 the $10 minimum order is 5% of equity. General rationale, independent
  of any result: executability must be measured at every size that might really be funded. So (1) `config/risk.json` gets
  `small_equity` (200) and the paper engine runs a twin of every book at that size: `small:<entry>` next to `shadow:<entry>`, and
  `small:main` / `small:main_bn` next to the main books (same targets, same engine, the min order now decides what opens).
  (2) Every walk-forward's robustness block gains `small_acct` = the chosen config at band min order / small_equity (0.05).
  (3) **The gate is unchanged**: it is still judged at the main size ($1,000); `small_acct` is reported next to it and is not part
  of `robust.worst`. If the owner funds $200, the `small_acct` column and the `small:` books are the relevant evidence.
  (4) Books that trade the same coin in one run share one order-book snapshot (≤ 180 s old), so the twins add no API calls.
* 2026-11-10 (owner direction, interactive): **always-on watcher.** The owner expected the system to be live at all times; it
  was a timer that looked once an hour. General rationale: risk limits are only as good as how often they are checked, and one
  request returns every mark on a venue, so continuous monitoring costs almost nothing. `kripto-live.service` (systemd,
  Restart=always; a managed service like the timers, not a stray session process) re-values every open book every 20 s and
  enforces the kill switch after 2 consecutive breaching ticks, only with a mark for every held coin. Still paper only, public
  data only, HL client ≥ 3 s. Trade DECISIONS stay at bar closes (decision-frequency study the same day: faster decisions lose
  net of modelled costs). Strategies accept fractional `every_days` (1/6 = every 4 h) so that question can be re-tested.
  **Cost model: not changed today.** Live fills say HL slippage is ≈ 0.9 bp vs 5.1 bp modelled, but on 2 calm days; the model
  will be re-fitted from ≥ 14 days of fills including a volatile one (backlog C1), with its own changelog entry, in a session
  that promotes nothing. Until then results may quote a "live-calibrated costs" sensitivity next to the gate number, clearly labelled.
* 2026-11-10 (owner mandate, interactive: "the only rule is that it should create a profitable trading bot, rest of the stuff is up
  to you"). Two protocol changes, each with a rationale independent of any strategy's result:
  (1) **What the main paper books are for.** Until now a main book stayed flat until a strategy passed the incubation gate, so
  "the bot" had no track record at all and could not be profitable or unprofitable. Paper trading an unproven portfolio costs
  nothing, while a flat book teaches nothing. From the next research session (2026-11-12; not in the session that made this
  change, HARD RULE 5) each venue's main book and its $200 twin trade the **best current estimate**: the equal-risk mix of that
  venue's candidates with walk-forward OOS > 0.8 on the venue and `robust.worst` > 0, chosen by this fixed rule, re-chosen only
  when a walk-forward result changes the list. Status `incubation` now means exactly that. **The full gate (incl. DSR > 0.9, the
  forward ledger and ≥ 60 days of main-book tracking) is unchanged and now governs one thing: telling the owner the evidence
  justifies real money.** STATUS.md must say on which side of that line every number is.
  (2) **Public websocket market data is allowed** (HARD RULE 1 amended by the owner's delegation): read-only, unauthenticated,
  one connection per venue. Rationale: order-flow data on Hyperliquid exists only as a live stream and cannot be backfilled.
* 2026-11-12 (M1 applied, as scheduled by the 2026-11-10 entry; a sizing rule for paper books, not a gate). The old "incubation alloc
  ≤ 0.25" cap belonged to incubation-as-toe-in; since incubation now means "the main book's best estimate", a 0.25 cap would run
  the paper main book at a quarter of the steady risk mode and measure nothing useful. `sum(alloc) ≤ 1` holds **per venue** (main and
  main_bn are alternative homes for the same $1,000). Interpretation fixed with the rule: a candidate that is a component of an
  included blend is not added again (it would double its weight), and of two blends of the same components the one chosen
  without hindsight (nested) is used. Real-money recommendation still needs the full gate in §4.
* 2026-11-12 (owner direction, interactive: "you are giving up on things too suddenly"). **No verdict on one formulation**
  (§4). General rationale, independent of any strategy's result: every protocol clause so far controls false positives (walk-forward,
  DSR, robustness block); nothing controlled false negatives, and one literal translation of an idea, tested once, was being recorded
  as DEAD (the five InSilico rules of 11-11/12 are the example that exposed it, and several earlier DEAD entries have the same
  shape). Costs of the change: more thinking and descriptive work per idea, none in walk-forward count, because exploration is
  descriptive and confined to an exploration sample while the gate numbers come only from a confirmation sample fixed in advance.
  It makes no gate easier: promotion clauses are unchanged, and an idea revived this way still has to pass them on data it was
  not shaped on. The Sunday retro audits two old DEAD entries a week against the new standard (relabel, do not re-test).
* 2026-11-17 (research session; backlog WF1, assumptions row 9). **Which out-of-sample number a walk-forward is read by.** General
  rationale, independent of any one strategy: choosing the in-sample-best config of a grid at each fold is a noisy estimator; on
  the 9 pre-registered strategy × venue walk-forwards of 2026-11-09 (same folds, research/studies/wf_selection.py) the equal-weight
  average of the whole grid beat the pick in 6/9 (mean OOS SR 0.95 vs 0.78). The pick's stitched OOS is one draw that contains
  selection luck in both directions. Rule, from the next research session (2026-11-19; not applied to any lifecycle change today,
  HARD RULE 5):
  (1) **Real-money gate** (§4 "WF out-of-sample Sharpe > 0.8"): reads **min(pick OOS, grid-average OOS)**. A pick that beats its
  grid average is treated as partly luck; a grid average above a weak pick does not rescue the pick for real money. DSR is
  unchanged (computed on the pick's stitched record).
  (2) **Main paper books' best estimate** (the 2026-11-10 M1 rule "WF OOS > 0.8 on the venue and robust.worst > 0"): reads the
  **grid average** (the lower-variance estimate of the idea's value), and requires the pick's OOS > 0 as well (pick and average
  must agree on sign). This can add or remove entries; the list is re-derived on 2026-11-19 by the fixed rule, not by hand.
  (3) The grid average is only meaningful when the grid is ONE hypothesis: if a grid mixes opposite directions (a sign/side
  parameter) or materially different signals, the average is taken within the picked direction, and the result says so.
  (4) Every new walk-forward quotes pick, grid average and robust.worst together (show_result already prints all three).
  This makes the real-money gate harder, never easier. It can make the paper best-estimate list longer or shorter; that list
  governs paper only.
* 2026-11-26 (research session; backlog AL1/AL2; a sizing rule for paper main books, not a gate). **Main books run at the steady-mode
  volatility.** General rationale, independent of any strategy's result: the owner's reference account is "steady, 25–30% vol"; every
  entry is vol-targeted on its own, but a main book that mixes several entries 1/N realises less (diversification between entries;
  AL1: main_bn's mixes 14–19%), so the paper main book measured roughly two thirds of the risk mode the owner would fund. Rule
  (pre-registered in research/studies/al2_mix_vol.py, both forms judged by the same written rule): each main book's mix is
  multiplied by ONE number per calendar month, s = clip(0.25 / realised vol of the current mix's net daily backtest returns over the
  trailing 365 days, 0.5, 2.0), gross still capped by max_gross (scripts/main_scale.py; risk.json `main_scale`, `main_scale_due`; the
  watchdog WARNs when due). Form a (daily ex-ante rescaling) was rejected by the rule (doubled costs, ΔSR −0.13/−0.19); form b passed
  (bnall flow+blend_nested: vol 19 → 26%, SR 1.93 → 2.02, mdd −26 → −32%; old mix 18 → 25%, 1.89 → 1.94; HL main 30 → 26%, 1.24 → 1.22).
  It scales risk and return together and changes no gate number (gates read single strategies' walk-forwards). **Not applied today**:
  the first `scripts.main_scale --write` runs in the next research session (HARD RULE 5 spirit: never adopt and act in one session).
* 2026-11-26 (interactive, owner present): **No unwritten hold-backs** (§4). General rationale, independent of any one result: the protocol had many guards
  against promoting a false edge and none against sitting on a real one, and the agent's own caution showed up as conditions that were never written
  (ladder@bn passed every clause on 11-23 and stayed at alloc 0). A gate that may be tightened silently is not a gate. This adds no clause and removes
  none; it makes the existing clauses sufficient. Applied from the NEXT session (11-27 06:40), not this one.
* 2026-11-27 (research session; a sizing rule for paper main books, not a gate). **Overlay sleeves.** The equal-risk share assumes a book that
  holds capital all the time. A strategy that is flat most of the time (an order book of resting limits, e.g. ladder@bn: flat ~97% of minutes) and whose
  per-order size is capped by a written risk rule (E2d: a -50% move on the largest historical same-minute batch must stay above the kill switch) does
  not carve capital out of the account: in one margin account it uses margin only while a position is open. Such a strategy runs as an **overlay** on the
  venue's main book and its $200 twin: orders of (frozen per-order size × alloc × the main book's whole equity), positions in the same ledger, kept apart
  from the hourly rebalance by the `sleeve` table; its alloc is a fraction of that cap and does not count in sum(alloc) ≤ 1. It may never exceed the cap,
  and it is used only while its risk at the cap is at or below its equal-risk share (ladder: ≈ 4%/yr vol at 2.9%/order vs ≈ 19%/yr for main_bn's daily mix).
  General rationale: carving a 1/3 capital slice for a book that is flat 97% of the time would cut the always-invested books by a third to leave cash idle,
  and would push the $200 twin's orders below the $5 minimum. First applied today because the gate result (11-23) and the no-hold-back rule (11-26) predate it.
* 2026-11-27 (research session; architecture/sizing, not a gate). **Two-account main book `main@pair`.** A strategy whose positions are legs on two venues
  (fspread_hold@pair) cannot live in `main` (HL) or `main_bn` (Binance), and "its venue's main book" did not exist, so a pair strategy passing the gate
  had nowhere to trade (an unwritten hold-back by construction). `main@pair` (+ `small:main@pair`) is the third alternative home for the reference $1,000:
  one HL and one Binance account, the equity split by the book's own legs. Incubation/active pair entries with alloc > 0 trade it by the usual alloc
  blend. alloc is capped by the deployable gross in two separately-margined accounts (X1c: gross 1.0 survives 2025-10-10, 2.0 does not); with one pair
  entry its equal-risk share is the whole book, so alloc = that cap (0.5 of the shadow's gross 2.0). Not vol-scaled by main_scale (a hedged book at
  1–5%/yr vol cannot be levered to the steady-mode 25–30% in real accounts).
