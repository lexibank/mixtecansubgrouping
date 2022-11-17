from pathlib import Path
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank import progressbar
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
        wl = lingpy.Wordlist(str(self.raw_dir / 'sm3_mixtecan_cognates.tsv'))
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
        for k in progressbar(wl, desc='wl-to-cldf', total=len(wl)):
            if wl[k, 'concept'] in concepts and wl[k, "doculect"] in languages:
                if wl[k, 'form']:
                    if len(wl[k, "tokens"].n) != len(wl[k, "cogids_broad"].split()):
                        errors.add("partial cognates: {0} / {1} / {2}".format(
                            k, str(wl[k, "tokens"]), wl[k, "cogids_broad"]))
                    args.writer.add_form_with_segments(
                        Local_ID=k,
                        Language_ID=languages[wl[k, 'doculect']],
                        Parameter_ID=concepts[wl[k, 'concept']],
                        Value=wl[k, 'value'],
                        Form=wl[k, 'form'],
                        Segments=wl[k, "tokens"],
                        Source=wl[k, 'source'],
                        Partial_Cognacy=wl[k, "cogids_broad"])
            else:
                if wl[k, "concept"] not in concepts:
                    errors.add("concept missing {0}".format(wl[k, "concept"]))
                elif wl[k, "doculect"] not in languages:
                    errors.add("language missing {0}".format(wl[k, "doculect"]))
        for i, error in enumerate(sorted(errors)):
            print("{0:4}".format(i + 1), error)
