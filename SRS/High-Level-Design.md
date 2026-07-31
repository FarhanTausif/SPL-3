[ User Prompt ]
      |
      v
+--------------------------------------------------+
| PHASE 0: PROMPT INTAKE AND NORMALIZATION          |
+--------------------------------------------------+
| - Receive natural-language programming prompt     |
| - Infer language, framework, runtime constraints  |
| - Mark uncertain assumptions                      |
+--------------------------------------------------+
      |
      v
+--------------------------------------------------+
| PHASE 1: LOCAL CODE GENERATION                    |
+--------------------------------------------------+
| [ Local CodeLLM ]                                 |
| - Generate initial code                           |
| - Separate code from explanation                  |
| - Log model metadata                              |
| - Capture entropy / log-prob signals if available |
+--------------------------------------------------+
      |
      v
+--------------------------------------------------+
| PHASE 2: CLAIM EXTRACTION                         |
+--------------------------------------------------+
| Extract checkable claims:                         |
| - imports and packages                            |
| - API calls and parameters                        |
| - symbols, functions, classes                     |
| - runtime assumptions                             |
| - behavioral claims from explanation              |
+--------------------------------------------------+
      |
      v
+--------------------------------------------------+
| PHASE 3: EXECUTION-FREE STATIC DETECTION          |
+--------------------------------------------------+
      |
      +--------------------+--------------------+
      |                    |                    |
      v                    v                    v
+-------------+    +---------------+    +----------------+
| Tree-sitter |    | Semgrep / SAST|    | Symbol Indexer |
| AST Parser  |    | Static Rules  |    | API Validator  |
+-------------+    +---------------+    +----------------+
| Detects:    |    | Detects:      |    | Detects:       |
| - syntax    |    | - unsafe ops  |    | - fake imports |
| - malformed |    | - vuln rules  |    | - invalid APIs |
| - incomplete|    | - code smells |    | - bad refs     |
+-------------+    +---------------+    +----------------+
      |                    |                    |
      +--------------------+--------------------+
                           |
                           v
+--------------------------------------------------+
| PHASE 4: QUANTITATIVE METRIC ENGINE              |
+--------------------------------------------------+
| Calculates:                                      |
| - MiHN: number of invalid micro-level claims      |
| - MaHR: ratio of hallucinated claims              |
| - TR-S: repetition / degeneration score           |
| - Static severity score                           |
| - Entropy/log-prob uncertainty score              |
|                                                  |
| Purpose:                                         |
| - quantify hallucination risk                     |
| - rank severity                                   |
| - compare initial vs repaired output              |
| - provide evidence for policy decision            |
+--------------------------------------------------+
                           |
                           v
+--------------------------------------------------+
| PHASE 5: SEMANTIC JUDGE POOL                     |
+--------------------------------------------------+
      |
      +--------------------+--------------------+
      |                    |                    |
      v                    v                    v
+----------------+  +----------------+  +----------------+
| Judge 1        |  | Judge 2        |  | Judge 3        |
| Requirement    |  | Functional     |  | Quality/Safety |
| Alignment      |  | Logic          |  | Review         |
+----------------+  +----------------+  +----------------+
| Checks:        |  | Checks:        |  | Checks:        |
| - requirement  |  | - logical flow |  | - resource use |
| - task match   |  | - edge cases   |  | - code smell   |
| - assumptions  |  | - behavior     |  | - safety risk  |
+----------------+  +----------------+  +----------------+
      |                    |                    |
      +--------------------+--------------------+
                           |
                           v
+--------------------------------------------------+
| PHASE 6: JUDGE CONSENSUS                         |
+--------------------------------------------------+
| - Aggregate judge verdicts                        |
| - Compute average score                           |
| - Measure agreement level                         |
| - Produce final semantic verdict                  |
+--------------------------------------------------+
                           |
                           v
+--------------------------------------------------+
| PHASE 7: POLICY DECISION GATEWAY                 |
+--------------------------------------------------+
| Inputs:                                           |
| - static findings                                 |
| - symbol/API validation results                   |
| - MiHN, MaHR, TR-S                                |
| - entropy/log-prob signals                        |
| - judge consensus                                 |
| - CoVe claim evidence                             |
|                                                  |
| Decision:                                         |
| - ACCEPT                                          |
| - WARN                                            |
| - REPAIR                                          |
| - REJECT                                          |
+--------------------------------------------------+
                           |
                           v
              Are blocking hallucinations present?
                    /                \
                  NO                  YES
                  |                    |
                  v                    v
+-------------------------+     +-----------------------------+
| VERIFIED / WARNED CODE  |     | PHASE 8: MITIGATION          |
| returned with evidence  |     +-----------------------------+
+-------------------------+     | - Build failure context      |
                                | - Convert errors into facts  |
                                | - Generate CoVe questions    |
                                | - Create repair prompt       |
                                +-----------------------------+
                                             |
                                             v
                                +-----------------------------+
                                | CODE REPAIR AGENT            |
                                +-----------------------------+
                                | - Receives failed code        |
                                | - Receives static evidence    |
                                | - Receives judge feedback     |
                                | - Receives CoVe facts         |
                                | - Produces repaired code      |
                                +-----------------------------+
                                             |
                                             v
                                +-----------------------------+
                                | RETRY CONTROL                 |
                                +-----------------------------+
                                | - Increment attempt_no        |
                                | - Stop if max_retry reached   |
                                +-----------------------------+
                                             |
                                             v
                                [ Loop back to Phase 2:
                                  claim extraction and
                                  static verification again ]

Final output is accepted only after the repaired code passes the verification policy.