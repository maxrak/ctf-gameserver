from collections import defaultdict, OrderedDict

from django.core.cache import cache

from ctf_gameserver.web.registration.models import Team
from . import models


def scores():
    """
    Returns the scores as currently stored in the database as an OrderedDict in this format:

        {team: {
            'offense': [{service: offense_points}, total_offense_points],
            'defense': [{service: defense_points}, total_defense_points],
            'sla': [{service: sla_points}, total_sla_points],
            'total': total_points
        }}

    The result is sorted by the total points.
    """

    # No good way to invalidate the cache, so use a generic key with a short timeout
    cache_key = 'scores'
    cached_scores = cache.get(cache_key)

    if cached_scores is not None:
        return cached_scores

    team_scores = defaultdict(lambda: {'offense': [{}, 0], 'defense': [{}, 0], 'sla': [{}, 0], 'total': 0})

    for score in models.ScoreBoard.objects.exclude(total=0):
        team_scores[score.team]['offense'][0][score.service] = score.attack
        team_scores[score.team]['offense'][1] += score.attack
        team_scores[score.team]['defense'][0][score.service] = score.defense
        team_scores[score.team]['defense'][1] += score.defense
        team_scores[score.team]['sla'][0][score.service] = score.sla
        team_scores[score.team]['sla'][1] += score.sla
        team_scores[score.team]['total'] += score.total

    sorted_team_scores = OrderedDict(sorted(team_scores.items(), key=lambda s: s[1]['total'], reverse=True))
    cache.set(cache_key, sorted_team_scores, 20)

    return sorted_team_scores


def team_statuses(from_tick, to_tick):
    """
    Returns the statuses of all teams and all services in the specified range of ticks. The result is an
    OrderedDict sorted by the team's names in this format:

        {'team': {
            'tick': {
                'service': status
            }
        }}
    """

    cache_key = 'team-statuses_{:d}-{:d}'.format(from_tick, to_tick)
    cached_statuses = cache.get(cache_key)

    if cached_statuses is not None:
        return cached_statuses

    statuses = {}
    status_checks = models.StatusCheck.objects.filter(tick__gte=from_tick, tick__lte=to_tick)

    for team in Team.active_objects.all():
        statuses[team] = {}

        for tick in range(from_tick, to_tick+1):
            statuses[team][tick] = {}
            for service in models.Service.objects.all():
                statuses[team][tick][service] = ''

        for check in status_checks.filter(team=team):
            statuses[team][check.tick][check.service] = check.get_status_display()

    sorted_statuses = OrderedDict(sorted(statuses.items(), key=lambda s: s[0].user.username))
    cache.set(cache_key, sorted_statuses, 20)

    return sorted_statuses
