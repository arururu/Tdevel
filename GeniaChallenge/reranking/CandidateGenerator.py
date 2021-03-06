#Generates most probable candidates for sentences
import parseGifxml
import sys
import nbest
from optparse import OptionParser
import Reranker
import random

#TODO: sentence level f-score
#Corpus level f-score
#Iterator for generating candidates
#oracle

def instantiateOptionParser():
    optparser = OptionParser(usage="python %prog [options] TRAINFILE PREDICTION_FILE GSTANDARD_FILE")
    optparser.add_option("-n", "--nbest", default = 10, dest = "nbest", help = "the maximum number of candidates to be generated per sentence", type = "int")
    (options, args) = optparser.parse_args()
    return optparser
    

def compare(x,y):
    if x[0] > y[0]:
        return 1
    elif x[0] == y[0]:
        return 0
    else:
        return -1

def score(tp, fp, fn):
    s = tp-fp-fn
    return s

def getSimplePredictions(entities, pairs):
    """Returns the prediction lists with no normalizations,
    preprocessing etc."""
    predictions = {}
    for pair in pairs:
        e1 = pair.attrib["e1"]
        e2 = pair.attrib["e2"]
        key = e1+"_"+e2
        values = pair.attrib["predictions"].split(",")
        values = [(float((x.split(":")[1])),x.split(":")[0]) for x in values]
        values.sort(compare)
        predictions[key] =values
    return predictions

def getGSEdges(pairs, entities):
    gsedges = set([])
    outside_count = 0
    entity_info = {}
    for entity in entities:
        head, typ_e = entity.attrib["headOffset"], entity.attrib["type"]
        entity_info[entity.attrib["id"]] = (head, typ_e)
    for pair in pairs:
        if pair.attrib["e1"] in entity_info and pair.attrib["e2"] in entity_info:
            head1, type1 = entity_info[pair.attrib["e1"]]
            head2, type2 = entity_info[pair.attrib["e2"]]
            etype = pair.attrib["type"]
            gsedges.add(etype+head1+type1+head2+type2)
        else:
            outside_count += 1
    return gsedges, outside_count

def getPredictedEdges(predictions, keys, entities, choices):
    choices = choices[1]
    assert len(predictions) == len(choices)
    entity_info = {}
    p_edges = set([])
    for entity in entities:
        head, typ_e = entity.attrib["headOffset"], entity.attrib["type"]
        entity_info[entity.attrib["id"]] = (head, typ_e)
    for key, index in zip(keys, choices):
        values = predictions[key]
        etype = values[index][1]
        if not etype == "neg":
            e1, e2 = key.split("_")
            head1, type1 = entity_info[e1]
            head2, type2 = entity_info[e2]
            p_edges.add(etype+head1+type1+head2+type2)
    return p_edges

def getGSOutputRepresentation(entities, pairs):
    entity_types = {}
    output_edges = {}
    for entity in entities:
        typ_e = entity.attrib["type"]
        entity_types[entity.attrib["id"]] = typ_e
    for pair in pairs:
        e1 = pair.attrib["e1"]
        e2 = pair.attrib["e2"]
        if e1 in entity_types and e2 in entity_types:
            type2 = entity_types[e2]
            etype = pair.attrib["type"]
            if not e1 in output_edges:
                output_edges[e1] = {}
            if not etype+type2 in output_edges[e1]:
                output_edges[e1][etype+type2] = 1
            else:
                output_edges[e1][etype+type2] += 1
        else:
            pass
    featureset = {}
    for key in entity_types.keys():
        etype = entity_types[key]
        edges = []
        if key in output_edges:
            for key2 in output_edges[key].keys():
                edges.append(key2+"_"+str(output_edges[key][key2]))
            edges.sort()
            fname = etype+"_"+"".join(e for e in edges)
        
            if not fname in featureset:
                featureset[fname] = 1
            else:
                featureset[fname] += 1
    for fset in featureset:
        if len(fset) == 0:
            fset["none"] = 10
    return featureset

def getOutputRepresentation(predictions, keys, entities, choices):
    #A bit more complicated version of the previous routine
    choices = choices[1]
    assert len(predictions) == len(choices)
    entity_types = {}
    output_edges = {}
    for entity in entities:
        head, typ_e = entity.attrib["headOffset"], entity.attrib["type"]
        entity_types[entity.attrib["id"]] = typ_e
    for key, index in zip(keys, choices):
        values = predictions[key]
        etype = values[index][1]
        if not etype == "neg":
            e1, e2 = key.split("_")
            type2 = entity_types[e2]
            if not e1 in output_edges:
                output_edges[e1] = {}
            if not etype+type2 in output_edges[e1]:
                output_edges[e1][etype+type2] = 1
            else:
                output_edges[e1][etype+type2] += 1
    featureset = {}
    for key in entity_types.keys():
        etype = entity_types[key]
        edges = []
        if key in output_edges:
            for key2 in output_edges[key].keys():
                edges.append(key2+"_"+str(output_edges[key][key2]))
            edges.sort()
            fname = etype+"_"+"".join(e for e in edges)
            if not fname in featureset:
                featureset[fname] = 1
            else:
                featureset[fname] += 1
    for fset in featureset:
        if len(fset) == 0:
            fset["none"] = 10
    return featureset
            

