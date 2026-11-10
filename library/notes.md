# Library notes: testable ideas mined from the books

One entry per idea: source (slug + section), the claim in our own words, the mechanical rule that would test it,
the data it needs, and the backlog id. ≤ 5 lines each. When tested, the verdict goes to research/findings.md and the
entry gets `→ <verdict>`. Ideas in a book count as hypotheses, not evidence.

### N1 Order-flow persistence → flow continuation (bouchaud-…-digest; toth-…-persistence) → backlog L2 → ALIVE on Binance (bnall OOS 1.42); on HL prices the sign transfers but taker costs kill it (2026-11-09)
Large orders are split over hours to days, so the sign of net taker flow is long-memory. Price impact is mostly
transient, though, so the simple prediction "flow → price continues" is weak in liquid names. Test both signs, pre-registered:
cross-sectional rank of k-day net taker flow / volume → next-k-day return, beta-hedged. Needs Binance kline cols 9–10
(taker buy volume), which the loader currently drops. Thin alts may behave differently from the majors: split by liquidity.

### N2 Delta–price divergence / absorption (valtos; tradingriot "CVD") → backlog L2
Heavy aggressive buying without price progress = passive sellers absorbing it → a reversal is likely (and the mirror
case). Mechanical rule: over a window, z(net taker flow) high AND return ≤ 0 → short next period (and the mirror). The
practitioners use it intraday with discretion. We can only test a daily/4h version, so the prior is low.

### N3 Square-root impact law (bouchaud-…-digest; maxdama §7) → backlog L3
Impact ≈ Y·σ_daily·√(Q/V_daily), Y ~ 0.5–1. Use it to sanity-check our liquidity-scaled slippage (1.5–25 bp) at the
$2,000 shadow and $200 main sizes. Live fills (T0a) are the ground truth.

### N4 Perp leadership in price discovery (alexander-heck-2020) → backlog L1 (daily version tested 2026-11-09 as flow-on-HL: Binance flow does lead HL prices gross; the 1h kill test is still open)
The deepest perps lead. Today that's Binance/Bybit, not HL. If HL alts lag Binance by more than our ~1h decision latency, the
Binance 1h return predicts the HL next-hour return. Most likely arbitraged within seconds, so run it as a cheap kill test first.

### N5 Reversion of defactored residuals with an entry threshold (pole ch. 3, 4, 7) → backlog L4
Our dead `xsrev` reversed raw short-term returns every bar and drowned in fees. Pole's angle is different: remove
common factors (BTC beta, sector), trade only when the residual spread is extreme (threshold), hold until it reverts.
Fewer trades, and a cleaner signal.

### N6 Range-based / HAR volatility forecasts (bencik-2014) → backlog L6
Parkinson/Garman–Klass range estimators are ~5× more efficient than close-to-close, and HAR on the realized range
forecasts best. Better vol forecasts → better vol targeting for tsmom/xsmom (risk, not alpha). Pre-register estimator ∈ {cc, parkinson, HAR}.

### N7 Value-area rejection (dalton; tradingriot AMT) → backlog L5 (low prior)
Price that trades outside the prior session's value area (70% of volume) but fails to gain acceptance reverts to
the POC. Crypto has no sessions, so use the UTC day built from 1h volume. Low prior: discretionary context matters to them.

### N8 Alpha loss vs execution cost (maxdama §7.3–7.6) → backlog T9b (mined 2026-11-10)
Execution shortfall = liquidity impact + alpha loss. Waiting (passive orders, slicing) saves impact and fees but loses the part of
the signal's alpha that arrives while you wait. Measure the alpha-decay curve from signals you did NOT trade (the baseline), then
choose the waiting time that minimises the sum. For us: a daily signal whose alpha arrives over days loses almost nothing by
waiting hours for a maker fill, while a fast signal (flow lb3) may. Mechanical test: for each strategy, the average signed return
of its trades from the decision close to +1h, +4h, +12h, +24h (hourly data). It also gives the right post-only horizon per strategy.
Adverse selection (limit buys fill as price falls) is the other half; T9's trade-through fill model includes it.

### N9 Intraday rules as written do not clear costs on minute bars (2026-11-10 event study; valtos, tradingriot, maxdama §4, alexander-heck)
Flow continuation, absorption / CVD divergence, sweep-and-fail, BTC leader-lag, breadth extremes (cumulative TICK), activity spikes:
all ≤ 7 bp and unstable across two 3-month halves on the 20 most liquid perps, against a 12 bp round trip. The practitioner books
trade these with discretion and context; the mechanical cores carry no edge at 1-min resolution with taker fees. Still open from
the library: weighted mid / microprice (maxdama §4.7; needs live L2), and traffic analysis on message counts (maxdama §4.2; the
owner's Telegram idea).
