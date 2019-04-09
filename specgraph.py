#!/usr/bin/env python

import sys
import getopt
import re
from graphviz import Digraph


def parse_program(src):
    labeled_instr_regex = r"(?P<label>\d+): (?P<instr>.*)"
    beqz_regex = r"beqz\((?P<cond>.+),(?P<target>\d+)\)"
    jmp_regex = r"jmp\((?P<target>\d+)\)"

    instructions = {}

    matches = re.finditer(labeled_instr_regex, src, re.MULTILINE)
    for match in matches:
        label = int(match.group('label'))
        text = match.group('instr')
        targets = []

        if text.startswith('beqz'):
            bezq_match = re.search(beqz_regex, text)
            targets.append(label + 1)
            targets.append(bezq_match.group('target'))
        elif text.startswith('jmp'):
            jmp_match = re.search(jmp_regex, text)
            targets.append(jmp_match.group('target'))
        else:
            targets.append(label + 1)

        instructions[label] = {'text': text, 'targets': targets}

    instructions[len(instructions)] = {'text': '⊥', 'targets': []}

    return instructions


def parse_trace(src, program):
    label_regex = r"(?P<label>\d+):\s*"
    trace_lines = re.split(label_regex, src)

    pc_matcher = re.compile(r"pc\((?P<target>\d+)\)")
    start_matcher = re.compile(r"start\((?P<tid>\d+)\)")
    commit_matcher = re.compile(r"commit\((?P<tid>\d+)\)")
    rollback_matcher = re.compile(r"rollback\((?P<tid>\d+)\)")

    combined_trace_lines = []
    for label, obs_str in zip(trace_lines[1::2], trace_lines[2::2]):
        label = int(label)
        obs = [o.strip() for o in obs_str.split('\n')]
        obs = list(filter(None, obs)) # drop empty obs
        if len(combined_trace_lines) > 0 and combined_trace_lines[-1][0] == label:
            combined_trace_lines[-1] = (label, combined_trace_lines[-1][1] + obs) # append obs to last line
        else:
            combined_trace_lines.append((label, obs))

    trace = []

    running_transactions = set()

    for label, obs in combined_trace_lines:
        def filter_obs(obs, matcher):
            return [ob for ob in obs if matcher.match(ob)]
        def extract_obs_info(obs, matcher, group):
            return [int(matcher.match(ob).group(group)) for ob in filter_obs(obs, matcher)]

        targets = program[label]['targets']

        pc_targets = extract_obs_info(obs, pc_matcher, 'target')
        if pc_targets:
            assert(len(pc_targets) == 1)
            to = pc_targets[0]
        elif len(targets) == 0: # end
            to = label
        else:
            assert(len(targets) == 1)
            to = targets[0]

        start_tids = set(extract_obs_info(obs, start_matcher, 'tid'))
        running_transactions = running_transactions.union(start_tids)

        commit_tids = set(extract_obs_info(obs, commit_matcher, 'tid'))
        running_transactions = running_transactions.difference(commit_tids)

        rollback_tids = set(extract_obs_info(obs, rollback_matcher, 'tid'))
        running_transactions = running_transactions.difference(rollback_tids)

        trace.append({'t': len(trace), 'from': label, 'to': to, 'obs': obs,
                      'running_transactions': running_transactions})

    return trace


def parse_assigment_list(src):
    regex = r"(?P<var>\w+)=(?P<value>\w+)"

    ass = {}

    matches = re.finditer(regex, src)
    for match in matches:
        ass[match.group('var')] = match.group('value')

    return ass


def parse_conf(src):
    regex = r"^\s*(?P<key>\w+)\s*=\s*(?P<value>.+)\s*$"

    conf = {}

    matches = re.finditer(regex, src, re.MULTILINE)
    for match in matches:
        key = match.group('key')
        value = match.group('value')

        if key == 'i':
            conf[key] = int(value)
        elif key in ['m', 'a']:
            conf[key] = parse_assigment_list(value)
        else:
            conf[key] = value

    return conf


