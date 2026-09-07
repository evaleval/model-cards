"""Model source bundle: the composer's replay layout, offline, with tiered paper binding."""

import json

import pytest

from model_cards.core import model_sources as MS


REV = "7df9a82518afdecae4e8c026b27adccc8c1f0032"


def _hf(tags=("arxiv:2501.00656", "license:apache-2.0"), readme="# OLMo 2\nSee https://github.com/allenai/OLMo\n"):
    return {"id": "allenai/OLMo-2-1124-7B", "sha": REV, "tags": list(tags), "readme_markdown": readme,
            "config": {"architectures": ["Olmo2ForCausalLM"]}, "card_data": {"license": "apache-2.0"},
            "downloads": 10, "resolved_revision": REV, "base_model_tags": [], "model_index": None}


def test_slug_and_name_tokens():
    assert MS.slug_for(f"allenai/OLMo-2-1124-7B@{REV}") == "allenai-olmo-2-1124-7b-7df9a82518af"
    assert MS.distinctive_name_tokens("allenai/OLMo-2-1124-7B") == {"olmo"}
    assert MS.distinctive_name_tokens("meta-llama/Llama-3.1-8B-Instruct") == {"llama"}
    assert MS.distinctive_name_tokens("Qwen/Qwen3-8B-Base") == {"qwen3"}


def test_paper_binding_tiers():
    assert MS.paper_binding_tier("allenai/OLMo-2-1124-7B", "2 OLMo 2 Furious", "we present OLMo 2") == "introduces_target"
    assert MS.paper_binding_tier("meta-llama/Llama-3.1-8B-Instruct", "The Llama 3 Herd of Models", "") == "introduces_target"
    assert MS.paper_binding_tier("Qwen/Qwen3-8B-Base", "Qwen3 Technical Report", "") == "introduces_target"
    # a fine-tune carrying its base's paper: the family reference tier (its own
    # distinctive tokens are absent from the title, the family token is present)
    assert MS.paper_binding_tier("acme/Llama-3.1-8B-Instruct-Finetune-Med", "The Llama 3 Herd of Models", "") == "family_reference"
    assert MS.paper_binding_tier("allenai/Llama-3.1-Tulu-3-8B", "The Llama 3 Herd of Models", "") == "family_reference"
    # the declared base's family counts as family too
    assert MS.paper_binding_tier("acme/MedTune-8B", "The Llama 3 Herd of Models", "",
                                 ["meta-llama/Llama-3.1-8B"]) == "family_reference"
    # wrong Hub tags seen live on the roster: no family token anywhere, dropped
    assert MS.paper_binding_tier("Qwen/Qwen3-8B", "YaRN: Efficient Context Window Extension of Large Language Models",
                                 "we present YaRN", ["Qwen/Qwen3-8B-Base"]) == "unrelated_tag"
    assert MS.paper_binding_tier("google/gemma-3-4b-it", "HellaSwag: Can a Machine Really Finish Your Sentence?",
                                 "", ["google/gemma-3-4b-pt"]) == "unrelated_tag"
    assert MS.paper_binding_tier("meta-llama/Llama-3.1-8B", "The Carbon Footprint of Machine Learning Training Will Plateau, Then Shrink",
                                 "") == "unrelated_tag"


def test_unrelated_tag_is_dropped_unread_and_stale_docling_removed(tmp_path, monkeypatch):
    class _Adapter:
        def __init__(self, allow_network=True):
            pass

        def collect(self, target, model_info=None):
            raise MS.ModelSourceError("offline")

    monkeypatch.setattr(MS, "HfModelSourceAdapter", _Adapter)
    hf = _hf(tags=("arxiv:2309.00071", "license:apache-2.0"), readme="# Qwen3-8B\nhttps://github.com/QwenLM/Qwen3\n")
    hf["id"] = "Qwen/Qwen3-8B"
    hf["base_model_tags"] = ["Qwen/Qwen3-8B-Base", "finetune:Qwen/Qwen3-8B-Base"]
    slug = MS.slug_for(f"Qwen/Qwen3-8B@{REV}")
    stale = tmp_path / slug / "tool_output" / "docling"
    stale.mkdir(parents=True)
    (stale / f"{slug}.json").write_text("{}")
    manifest = MS.collect_model_bundle(
        f"Qwen/Qwen3-8B@{REV}", tmp_path, hf_metadata=lambda m, r: hf,
        paper_meta=lambda u: {"title": "YaRN: Efficient Context Window Extension of Large Language Models",
                              "abstract": "Rotary Position Embeddings...", "fetch_error": False},
        docling=lambda u: pytest.fail("an unrelated tag must never reach docling"),
        github=lambda *t: {"success": True, "text": "# Qwen3", "url": "https://github.com/QwenLM/Qwen3"},
        eee_datastore=str(tmp_path / "empty"))
    sidecar = json.load(open(tmp_path / slug / "tool_output" / "paper_resolver" / "paper-verification.json"))
    assert sidecar["resolved_url"] is None
    assert sidecar["binding"] == {"tier": "unrelated_tag", "verdict": "dropped",
                                  "paper_url": "https://arxiv.org/abs/2309.00071",
                                  "reason": "no family token in title or abstract", "fetch_error": False}
    assert not (stale / f"{slug}.json").exists()
    assert manifest["channels"]["paper"]["verdict"] == "dropped"
    # the manifest names every absent channel and why, instead of leaving the key out
    assert manifest["channels"]["docling"] == {
        "error": "no paper bound", "reason": "no family token in title or abstract"}
    assert "docling" in manifest["absent_channels"] and "paper" in manifest["absent_channels"]


