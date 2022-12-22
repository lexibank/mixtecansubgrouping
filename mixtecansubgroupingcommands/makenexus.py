#!/usr/bin/env python3
# original script created by Simon J. Greenhill <simon@simon.net.nz>
# cldfbench version by Johannes Englisch <johannes_englisch@eva.mpg.de>

"""Create a NEXUS file from the cognate table of a cldf dataset."""

import argparse
from collections import defaultdict
from pathlib import Path
import sys

from cldfbench.cli_util import with_dataset, add_dataset_spec
import csvw
from pycldf import iter_datasets

from nexus import NexusWriter


def read(filename, delimiter="\t"):
    """Read `filename` returning an iterator of lines."""
    with csvw.UnicodeDictReader(filename, delimiter=delimiter) as reader:
        for row in reader:
            yield row


def read_partitions(filename):
    parts = defaultdict(set)
    for row in read(filename):
        # figure out cogid
        if row.get('COGIDS_BROAD', None):
            cogid = row.get('COGIDS_BROAD')
        elif row.get('COGIDS_FINE', None):  # pragma: no cover
            cogid = row.get('COGIDS_FINE')
        else:  # pragma: no cover
            raise ValueError(
                "Unknown COGIDS column, expecting either COGIDS_BROAD or COGIDS_FINE"
            )
        parts[row['PARTITION']].add((row['CONCEPT'], cogid))
    return parts


def get_cognates(cldf_dataset, cognate_coding=None):
    """
    Collect cognate sets from column `cognate_column` in `filename`.

    Returns:
        - a set of language varieties
        - a dict of words to language sets (word -> {l1, l2, l3})
        - a dict of cognates to language sets (cogset -> {l1, l2, l3})
    """
    # XXX What changes if there's a cognateset table?
    concepts = {
        row['id']: row['name']
        for row in cldf_dataset.iter_rows(
            'ParameterTable', 'id', 'name')}
    form_info = {
        row['id']: (row['languageReference'], row['parameterReference'])
        for row in cldf_dataset.iter_rows(
            'FormTable', 'id', 'languageReference', 'parameterReference')}

    # TODO switch to a less ad-hoc solution once a standard is established
    cognate_columns = ['formReference', 'cognatesetReference', 'Cognate_Coding']
    if cognate_coding is not None:
        cognate_columns.append('Cognate_Coding')

    # collect cognate sets and language varieties
    doculects, cognates, words = set(), defaultdict(set), defaultdict(set)
    for row in cldf_dataset.iter_rows('CognateTable', *cognate_columns):
        # TODO less ad-hoc solution for filtering cognates
        if cognate_coding and cognate_coding not in row['Cognate_Coding']:
            continue
        language_id, concept_id = form_info[row['formReference']]
        concept = concepts[concept_id]
        cognateset = row['cognatesetReference']

        doculects.add(language_id)
        words[concept].add(language_id)
        cognates[(concept, cognateset)].add(language_id)

    return (doculects, cognates, words)


def make_nexus(doculects, cognates, words, ascertainment='none'):
    """Make a nexus object from the output of get_cognates."""
    nex = NexusWriter()

    # handle ascertainment corrections:
    if ascertainment == 'overall':
        for d in doculects:
            nex.add(d, '0ascertainment', '0')
    elif ascertainment == 'word':
        for w in words:
            for d in doculects:
                state = '0' if d in words[w] else '?'
                nex.add(d, '%s_0ascertainment' % w, state)
    elif ascertainment == 'none':
        pass
    elif isinstance(ascertainment, dict):
        # need a lookup of <cogset> -> <partition>
        partitionmap = {}
        for partition in ascertainment:
            for cognate in ascertainment[partition]:
                assert cognate not in partitionmap,\
                    'Cognate set %r in two partitions' % cognate
                partitionmap[cognate] = partition

        for s in ascertainment:
            for d in doculects:
                # TODO ? or 0
                # state = '0' if d in words[w] else '?'
                state = '0'
                nex.add(d, '%s_0ascertainment' % s, state)
    else:
        raise ValueError("Unknown ascertainment correction: %s" % ascertainment)

    # add data
    for cogset in sorted(cognates):
        for doculect in doculects:
            # identify state
            if doculect in cognates[cogset]:
                state = '1'
            elif doculect not in cognates[cogset] and doculect in words[cogset[0]]:
                state = '0'
            elif doculect not in words[cogset[0]]:
                state = '?'
            else:  # pragma: no cover
                raise RuntimeError("yikes. something is badly broken")

            if isinstance(ascertainment, dict):
                partition = partitionmap[cogset]
                label = "%s_%s_%s" % (partition, cogset[0], cogset[1])
            else:
                label = "%s_%s" % cogset
            nex.add(doculect, label, state)

    return nex