def getEntitiesAndPairs(sentence):
    entities = []
    pairs = []
    for child in sentence:
        if child.tag == "entity":
            entities.append(child)
        elif child.tag == "pair" or child.tag == "interaction":
            pairs.append(child)
    return entities, pairs

def toTable(predictions):
    rows = []
    keys = []
    for key in predictions.keys():
        keys.append(key)
        column = []
        for pair in predictions[key]:
            column.append(pair[0])
        rows.append(column)
    normalizeTable(rows)
    rows_transpose = [[] for i in range(len(rows[0]))]
    #Transpose
    for i in range(len(rows)):
        for j in range(len(rows[0])):
            rows_transpose[j].append(rows[i][j])
    return rows, rows_transpose, keys

def normalizeTable(table):
    minimum = None
    #No need for maximum actually, but maybe I'll change this later
    #to normalize to probabilities or something...
    maximum = None
    for i in range(len(table)):
        for j in range(len(table[i])):
            value = table[i][j]
            if not minimum:
                minimum = value
            if not maximum:
                maximum = value
            if value > maximum:
                maximum = value
            elif value < minimum:
                minimum = value
    if minimum <=0:
        for i in range(len(table)):
            for j in range(len(table[i])):
                table[i][j]+= abs(minimum)+1

def oracleStatistics(p_iterator, g_iterator, n):
    TP = 0
    FP = 0
    FN = 0
    TP_oracle = 0
    FP_oracle = 0
    FN_oracle = 0
    counter = 0
    for p_document, g_document in zip(p_iterator, g_iterator):
        #counter3 += 1
        #counter += 1
        #if counter > 30:
        #    print FN
        #    sys.exit(0)
        for p_child, g_child in zip(p_document, g_document):
            if g_child.tag == "sentence":
                assert p_child.attrib["origId"]==g_child.attrib["origId"]
                p_entities, p_pairs = getEntitiesAndPairs(p_child)
                g_entities, g_pairs = getEntitiesAndPairs(g_child)
                if len(p_pairs) == 0:
                    FN += len(g_pairs)
                    FN_oracle += len(g_pairs)
                else:
                    g_edges, outside_count = getGSEdges(g_pairs, g_entities)
                    predictions = getSimplePredictions(p_entities, p_pairs)
                    table, table_transpose, keys = toTable(predictions)
                    best = nbest.decode(table_transpose, n)
                    p_edges = getPredictedEdges(predictions, keys, p_entities, best[0])
                    tp, fp, fn = getTP_FP_FN(g_edges, p_edges)
                    TP += tp
                    FP += fp
                    FN += fn
                    tp_best = tp
                    fp_best = fp
                    fn_best = fn
                    best_s = score(tp, fp, fn)
                    for i in range(1,len(best)):
                        p_edges = getPredictedEdges(predictions, keys, p_entities, best[i])
                        tp_c, fp_c, fn_c = getTP_FP_FN(g_edges, p_edges)
                        assert tp_c+fn_c == tp+fn
                        s = score(tp_c, fp_c, fn_c)
                        if s > best_s:
                            tp_best = tp_c
                            fp_best = fp_c
                            fn_best = fn_c
                            best_s = s
                    TP_oracle += tp_best
                    FP_oracle += fp_best
                    FN_oracle += fn_best
    PR = float(TP)/float(TP+FP)
    R = float(TP)/float(TP+FN)
    PR_oracle = float(TP_oracle)/float(TP_oracle+FP_oracle)
    R_oracle = float(TP_oracle)/float(TP_oracle+FN_oracle)
    assert TP_oracle+FN_oracle == TP+FN
    print "TP", TP
    print "FP", FP
    print "FN", FN
    print "F-score", (2*PR*R)/(PR+R)
    print "TP (oracle)", TP_oracle
    print "FP (oracle)", FP_oracle
    print "FN (oracle)", FN_oracle
    print "F-score (oracle)", (2*PR_oracle*R_oracle)/(PR_oracle+R_oracle)
    
    
def getTP_FP_FN(g_edges, p_edges):
    TP = len(g_edges.intersection(p_edges))
    FP = len(p_edges)-TP
    FN = len(g_edges)-TP
    return TP, FP, FN