def test_collect_writes_the_replay_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(MS, "HfModelSourceAdapter", None)  # snapshot path not exercised here
    calls = {}

    def hf_metadata(mid, rev):
        calls["hf"] = (mid, rev)
        return _hf()

    def paper_meta(url):
        calls["paper"] = url
        return {"title": "2 OLMo 2 Furious", "abstract": "We present OLMo 2.", "fetch_error": False}

    def docling(url):
        return {"success": True, "filtered_text": "OLMo 2 was trained on 4T tokens.", "metadata": {"title": "2 OLMo 2 Furious"}}

    def github(*texts):
        return {"success": True, "text": "# OLMo repo", "url": "https://github.com/allenai/OLMo"}

    class _Adapter:
        def __init__(self, allow_network=True):
            pass

        def collect(self, target, model_info=None):
            raise MS.ModelSourceError("offline test: no snapshot")

    monkeypatch.setattr(MS, "HfModelSourceAdapter", _Adapter)
    eee = tmp_path / "eee" / "hfopenllm_v2" / "allenai" / "OLMo-2-1124-7B"
    eee.mkdir(parents=True)
    (eee / "u.json").write_text(json.dumps({"model_info": {"id": "allenai/OLMo-2-1124-7B"},
                                            "evaluation_results": [{"evaluation_name": "MMLU",
                                                                    "metric_config": {"metric_name": "Accuracy"},
                                                                    "score_details": {"score": 0.61}}]}))
    manifest = MS.collect_model_bundle(f"allenai/OLMo-2-1124-7B@{REV}", tmp_path / "bundle",
                                       hf_metadata=hf_metadata, paper_meta=paper_meta, docling=docling,
                                       github=github, eee_datastore=str(tmp_path / "eee"))
    slug = "allenai-olmo-2-1124-7b-7df9a82518af"
    root = tmp_path / "bundle" / slug / "tool_output"
    assert calls["hf"] == ("allenai/OLMo-2-1124-7B", REV)
    assert calls["paper"] == "https://arxiv.org/abs/2501.00656"
    assert json.load(open(root / "hf" / f"{slug}.json"))["id"] == "allenai/OLMo-2-1124-7B"
    sidecar = json.load(open(root / "paper_resolver" / "paper-verification.json"))
    assert sidecar["resolved_url"] == "https://arxiv.org/abs/2501.00656"
    assert sidecar["binding"]["tier"] == "introduces_target"
    assert json.load(open(root / "docling" / f"{slug}.json"))["success"] is True
    assert json.load(open(root / "github" / f"{slug}.json"))["url"] == "https://github.com/allenai/OLMo"
    eee_out = json.load(open(root / "eee" / f"{slug}.json"))
    assert eee_out["tier"] == "exact" and eee_out["benchmarks"]["hfopenllm_v2"][0]["score"] == 0.61
    assert manifest["channels"]["paper"]["tier"] == "introduces_target"
    assert manifest["channels"]["source_bundle"]["error"].startswith("offline test")
    assert manifest["channels"]["eee"]["benchmarks"] == ["hfopenllm_v2"]


def test_collect_without_paper_or_repo(tmp_path, monkeypatch):
    class _Adapter:
        def __init__(self, allow_network=True):
            pass

        def collect(self, target, model_info=None):
            raise MS.ModelSourceError("offline")

    monkeypatch.setattr(MS, "HfModelSourceAdapter", _Adapter)
    manifest = MS.collect_model_bundle(
        f"acme/NoPaper-1B@{REV}", tmp_path, hf_metadata=lambda m, r: _hf(tags=("license:mit",), readme="# nothing"),
        paper_meta=lambda u: pytest.fail("no paper to fetch"), docling=lambda u: pytest.fail("no docling"),
        github=lambda *t: {"success": False, "url": ""}, eee_datastore=str(tmp_path / "empty"))
    root = tmp_path / manifest["slug"] / "tool_output"
    assert json.load(open(root / "paper_resolver" / "paper-verification.json"))["resolved_url"] is None
    assert not (root / "docling").exists() and not (root / "github").exists()
    assert manifest["channels"]["eee"]["tier"] == "none"


def test_paper_reached_through_the_declared_base_tag_behind_the_title_gate(tmp_path, monkeypatch):
    class _Adapter:
        def __init__(self, allow_network=True):
            pass

        def collect(self, target, model_info=None):
            raise MS.ModelSourceError("offline")

    monkeypatch.setattr(MS, "HfModelSourceAdapter", _Adapter)
    own = _hf(tags=("arxiv:2309.00071",), readme="# Qwen3-8B\n")
    own["id"] = "Qwen/Qwen3-8B"
    own["base_model_tags"] = ["Qwen/Qwen3-8B-Base", "finetune:Qwen/Qwen3-8B-Base"]
    base = _hf(tags=("arxiv:2505.09388",), readme="# Qwen3-8B-Base\n")
    seen = []

    def hf_metadata(mid, rev):
        seen.append((mid, rev))
        return own if mid == "Qwen/Qwen3-8B" else base

    papers = {"https://arxiv.org/abs/2309.00071": {"title": "YaRN: Efficient Context Window Extension of Large Language Models", "abstract": "", "fetch_error": False},
              "https://arxiv.org/abs/2505.09388": {"title": "Qwen3 Technical Report", "abstract": "we present Qwen3", "fetch_error": False}}
    docled = []
    manifest = MS.collect_model_bundle(
        f"Qwen/Qwen3-8B@{REV}", tmp_path, hf_metadata=hf_metadata, paper_meta=lambda u: papers[u],
        docling=lambda u: (docled.append(u), {"success": True, "filtered_text": "Qwen3 text", "metadata": {}})[1],
        github=lambda *t: {"success": False, "url": ""}, eee_datastore=str(tmp_path / "empty"))
    # the base was looked up once (the duplicate kind-qualified tag collapses), at main
    assert seen == [("Qwen/Qwen3-8B", REV), ("Qwen/Qwen3-8B-Base", "main")]
    sidecar = json.load(open(tmp_path / manifest["slug"] / "tool_output" / "paper_resolver" / "paper-verification.json"))
    assert sidecar["resolved_url"] == "https://arxiv.org/abs/2505.09388"
    assert sidecar["resolved_from"] == "base_model:hf_arxiv_tag:Qwen/Qwen3-8B-Base"
    assert sidecar["binding"]["tier"] == "introduces_target" and sidecar["binding"]["via_base_model"] == "Qwen/Qwen3-8B-Base"
    # every candidate that was tried stays visible, own tag first
    own = sidecar["candidates"][0]
    assert own["arxiv_id"] == "2309.00071" and own["from"] == "hf_arxiv_tag" and own["tier"] == "unrelated_tag"
    assert docled == ["https://arxiv.org/abs/2505.09388"]
    assert manifest["channels"]["docling"] == {"chars": len("Qwen3 text")}


