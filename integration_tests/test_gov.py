from .utils import submit_any_proposal


def test_submit_any_proposal(mantra, tmp_path):
    submit_any_proposal(mantra, tmp_path)
