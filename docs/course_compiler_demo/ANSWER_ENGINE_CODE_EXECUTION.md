# Bounded Python Code-Execution Engine

`code_execution_python` is a deliberately small Python grading capability. It accepts expressions, variables, conditionals, bounded-by-runtime loops, functions, basic collections and strings, stdout traces, and deterministic function test cases. It reports the actual engine identifier and stable per-case results.

## Security boundary

Source first passes a positive AST allowlist. Attributes, imports, exception machinery, classes, lambdas, decorators, async constructs, reflection, dynamic evaluation, file APIs, and non-allowlisted calls are rejected before execution. Names beginning with `_` are rejected. The callable builtins set contains only deterministic collection, numeric, iteration, conversion, and print helpers.

Accepted code runs in a fresh isolated (`-I -S`) Python subprocess, in a new temporary working directory, with a two-variable environment. The child receives CPU, address-space, file-size, process-count, and descriptor limits; the parent additionally imposes a wall-clock timeout and response-size bound. Captured `print` output has its own byte counter. No student-controlled exception details or stderr are exposed.

This is defense in depth, not an OS sandbox: AST validation is the principal filesystem/network/process barrier. The worker has no file, import, attribute, reflection, network, thread, or process primitives. Deployments needing adversarial multi-tenant isolation should additionally place the worker in a disposable container/VM with kernel-enforced networking and filesystem namespaces. `RLIMIT_NPROC` enforcement varies by operating system and user identity.

## Contract

Answers are source strings or `{"source": "..."}`. Normalization parses, validates, and deterministically unparses source. Independent derivation requires `independently_derived_answer`. Grading contracts contain one to 100 cases, each using only `entrypoint`, `args`, `expected`, and/or `expected_stdout`. Arguments and return values must be JSON-compatible. Unsupported syntax, malformed contracts, timeouts, resource exhaustion, and runtime errors fail closed; there is no fallback engine.

## Independent security audit

The lane audit reviewed the AST-to-worker trust boundary and checked import, file-write, network, process, reflection, dynamic-evaluation, timeout, memory, and output attacks. The allowlist contains no `Attribute`, import, dynamic execution, context manager, exception handler, class, lambda, or async nodes. Calls must target either a declared public function or an explicit safe builtin. The worker’s own `exec`/`compile` are trusted implementation code and cannot be named by student code.

Residual limitations are explicit: the AST policy cannot by itself constrain algorithmic complexity, so subprocess limits remain mandatory; macOS resource semantics are less comprehensive than a Linux namespace/seccomp boundary; and permitted large integer/list computations may terminate by timeout or memory limit rather than static rejection. On that documented boundary, the audit finds the engine suitable for the bounded educational grading contract.