def test_github_repo_must_be_the_developers_own():
    # the OLMo-2 README links huggingface/transformers first; that is not the model's repo
    assert MS.github_repo_is_own("allenai/OLMo-2-1124-7B", "https://github.com/huggingface/transformers") is False
    assert MS.github_repo_is_own("allenai/OLMo-2-1124-7B", "https://github.com/allenai/OLMo-core") is True
    assert MS.github_repo_is_own("Qwen/Qwen3-8B", "https://github.com/QwenLM/Qwen3") is True   # family token
    assert MS.github_repo_is_own("acme/MedTune-8B", "https://github.com/huggingface/peft") is False
    assert MS.github_repo_is_own("meta-llama/Llama-3.1-8B", "https://github.com/meta-llama/llama-models") is True
    assert MS.github_repo_is_own("mistralai/Mistral-7B-v0.3", "https://github.com/mistralai/mistral-inference") is True
    # seen live on the roster: an own-org repo of another generation, and a
    # google-owned dataset repo; neither is this model's code
    assert MS.github_repo_is_own("deepseek-ai/DeepSeek-V3", "https://github.com/deepseek-ai/DeepSeek-V2") is False
    assert MS.github_repo_is_own("deepseek-ai/DeepSeek-V3", "https://github.com/deepseek-ai/DeepSeek-V3") is True
    assert MS.github_repo_is_own("google/gemma-3-4b-pt", "https://github.com/google-research-datasets/natural-questions") is False
    assert MS.github_repo_is_own("Qwen/Qwen3-8B", "https://github.com/QwenLM/Qwen2.5") is False


def test_family_version_markers():
    assert MS.family_version("Qwen3-8B-Base") == "3"
    assert MS.family_version("Llama-3.1-8B-Instruct") == "3.1"
    assert MS.family_version("DeepSeek-V3-Base") == "3"
    assert MS.family_version("OLMo-2-1124-7B") == "2"
    assert MS.family_version("gemma-3-4b-it") == "3"
    assert MS.family_version("mistral-inference") is None
    assert MS.family_version("llama-models") is None
    assert MS.family_version("Mistral-7B-v0.3") is None   # the release marker after the size is not a generation


def test_own_github_candidates_prefer_the_target_repo_over_an_earlier_sibling_link():
    readme = ("Built on https://github.com/deepseek-ai/DeepSeek-V2 ideas. Code: "
              "https://github.com/deepseek-ai/DeepSeek-V3. Runs with https://github.com/vllm-project/vllm")
    assert MS.own_github_candidates("deepseek-ai/DeepSeek-V3", None, readme) == ["https://github.com/deepseek-ai/DeepSeek-V3"]
    two = MS.own_github_candidates("Qwen/Qwen3-8B", "https://github.com/QwenLM/Qwen3-Coder", "see https://github.com/QwenLM/Qwen3")
    assert two[0] == "https://github.com/QwenLM/Qwen3"


# --- WP1 channels: BibTeX and link harvesting, HTML pages, extras, docling cache -----


def test_bibtex_and_link_harvesting_orders_candidates_by_authority():
    """Failure class: paper_only_reachable_via_a_wrong_tag. The Hub tag is sometimes the
    wrong paper while the BibTeX right below it is correct, and some repos carry no tag
    at all and only a citation block."""
    readme = (
        "# Qwen3-8B\n"
        "Read the [blog](https://qwenlm.github.io/blog/qwen3/) and the "
        "[report](https://arxiv.org/abs/2505.09388).\n"
        "```bibtex\n@misc{qwen3technicalreport,\n  title={Qwen3 Technical Report},\n"
        "  eprint={2505.09388},\n  archivePrefix={arXiv}\n}\n```\n"
    )
    hf = {"tags": ["arxiv:2309.00071"], "readme_markdown": readme}
    cands = MS.arxiv_candidates(hf)
    assert [c["arxiv_id"] for c in cands] == ["2309.00071", "2505.09388"]
    assert cands[0]["from"] == "hf_arxiv_tag" and cands[1]["from"] == "readme_bibtex"
    # a repo with no tag at all still reaches its paper through the citation block
    assert MS.arxiv_candidates({"tags": [], "readme_markdown": readme})[0] == {
        "arxiv_id": "2505.09388", "from": "readme_bibtex"}
    assert len(MS.readme_bibtex_blocks(readme)) == 1


def test_a_wrong_tag_is_overridden_by_the_readme_bibtex(tmp_path, monkeypatch):
    """Failure class: paper_only_reachable_via_a_wrong_tag (end to end)."""
    monkeypatch.setattr(MS, "HfModelSourceAdapter", _OfflineAdapter)
    hf = _hf(tags=("arxiv:2309.00071",),
             readme="# Qwen3-8B\n```bibtex\n@misc{q,\n eprint={2505.09388}\n}\n```\n")
    hf["id"] = "Qwen/Qwen3-8B"
    papers = {"https://arxiv.org/abs/2309.00071": {"title": "YaRN: Efficient Context Window Extension",
                                                   "abstract": "we present YaRN"},
              "https://arxiv.org/abs/2505.09388": {"title": "Qwen3 Technical Report",
                                                   "abstract": "we present Qwen3"}}
    manifest = MS.collect_model_bundle(
        f"Qwen/Qwen3-8B@{REV}", tmp_path, hf_metadata=lambda m, r: hf,
        paper_meta=lambda u: papers[u],
        docling=lambda u: {"success": True, "filtered_text": "Qwen3 text"},
        github=lambda *t: {"success": False, "url": ""}, html=lambda u: {"success": False},
        eee_datastore=str(tmp_path / "empty"), allow_network=False)
    sidecar = json.load(open(tmp_path / manifest["slug"] / "tool_output" /
                             "paper_resolver" / "paper-verification.json"))
    assert sidecar["resolved_url"] == "https://arxiv.org/abs/2505.09388"
    assert sidecar["resolved_from"] == "readme_bibtex"
    assert [c["tier"] for c in sidecar["candidates"]] == ["unrelated_tag", "introduces_target"]


