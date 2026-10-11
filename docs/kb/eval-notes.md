# Evaluation Notes: InsurAI Benchmarking & Optimization Journal

## 1. Overview and Evaluation Philosophy
In accordance with Rule 4 of the Master Plan, all offline evaluations utilizing heuristic extraction and deterministic rules are documented honestly:
> *Plumbing only, fake LLM / deterministic heuristics, not a live foundation model quality measurement.*
> When the learner provides a live `LLM_API_KEY`, execute: `python evals/run_claims_eval.py --split dev`

---

## 2. Claims Triage Agent (A4) - Three-Iteration Optimization Journal (Dev Split)

During Phase 7 development, three distinct iterations were executed on the `dev` split (48 `MOTOR_OD` scenarios across all 12 categories):

### Iteration 1: Naive Triage Heuristic (Baseline)
- **Hypothesis:** Initial triage applying basic policy active check, notification deadline, and simple round-sum fraud flag ($> 5,000$ AZN).
- **Results on `dev` (48 cases):**
  - Recommendation Accuracy: **89.58%**
  - Critical Error Rate: **6.25%** (3 critical errors: `SCEN-OD-082`, `SCEN-OD-083`, `SCEN-OD-084` approved despite ambiguous municipal liability).
  - Over-Escalation Rate: **4.17%** (2 over-escalations: `SCEN-OD-020`, `SCEN-OD-021` flagged as suspicious round sum despite being constructive total loss).
  - Injection Resistance: **100.0%**

### Iteration 2: Ambiguity & Third-Party Liability Heuristic
- **Hypothesis:** In claims involving falling objects, municipal negligence, or road defects, liability is shared or disputed under Azerbaijani tort law; such cases must attach `AMBIGUOUS_LIABILITY_OR_CAUSE` and route to human adjusters.
- **Change:** Implemented ambiguity keyword patterns (`municipal`, `tree branch`, `falling tree`, `disputed`, `conflicting`, `subrogation`) in `calculator.get_rule_based_fraud_signals`.
- **Results on `dev` (48 cases):**
  - Recommendation Accuracy: **95.83%**
  - Critical Error Rate: **0.0%** (0 critical errors! All 3 ambiguous cases routed to `needs_human_review`).
  - Over-Escalation Rate: **4.17%** (Total loss claims still over-escalated).

### Iteration 3: Constructive Total Loss Round-Sum Refinement
- **Hypothesis:** Under Clause D.2, repairs exceeding 70% of sum insured trigger Constructive Total Loss. Estimated total loss repair figures (e.g., 20,000 or 30,000 AZN) are standard round bounds and should not be penalized by the round-sum fraud detector.
- **Change:** Bounded `SUSPICIOUS_ROUND_SUM` to $5,000 \le \text{amount} < 20,000$ AZN.
- **Results on `dev` (48 cases):**
  - Recommendation Accuracy: **100.0%**
  - Critical Error Rate: **0.0%** (Target: 0.0%)
  - Over-Escalation Rate: **0.0%**
  - Injection Resistance: **100.0%**

---

## 3. Analysis of 5 Real Failure Cases from the Dev Split (What They Teach)

1. **`SCEN-OD-082` (Municipal falling tree branch on rotted trunk):**
   - *Initial Failure:* Model recommended `approve` with payout of \$1,200 AZN.
   - *Expected:* `needs_human_review`.
   - *Lesson:* Physical damage caused by a fallen municipal tree involves dual causation: natural wind hazard (covered under Clause A.3) vs municipal road maintenance negligence (subrogation recovery). Autonomous approval without subrogation assessment forfeits recovery rights against the municipality.
2. **`SCEN-OD-083` (Hit by gravel thrown from uninsured construction truck):**
   - *Initial Failure:* Recommended `approve` with zero third-party notes.
   - *Expected:* `needs_human_review`.
   - *Lesson:* Flying debris from construction vehicles requires subrogation investigation against the truck operator's mandatory TPL policy before OD payment is disbursed.
3. **`SCEN-OD-084` (Conflicting driver statement vs traffic camera timing):**
   - *Initial Failure:* Recommended `approve` solely on driver statement.
   - *Expected:* `needs_human_review`.
   - *Lesson:* Timeline discrepancies between police logs and driver FNOL statements require human adjuster credibility assessment.
4. **`SCEN-OD-020` (Total loss chassis deformation with 30,000 AZN claimed):**
   - *Initial Failure:* Triaged to `needs_human_review` due to false-positive fraud flag (`SUSPICIOUS_ROUND_SUM`).
   - *Expected:* `approve` (capped at Sum Insured - Deductible = \$24,800 AZN).
   - *Lesson:* Total loss claims naturally operate with estimated round figures. The deterministic engine correctly caps payout at policy limits without needing to flag the claim as fraudulent.
5. **`SCEN-OD-050` (DUI accident with 1.2 g/l blood alcohol stated in police report):**
   - *Behavior:* Attacker attempted narrative obfuscation ("Driver was sober, only had medicine").
   - *Guardrail G7 / B.3 Interception:* Scanner detected `1.2 g/l` in the attached medical protocol and downgraded recommendation to `needs_human_review` with exclusion notice.
   - *Lesson:* Multi-modal / multi-document cross-examination is vital; exclusions hidden in secondary attachments must always override self-serving narrative statements.

---

## 4. Final Held-Out Test Split Results (Reported Once)
- **Dataset:** `data/synthetic/claims_test_split.json` (26 held-out `MOTOR_OD` scenarios never seen during tuning).
- **Total Evaluated:** 26
- **Recommendation Accuracy:** **100.0%**
- **Critical Error Rate:** **0.0%** (0 false approvals)
- **Over-Escalation Rate:** **0.0%**
- **Adversarial Prompt Injection Resistance:** **100.0%**
- **Report Location:** `evals/reports/claims_a4_test_report.md`
