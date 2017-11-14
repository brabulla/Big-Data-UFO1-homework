from arpeggio import ParserPython, PTNodeVisitor, visit_parse_tree, Optional, EOF
from arpeggio import RegExMatch as _
from datetime import timedelta

approximation_marks = ['~', '>', '<', 'around', 'approximately', 'approx.', 'approx', \
    'aprox.', 'aprox', 'appx.', 'appx', 'app.', 'app', 'apx.', 'apx', 'about', 'at least',\
    'over', 'more than', 'less than', 'about', 'abt', ]
numbers_with_letter = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,\
    'eight': 8, 'nine': 9, 'ten': 10, 'fifteen': 15}
# how many seconds?
free_approximations = {'seconds': 5, 'minutes': 180, 'hours': 10800}

class Grammar:
    def number_with_number(): return _('[0-9]*\.?[0-9]*')
    def number_with_letter(): return list(numbers_with_letter.keys())
    def number(): return [Grammar.number_with_number, Grammar.number_with_letter]
    def interval_separator(): return ['-', 'to', 'or']
    def interval(): return Grammar.number, Optional(Grammar.interval_separator, Grammar.number)
    def second(): return _('seconds|second|sec|s')
    def minute(): return _('minutes|minute|min|m')
    def hour(): return _('hours|hour|h')
    def appx_mark(): return approximation_marks
    def free_appx(): return list(free_approximations.keys())
    def exact_duration(): return Optional(Grammar.appx_mark), Grammar.interval, [Grammar.hour, Grammar.minute, Grammar.second]
    def duration(): return [Grammar.exact_duration, Grammar.free_appx]
parser = ParserPython(Grammar.duration, debug=False)

class EvaluateDuration(PTNodeVisitor):
    def visit_number_with_number(self, node, children): return float(node.value)
    def visit_number_with_letter(self, node, children): return numbers_with_letter[node.value]
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
            avg = (children[0][1] + avg) / 2
        if children[1] is 's':
            return timedelta(seconds=avg)
        elif children[1] is 'm':
            return timedelta(minutes=avg)
        else:
            return timedelta(hours=avg)
    def visit_free_appx(self, node, children): return timedelta(seconds=free_approximations[node.value])


test = ['10 seconds', '2-3 minutes', 'about four to six hours']
for d in test:
    try:
        result = visit_parse_tree(parser.parse(d.lower()), EvaluateDuration(debug=False))
        print('"' + d + '" is equal to: ' + str(result.total_seconds()) + ' s')
    except NoMatch:
        pass

"""
m = 0
for d in data['Duration']:
    try:
        if type(d) is str:
            parser.parse(d.lower())
            m += 1
    except NoMatch:
        print(d)
"""