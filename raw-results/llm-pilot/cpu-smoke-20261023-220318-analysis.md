# LLM pilot analysis

- stage: smoke
- model: Qwen/Qwen2.5-1.5B-Instruct @ 989aa7980e4cf806f80c7fef2b1adb7bc71aa306
- runtime: {'torch': '2.5.1+cu124', 'transformers': '4.46.3'}
- compute: CPU FALLBACK: not a GPU result
- prompt fingerprint: bbdf4805aa3106b5503f279cd53a7dde7c52d5af99de018827876984c92aeab3
- runs declared: 0, rounds completed: 0, decisions logged: 0, truncated: None

## Output validity

- parse counts: {}
- strict rate: None
- retries: 0, fallbacks: 0 (rate None)
- mean new tokens: None, mean prompt tokens: None
- mean latency per prompt: None ms

## Action behaviour



## Compliance

- seed message followed: 0/0 = None
- by condition: {}
- cue rule followed: 0/0 = None
- recommendation followed (free agents): 0/0 = None

## Mean payoff


## Descriptive influence statistics

30 rounds per run, 3 runs per condition. CMI/net are reported for pipeline sanity only: no threshold, no p-value, no inference at this sample size.

| condition | run | rounds | max cmi | max net | cmi top1 | net top1 | truth |
|---|---|---|---|---|---|---|---|

## Cost estimate

_ESTIMATE from published Modal rates x measured container seconds; not an invoice_

- container_seconds: 61.9
- assumed_physical_cores: 8.0
- cpu_usd: 0.0065
- memory_usd: 0.0044
- total_usd: 0.0109
- rates_used: {'cpu_per_physical_core_s': 1.31e-05, 'memory_per_gib_s': 2.22e-06}
