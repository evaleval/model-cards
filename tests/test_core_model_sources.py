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
