# Topic–Skill–Procedure Generation Recipe Runtime

The shared runtime executes bounded course recipes only when one registered recipe exactly matches the course, topic, micro-skill, procedure, generation family, and actual answer engine. Unknown recipes, aliases, incomplete family declarations, or any identity mismatch fail closed; there is no generic or alternate-engine fallback.

Each recipe declares deterministic parameter domains, at least two domain-semantic terms, operation terms, and the parameters that make its prompt answer-determinate. It supplies four separate operations: candidate answer generation, independent derivation from parameters, prompt construction, and answer-contract construction. Generator and deriver method identities must differ. The runtime never gives the generated answer to the independent deriver.

Parameters derive from SHA-256 over the seed, variant, recipe, position, and parameter name. Recipe domains must fit within the associated family's declared domains. Prompts must name the exact topic and skill titles, include the recipe's domain and operation semantics, expose every determinative parameter, avoid known generic template phrases, and remain bounded in length. These gates prevent course labels from being wrapped around unrelated generic arithmetic.

After construction, the runtime calls the actual universal answer-engine registry for normalization, derivation, and grading. All three operations must pass, the normalized candidate and independently derived answer must serialize identically, and the engine must equal the registered binding. Results record each registry report and use a deterministic content fingerprint over prompt, parameters, normalized answer, and actual engine. Coverage reporting counts engines, families, procedures, micro-skills, questions, and content duplicates.

The runtime is infrastructure, not course content. Course lanes must register one or more semantically truthful recipes for exact catalog bindings. A catalog family without such a binding remains unsupported and cannot produce or lock a candidate.