class _OfflineAdapter:
    def __init__(self, allow_network=True):
        pass

    def collect(self, target, model_info=None):
        raise MS.ModelSourceError("offline")


def test_html_candidates_take_developer_documents_only():
    """Failure class: html_channel_reads_a_random_page. A README links licences, hubs,
    social accounts and third-party tooling; only a developer document is a source."""
    hf = {"author": "allenai", "readme_markdown": (
        "# OLMo-2\n"
        "[blog](https://allenai.org/blog/olmo2)\n"
        "[license](https://www.apache.org/licenses/LICENSE-2.0)\n"
        "[demo](https://huggingface.co/spaces/allenai/OLMo-2-Demo)\n"
        "[code](https://github.com/allenai/OLMo)\n"
        "[twitter](https://x.com/allen_ai/status/1)\n"
        "[unrelated](https://example.com/blog/other-thing)\n"
        "[paper](https://arxiv.org/abs/2501.00656)\n")}
    assert MS.readme_html_candidates("allenai/OLMo-2-1124-7B", hf) == [
        "https://allenai.org/blog/olmo2"]
    # a gated README that links only the licence contributes nothing
    assert MS.readme_html_candidates("meta-llama/Llama-3.1-8B", {
        "author": "meta-llama",
        "readme_markdown": "[LICENSE](https://www.llama.com/llama3_1/license/)\n"}) == []


def test_absent_channels_carry_a_reason_each(tmp_path, monkeypatch):
    """Failure class: silent_absent_channel. A missing channel must say why, or a
    README-only card is indistinguishable from a collection failure."""
    monkeypatch.setattr(MS, "HfModelSourceAdapter", _OfflineAdapter)
    hf = _hf(tags=("license:apache-2.0",), readme="# Thing\nnothing here.\n")
    hf["id"] = "acme/Thing-7B"
    manifest = MS.collect_model_bundle(
        f"acme/Thing-7B@{REV}", tmp_path, hf_metadata=lambda m, r: hf,
        paper_meta=lambda u: {}, docling=lambda u: pytest.fail("no paper must reach docling"),
        github=lambda *t: {"success": False, "url": ""}, html=lambda u: {"success": False},
        eee_datastore=str(tmp_path / "empty"), allow_network=False)
    assert set(manifest["absent_channels"]) >= {"docling", "eee", "github", "html", "paper"}
    for name in ("docling", "eee", "github", "html", "paper"):
        entry = manifest["channels"][name]
        assert entry.get("reason") or entry.get("error"), f"{name} is absent without a reason"
    assert manifest["channels"]["paper"]["reason"].startswith("no arXiv id")
    assert manifest["channels"]["html"]["reason"] == "no README link is a developer document page"


def test_docling_text_is_cached_per_arxiv_id(tmp_path, monkeypatch):
    """Failure class: paper_re_extracted_per_target. A base and its instruct variant bind
    the same report; extracting it twice is minutes of the batch for identical bytes."""
    monkeypatch.setattr(MS, "HfModelSourceAdapter", _OfflineAdapter)
    calls = []

    def _docling(url):
        calls.append(url)
        return {"success": True, "filtered_text": "OLMo 2 paper text"}

    common = dict(hf_metadata=lambda m, r: _hf(),
                  paper_meta=lambda u: {"title": "2 OLMo 2 Furious", "abstract": "we present OLMo 2"},
                  docling=_docling, github=lambda *t: {"success": False, "url": ""},
                  html=lambda u: {"success": False}, eee_datastore=str(tmp_path / "empty"),
                  allow_network=False)
    first = MS.collect_model_bundle(f"allenai/OLMo-2-1124-7B@{REV}", tmp_path, **common)
    second = MS.collect_model_bundle(f"allenai/OLMo-2-1124-7B-Instruct@{'b' * 40}", tmp_path, **common)
    assert calls == ["https://arxiv.org/abs/2501.00656"], "the paper was extracted twice"
    assert first["channels"]["docling_cache"] == "miss"
    assert second["channels"]["docling_cache"] == "hit"
    assert second["channels"]["docling"] == {"chars": len("OLMo 2 paper text")}


def test_extras_channel_carries_bytes_frontmatter_and_bibtex(tmp_path, monkeypatch):
    """Failure class: model_size_and_model_index_unavailable. model_info returns no file
    sizes unless asked, and card_data comes back empty for model repos, so the
    model-index lives only in the README frontmatter."""
    monkeypatch.setattr(MS, "HfModelSourceAdapter", _OfflineAdapter)
    monkeypatch.setattr(MS, "safetensors_bytes", lambda mid, rev: 16_069_397_968)
    readme = ("---\nlicense: apache-2.0\nmodel-index:\n- name: Thing-7B\n  results: []\n---\n"
              "# Thing-7B\n```bibtex\n@misc{t,\n title={Thing}\n}\n```\n")
    hf = _hf(tags=("license:apache-2.0",), readme=readme)
    hf["id"] = "acme/Thing-7B"
    manifest = MS.collect_model_bundle(
        f"acme/Thing-7B@{REV}", tmp_path, hf_metadata=lambda m, r: hf, paper_meta=lambda u: {},
        docling=lambda u: {"success": False}, github=lambda *t: {"success": False, "url": ""},
        html=lambda u: {"success": False}, eee_datastore=str(tmp_path / "empty"))
    extras = json.load(open(tmp_path / manifest["slug"] / "tool_output" / "extras" /
                            f"{manifest['slug']}.json"))
    assert extras["safetensors_bytes"] == 16_069_397_968
    assert extras["readme_frontmatter"]["license"] == "apache-2.0"
    assert extras["model_index_from_frontmatter"][0]["name"] == "Thing-7B"
    assert len(extras["bibtex_blocks"]) == 1
    assert manifest["channels"]["extras"]["model_index"] == "readme_frontmatter"


