'''
Calculates rating of games provided by steam id
Credits go to woctezuma:
https://github.com/woctezuma/Steam-Bayesian-Average

'''
from __future__ import annotations

import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING

import steamspypi

if TYPE_CHECKING:
    from typing import Dict


def compute_game_increment_value(game: Dict) -> int:
    '''Compute increment for a game'''
    return game['positive']


def compute_game_raw_score(game: Dict) -> int:
    '''Compute raws score for a game'''
    try:
        return game['positive'] / (game['positive'] + game['negative'])
    except ZeroDivisionError:
        return 0


def compute_game_num_votes(game: Dict) -> int:
    '''Compute total votes for a game'''
    return game['positive'] + game['negative']


def compute_bayesian_average_for_a_game(game: Dict, prior: Dict) -> int:
    '''Compute bayesian avarage rating for a game'''
    raw_score = compute_game_raw_score(game)
    num_votes = compute_game_num_votes(game)

    return (prior['num_votes'] * prior['raw_score'] + num_votes * raw_score) / (
            prior['num_votes'] + num_votes)


def compute_prior(games: Dict) -> Dict:
    '''Compute prior for a set of games'''
    list_increment_values = [compute_game_increment_value(game) for game in games.values()]
    list_num_votes = [compute_game_num_votes(game) for game in games.values()]

    prior = {}
    try:
        prior['raw_score'] = sum(list_increment_values) / sum(list_num_votes)
    except ZeroDivisionError:
        print(list_increment_values, list_num_votes)
    prior['num_votes'] = sum(list_num_votes) / len(list_num_votes)

    return prior


def compute_bayesian_average_for_games(games: Dict) -> Dict:
    '''Compute bayesian average rating for a set of games'''
    prior = compute_prior(games)

    for game in games:
        games[game]['bayesian_average'] = compute_bayesian_average_for_a_game(games[game], prior)

    return games


def get_steamspy_data(game_id: str) -> Dict:
    '''Get votes info from SteamSpy for a game'''
    empty_data = {'positive': 0,
                  'negative': 0}

    if not game_id:
        return empty_data

    data_request = {}
    data_request['request'] = 'appdetails'
    data_request['appid'] = game_id


    try:
        data = steamspypi.download(data_request)
    except JSONDecodeError:
        logging.warning(f'Failed to fetch SteamSpy data for {game_id}')
        data = empty_data

    try:
        return {'positive': data['positive'],
                'negative': data['negative']}
    except KeyError:
        logging.warning(f'Wrong SteamSpy data for {game_id}: {data}')
        return empty_data


def get_ranking(game_ids: list[str]) -> Dict:
    '''Calculate bayesian ranking for a set of games provided by Steam ID'''
    games = {game_id: get_steamspy_data(game_id) for game_id in game_ids}

    games = compute_bayesian_average_for_games(games)

    return {game: games[game]['bayesian_average'] for game in games}
