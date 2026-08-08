# Initial Use Cases

This document records the first classic ML and RAG use cases for the study platform. The template is intentionally shared so later issues can compare data, model, service, safety, and evaluation requirements consistently.

| Area | Use case | Dataset | User | Output | Offline metric and threshold | Service metric and threshold | Safety constraint | Baseline |
|---|---|---|---|---|---|---|---|---|
| Classic ML | Train and serve a small tabular classifier for a local vertical slice. | Open decision: select a small public tabular dataset before issue `00.14`; candidate shape is <=100,000 rows and <=100 columns. | Platform learner validating the end-to-end ML workflow. | JSON prediction with predicted class, class probabilities, model version, and request ID. | Threshold: accuracy >=0.85 on a held-out test split, with the split seed recorded. | Threshold: p95 prediction latency <=100 ms for single-row CPU inference in local development. | Do not use sensitive, regulated, or private user data; reject rows that fail the input schema. | Baseline: majority-class predictor; Threshold: trained model must improve accuracy by >=0.10 absolute over this baseline. |
| RAG | Answer study-platform questions from a small local document corpus with citations. | Open decision: select the first local corpus before issue `09.01`; candidate shape is 20-200 Markdown/PDF/text documents. | Platform learner asking implementation and architecture questions about the project. | Answer text with cited source chunks, abstention flag, retrieval metadata, and trace ID. | Threshold: cited-answer accuracy >=0.75 on a 20-question evaluation set, with unsupported-answer rate <=0.10. | Threshold: p95 answer latency <=5 seconds for a local small-model or stubbed generator path. | Every factual answer must include at least 1 citation; abstain when no retrieved chunk reaches the configured relevance threshold. | Baseline: lexical keyword retrieval with template answer; Threshold: RAG route must improve cited-answer accuracy by >=0.15 absolute over this baseline. |

## Open Decisions

- Classic ML dataset: choose the exact public dataset and record its license, source URL, schema, and target column.
- RAG corpus: choose the exact starter corpus and define the 20-question evaluation set.
- Evaluation ownership: decide who approves the first labeled examples and cited-answer judgments.