def getTrainingOutputs(t_iterator):
    fsets = []
    for document in t_iterator:
        for child in document:
            if child.tag == "sentence":
                 entities, pairs = getEntitiesAndPairs(child)
                 if len(pairs) == 0:
                     fsets.append({})
                 else:
                     fsets.append(getGSOutputRepresentation(entities, pairs))
    return fsets

if __name__=="__main__":
    TP = 0
    FP = 0
    FN = 0
    TP_oracle = 0
    FP_oracle = 0
    FN_oracle = 0
    optparser = instantiateOptionParser()
    (options, args) = optparser.parse_args()
    if len(args) != 3:
        sys.stdout.write(optparser.get_usage())
        print "python CandidateGenerator.py -h for options\n"
        sys.exit(0)
    t_file = open(args[0])
    p_file = open(args[1])
    g_file = open(args[2])
    t_parser = parseGifxml.gifxmlParser(t_file)
    t_iterator = t_parser.documentIterator()
    p_parser = parseGifxml.gifxmlParser(p_file)
    p_iterator = p_parser.documentIterator()
    g_parser = parseGifxml.gifxmlParser(g_file)
    g_iterator = g_parser.documentIterator()
    n = options.nbest
    print "Building representation for training outputs"
    train_outputs = getTrainingOutputs(t_iterator)
    reranker = Reranker.KDLearner("train_inputs", "devel_inputs", "bvectors", train_outputs)
    reranker.solve(1)
    counter = 0
    c_decisions = 0
    w_decisions = 0
    ties = 0
    for p_document, g_document in zip(p_iterator, g_iterator):
        for p_child, g_child in zip(p_document, g_document):
            if g_child.tag == "sentence":
                assert p_child.attrib["origId"]==g_child.attrib["origId"]
                p_entities, p_pairs = getEntitiesAndPairs(p_child)
                g_entities, g_pairs = getEntitiesAndPairs(g_child)
                if len(p_pairs) == 0:
                    FN += len(g_pairs)
                    FN_oracle += len(g_pairs)
                else:
                    g_edges, outside_count = getGSEdges(g_pairs, g_entities)
                    predictions = getSimplePredictions(p_entities, p_pairs)
                    table, table_transpose, keys = toTable(predictions)
                    best = nbest.decode(table_transpose, n)
                    p_edges = getPredictedEdges(predictions, keys, p_entities, best[0])
                    Y = []
                    for b in best:
                        Y.append(getOutputRepresentation(predictions, keys, p_entities, b))
                    correct = getGSOutputRepresentation(g_entities, g_pairs)
                    correct_score = reranker.score([correct], counter)[0]
                    predicted_scores = reranker.score(Y, counter)
                    minimum = predicted_scores[0]
                    min_index = 0
                    #min_index = random.randint(0,len(predicted_scores)-1)
                    for i in range(len(predicted_scores)):
                        if predicted_scores[i] < minimum:
                            minimum = predicted_scores[i]
                            min_index = i
                    tp_b, fp_b, fn_b = getTP_FP_FN(g_edges, p_edges)
                    #ADDITION:
                    #if min_index != len(predicted_scores):
                    r_edges = getPredictedEdges(predictions, keys, p_entities, best[min_index])
                    tp_r, fp_r, fn_r = getTP_FP_FN(g_edges, r_edges)
                    #else:
                    #    tp_r, fp_r, fn_r = getTP_FP_FN(g_edges, g_edges)
                    TP += tp_b
                    FP += fp_b
                    FN += fn_b
                    TP_oracle += tp_r
                    FP_oracle += fp_r
                    FN_oracle += fn_r
                    
                    #print "c_score", correct_score
                    #print "p_score", predicted_score
                    #if correct_score < predicted_score:
                    #    c_decisions += 1
                    #elif correct_score == predicted_score:
                    #    ties += 1
                    #else:
                    #    w_decisions += 1
                counter += 1
    PR = float(TP)/float(TP+FP)
    R = float(TP)/float(TP+FN)
    PR_oracle = float(TP_oracle)/float(TP_oracle+FP_oracle)
    R_oracle = float(TP_oracle)/float(TP_oracle+FN_oracle)
    assert TP_oracle+FN_oracle == TP+FN
    print "TP", TP
    print "FP", FP
    print "FN", FN
    print "F-score", (2*PR*R)/(PR+R)
    print "TP (reranker)", TP_oracle
    print "FP (reranker)", FP_oracle
    print "FN (reranker)", FN_oracle
    print "F-score (reranker)", (2*PR_oracle*R_oracle)/(PR_oracle+R_oracle)
