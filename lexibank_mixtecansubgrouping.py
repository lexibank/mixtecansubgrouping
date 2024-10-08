from pathlib import Path
import re

from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.models import Language, Concept, Lexeme, Cognate
from clldutils.misc import slug
import attr

import lingpy


@attr.s
class CustomLanguage(Language):
    Location = attr.ib(default=None)
    SubGroup = attr.ib(default=None)
    Number = attr.ib(default=None)


@attr.s
class CustomConcept(Concept):
    Number = attr.ib(default=None)


@attr.s
class CustomLexeme(Lexeme):
    Floating_Tone = attr.ib(default=None)
    Loan = attr.ib(default=None)
    Loan_Source = attr.ib(default=None)
    Partial_Cognacy_Broad = attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(list),
        metadata={'separator': ' '})
    Partial_Cognacy_Fine = attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(list),
        metadata={'separator': ' '})


@attr.s
class CustomCognate(Cognate):
    Morpheme_Index = attr.ib(default=None)
    Cognate_Coding = attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(list),
        metadata={'separator': ';'})


class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = 'mixtecansubgrouping'
    language_class = CustomLanguage
    concept_class = CustomConcept
    lexeme_class = CustomLexeme
    cognate_class = CustomCognate
    writer_options = dict(keep_languages=False, keep_parameters=False)

    def cmd_makecldf(self, args):
        word_list = lingpy.Wordlist(
            str(self.raw_dir / 'sm3_mixtecan_cognates.tsv'))
        args.writer.add_sources()

        languages = {}
        for language in self.languages:
            language['ID'] = re.sub('_[A-Z]+$', '', language['ID'])
            language['Name'] = re.sub('_[A-Z]+$', '', language['Name'])
            if language['Name'] not in languages:
                languages[language['Name']] = language['ID']
                args.writer.add_language(**language)

        concepts = {}
        for concept in self.conceptlists[0].concepts.values():
            id_ = '{}_{}'.format(concept.number, slug(concept.english))
            args.writer.add_concept(
                ID=id_,
                Name=concept.english,
                Number=concept.number,
                Concepticon_ID=concept.concepticon_id,
                Concepticon_Gloss=concept.concepticon_gloss)
            concepts[concept.english] = id_

        errors = set()
        for key in word_list:
            if word_list[key, "doculect"] not in languages:
                errors.add("language missing {0}".format(
                    word_list[key, "doculect"]))
            elif word_list[key, "concept"] not in concepts:
                errors.add("concept missing {0}".format(
                    word_list[key, "concept"]))
            elif word_list[key, 'form']:
                segmented_word = word_list[key, "tokens"]
                form_count = len(segmented_word.n)

                broad_cognate_id_str = word_list[key, 'cogids_broad']
                broad_cognate_ids = broad_cognate_id_str.split()
                if form_count != len(broad_cognate_ids):
                    errors.add("partial cognates: {0} / {1} / {2}".format(
                        key, str(segmented_word), broad_cognate_id_str))

                fine_cognate_id_str = word_list[key, 'cogids_fine']
                fine_cognate_ids = fine_cognate_id_str.split()
                if form_count != len(fine_cognate_ids):
                    errors.add("partial cognates: {0} / {1} / {2}".format(
                        key, str(segmented_word), fine_cognate_id_str))

                lexeme = args.writer.add_form_with_segments(
                    Local_ID=key,
                    Language_ID=languages[word_list[key, 'doculect']],
                    Parameter_ID=concepts[word_list[key, 'concept']],
                    Value=word_list[key, 'value'],
                    Form=word_list[key, 'form'],
                    Segments=word_list[key, "tokens"],
                    Source=word_list[key, 'source'],
                    Partial_Cognacy_Broad=broad_cognate_ids,
                    Partial_Cognacy_Fine=fine_cognate_ids)

                cognate_ids = list(enumerate(broad_cognate_ids))
                cognate_ids.extend(
                    (morpheme_index, id_)
                    for morpheme_index, id_ in enumerate(fine_cognate_ids)
                    if id_ not in broad_cognate_ids)

                for morpheme_index, cognate_id in cognate_ids:
                    is_broad = cognate_id in broad_cognate_ids
                    is_fine = cognate_id in fine_cognate_ids
                    if is_broad and is_fine:
                        cognate_coding = ['broad', 'fine']
                    elif is_broad:
                        cognate_coding = ['broad']
                    else:
                        cognate_coding = ['fine']

                    args.writer.add_cognate(
                        lexeme=lexeme,
                        Cognateset_ID=cognate_id,
                        Cognate_Coding=cognate_coding,
                        Morpheme_Index=morpheme_index)

        for i, error in enumerate(sorted(errors)):
            print("{0:4}".format(i + 1), error)