def parse(src):
    src = src.replace('<-', '←')
    src = src.replace('\\/', '∨')
    src = src.replace('/\\', '∧')
    src = src.replace('>=', '≥')
    src = src.replace('<=', '≤')
    src = src.replace('\=', '≠')

    regex = r"program:\n(?P<program>.*).*"\
            r"Assignments:\n\s*\[(?P<assignments>.*)\].*"\
            r"initial conf:\n(?P<init_conf>.*).*"\
            r"trace:\n(?P<trace>.*).*"\
            r"final conf:\n(?P<final_conf>.*)"

    match = re.search(regex, src, re.MULTILINE | re.DOTALL)
    if not match:
        return None

    program = parse_program(match.group('program'))
    trace = parse_trace(match.group('trace'), program)
    init_conf = parse_conf(match.group('init_conf'))
    final_conf = parse_conf(match.group('final_conf'))

    return {
        'program': program,
        'trace': trace,
        'init_conf': init_conf,
        'final_conf': final_conf,
    }


def main(inputfile, outputfile):
    try:
        with open(inputfile, 'r') as f:
            spectector_out = parse(f.read())
    except FileNotFoundError:
        print("Could not read file '{}'".format(inputfile))
        sys.exit(-2)

    if not spectector_out:
        print("Could not parse file '{}'".format(inputfile))
        sys.exit(-3)

    graph = Digraph(format='svg')
    graph.node_attr.update(style='filled', fontcolor='#4a4a4a', fillcolor='#e6e6e6', color='#4a4a4a')

    # cfg
    program = spectector_out['program']
    for label, instr in program.items():
        is_end = len(instr['targets']) == 0
        graph.node(str(label), label='{}: {}'.format(label, instr['text']),
                   shape='doubleoctagon' if is_end else 'rect')
        for target in instr['targets']:
            graph.edge(str(label), str(target), color='#a2a2a2', penwidth='1.5')

    # trace
    trace = spectector_out['trace']
    for entry in trace:
        graph.edge(str(entry['from']), str(entry['to']), color='#f60000', fontcolor='#f60000', penwidth='3.5',
                   label='@{}\n{}'.format(entry['t'], '\n'.join(entry['obs'])))

    # transactions
    transaction_colors = ['#00934a', '#4363d8', '#F96714', '#2A4B7C', '#CE5B78', '#800000', '#797B3A']
    for entry in trace:
        for tid in entry['running_transactions']:
            color = transaction_colors[tid % len(transaction_colors)]
            graph.edge(str(entry['from']), str(entry['to']), color=color, fontcolor=color,
                       penwidth='3.0', style='dashed', arrowhead='none', label='t{}'.format(tid))

    # configs
    def annotate_node_with_config(node_id, conf, draw_on_top=False):
        conf_node_id = 'conf_{}'.format(node_id)
        graph.node(conf_node_id, shape='note', style='solid',
                   label='mem: {}\nreg: {}'.format(str(conf['m']), str(conf['a'])))
        f = conf_node_id if draw_on_top else node_id
        t = node_id if draw_on_top else conf_node_id
        graph.edge(f, t, color='grey', penwidth='2.0', style='dotted', arrowhead='none')

    annotate_node_with_config('0', spectector_out['init_conf'], draw_on_top=True)
    annotate_node_with_config(str(len(program)-1), spectector_out['final_conf'])

    graph.render(outputfile)


if __name__ == '__main__':
    def print_help_and_exit():
        print('Tool for visualizing Spectector traces.')
        print('\nUSAGE:\n  {} [-i <inputfile>] -o <outputfile>'.format(sys.argv[0]))
        options = [
            '-i, --in\tInput text-file containing the output of Spectector (will read from stdin if not set)',
            '-o, --out\tOutput file containing the graph (will create SVG- and DOT-files)',
        ]
        print('\nOPTIONS:\n  ' + '\n  '.join(options))

        sys.exit(-1)

    inputfile = sys.stdin.fileno()
    outputfile = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hi:o:", ["in=","out="])
    except getopt.GetoptError:
        print_help_and_exit()
    for opt, arg in opts:
        if opt == '-h':
            print_help_and_exit()
        elif opt in ("-i", "--in"):
            inputfile = arg
        elif opt in ("-o", "--out"):
            outputfile = arg

    if not outputfile:
        print_help_and_exit()

    main(inputfile, outputfile)