def test_a_benchmark_paper_that_merely_evaluates_the_family_is_not_the_tech_report():
    """Failure class: benchmark_paper_tagged_as_the_tech_report. google/gemma-3-4b-pt and
    -it published https://arxiv.org/abs/2404.16816 as links.tech_report. That is
    IndicGenBench, whose abstract reads "we evaluate a wide range of proprietary and
    open-source LLMs including gpt-3.5, gpt-4, palm-2, mt5, gemma, bloom and llama". The
    single word "gemma" satisfied "every distinctive name token is present", and the
    resolver recorded the title and kept it anyway (seen 2026-09-05). The same abstract
    exposed meta-llama/Llama-3.1-8B through the word "llama"."""
    from model_cards.core.model_sources import name_discriminators, paper_binding_tier

    indic_title = ("IndicGenBench: A Multilingual Benchmark to Evaluate Generation "
                   "Capabilities of LLMs on Indic Languages")
    indic_abstract = ("we evaluate a wide range of proprietary and open-source llms "
                      "including gpt-3.5, gpt-4, palm-2, mt5, gemma, bloom and llama "
                      "on indicgenbench in a variety of settings")
    assert paper_binding_tier("google/gemma-3-4b-pt", indic_title, indic_abstract) \
        == "family_reference"
    assert paper_binding_tier("meta-llama/Llama-3.1-8B", indic_title, indic_abstract) \
        == "family_reference"

    # the real reports still bind, including the two shapes that motivated the rule
    assert paper_binding_tier(
        "google/gemma-3-4b-pt", "Gemma 3 Technical Report",
        "We introduce Gemma 3, a multimodal addition to the Gemma family.") == "introduces_target"
    assert paper_binding_tier(
        "Qwen/Qwen3-8B-Base", "Qwen3 Technical Report",
        "We present Qwen3, the latest version of the Qwen model family.") == "introduces_target"
    assert paper_binding_tier(
        "allenai/OLMo-2-1124-7B", "2 OLMo 2 Furious",
        "We present OLMo 2, a family of fully open language models.") == "introduces_target"
    # the herd paper introduces Llama 3.1 under the shorter version form
    assert paper_binding_tier(
        "meta-llama/Llama-3.1-8B", "The Llama 3 Herd of Models",
        "This paper presents a new set of foundation models, Llama 3.") == "introduces_target"
    # an unrelated tag is still unrelated
    assert paper_binding_tier(
        "Qwen/Qwen3-8B", "YaRN: Efficient Context Window Extension of Large Language Models",
        "We present YaRN, a compute-efficient method.") == "unrelated_tag"

    assert "gemma 3" in name_discriminators("google/gemma-3-4b-pt")
    # the repo-name splitter treats the dot as a separator, so Llama-3.1-8B discriminates
    # on "llama 3", which is what both the herd paper and the IndicGenBench case need
    assert "llama 3" in name_discriminators("meta-llama/Llama-3.1-8B")
    assert "llama" not in name_discriminators("meta-llama/Llama-3.1-8B")


def test_two_weight_formats_in_one_repo_are_not_added_together():
    """Failure class: duplicate_weight_format_double_counts_size.
    mistralai/Mistral-7B-v0.3 ships consolidated.safetensors (14,496,078,512 B) next to
    model-0000n-of-00003.safetensors (14,496,080,928 B together): the same weights in two
    packagings. Summing both published "27.0 GiB ... in BF16" for a 7B model, exactly
    double, on both Mistral cards of 2026-09-05."""
    from model_cards.core import model_sources as MS

    class _Sib:
        def __init__(self, rfilename, size):
            self.rfilename, self.size = rfilename, size

    class _Info:
        def __init__(self, siblings):
            self.siblings = siblings

    class _Api:
        def __init__(self, siblings):
            self._siblings = siblings

        def model_info(self, *args, **kwargs):
            return _Info(self._siblings)

    def total_for(siblings, monkeypatch_target=MS):
        import huggingface_hub

        original = huggingface_hub.HfApi
        huggingface_hub.HfApi = lambda *a, **k: _Api(siblings)
        try:
            return MS.safetensors_bytes("x/y", "r")
        finally:
            huggingface_hub.HfApi = original

    both = [_Sib("consolidated.safetensors", 14_496_078_512),
            _Sib("model-00001-of-00003.safetensors", 4_949_453_792),
            _Sib("model-00002-of-00003.safetensors", 4_999_819_336),
            _Sib("model-00003-of-00003.safetensors", 4_546_807_800)]
    assert total_for(both) == 14_496_080_928  # the shards, not the 28,992,159,440 sum

    assert total_for([_Sib("model.safetensors", 5_000)]) == 5_000
    assert total_for([_Sib("consolidated.safetensors", 7_000)]) == 7_000
    assert total_for([_Sib("config.json", 10)]) is None


def test_a_size_that_cannot_be_that_many_parameters_is_not_published():
    """Failure class: duplicate_weight_format_double_counts_size. The collector picks one
    packaging now; this is the arithmetic backstop for a repo shaped some other way."""
    from model_cards.core.compose_llm import _size_contradicts_precision as contradicts

    assert contradicts(28_992_159_440, 7_248_023_552, "BF16")
    assert not contradicts(14_496_080_928, 7_248_023_552, "BF16")
    assert not contradicts(29_194_510_544, 7_298_716_672, "F32")
    assert not contradicts(10 ** 12, 7_000_000_000, None)
    assert not contradicts(5_000, None, "BF16")


