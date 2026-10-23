from modules.helpers import lookup_custom_answer

ANSWERS = [{"match": "German", "answer": "None"}, {"match": "proficiency", "answer": "Professional"}]


def test_lookup_custom_answer():
    assert lookup_custom_answer("Proficiency in german?", ANSWERS) == "None"
    assert lookup_custom_answer("What is your notice period?", ANSWERS) is None


def test_first_match_wins_and_blank_ignored():
    assert lookup_custom_answer("English proficiency", ANSWERS) == "Professional"
    assert lookup_custom_answer("anything", [{"match": "  ", "answer": "x"}]) is None
    assert lookup_custom_answer("", ANSWERS) is None
    assert lookup_custom_answer("German", []) is None
