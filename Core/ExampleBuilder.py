"""
Base class for ExampleBuilders
"""
__version__ = "$Revision: 1.32 $"

from SentenceGraph import SentenceGraph
from SentenceGraph import getCorpusIterator
from IdSet import IdSet
import sys, os, types
import gzip
import itertools
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.ProgressCounter import ProgressCounter
#from Utils.Parameters import getArgs
#from Utils.Parameters import splitParameters
#from Utils.Parameters import toString
import Utils.Parameters
import Core.ExampleUtils as ExampleUtils
import SentenceGraph
#IF LOCAL
from ExampleBuilders.ExampleStats import ExampleStats
#ENDIF

class ExampleBuilder:
    """ 
    ExampleBuilder is the abstract base class for specialized example builders.
    Example builders take some data and convert it to examples usable by e.g. SVMs.
    An example builder writes three files, an example-file (in extended Joachim's
    SVM format) and .class_names and .feature_names files, which contain the names
    for the class and feature id-numbers. An example builder can also be given
    pre-existing sets of class and feature ids (optionally in files) so that the
    generated examples are consistent with other, previously generated examples.
    """
    def __init__(self, classSet=None, featureSet=None):
        if(type(classSet) == types.StringType):
            self.classSet = IdSet(filename=classSet)
        else:
            self.classSet = classSet
        
        if(type(featureSet) == types.StringType):
            self.featureSet = IdSet(filename=featureSet)
        else:
            self.featureSet = featureSet
        
        self.featureTag = ""      
        self.exampleStats = ExampleStats()
        self.parse = None
        self.tokenization = None
        #self.idFileTag = None
        self.classIdFilename = None
        self.featureIdFilename = None
    
    def getParameters(self, parameters, defaults=None, limitValues = None):
        return Utils.Parameters.get(parameters, defaults=defaults, limitValues=limitValues)
    
    def setFeature(self, name, value):
        self.features[self.featureSet.getId(self.featureTag+name)] = value
    
    def getElementCounts(self, filename):
        print >> sys.stderr, "Counting elements:",
        if filename.endswith(".gz"):
            f = gzip.open(filename, "rt")
        else:
            f = open(filename, "rt")
        counts = {"documents":0, "sentences":0}
        for line in f:
            if "<document " in line:
                counts["documents"] += 1
            elif "<sentence " in line:
                counts["sentences"] += 1
        f.close()
        print >> sys.stderr, counts
        return counts

    def saveIds(self):
        if self.classIdFilename != None:
            print >> sys.stderr, "Saving class names to", self.classIdFilename
            self.classSet.write(self.classIdFilename)
        else:
            print >> sys.stderr, "Class names not saved"
        if self.featureIdFilename != None:
            print >> sys.stderr, "Saving feature names to", self.featureIdFilename
            self.featureSet.write(self.featureIdFilename)
        else:
            print >> sys.stderr, "Feature names not saved"

    def processCorpus(self, input, output, gold=None, append=False, allowNewIds=True):
        # Create intermediate paths if needed
        if os.path.dirname(output) != "" and not os.path.exists(os.path.dirname(output)):
            os.makedirs(os.path.dirname(output))
        # Open output file
        openStyle = "wt"
        if append:
            print "Appending examples"
            openStyle = "at"
        if output.endswith(".gz"):
            outfile = gzip.open(output, openStyle)
        else:
            outfile = open(output, openStyle)
        
        # Build examples
        self.exampleCount = 0
        if type(input) in types.StringTypes:
            self.elementCounts = self.getElementCounts(input)
            if self.elementCounts["sentences"] > 0:
                self.progress = ProgressCounter(self.elementCounts["sentences"], "Build examples")
            else:
                self.elementCounts = None
                self.progress = ProgressCounter(None, "Build examples")
        else:
            self.elementCounts = None
            self.progress = ProgressCounter(None, "Build examples")
        
        self.calculatePredictedRange(self.getSentences(input, self.parse, self.tokenization))
        
        inputIterator = getCorpusIterator(input, None, self.parse, self.tokenization)            
        
        #goldIterator = []
        if gold != None:
            goldIterator = getCorpusIterator(gold, None, self.parse, self.tokenization)
            for inputSentences, goldSentences in itertools.izip_longest(inputIterator, goldIterator, fillvalue=None):
                assert inputSentences != None
                assert goldSentences != None
                self.processDocument(inputSentences, goldSentences, outfile)
        else:
            for inputSentences in inputIterator:
                self.processDocument(inputSentences, None, outfile)
        outfile.close()
        self.progress.endUpdate()
        
        # Show statistics
        print >> sys.stderr, "Examples built:", self.exampleCount
        print >> sys.stderr, "Features:", len(self.featureSet.getNames())
        if self.exampleStats.getExampleCount() > 0:
            self.exampleStats.printStats()
    
        # Save Ids
        if allowNewIds:
            self.saveIds()
    
    def processDocument(self, sentences, goldSentences, outfile):
        #calculatePredictedRange(self, sentences)            
        for i in range(len(sentences)):
            sentence = sentences[i]
            goldSentence = None
            if goldSentences != None:
                goldSentence = goldSentences[i]
            self.progress.update(1, "Building examples ("+sentence.sentence.get("id")+"): ")
            self.processSentence(sentence, outfile, goldSentence)
    
    def processSentence(self, sentence, outfile, goldSentence=None):
        if sentence.sentenceGraph != None:
            goldGraph = None
            if goldSentence != None:
                goldGraph = goldSentence.sentenceGraph
            self.exampleCount += self.buildExamplesFromGraph(sentence.sentenceGraph, outfile, goldGraph)

    @classmethod
    def run(cls, input, output, parse, tokenization, style, classIds=None, featureIds=None, gold=None, append=False, allowNewIds=True):
        print >> sys.stderr, "Running", cls.__name__
        print >> sys.stderr, "  input:", input
        print >> sys.stderr, "  gold:", gold
        print >> sys.stderr, "  output:", output, "(append:", str(append) + ")"
        print >> sys.stderr, "  add new class/feature ids:", allowNewIds
        if not isinstance(style, types.StringTypes):
            style = toString(style)
        print >> sys.stderr, "  style:", style
        if tokenization == None: 
            print >> sys.stderr, "  parse:", parse
        else:
            print >> sys.stderr, "  parse:", parse + ", tokenization:", tokenization
        classSet, featureSet = cls.getIdSets(classIds, featureIds, allowNewIds) #cls.getIdSets(idFileTag)
        builder = cls(style=style, classSet=classSet, featureSet=featureSet)
        #builder.idFileTag = idFileTag
        builder.classIdFilename = classIds
        builder.featureIdFilename = featureIds
        builder.parse = parse ; builder.tokenization = tokenization
        builder.processCorpus(input, output, gold, append=append, allowNewIds=allowNewIds)
        return builder

    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph=None):
        raise NotImplementedError
    
    def definePredictedValueRange(self, sentences, elementName):
        pass
    
    def getPredictedValueRange(self):
        return None
    
    @classmethod
    def getIdSets(self, classIds=None, featureIds=None, allowNewIds=True):
        # Class ids
        #print classIds
        #print featureIds
        if classIds != None and os.path.exists(classIds):
            print >> sys.stderr, "Using predefined class names from", classIds
            classSet = IdSet(allowNewIds=allowNewIds)
            classSet.load(classIds)
        else:
            print >> sys.stderr, "No predefined class names"
            classSet = None
        # Feature ids
        if featureIds != None and os.path.exists(featureIds):
            print >> sys.stderr, "Using predefined feature names from", featureIds
            featureSet = IdSet(allowNewIds=allowNewIds)
            featureSet.load(featureIds)
        else:
            print >> sys.stderr, "No predefined feature names"
            featureSet = None
        return classSet, featureSet
        