def test_a_failed_paper_fetch_is_retried_and_never_tiered_as_unrelated(tmp_path, monkeypatch):
    """Failure class: fetch_error_tiered_as_unrelated_tag. arXiv rate-limited the fresh
    collect of 2026-09-06; the resolver tiered every empty title as unrelated_tag and
    silently dropped the paper channel from 126 of 247 bundles, DeepSeek-V3's technical
    report among them. A fetch that fails after retries is recorded as fetch_failed and
    the binding says unresolved, so a re-collect knows what to redo."""
    from model_cards.core import model_sources as MS

    monkeypatch.setattr(MS, "PAPER_FETCH_BACKOFF_S", 0.0)

    class _Adapter:
        def __init__(self, allow_network=True):
            pass

        def collect(self, target, model_info=None):
            raise MS.ModelSourceError("offline test: no snapshot")

    monkeypatch.setattr(MS, "HfModelSourceAdapter", _Adapter)
    hf = {"id": "deepseek-ai/DeepSeek-V3", "sha": REV, "tags": ["arxiv:2412.19437"],
          "readme_markdown": "", "base_model_tags": [], "model_index": None, "card_data": {}}
    calls = []

    def flaky(url):
        calls.append(url)
        if len(calls) < 3:
            return {"fetch_error": True, "title": "", "abstract": ""}
        return {"title": "DeepSeek-V3 Technical Report", "abstract": "We present DeepSeek-V3."}

    MS.collect_model_bundle(f"deepseek-ai/DeepSeek-V3@{REV}", tmp_path / "a",
                            hf_metadata=lambda m, r: hf, paper_meta=flaky,
                            docling=lambda url: {"success": True, "filtered_text": "DeepSeek-V3 Technical Report"},
                            github=lambda *a, **k: None, allow_network=False)
    slug = "deepseek-ai-deepseek-v3-" + REV[:12]
    sidecar = json.load(open(tmp_path / "a" / slug / "tool_output" / "paper_resolver" / "paper-verification.json"))
    assert sidecar["binding"]["tier"] == "introduces_target"
    assert len(calls) == 3

    MS.collect_model_bundle(f"deepseek-ai/DeepSeek-V3@{REV}", tmp_path / "b",
                            hf_metadata=lambda m, r: hf,
                            paper_meta=lambda url: {"fetch_error": True, "title": "", "abstract": ""},
                            docling=lambda url: {"success": False}, github=lambda *a, **k: None,
                            allow_network=False)
    sidecar = json.load(open(tmp_path / "b" / slug / "tool_output" / "paper_resolver" / "paper-verification.json"))
    assert sidecar["binding"] == {"tier": "fetch_failed", "verdict": "unresolved",
                                  "paper_url": "https://arxiv.org/abs/2412.19437",
                                  "reason": "paper metadata could not be fetched; re-collect to resolve",
                                  "fetch_error": True}
    assert sidecar["candidates"][0]["tier"] == "fetch_failed"


# The paper search trap set ------------------------------------------------------------
# Recorded search responses, one row per trap of the 2026-09-07 test plan. A search hit
# reaches a card only through search_title_gate AND paper_binding_tier, so every trap
# states the tier its paper must end at. Nothing here touches the network.

_TRAPS = [
    # (model_id, base_model_tags, search hit title, the arXiv title, tier the row must get)
    ("google/gemma-2-9b", [], "Gemma 2: Improving Open Language Models at a Practical Size",
     "Gemma 2: Improving Open Language Models at a Practical Size",
     "In this work we introduce Gemma 2, a new addition to the Gemma family.", "introduces_target"),
    # the plan expected family_reference here; the live check of 2026-09-07 showed the
    # class costs more than it earns (the 2023 LLaMA paper reached Llama-3.1-8B the same
    # way), so a SEARCHED title that states no generation is refused for a checkpoint
    # whose name states one. A developer's own tag pointing at the v1 paper still binds.
    ("google/gemma-2-9b", [], "Gemma: Open Models Based on Gemini Research and Technology",
     "Gemma: Open Models Based on Gemini Research and Technology",
     "This work introduces Gemma, a family of lightweight open models.", "gated_out"),
    ("google/gemma-2-9b", [], "IndicGenBench: A Multilingual Benchmark",
     "IndicGenBench: A Multilingual Benchmark",
     "We evaluate mT5, Gemma, BLOOM and LLaMA on Indic languages.", "gated_out"),
    # the herd paper names this checkpoint's own discriminator ("Llama 3"), which is the
    # form the paper itself uses, so it tiers exactly as it does when a tag points at it
    ("meta-llama/Llama-3.2-3B", [], "The Llama 3 Herd of Models", "The Llama 3 Herd of Models",
     "Modern artificial intelligence systems are powered by foundation models.",
     "introduces_target"),
    ("meta-llama/Llama-3.2-3B", [], "Llama 2: Open Foundation and Fine-Tuned Chat Models",
     "Llama 2: Open Foundation and Fine-Tuned Chat Models",
     "In this work, we develop and release Llama 2.", "gated_out"),
    ("meta-llama/Llama-3.2-3B", [], "LLaMA-Adapter: Efficient Fine-tuning of Language Models",
     "LLaMA-Adapter: Efficient Fine-tuning of Language Models",
     "We present LLaMA-Adapter, a lightweight adaption method.", "gated_out"),
    ("Qwen/Qwen1.5-7B-Chat", [], "Qwen2 Technical Report", "Qwen2 Technical Report",
     "This report introduces the Qwen2 series.", "gated_out"),
    ("Qwen/Qwen1.5-7B-Chat", [], "Qwen-VL: A Versatile Vision-Language Model",
     "Qwen-VL: A Versatile Vision-Language Model",
     "We introduce the Qwen-VL series.", "gated_out"),
    ("01-ai/Yi-1.5-9B", [], "Yi: Open Foundation Models by 01.AI", "Yi: Open Foundation Models by 01.AI",
     "We introduce the Yi model family.", "gated_out"),
    ("Nexesenex/Llama_3.2_3b_Kermes_v2.1", ["meta-llama/Llama-3.2-3B"],
     "The Llama 3 Herd of Models", "The Llama 3 Herd of Models",
     "Modern artificial intelligence systems are powered by foundation models.",
     "family_reference"),
    ("jayhyeon/qwen2.5-0.5b-sft-mdpo", ["Qwen/Qwen2.5-0.5B"], "Qwen2.5 Technical Report",
     "Qwen2.5 Technical Report", "In this report, we introduce Qwen2.5.", "family_reference"),
    ("jayhyeon/qwen2.5-0.5b-sft-mdpo", ["Qwen/Qwen2.5-0.5B"],
     "mDPO: Conditional Preference Optimization for Multimodal Large Language Models",
     "mDPO: Conditional Preference Optimization for Multimodal Large Language Models",
     "We propose mDPO, a multimodal DPO objective.", "gated_out"),
    # "Mistral 7B" carries this repo's family-plus-size discriminator, so the tier rule
    # reads it as the paper of this line; the point-release suffix (v0.3) is not part of
    # any discriminator, here or on the tag path
    ("mistralai/Mistral-7B-v0.3", [], "Mistral 7B", "Mistral 7B",
     "We introduce Mistral 7B, a 7-billion-parameter language model.", "introduces_target"),
]


