import pytest

from autosg.sgbot import steam_rating as sr


GAME = {
    'positive': 2,
    'negative': 6
}

GAME_ZERO = {
    'positive': 0,
    'negative': 0
}

def test_compute_game_increment_value():
    assert sr.compute_game_increment_value(GAME) == GAME['positive']

@pytest.mark.parametrize('value,result', [(GAME, 0.25), (GAME_ZERO, 0)])
def test_compute_game_raw_score(value, result):
    assert sr.compute_game_raw_score(value) == result

def test_compute_game_num_votes():
    assert sr.compute_game_num_votes(GAME): == 8