#        if idFileTag != None and os.path.exists(idFileTag + ".feature_names.gz") and os.path.exists(idFileTag + ".class_names"):
#            print >> sys.stderr, "Using predefined class and feature names"
#            featureSet = IdSet()
#            featureSet.load(idFileTag + ".feature_names.gz")
#            classSet = IdSet()
#            classSet.load(idFileTag + ".class_names")
#            return classSet, featureSet
#        else:
#            print >> sys.stderr, "No predefined class or feature-names"
#            if idFileTag != None:
#                assert(not os.path.exists(idFileTag + ".feature_names.gz")), idFileTag
#                assert(not os.path.exists(idFileTag + ".class_names")), idFileTag
#            return None, None


    def getSentences(self, input, parse, tokenization, removeNameInfo=False):
        if type(input) != types.ListType:
            # Load corpus and make sentence graphs
            corpusElements = SentenceGraph.loadCorpus(input, parse, tokenization, removeNameInfo=removeNameInfo)
            sentences = []
            for sentence in corpusElements.sentences:
                if sentence.sentenceGraph != None: # required for event detection
                    sentences.append( [sentence.sentenceGraph,None] )
            return sentences
        else: # assume input is already a list of sentences
            assert(removeNameInfo == False)
            return input

    def calculatePredictedRange(self, sentences):
        print >> sys.stderr, "Defining predicted value range:",
        sentenceElements = []
        for sentence in sentences:
            sentenceElements.append(sentence[0].sentenceElement)
        self.definePredictedValueRange(sentenceElements, "entity")
        print >> sys.stderr, self.getPredictedValueRange()

def addBasicOptions(optparser):
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file for the examples")
    optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="parse")
    optparser.add_option("-x", "--exampleBuilderParameters", default=None, dest="parameters", help="Parameters for the example builder")
    optparser.add_option("-b", "--exampleBuilder", default="SimpleDependencyExampleBuilder", dest="exampleBuilder", help="Example Builder Class")
    optparser.add_option("-d", "--predefined", default=None, dest="predefined", help="Directory with predefined class_names.txt and feature_names.txt files")

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPIVisible.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    addBasicOptions(optparser)
    (options, args) = optparser.parse_args()
    
    print >> sys.stderr, "Importing modules"
    exec "from ExampleBuilders." + options.exampleBuilder + " import " + options.exampleBuilder + " as ExampleBuilderClass"
    
    #input, output, parse, tokenization, style, classIds=None, featureIds=None, gold=None, append=False)
    ExampleBuilderClass.run(options.input, options.output, options.parse, options.tokenization, options.parameters, 
                            options.predefined+"/unmerging-ids.classes",
                            options.predefined+"/unmerging-ids.features",
                            options.input.replace("-nodup", "") )
