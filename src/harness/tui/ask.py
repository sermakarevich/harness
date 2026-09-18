"""Ask one permission question in the terminal."""

from harness.tools.permission import Answer

QUESTION = "allow {call}?"

HINT = "/".join(f"[{choice.value[0]}]{choice.value[1:]}" for choice in Answer)


def answer_of(reply: str) -> Answer:
    """Pick an answer from the first letter of a reply."""
    letter = reply[:1].lower()
    for choice in Answer:
        if letter and choice.value.startswith(letter):
            return choice
    return Answer.NO


def ask_permission(app, call: str) -> Answer:
    try:
        return answer_of(app.read_line(f"{QUESTION.format(call=call)} {HINT} "))
    except EOFError:
        return Answer.NO
