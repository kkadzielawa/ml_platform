# Study SLO and Metric Vocabulary

This document defines the measurement vocabulary for study platform experiments. These terms are for local learning and reproducibility; they are not production commitments.

## Objective Types

| Term | Meaning | Example |
|---|---|---|
| SLI | A measured service level indicator. It is the raw measurement or computed metric. | `prediction_latency_ms` measured per request. |
| SLO | A target level for an SLI over a stated window and boundary. | `p95 prediction latency <=100 ms over a local test run`. |
| Alert threshold | A condition that would page, notify, or mark a run unhealthy. | `error rate >5% for 5 minutes`. |
| Experiment target | A study goal used to compare implementations; it may be looser than a production SLO. | `cited-answer accuracy >=0.75 on 20 questions`. |

## Service Terms

| Term | Unit | Boundary | Definition |
|---|---|---|---|
| Availability | Ratio from `0` to `1` or percent | Requests sent to a service endpoint during a measurement window | Successful requests divided by total requests. A successful request returns a valid response before the timeout and does not return a server error. |
| Error rate | Ratio from `0` to `1` or percent | Requests sent to a service endpoint during a measurement window | Failed requests divided by total requests. Failures include server errors, timeouts, malformed responses, and rejected requests that should have been accepted. |
| Latency | Milliseconds or seconds | One request from client send time to full response received | End-to-end elapsed time for a request. Report percentiles such as p50, p95, and p99, not only averages. |
| p95 latency | Milliseconds or seconds | Same as latency | The latency value at or below which 95% of measured requests completed. Phase 0 uses p95 prediction latency and p95 answer latency as service metrics. |
| Saturation | Percent, queue depth, active workers, memory bytes, CPU percent, or GPU memory percent | One service instance, worker pool, node, or local process | How close a resource is to its useful limit. The measured resource and boundary must be named. |
| Throughput | Requests per second, rows per second, documents per second, tokens per second, or bytes per second | A named service, job, or pipeline step during a measurement window | Completed units divided by elapsed time. Failed units are reported separately through error rate. |

## ML and RAG Quality Terms

| Term | Unit | Boundary | Definition |
|---|---|---|---|
| Quality | Metric-specific score | A named evaluation dataset, split, or question set | Model or system correctness for a task. The exact quality metric must be named, such as accuracy or cited-answer accuracy. |
| Accuracy | Ratio from `0` to `1` | A labeled held-out test split | Correct predictions divided by evaluated examples. The split method and seed must be recorded. |
| Baseline improvement | Absolute score delta | Same evaluation boundary as the baseline and candidate | Candidate metric minus baseline metric. Phase 0 classic ML requires trained accuracy to improve by `>=0.10` absolute over the majority-class baseline. |
| Cited-answer accuracy | Ratio from `0` to `1` | A fixed RAG evaluation set | Answers judged correct and supported by citations divided by evaluated questions. A correct answer without required citations is not counted as cited-answer accurate. |
| Unsupported-answer rate | Ratio from `0` to `1` | A fixed RAG evaluation set | Answers that make factual claims not supported by retrieved citations divided by evaluated questions. Phase 0 RAG targets `<=0.10`. |
| Freshness | Seconds, minutes, hours, or age timestamp | A source-to-index or source-to-feature boundary | Age of the data used by a serving path relative to the source of truth. For batch artifacts, record artifact creation time and source snapshot time. |

## LLM Serving Terms

| Term | Unit | Boundary | Definition |
|---|---|---|---|
| TTFT | Milliseconds or seconds | One streaming generation request from client send time to first output token received | Time to first token. Use TTFT for interactive LLM and RAG paths because users perceive it before total response time. |
| Token latency | Milliseconds per token or tokens per second | Output tokens after the first token for one generation request or a batch of requests | Speed of token generation after TTFT. Report whether the value includes only generated tokens or both prompt and generated tokens. |
| End-to-end answer latency | Milliseconds or seconds | One RAG request from client send time to final answer received | Total time across retrieval, optional reranking, generation, citation formatting, and response transfer. Phase 0 RAG uses p95 answer latency `<=5 seconds`. |

## Phase 0 Metric Mapping

| Use case metric | Objective type | Vocabulary term | Unit | Measurement boundary |
|---|---|---|---|---|
| Classic ML accuracy `>=0.85` | Experiment target | Accuracy | Ratio | Held-out tabular test split with recorded seed. |
| Classic ML p95 prediction latency `<=100 ms` | SLO for local study | p95 latency | Milliseconds | Single-row CPU inference request from client send to full JSON response. |
| Classic ML majority-class baseline improvement `>=0.10` | Experiment target | Baseline improvement | Absolute accuracy delta | Same held-out split used for trained model accuracy. |
| RAG cited-answer accuracy `>=0.75` | Experiment target | Cited-answer accuracy | Ratio | Fixed 20-question RAG evaluation set. |
| RAG unsupported-answer rate `<=0.10` | Experiment target | Unsupported-answer rate | Ratio | Same fixed 20-question RAG evaluation set. |
| RAG p95 answer latency `<=5 seconds` | SLO for local study | End-to-end answer latency | Seconds | One local RAG request from client send to final cited answer. |
| RAG citation requirement `>=1 citation` | Safety constraint | Cited-answer accuracy and unsupported-answer rate | Count and ratio | Every factual answer must include at least one supporting citation. |

## Reporting Rules

- Always state the objective type: SLI, SLO, alert threshold, or experiment target.
- Always state the unit and measurement boundary.
- Prefer percentiles for latency and saturation-sensitive paths.
- Keep offline quality metrics separate from online service metrics.
- Do not compare a candidate to a baseline unless both use the same evaluation boundary.
- For local study runs, record hardware assumptions when latency, throughput, TTFT, token latency, or saturation is reported.