def _search_stub(title, arxiv_id="2408.00118"):
    def search(query):
        return [{"title": title, "externalIds": {"ArXiv": arxiv_id}, "abstract": "",
                 "year": 2024, "authors": []}]
    return search


def test_the_paper_search_trap_set(tmp_path, monkeypatch):
    """Failure class: search_binds_an_unrelated_paper. Every trap of the 2026-09-07 plan,
    offline, with the tier its hit must end at. A paper that only names the family is
    never introduces_target for a versioned checkpoint; a hit for a community fine-tune
    is a family reference through its declared base or nothing; a paper of another
    generation, another artifact with the family name in it (LLaMA-Adapter, Qwen-VL), and
    a benchmark paper that merely evaluates the family are all refused."""
    class _Adapter:
        def __init__(self, allow_network=True):
            pass

        def collect(self, target, model_info=None):
            raise MS.ModelSourceError("offline")

    monkeypatch.setattr(MS, "HfModelSourceAdapter", _Adapter)
    from auto_benchmarkcard.tools.eee.paper_resolver import _normalize_s2_paper as norm
    for model_id, bases, hit_title, arxiv_title, arxiv_abstract, want in _TRAPS:
        hf = _hf(tags=(), readme="# model\n")
        hf["id"] = model_id
        hf["base_model_tags"] = list(bases)
        out = tmp_path / MS.slug_for(f"{model_id}@{REV}")
        manifest = MS.collect_model_bundle(
            f"{model_id}@{REV}", tmp_path, hf_metadata=lambda m, r, _hf=hf: _hf,
            paper_meta=lambda u, t=arxiv_title, a=arxiv_abstract: {
                "title": t, "abstract": a, "fetch_error": False},
            docling=lambda u: {"success": True, "filtered_text": "text", "metadata": {}},
            github=lambda *t: {"success": False}, eee_datastore=str(tmp_path / "empty"),
            paper_search=True,
            search_fns=[("s2_search", _search_stub(hit_title), norm)])
        sidecar = json.load(open(out / "tool_output" / "paper_resolver" /
                                 "paper-verification.json"))
        row = next((r for r in sidecar["candidates"] if r.get("from") == "s2_search"), None)
        if want == "gated_out":
            # either the title gate refused it before the fetch, or the tier did after
            assert row is None or row["tier"] == "unrelated_tag", f"{model_id} <- {hit_title}"
            assert sidecar["resolved_url"] is None, f"{model_id} <- {hit_title}"
        else:
            assert row is not None and row["tier"] == want, f"{model_id} <- {hit_title}"
            assert sidecar["resolved_url"] == "https://arxiv.org/abs/2408.00118"
            assert sidecar["resolved_from"] == "s2_search"


def test_the_search_runs_only_when_the_repo_points_at_nothing(tmp_path, monkeypatch):
    """The search is the third source, never the first: a repo whose own tag introduces
    it is never searched, and the search is off unless it is asked for."""
    class _Adapter:
        def __init__(self, allow_network=True):
            pass

        def collect(self, target, model_info=None):
            raise MS.ModelSourceError("offline")

    monkeypatch.setattr(MS, "HfModelSourceAdapter", _Adapter)
    hf = _hf(tags=("arxiv:2501.00656",), readme="# OLMo 2\n")
    searched = []

    def never(query):
        searched.append(query)
        return []

    common = dict(hf_metadata=lambda m, r: hf,
                  paper_meta=lambda u: {"title": "2 OLMo 2 Furious",
                                        "abstract": "We present OLMo 2.", "fetch_error": False},
                  docling=lambda u: {"success": True, "filtered_text": "t", "metadata": {}},
                  github=lambda *t: {"success": False}, eee_datastore=str(tmp_path / "empty"))
    MS.collect_model_bundle(f"allenai/OLMo-2-1124-7B@{REV}", tmp_path / "a", paper_search=True,
                            search_fns=[("s2_search", never, lambda p: p)], **common)
    assert searched == []
    monkeypatch.delenv("MODELCARDS_PAPER_SEARCH", raising=False)
    assert MS.paper_search_enabled() is False
    monkeypatch.setenv("MODELCARDS_PAPER_SEARCH", "1")
    assert MS.paper_search_enabled() is True
    assert MS.search_queries_for_model("google/gemma-2-9b")[0] == "gemma 2 technical report"
    assert MS.head_family_token("jayhyeon/qwen2.5-0.5b-sft-mdpo") == "qwen2"


def test_a_searched_title_must_name_this_family_and_no_other_model():
    """Failure class: search_binds_another_models_report. The live check of 2026-09-07 ran
    the search against the flagship targets and OpenAlex answered "Llama-3.1-FoundationAI-
    SecurityLLM-Reasoning-8B Technical Report" for meta-llama/Llama-3.2-3B, which the first
    gate accepted because "llama-3" is a substring of it. A family token counts only when
    it stands as the title's own subject: nothing may continue the name after it, nothing
    but a lead word may stand before it, and the generation it states must be this
    checkpoint's own or an earlier part of it."""
    gate = MS.search_title_gate
    llama32 = "meta-llama/Llama-3.2-3B"
    assert gate(llama32, "The Llama 3 Herd of Models") is True
    for title in ("Llama-3.1-FoundationAI-SecurityLLM-Reasoning-8B Technical Report",
                  "Llama-3.1-FoundationAI-SecurityLLM-Base-8B Technical Report",
                  "Lawyer LLaMA Technical Report",
                  "Code Llama: Open Foundation Models for Code",
                  "LLaMA-Adapter: Efficient Fine-tuning of Language Models",
                  "Llama 2: Open Foundation and Fine-Tuned Chat Models"):
        assert gate(llama32, title) is False, title
    # a generation glued to the token counts as stated: the Qwen2.5 report is not the
    # Qwen2 checkpoint's, and the Qwen2 report is not the Qwen2.5-Math model's
    assert gate("Qwen/Qwen2.5-32B-Instruct", "Qwen2.5 Technical Report") is True
    assert gate("Qwen/Qwen2-72B", "Qwen2.5 Technical Report") is False
    assert gate("Qwen/Qwen2-57B-A14B", "Qwen2 Technical Report") is True
    assert gate("Qwen/Qwen2-57B-A14B", "Qwen2.5-Math Technical Report") is False
    # a title that states a generation for a checkpoint whose name states none is a
    # different generation of it
    assert gate("google/gemma-7b", "Gemma: Open Models Based on Gemini Research and Technology") is True
    assert gate("google/gemma-7b", "Gemma 2: Improving Open Language Models at a Practical Size") is False
    # a version suffix is not another model: the report of this checkpoint still binds
    assert gate("deepseek-ai/DeepSeek-V3", "DeepSeek-V3 Technical Report") is True
    assert gate("mistralai/Mistral-7B-v0.3", "Mistral 7B") is True
    assert gate("moonshotai/kimi-k2-instruct", "Kimi K2: Open Agentic Intelligence") is True


