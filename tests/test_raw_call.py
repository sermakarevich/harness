REPLY = {
    "output": [
        {"type": "reasoning", "summary": []},
        {
            "type": "message",
            "content": [
                {"type": "output_text", "text": "po"},
                {"type": "output_text", "text": "ng"},
                {"type": "refusal", "refusal": "no"},
            ],
        },
    ]
}


def test_output_types_lists_every_block(raw_call):
    assert raw_call.output_types(REPLY) == ["reasoning", "message"]


def test_text_of_joins_only_output_text(raw_call):
    assert raw_call.text_of(REPLY) == "pong"
