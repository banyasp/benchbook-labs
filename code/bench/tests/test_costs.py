from bench.costs import call_cost, tokens


def test_bedrock_cache_reads_are_added():
    usd, basis = call_cost("bedrock/us.openai.gpt-6-luna", {"inputTokens": 1000, "outputTokens": 2000, "cacheReadInputTokens": 10000})
    assert basis == "estimate" and abs(usd - (1000 * 0.10 + 10000 * 0.01 + 2000 * 0.50) / 1e6) < 1e-12


def test_openai_style_cached_inside_prompt():
    usd, _ = call_cost("openrouter/openai/gpt-oss-120b", {"prompt_tokens": 1000, "completion_tokens": 100,
                                                          "prompt_tokens_details": {"cached_tokens": 400}})
    assert abs(usd - (600 * 0.15 + 400 * 0.15 + 100 * 0.60) / 1e6) < 1e-12      # no cached price listed: input price


def test_exact_cost_wins_and_local_is_free():
    assert call_cost("openrouter/x", {"cost": 0.0123, "prompt_tokens": 5}) == (0.0123, "exact")
    assert call_cost("vllm/granite-4.2-8b", {"prompt_tokens": 9, "completion_tokens": 9}) == (0.0, "local")
    assert call_cost("bedrock/unknown-model", {"inputTokens": 5})[1] == "unknown"
    assert tokens({"inputTokens": 3, "outputTokens": 4}) == (3, 4, 0)