def get_partitions_from_nexus(nex):
    if not isinstance(nex, NexusWriter):
        raise TypeError('expected a NexusWriter instance')

    partitions, partition = defaultdict(list), None
    # handle null case first
    ascchars = [c.endswith("0ascertainment") for c in nex.characters]
    ascchars = [c for c in ascchars if c]
    if len(ascchars) < 2:
        return {}

    for i, char in enumerate(sorted(nex.characters), 1):
        if char.endswith("0ascertainment"):
            partition = char.rsplit("_", 1)[0]
        assert partition is not None, "badly formatted partitions!"
        partitions[partition].append(i)
    return partitions


def add_to_nexus(filename, partitions):
    with open(filename, 'a') as handle:
        handle.write("\n")
        handle.write("begin sets;\n")
        for p in partitions:
            charids = ", ".join([str(i) for i in sorted(partitions[p])])
            handle.write("\tcharset %s = %s;\n" % (p, charids))
        handle.write("end;\n\n")


def register(parser):
    add_dataset_spec(parser)
    parser.add_argument(
        '-o', '--output', type=Path, metavar='FILENAME',
        default=argparse.SUPPRESS,
        help='Output file [default: ./<id>.nex]')
    parser.add_argument(
        '-c', '--cognate-coding', dest='cognate_coding',
        help='set cognate coding (broad, fine, or any)', action='store',
        default='broad')
    parser.add_argument(
        '-a', "--ascertainment", dest='ascertainment',
        help="set ascertainment correction mode", action='store',
        default='none')


def run_makenexus(dataset, args):
    if args.ascertainment.lower() in ("none", "overall", "word"):
        asc = args.ascertainment.lower()
    elif Path(args.ascertainment).is_file():
        asc = read_partitions(Path(args.ascertainment))
    else:
        print(
            'Unknown Ascertainment type %s' % args.ascertainment,
            file=sys.stderr)
        return

    if args.cognate_coding == 'broad':
        cognate_coding = 'broad'
    elif args.cognate_coding == 'fine':
        cognate_coding = 'fine'
    elif args.cognate_coding == 'any':
        cognate_coding = None
    else:
        print(
            "Unkown cognate coding: '{}'.".format(args.cognate_coding),
            "Must be 'broad', 'fine', or 'any'.",
            file=sys.stderr)
        return

    try:
        cldf_dataset = next(iter_datasets(dataset.cldf_dir))
    except StopIteration:
        print(
            '{}: no cldf dataset found'.format(dataset.cldf_dir),
            file=sys.stderr)
        return

    if 'CognateTable' not in cldf_dataset:
        print('{}: no CognateTable'.format(dataset.cldf_dir), file=sys.stderr)
        return
    if 'FormTable' not in cldf_dataset:
        print('{}: no FormTable'.format(dataset.cldf_dir), file=sys.stderr)
        return
    if 'ParameterTable' not in cldf_dataset:
        print('{}: no ParameterTable'.format(dataset.cldf_dir), file=sys.stderr)
        return

    cogs = get_cognates(cldf_dataset, cognate_coding)
    nex = make_nexus(*cogs, ascertainment=asc)
    nex.write_to_file(args.output, charblock=True)

    # add sets -- get partitions from nexus so we make sure to have
    # the correct character ids
    parts = get_partitions_from_nexus(nex)
    if parts:
        add_to_nexus(args.output, parts)


def run(args):
    with_dataset(args, run_makenexus)
