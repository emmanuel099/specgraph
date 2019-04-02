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


def parse_trace(trace, program):
    label_regex = r"(?P<label>\d+):\s*"
    trace_parts = re.split(label_regex, trace)
    trace_parts.pop(0)

    pc_matcher = re.compile(r"pc\((?P<target>\d+)\)")
    start_matcher = re.compile(r"start\((?P<tid>\d+)\)")
    commit_matcher = re.compile(r"commit\((?P<tid>\d+)\)")
    rollback_matcher = re.compile(r"rollback\((?P<tid>\d+)\)")

    trace_entries = []

    running_transactions = set()

    for label, obs_str in zip(trace_parts[:-1:2], trace_parts[1::2]):
        obs = [o.strip() for o in obs_str.split('\n')]
        label = int(label)

        targets = program[label]['targets']

        def filter_obs(obs, matcher):
            return [ob for ob in obs if matcher.match(ob)]
        def extract_obs_info(obs, matcher, group):
            return [int(matcher.match(ob).group(group)) for ob in filter_obs(obs, matcher)]

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

        trace_entries.append({'t': len(trace_entries), 'from': label, 'to': to, 'obs': obs,
                              'running_transactions': running_transactions})

    return trace_entries


def parse(src):
    src = src.replace('<-', '←')
    src = src.replace('\\/', '∨')
    src = src.replace('/\\', '∧')

    regex = r"program:\n(?P<program>.*).*Assignments:\n\s*\[(?P<assignments>.*)\].*initial conf:\n(?P<init_conf>.*).*trace:\n(?P<trace>.*).*final conf:\n(?P<final_conf>.*)"
    match = re.search(regex, src, re.MULTILINE | re.DOTALL)
    if not match:
        return None

    program = parse_program(match.group('program'))
    trace = parse_trace(match.group('trace'), program)

    return {
        'program': program,
        'trace': trace,
    }


def main(inputfile, outputfile):
    try:
        with open(inputfile, 'r') as f:
            out = parse(f.read())
    except FileNotFoundError:
        print("Could not read file '{}'".format(inputfile))
        sys.exit(-2)

    if not out:
        print("Could not parse file '{}'".format(inputfile))
        sys.exit(-3)

    graph = Digraph(format='svg')
    graph.node_attr.update(style='filled', fillcolor='#e6e6e6', color='#a2a2a2')

    # cfg
    program = out['program']
    for label, instr in program.items():
        graph.node(str(label), label='{}: {}'.format(label, instr['text']))
        for target in instr['targets']:
            graph.edge(str(label), str(target), color='#a2a2a2', penwidth='1.5')

    # trace
    trace = out['trace']
    for entry in trace:
        graph.edge(str(entry['from']), str(entry['to']), color='red', penwidth='2.5',
                   label='@{}\ns: [{}]\n{}'.format(entry['t'],
                           ', '.join(map(str, entry['running_transactions'])),
                           '\n'.join(entry['obs'])))

    graph.render(outputfile)


if __name__ == '__main__':
    def print_help_and_exit():
        print('Tool for visualizing Spectector traces.')
        print('\nUSAGE:\n  {} -i <inputfile> -o <outputfile>'.format(sys.argv[0]))
        options = [
            '-i, --in\tInput text-file containing the output of Spectector',
            '-o, --out\tOutput file containing the graph (will create SVG- and DOT-files)',
        ]
        print('\nOPTIONS:\n  ' + '\n  '.join(options))

        sys.exit(-1)

    inputfile = None
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

    if not inputfile:
        print_help_and_exit()
    if not outputfile:
        print_help_and_exit()

    main(inputfile, outputfile)
