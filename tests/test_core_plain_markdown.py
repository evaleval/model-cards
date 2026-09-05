"""The plain README view: markup gone, words and tables intact, deterministic."""

from model_cards.core.plain_markdown import markdown_plain, RULE


README = (
    "# OLMo-2-1124-7B-Instruct\n\n"
    "<!-- provider-note -->\n"
    "OLMo 2 7B Instruct November 2024 is post-trained variant of the [OLMo-2 7B November 2024]"
    "(https://huggingface.co/allenai/OLMo-2-1124-7B) model, which has undergone supervised finetuning "
    "on an OLMo-specific variant of the [Tülu 3 data](https://huggingface.co/datasets/allenai/tulu-3-sft-olmo-2-mixture) "
    "and further **DPO training** on <a href=\"https://x\">this dataset</a>, and finally *RLVR* training using `allenai/RLVR-GSM`.\n\n"
    "| Model | AVG |\n|---|---|\n| **OLMo-2-7B-1124-Instruct** | 54.8 |\n\n"
    "![banner](https://x/olmo.png) See <https://github.com/allenai/OLMo> and olmo_2_mix &amp; friends.\n"
)


def test_markup_removed_words_kept():
    plain = markdown_plain(README)
    assert "post-trained variant of the OLMo-2 7B November 2024 model, which has undergone supervised finetuning " \
           "on an OLMo-specific variant of the Tülu 3 data and further DPO training on this dataset, and finally " \
           "RLVR training using allenai/RLVR-GSM." in plain
    assert "| OLMo-2-7B-1124-Instruct | 54.8 |" in plain
    assert "banner See https://github.com/allenai/OLMo and olmo_2_mix & friends." in plain
    assert "provider-note" not in plain and "](" not in plain and "**" not in plain and "<a" not in plain
    assert plain.startswith("# OLMo-2-1124-7B-Instruct")


def test_plain_view_is_idempotent_and_named():
    plain = markdown_plain(README)
    assert markdown_plain(plain) == plain
    assert RULE == "markdown_plain_v1"
    assert markdown_plain("") == "" and markdown_plain(None) == ""
