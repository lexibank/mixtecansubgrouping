from pathlib import Path
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
    Spanish_Gloss = attr.ib(default=None)
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

    def cmd_makecldf(self, args):
        word_list = lingpy.Wordlist(
            str(self.raw_dir / 'sm3_mixtecan_cognates.tsv'))
        args.writer.add_sources()

        languages = {}
        for language in self.languages:
            args.writer.add_language(**language)
            languages[language["Name"]] = language["ID"]

        concepts = {}
        for concept in self.concepts:
            id_ = '{}_{}'.format(concept['NUMBER'], slug(concept['ENGLISH']))
            args.writer.add_concept(
                ID=id_,
                Name=concept['ENGLISH'],
                Number=concept['NUMBER'],
                Concepticon_ID=concept['CONCEPTICON_ID'],
                Concepticon_Gloss=concept['CONCEPTICON_GLOSS'],
                Spanish_Gloss=concept['SPANISH'])
            concepts[concept['ENGLISH']] = id_

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

                cognate_ids = broad_cognate_ids[::]
                cognate_ids.extend(
                    id_
                    for id_ in fine_cognate_ids
                    if id_ not in broad_cognate_ids)

                def _cognate_coding(id_):
                    in_broad = id_ in broad_cognate_ids
                    in_fine = id_ in fine_cognate_ids
                    if in_broad and in_fine:
                        return ['broad', 'fine']
                    elif in_broad:
                        return ['broad']
                    else:
                        return ['fine']

                for cognate_id in cognate_ids:
                    args.writer.add_cognate(
                        lexeme=lexeme,
                        Cognateset_ID=cognate_id,
                        Cognate_Coding=_cognate_coding(cognate_id))

        for i, error in enumerate(sorted(errors)):
            print("{0:4}".format(i + 1), error)
