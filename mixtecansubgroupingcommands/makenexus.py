#!/usr/bin/env python3
# original script created by Simon J. Greenhill <simon@simon.net.nz>
# cldfbench version by Johannes Englisch <johannes_englisch@eva.mpg.de>

# TODO docstring
"""..."""

from collections import defaultdict
from pathlib import Path

import csvw
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


def get_cognates(filename, cognate_column='COGIDS_BROAD'):
    """
    Collect cognate sets from column `cognate_column` in `filename`.

    Returns:
        - a set of language varieties
        - a dict of words to language sets (word -> {l1, l2, l3})
        - a dict of cognates to language sets (cogset -> [l1, l2, l3])
    """
    # collect cognate sets and language varieties
    doculects, cognates, words = set(), defaultdict(set), defaultdict(set)
    for row in read(filename):
        if cognate_column not in row:
            raise ValueError('Unknown column %s' % cognate_column)

        doculects.add(row['DOCULECT'])
        words[row['CONCEPT']].add(row['DOCULECT'])
        for cog in parse_cognates(row[cognate_column]):
            cognates[(row['CONCEPT'], cog)].add(row['DOCULECT'])
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


def parse_cognates(cog):
    """Parse out cognate sets from the tsv file."""
    if not len(cog.strip()):
        return []
    return [c for c in cog.split(" ")]


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
    parser.add_argument("filename", help='input filename (.tsv)', type=Path)
    parser.add_argument("outfilename", help='output filename (.nex)', type=Path)
    parser.add_argument(
        '-c', "--column", dest='column',
        help="set cognate column (COGIDS_BROAD/COGIDS_FINE)", action='store',
        default='COGIDS_BROAD')
    parser.add_argument(
        '-a', "--ascertainment", dest='ascertainment',
        help="set ascertainment correction mode", action='store',
        default='none')


def run(args):
    if args.ascertainment.lower() in ("none", "overall", "word"):
        asc = args.ascertainment.lower()
    elif Path(args.ascertainment).is_file():
        asc = read_partitions(Path(args.ascertainment))
    else:
        raise ValueError("Unknown Ascertainment type %s" % args.ascertainment)

    if not args.filename.exists():
        raise IOError("Unable to find filename %s" % args.filename)

    cogs = get_cognates(args.filename, args.column)
    nex = make_nexus(*cogs, ascertainment=asc)
    nex.write_to_file(args.outfilename, charblock=True)

    # add sets -- get partitions from nexus so we make sure to have
    # the correct character ids
    parts = get_partitions_from_nexus(nex)
    if parts:
        add_to_nexus(args.outfilename, parts)
