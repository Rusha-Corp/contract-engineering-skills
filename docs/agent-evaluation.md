# Behavioral and Adversarial Evaluation

Passing unit tests does not establish that an agent followed scope, used
tools safely, or handled hostile content correctly. Packets that use an
agent to make decisions, plan work, call tools, or generate externally
consumed output require an evaluation plan.

## Evaluation suite

Use `templates/evaluation-plan.yaml` to define:

- golden tasks that represent normal work;
- regression tasks for previously observed failures;
- adversarial tasks for prompt injection, tool poisoning, scope expansion,
  unauthorized access, secret exposure, and unsafe output;
- safety cases for cancellation, budget exhaustion, stale locks, and partial
  completion.

Each case has an input reference, expected outcome, prohibited outcomes,
allowed tools, and risk tier. Inputs and outputs follow the evidence privacy
policy.

## Metrics

Measure at least the metrics relevant to the packet:

- task success and acceptance-criterion coverage;
- scope adherence and unauthorized-change count;
- tool-call correctness and approval compliance;
- safety failures and injection escapes;
- quality or reviewer agreement;
- cost, latency, retries, and completion rate.

Metrics need a threshold and a pass/fail/unknown result. A single aggregate
score must not hide a critical safety failure.

## Evaluation gates

1. Pin the agent context, model/provider, tools, policy, and evaluator version.
2. Run golden and relevant adversarial cases before handoff.
3. Investigate every prohibited outcome and threshold failure.
4. Block completion when a safety, authorization, scope, or data-correctness
   threshold fails.
5. Record an explicit user-approved exception with owner, expiry, mitigation,
   and rollback when a non-safety threshold cannot be met.
6. Compare results with the prior suite and retain evidence.

Evaluation is not a substitute for human approval of high-risk actions. A
high score cannot authorize an external effect outside the packet.

## Continuous evaluation

Run the suite on protocol, model, tool, prompt-policy, and adapter changes.
Add a regression case for each confirmed incident or escaped failure. Review
thresholds when the task distribution, risk, or consumer population changes.
Do not silently change a case or threshold to turn a failure into a pass.

## Evaluator independence

The actor that produced the result cannot be the sole evaluator of high-risk
or critical cases. Human, deterministic-rule, model, or hybrid evaluators
must identify their version and limitations. Unknown evaluator output blocks
claims of success.
