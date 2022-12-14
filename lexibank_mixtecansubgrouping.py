from pathlib import Path
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.models import Language, Concept, Lexeme
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
    Partial_Cognacy = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = 'mixtecansubgrouping'
    language_class = CustomLanguage
    concept_class = CustomConcept
    lexeme_class = CustomLexeme

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
                cognate_id_str = word_list[key, "cogids_broad"]
                form_count = len(segmented_word.n)
                cognate_ids = cognate_id_str.split()
                cognate_id_count = len(cognate_ids)
                if form_count != cognate_id_count:
                    errors.add("partial cognates: {0} / {1} / {2}".format(
                        key, str(segmented_word), cognate_id_str))
                lexeme = args.writer.add_form_with_segments(
                    Local_ID=key,
                    Language_ID=languages[word_list[key, 'doculect']],
                    Parameter_ID=concepts[word_list[key, 'concept']],
                    Value=word_list[key, 'value'],
                    Form=word_list[key, 'form'],
                    Segments=word_list[key, "tokens"],
                    Source=word_list[key, 'source'],
                    Partial_Cognacy=word_list[key, "cogids_broad"])
                for cognate_id in cognate_ids:
                    args.writer.add_cognate(
                        lexeme=lexeme,
                        Cognateset_ID=cognate_id)

        for i, error in enumerate(sorted(errors)):
            print("{0:4}".format(i + 1), error)