def test_the_family_token_is_the_one_the_repo_puts_its_generation_next_to():
    """Failure class: vendor_token_read_as_the_family. With "meta" as the family token of
    meta-llama/Meta-Llama-3.1-8B, a survey titled "Evolution of meta's llama models and
    parameter-efficient fine-tuning of large language models" passed the gate in the live
    check of 2026-09-07. The family token is the one the repo name puts its generation
    next to, and a checkpoint whose name carries a generation needs the title to say
    which one: the 2023 LLaMA paper is not Llama-3.1-8B's report."""
    assert MS.head_family_token("meta-llama/Meta-Llama-3.1-8B") == "llama"
    assert MS.family_generation("meta-llama/Meta-Llama-3.1-8B", "llama") == "3.1"
    assert MS.family_generation("jayhyeon/qwen2.5-0.5b-sft-mdpo", "qwen2") == "2.5"
    assert MS.family_generation("deepseek-ai/DeepSeek-V3", "deepseek") == "3"
    # a size and a point release are not a generation
    assert MS.family_generation("google/gemma-7b", "gemma") is None
    assert MS.family_generation("mistralai/Mistral-7B-v0.3", "mistral") is None
    gate = MS.search_title_gate
    assert gate("meta-llama/Meta-Llama-3.1-8B", "The Llama 3 Herd of Models") is True
    assert gate("meta-llama/Meta-Llama-3.1-8B",
                "Evolution of meta's llama models and parameter-efficient fine-tuning of "
                "large language models") is False
    assert gate("meta-llama/Llama-3.1-8B",
                "LLaMA: Open and Efficient Foundation Language Models") is False
    assert gate("google/gemma-3-4b-it",
                "Gemma: Open Models Based on Gemini Research and Technology") is False
    assert gate("google/gemma-3-4b-it", "Gemma 3 Technical Report") is True
    # a checkpoint whose own name states no generation still takes its family's paper
    assert gate("google/gemma-7b",
                "Gemma: Open Models Based on Gemini Research and Technology") is True
    assert gate("mistralai/mixtral-8x22b-instruct-v0.1", "Mixtral of Experts") is True
    assert gate("google/recurrentgemma-9b",
                "RecurrentGemma: Moving Past Transformers for Efficient Open Language Models") is True
    # Failure class: paper_about_the_model_read_as_its_report. A preposition in front of
    # the family name is the signature of a paper about the model, and its abstract names
    # the checkpoint, so the tier alone said introduces_target (live check 2026-09-07).
    assert gate("meta-llama/Meta-Llama-3-8B",
                "Model Inversion Attacks on Llama 3: Extracting PII from Large Language "
                "Models") is False
    assert gate("meta-llama/Meta-Llama-3-8B", "The Llama 3 Herd of Models") is True
    assert gate("allenai/OLMo-2-1124-7B", "2 OLMo 2 Furious") is True


def test_the_second_search_source_is_only_asked_when_the_first_found_nothing():
    """Failure class: collect_timed_out_in_the_search. Semantic Scholar without a key
    sleeps a second per request and answers 429 under load; walking both sources for
    every query ran the collect past its 900 s timeout on the first two targets of the
    2026-09-07 re-collect. Sources are walked in order, and the next one is asked only
    when the one before it produced no candidate."""
    calls = []

    def source(name, results):
        def search(query):
            calls.append((name, query))
            return results
        return search

    hit = [{"title": "Gemma 2: Improving Open Language Models at a Practical Size",
            "arxiv_id": "2408.00118"}]
    found = MS.search_paper_candidates(
        "google/gemma-2-9b", [],
        search_fns=[("openalex_search", source("openalex", hit), lambda p: p),
                    ("s2_search", source("s2", hit), lambda p: p)])
    assert [c["origin"] for c in found] == ["openalex_search"]
    assert {name for name, _ in calls} == {"openalex"}
    calls.clear()
    found = MS.search_paper_candidates(
        "google/gemma-2-9b", [],
        search_fns=[("openalex_search", source("openalex", []), lambda p: p),
                    ("s2_search", source("s2", hit), lambda p: p)])
    assert [c["origin"] for c in found] == ["s2_search"]
    assert {name for name, _ in calls} == {"openalex", "s2"}


def test_a_hyphenated_sibling_report_is_not_this_checkpoints():
    """Failure class: sibling_line_report_bound_to_the_base_line. The recorded search of
    2026-09-07 offered "Qwen2.5-1M Technical Report" for Qwen/Qwen2.5-32B-Instruct. A word
    after the generation names a different member of the family, unless the checkpoint's
    own name carries that same word, which is how Qwen2.5-Math-7B keeps its own report."""
    gate = MS.search_title_gate
    assert gate("Qwen/Qwen2.5-32B-Instruct", "Qwen2.5 Technical Report") is True
    assert gate("Qwen/Qwen2.5-32B-Instruct", "Qwen2.5-1M Technical Report") is False
    assert gate("Qwen/Qwen2.5-Math-7B",
                "Qwen2.5-Math Technical Report: Toward Mathematical Expert Model") is True
    assert gate("Qwen/Qwen2-57B-A14B", "Qwen2.5-Math Technical Report") is False
    assert gate("deepseek-ai/DeepSeek-V3", "DeepSeek-V3 Technical Report") is True
