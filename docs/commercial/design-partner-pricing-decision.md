# Design-Partner Pricing Decision Sheet

**Status:** Decision support only. No price is set and no willingness-to-pay evidence exists until named-buyer discovery is recorded.

## Fixed package boundary

- 30 calendar days, one customer-controlled MCP environment, one existing workflow.
- Two read-only tools and one ticker per invocation.
- One versioned wheel/sdist handoff, configuration, five-ticker proof, onboarding, rollback, and acceptance record.
- Up to eight founder support hours and one acceptance-defect patch are packaging hypotheses to validate.
- No hosting, monitoring, alerts, batching/watchlist, advice, execution, predictive performance, new adapter, or source procurement.

## Cost inputs

Complete from the actual deployment. Do not infer buyer value from build effort.

| Input | Symbol | Evidence/value |
| --- | --- | --- |
| Discovery and scoping hours | `H_discovery` |  |
| Installation/integration hours | `H_install` |  |
| Validation and documentation hours | `H_validation` |  |
| Expected support hours, capped at 8 | `H_support` |  |
| Acceptance-patch reserve hours | `H_patch` |  |
| Founder loaded hourly cost | `C_hour` |  |
| Customer-specific source/license cost paid by provider | `C_source` |  |
| Counsel/contract cost allocated to engagement | `C_legal` |  |
| Other direct delivery cost | `C_other` |  |
| Payment fee rate | `F_payment` |  |
| Contingency rate for bounded delivery risk | `F_risk` |  |
| Target gross-margin rate | `M_target` |  |

Calculations:

```text
labor_cost = (H_discovery + H_install + H_validation + H_support + H_patch) * C_hour
direct_cost = labor_cost + C_source + C_legal + C_other
risk_adjusted_cost = direct_cost * (1 + F_risk)
cash_break_even_price = risk_adjusted_cost / (1 - F_payment)
target_margin_price = risk_adjusted_cost / (1 - F_payment - M_target)
```

If the denominator is zero or negative, the proposed margin/fee assumptions are invalid. Source costs owned directly by the customer remain outside provider revenue and must be stated separately.

## Named-buyer evidence

| Buyer/date | Environment and integration owner | Installation complexity | Support expectation | Rights/source burden | Budget or price reaction | Decision evidence |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

Record exact buyer language or a faithful short paraphrase. A demo request, compliment, or hypothetical budget is not willingness-to-pay evidence. Paid continuation is separate from the upfront installation decision.

## Decision rule

1. Exclude any prospect whose requested outcome crosses the package boundary or rights/legal gate.
2. Estimate cost from the actual environment and support facts.
3. Compare cash break-even and target-margin prices with named-buyer evidence.
4. Scope down before discounting; never hide additional support or source work inside the fixed package.
5. Ryan selects the pricing hypothesis and test. Counsel/accounting approves payment terms; the counterparty accepts or rejects them.

## Owner decision

- Selected upfront price hypothesis: `[unset]`
- Scope assumptions supporting it: `[unset]`
- Named-buyer evidence used: `[none]`
- Minimum acceptable price and rationale: `[unset]`
- Test cadence and stop/change rule: `[unset]`
- Ryan decision/date: `[required]`
