#!/usr/bin/env python2

import argparse
import sys
import xml.etree.ElementTree as ET

import corpus.models as models

def dbGetLanguage(id):
    try:
        language = models.Language.objects.get(name=id)
        return language
    except models.Language.DoesNotExist:
        argumentParser.error("Language \"%s\" does not exist in the database" % id)

class TranslationSystemInfo:
    # Basically a dictionary from system ids to (database) systems and documents

    class info:
        system = None
        document = None

        def __init__(self, system, document):
            self.system = system
            self.document = document

    def __init__(self, sourceDocument, targetLanguage):
        self.sourceDocument = sourceDocument
        self.targetLanguage = targetLanguage
        self.infoDict = {}

    def __getitem__(self, id):
        thisInfo = self.infoDict.get(id)
        if not thisInfo:
            try:
                system = models.TranslationSystem.objects.get(name=id)
            except models.TranslationSystem.DoesNotExist:
                system = models.TranslationSystem(name=id)
                system.save()
            document = models.TranslatedDocument(source=self.sourceDocument,
                                                 translation_system=system,
                                                 language=self.targetLanguage)
            document.save()
            thisInfo = self.info(system, document)
            self.infoDict[id] = thisInfo
        return thisInfo

    def getSystemIds(self):
        return self.infoDict.keys()

argumentParser = argparse.ArgumentParser()
argumentParser.add_argument("file", help="file to read the data from", type=argparse.FileType())
argumentParser.add_argument("-e", "--error-on-duplicates", dest="errorOnDuplicates", default=False, action="store_true", help="Abort with an error on duplicate entities (corpora, translations, etc.)")
args = argumentParser.parse_args()

log = lambda x : sys.stdout.write("%s\n" % x)
warning = lambda x : sys.stderr.write("Warning: %s\n" % x)

tree = ET.parse(args.file)
root = tree.getroot()

corpusName = "r2-" + root.get("id")
sourceLanguageId = root.get("source-language")
targetLanguageId = root.get("target-language")

sourceLanguage = dbGetLanguage(sourceLanguageId)
targetLanguage = dbGetLanguage(targetLanguageId)
log("Source language: %s" % sourceLanguage.english_name)
log("Target language: %s" % targetLanguage.english_name)

try:
    document = models.SourceDocument.objects.get(custom_id=corpusName,
                                                 language=sourceLanguage)
    documentAlreadyExists = True
    if args.errorOnDuplicates:
        argumentParser.error("Document \"%s\" (%s) already exists in the database, aborting\n"
                         % (corpusName, sourceLanguage.english_name))
    else:
        warning("Document \"%s\" (%s) already exists in the database, sentence ordering may become corrupt\n" % (corpusName, sourceLanguage.english_name))
except models.SourceDocument.DoesNotExist:
    documentAlreadyExists = False
    document = models.SourceDocument(custom_id=corpusName, language=sourceLanguage)
    document.save()

try:
    corpus = models.Corpus.objects.get(custom_id=corpusName, language=sourceLanguage)
    if args.errorOnDuplicates:
        argumentParser.error("Corpus \"%s\" (%s) already exists in the database, aborting\n"
                             % (corpusName, sourceLanguage.english_name))
except models.Corpus.DoesNotExist:
    corpus = None

sentenceCount = 0
systemInfoInventary = TranslationSystemInfo(document, targetLanguage)
for c in root.iter():
    if c.tag == "seg":
        sentenceId = c.get("id")
    elif c.tag == "source":
        try:
            sentence = models.SourceSentence.objects.get(custom_id=sentenceId,
                                                         document=document)
            if sentence:
                if args.errorOnDuplicates:
                    argumentParser.error("Sentence %s already exists in the database" % sentenceId)
        except models.SourceSentence.DoesNotExist:
            sentence = models.SourceSentence(text=c.text.strip())
            sentence.document = document
            sentence.custom_id = sentenceId
            sentence.save()
        sentenceCount += 1
        sys.stdout.write("\r%d sentences" % sentenceCount)
        sys.stdout.flush()
    elif c.tag == "translation":
        systemId = c.get("system")
        systemInfo = systemInfoInventary[systemId]
        if models.Translation.objects.filter(source_sentence=sentence,
                                             document=systemInfo.document).exists():
            if args.errorOnDuplicates:
                argumentParser.error("Translation of sentence %s by system %s already exists in the database" % (sentenceId, systemId))
        else:
            translation = models.Translation(source_sentence=sentence,
                                             text=c.text.strip(),
                                             document=systemInfo.document)
            translation.save()
        
sys.stdout.write("\r") # Clear the sentence counter
document.save()
log("Document %s created with %d sentences" % (corpusName, sentenceCount))

if not corpus:
    corpus = models.Corpus(custom_id=corpusName, language=sourceLanguage)
    corpus.save()
if not documentAlreadyExists:
    c2d = models.Document2Corpus(document=document, corpus=corpus, order=0)
    c2d.save()
    log("Corpus %s created" % corpusName)
log("Translations added for: %s" % " ".join(systemInfoInventary.getSystemIds()))
