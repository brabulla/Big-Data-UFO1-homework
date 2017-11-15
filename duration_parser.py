from arpeggio import ParserPython, PTNodeVisitor, visit_parse_tree, Optional, NoMatch
from arpeggio import RegExMatch as _
from datetime import timedelta

class UFOParser:

    approximation_marks = ['~', '>', '<', 'around', 'approximately', 'approx.', 'approx', \
        'aprox.', 'aprox', 'appx.', 'appx', 'app.', 'app', 'apx.', 'apx', 'about', 'at least',\
        'over', 'more than', 'less than', 'about', 'abt', ]
    numbers_with_letter = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,\
        'eight': 8, 'nine': 9, 'ten': 10, 'fifteen': 15}
    # how many seconds?
    free_approximations = {'seconds': 5, 'minutes': 180, 'hours': 10800, 'a few seconds': 5, 'few seconds': 5, \
        'several seconds': 10, 'a few minutes': 180, 'few minutes': 180, 'several minutes': 300,'half hour': 1800, \
        'several hours': 10800,}

    __parser = None
    __evaluater = None

    def parse_duration(data):
        if data is None:
            return data
        if __class__.__parser is None:
            __class__.__parser = ParserPython(Grammar.duration, debug=False)
            __class__.__evaluater = EvaluateDuration(debug=False)
        try:
            return visit_parse_tree(__class__.__parser.parse(data.lower()), __class__.__evaluater)
        except NoMatch:
            return None


class Grammar:

    """ This class defines the grammar of the duration texts. """

    def number_with_number(): return _('[0-9]*\.?[0-9]*')
    def number_with_letter(): return list(UFOParser.numbers_with_letter.keys())
    def number(): return [Grammar.number_with_number, Grammar.number_with_letter]
    def interval_separator(): return ['-', 'to', 'or']
    def interval(): return Grammar.number, Optional(Grammar.interval_separator, Grammar.number)
    def second(): return _('seconds|second|sec|s')
    def minute(): return _('minutes|minute|min|m')
    def hour(): return _('hours|hour|h')
    def appx_mark(): return UFOParser.approximation_marks
    def free_appx(): return list(UFOParser.free_approximations.keys())
    def exact_duration(): return Optional(Grammar.appx_mark), Grammar.interval, [Grammar.hour, Grammar.minute, Grammar.second]
    def duration(): return [Grammar.exact_duration, Grammar.free_appx]


class EvaluateDuration(PTNodeVisitor):

    """ This class defines how to evaluate an already parsed (checked) strgin. """

    def visit_number_with_number(self, node, children): return float(node.value)
    def visit_number_with_letter(self, node, children): return UFOParser.numbers_with_letter[node.value]
    def visit_number(self, node, children): return children[0]
    def visit_interval(self, node, children): return (children[0],) if len(children) == 1 else (children[0], children[2])
    def visit_second(self, node, children): return 's'
    def visit_minute(self, node, children): return 'm'
    def visit_hour(self, node, children): return 'h'
    def visit_exact_duration(self, node, children):
        if len(children) == 3:
            children.pop(0)
        avg = children[0][0]
        if len(children[0]) == 2:
            avg = (children[0][1] + avg) / 2  # simply get the avarage of the interval...
        if children[1] is 's':
            return timedelta(seconds=avg)
        elif children[1] is 'm':
            return timedelta(minutes=avg)
        else:
            return timedelta(hours=avg)
    def visit_free_appx(self, node, children): return timedelta(seconds=UFOParser.free_approximations[node.value])


if __name__ == "__main__":
    # Demo...
    test = ['10 seconds', '2-3 minutes', 'about four to six hours', '~17 seconds', 'hours']
    for d in test:
        print(d, '->', UFOParser.parse_duration(d))

"""

import json
import operator
from collections import Counter
from duration_parser import UFOParser

with open('data.json', 'r') as file:
    data = json.load(file)
    durations = list(data['Duration'].values())

bad_durations = [x for x in durations if x is not None and UFOParser.parse_duration(x) is None]
counts = Counter(bad_durations)
sorted(dict(counts).items(), key=operator.itemgetter(1), reverse=True)[:100]

"""