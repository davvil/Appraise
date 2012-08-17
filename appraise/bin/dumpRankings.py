#!/usr/bin/env python2

import optparse
import os
import sys

import corpus.models as corpusM
import evaluation.models as evalM

order = [
      "taskId"
    , "taskName"
    , "sourceDocument"
    , "sourceSentence"
    , "user"
    , "duration"
    , "rankings"
]

optionParser = optparse.OptionParser(usage="%s <options> [<queries>]" % os.environ["ESMT_PROG_NAME"], add_help_option=False)
optionParser.add_option("-h", "--help", action="help", help=optparse.SUPPRESS_HELP)
optionParser.add_option("-H", "--header", help="Show header", action="store_true", dest="showHeader")
optionParser.add_option("-d", "--delimiter", help="Delimiter for fields (default: tab)",
                        metavar="SEP", default="\t")
(options, args) = optionParser.parse_args()

out = sys.stdout

if options.showHeader:
    string = options.delimiter.join(order)
    out.write("%s\n" % string)
    out.write("%s\n" % ("-" * len(string.expandtabs())))
    sys.exit(0)

if len(args) == 0:
    rankings = evalM.RankingResult.objects.all()
else:
    queries = {}
    for a in args:
        (key, value) = a.split("=")
        queries[key] = value
    rankings = evalM.RankingResult.objects.filter(**queries)
    
for r in rankings:
    evalItem = r.item
    evalTask = evalItem.task
    sourceSentence = evalItem.source_sentence
    sourceDocument = corpusM.SourceDocument.objects.get(id=sourceSentence.document.id)
    fields = []

    fields.append(evalTask.task_id)
    fields.append(evalTask.task_name)

    fields.append(sourceDocument.custom_id)

    fields.append(sourceSentence.custom_id)

    fields.append(r.user.username)

    fields.append('{}'.format(r.duration))

    if r.skipped:
        fields.append("__SKIPPED__")
    else:
        for rank in r.results.all():
            system = corpusM.TranslatedDocument.objects.get(id=rank.translation.document.id).translation_system
            fields.append(":".join([system.name, str(rank.rank)]))
    
    out.write("%s\n" % options.delimiter.join(fields))