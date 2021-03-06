import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
import Core.SentenceGraph as SentenceGraph
from optparse import OptionParser
#import networkx as NX
import Graph.networkx_v10rc1 as NX10
import sys, os
import shutil
import Utils.TableUtils as TableUtils

options = None

def calculateMainStatistics(corpusElements):
    totalTokens = 0
    totalHeadTokens = 0
    headTokenPairs = 0
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        totalTokens += len(sentenceGraph.tokens)
        
        headTokens = 0
        for token in sentenceGraph.tokens:
            if sentenceGraph.tokenIsEntityHead[token] != None:
                headTokens += 1
        totalHeadTokens += headTokens
        headTokenPairs += headTokens * headTokens
    print >> sys.stderr, "Tokens:", totalTokens
    print >> sys.stderr, "Head Tokens:", totalHeadTokens
    print >> sys.stderr, "Head Token Pairs:", headTokenPairs

def analyzeLinearDistance(corpusElements):
    interactionEdges = 0
    interactionLinearDistanceCounts = {}
    allEntitiesLinearDistanceCounts = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        interactionEdges += len(sentence.interactions)
        
        # Linear distance between end tokens of interaction edges
        for interaction in sentence.interactions:
            e1 = sentence.entitiesById[interaction.get("e1")]
            e2 = sentence.entitiesById[interaction.get("e2")]
            t1 = sentenceGraph.entityHeadTokenByEntity[e1]
            t2 = sentenceGraph.entityHeadTokenByEntity[e2]
            linDistance = int(t1.get("id").split("_")[-1]) - int(t2.get("id").split("_")[-1])
            if linDistance < 0:
                linDistance *= -1
            if not interactionLinearDistanceCounts.has_key(linDistance):
                interactionLinearDistanceCounts[linDistance] = 0
            interactionLinearDistanceCounts[linDistance] += 1

        # Linear distance between all entities
        for i in range(len(sentence.entities)-1):
            for j in range(i+1,len(sentence.entities)):
                tI = sentenceGraph.entityHeadTokenByEntity[sentence.entities[i]]
                tJ = sentenceGraph.entityHeadTokenByEntity[sentence.entities[j]]
                linDistance = int(tI.get("id").split("_")[-1]) - int(tJ.get("id").split("_")[-1])
                if linDistance < 0:
                    linDistance *= -1
                if not allEntitiesLinearDistanceCounts.has_key(linDistance):
                    allEntitiesLinearDistanceCounts[linDistance] = 0
                allEntitiesLinearDistanceCounts[linDistance] += 1
    
    print >> sys.stderr, "=== Linear Distance ==="
    print >> sys.stderr, "Interaction edges:", interactionEdges
    print >> sys.stderr, "Entity head token linear distance for interaction edges:"
    printPathDistribution(interactionLinearDistanceCounts)
    if options.output != None:
        interactionLinearDistanceCounts["corpus"] = options.input
        interactionLinearDistanceCounts["parse"] = options.parse
        TableUtils.addToCSV(interactionLinearDistanceCounts, options.output+"/interactionEdgeLinearDistance.csv")
    print >> sys.stderr, "Linear distance between head tokens of all entities:"
    printPathDistribution(allEntitiesLinearDistanceCounts)
    if options.output != None:
        allEntitiesLinearDistanceCounts["corpus"] = options.input
        allEntitiesLinearDistanceCounts["parse"] = options.parse
        TableUtils.addToCSV(allEntitiesLinearDistanceCounts, options.output+"/allEntitiesLinearDistance.csv")

def analyzeLengths(corpusElements):
    interactionEdges = 0
    dependencyEdges = 0
    pathsByLength = {}
    pathsBetweenAllEntitiesByLength = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        #interactionEdges += len(sentenceGraph.interactionGraph.edges())
        interactionEdges += len(sentence.interactions)
        dependencyEdges += len(sentenceGraph.dependencyGraph.edges())
        
        undirected = sentenceGraph.dependencyGraph.to_undirected()
        paths = NX10.all_pairs_shortest_path(undirected, cutoff=999)
        # Shortest path for interaction edge
        for interaction in sentence.interactions:
            e1 = sentence.entitiesById[interaction.attrib["e1"]]
            e2 = sentence.entitiesById[interaction.attrib["e2"]]
            t1 = sentenceGraph.entityHeadTokenByEntity[e1]
            t2 = sentenceGraph.entityHeadTokenByEntity[e2]
            if paths.has_key(t1) and paths[t1].has_key(t2):
                path = paths[t1][t2]
                if not pathsByLength.has_key(len(path)-1):
                    pathsByLength[len(path)-1] = 0
                pathsByLength[len(path)-1] += 1
            else:
                if not pathsByLength.has_key("none"):
                    pathsByLength["none"] = 0
                pathsByLength["none"] += 1

#        for intEdge in sentenceGraph.interactionGraph.edges():
#            if paths.has_key(intEdge[0]) and paths[intEdge[0]].has_key(intEdge[1]):
#                path = paths[intEdge[0]][intEdge[1]]
#                if not pathsByLength.has_key(len(path)-1):
#                    pathsByLength[len(path)-1] = 0
#                pathsByLength[len(path)-1] += 1
#            else:
#                if not pathsByLength.has_key("none"):
#                    pathsByLength["none"] = 0
#                pathsByLength["none"] += 1
        # Shortest paths between all entities
        for i in range(len(sentence.entities)-1):
            for j in range(i+1,len(sentence.entities)):
                tI = sentenceGraph.entityHeadTokenByEntity[sentence.entities[i]]
                tJ = sentenceGraph.entityHeadTokenByEntity[sentence.entities[j]]
                if paths.has_key(tI) and paths[tI].has_key(tJ):
                    path = paths[tI][tJ]
                    if not pathsBetweenAllEntitiesByLength.has_key(len(path)-1):
                        pathsBetweenAllEntitiesByLength[len(path)-1] = 0
                    pathsBetweenAllEntitiesByLength[len(path)-1] += 1
                elif tI == tJ:
                    if not pathsBetweenAllEntitiesByLength.has_key(0):
                        pathsBetweenAllEntitiesByLength[0] = 0
                    pathsBetweenAllEntitiesByLength[0] += 1
                else:
                    if not pathsBetweenAllEntitiesByLength.has_key("none"):
                        pathsBetweenAllEntitiesByLength["none"] = 0
                    pathsBetweenAllEntitiesByLength["none"] += 1

#        for i in range(len(sentenceGraph.tokens)-1):
#            for j in range(i+1,len(sentenceGraph.tokens)):
#                tI = sentenceGraph.tokens[i]
#                tJ = sentenceGraph.tokens[j]
#                if sentenceGraph.tokenIsEntityHead[tI] == None or sentenceGraph.tokenIsEntityHead[tJ] == None:
#                    continue
#                if paths.has_key(tI) and paths[tI].has_key(tJ):
#                    path = paths[tI][tJ]
#                    if not pathsBetweenAllEntitiesByLength.has_key(len(path)-1):
#                        pathsBetweenAllEntitiesByLength[len(path)-1] = 0
#                    pathsBetweenAllEntitiesByLength[len(path)-1] += 1
#                else:
#                    if not pathsBetweenAllEntitiesByLength.has_key("none"):
#                        pathsBetweenAllEntitiesByLength["none"] = 0
#                    pathsBetweenAllEntitiesByLength["none"] += 1
    
    print >> sys.stderr, "Interaction edges:", interactionEdges
    print >> sys.stderr, "Dependency edges:", dependencyEdges
    print >> sys.stderr, "Shortest path of dependencies for interaction edge:"
    printPathDistribution(pathsByLength)
    if options.output != None:
        pathsByLength["corpus"] = options.input
        pathsByLength["parse"] = options.parse
        TableUtils.addToCSV(pathsByLength, options.output+"/pathsByLength.csv")
    print >> sys.stderr, "Shortest path of dependencies between all entities:"
    printPathDistribution(pathsBetweenAllEntitiesByLength)
    if options.output != None:
        pathsByLength["corpus"] = options.input
        pathsByLength["parse"] = options.parse
        TableUtils.addToCSV(pathsBetweenAllEntitiesByLength, options.output+"/pathsBetweenAllEntitiesByLength.csv")

def printPathDistribution(pathsByLength):
    lengths = pathsByLength.keys()
    lengths.sort()
    totalPaths = 0
    for length in lengths:
        totalPaths += pathsByLength[length]
    print >> sys.stderr, "  Total: " + str(totalPaths)
    for length in lengths:
        print >> sys.stderr, "  " + str(length) + ": " + str(pathsByLength[length]), "(%.2f" % (100*float(pathsByLength[length])/totalPaths) + " %)"

def countMultipleEdges(corpusElements):
    parallelEdgesByType = {}
    nonParallelEdgesByType = {}
    circular = 0
    total = 0
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        for edge in sentenceGraph.interactionGraph.edges():
            isCircular = False
            intEdges = sentenceGraph.interactionGraph.get_edge(edge[0], edge[1])
            if len(intEdges) > 0 and len(sentenceGraph.interactionGraph.get_edge(edge[1], edge[0])) > 0:
                circular += 1
                isCircular = True
            intEdges.extend( sentenceGraph.interactionGraph.get_edge(edge[1], edge[0]) )
            types = []
            for intEdge in intEdges:
                types.append(intEdge.attrib["type"])
            if len(types) > 1:
                total += 1
                types.sort()
                types = tuple(types)
                if not parallelEdgesByType.has_key(types):
                    parallelEdgesByType[types] = [0,0]
                parallelEdgesByType[types][0] += 1
                if isCircular: parallelEdgesByType[types][1] += 1
            elif len(types) == 1:
                if not nonParallelEdgesByType.has_key(types[0]):
                    nonParallelEdgesByType[types[0]] = 0
                nonParallelEdgesByType[types[0]] += 1
    types = parallelEdgesByType.keys()
    types.sort()
    print >> sys.stderr, "Parallel edges:"
    print >> sys.stderr, "  Total:", total, "Circular:", circular
    for type in types:
        print >> sys.stderr, "  " + str(type) + ": " + str(parallelEdgesByType[type][0]) + " (circular: " + str(parallelEdgesByType[type][1]) + ")"

    types = nonParallelEdgesByType.keys()
    types.sort()
    print >> sys.stderr, "Non-Parallel edges:"
    for type in types:
        print >> sys.stderr, "  " + str(type) + ": " + str(nonParallelEdgesByType[type])

def listEntities(corpusElements):
    entitiesByType = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        for entity in sentenceGraph.entities:
            type = entity.attrib["type"]
            if not entitiesByType.has_key(type):
                entitiesByType[type] = [0,0,{}]
            entitiesByType[type][0] += 1
            if not entitiesByType[type][2].has_key(entity.get("text")):
                entitiesByType[type][2][entity.get("text")] = 0
            entitiesByType[type][2][entity.get("text")] += 1
            if entity.attrib["isName"] == "True":
                entitiesByType[type][1] += 1
    keys = entitiesByType.keys()
    keys.sort()
    print >> sys.stderr, "Entities (all, named):"
    for k in keys:
        print >> sys.stderr, "  " + k + ": " + str(entitiesByType[k][0]) + ", " + str(entitiesByType[k][1])
        texts = entitiesByType[k][2].keys()
        texts.sort()
        for text in texts:
            print >> sys.stderr, "    " + text + "    (" + str(entitiesByType[k][2][text]) + ")"

def listStructures(corpusElements):
    interactionEdges = 0
    dependencyEdges = 0
    
    structures = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        #interactionEdges += len(sentenceGraph.interactionGraph.edges())
        interactionEdges += len(sentence.interactions)
        dependencyEdges += len(sentenceGraph.dependencyGraph.edges)
        
        undirected = sentenceGraph.dependencyGraph.to_undirected()
        paths = NX.all_pairs_shortest_path(undirected, cutoff=999)
        # Shortest path for interaction edge
        for interaction in sentence.interactions:
            e1 = sentence.entitiesById[interaction.attrib["e1"]]
            e2 = sentence.entitiesById[interaction.attrib["e2"]]
            t1 = sentenceGraph.entityHeadTokenByEntity[e1]
            t2 = sentenceGraph.entityHeadTokenByEntity[e2]
            if paths.has_key(t1) and paths[t1].has_key(t2):
                path = paths[t1][t2]
                prevToken = None
                structure = ""
                for pathToken in path:
                    if prevToken != None:
                        if sentenceGraph.dependencyGraph.has_edge(prevToken,pathToken):
                            structure += ">" + sentenceGraph.dependencyGraph.get_edge(prevToken,pathToken)[0].attrib["type"] + ">"
                        elif sentenceGraph.dependencyGraph.has_edge(pathToken,prevToken):
                            structure += "<" + sentenceGraph.dependencyGraph.get_edge(pathToken,prevToken)[0].attrib["type"] + "<"
                        else:
                            assert(False)
                    structure += pathToken.attrib["POS"][0:1]
                    prevToken = pathToken
                
                if not structures.has_key(structure):
                    structures[structure] = {}
                if not structures[structure].has_key(interaction.attrib["type"]):
                    structures[structure][interaction.attrib["type"]] = 0
                structures[structure][interaction.attrib["type"]] += 1
    
    print >> sys.stderr, "Structures"
    #keys = sorted(structures.keys())
    for s in sorted(structures.keys()):
        print >> sys.stderr, s + ":"
        for i in sorted(structures[s].keys()):
            print >> sys.stderr, "  " + i + ": " + str(structures[s][i])

def countEventComponents(corpusElements):
    counts = {}
    interSentenceCounts = {}
    nonOverlappingCounts = {}
    for sentence in corpusElements.sentences:
        tokenPairsByType = {}
        sentenceGraph = sentence.sentenceGraph
        for interaction in sentence.interactions:
            #sId = sentenceGraph.getSentenceId()
            e1Id = interaction.get("e1")
            e2Id = interaction.get("e2")
            if not sentence.entitiesById.has_key(e1Id):
                continue
            if not sentence.entitiesById.has_key(e2Id):
                if not interSentenceCounts.has_key(tag):
                    interSentenceCounts[tag] = 0
                interSentenceCounts[tag] += 1
                continue
            
            # Actual
            e1 = sentence.entitiesById[e1Id]
            e2 = sentence.entitiesById[e2Id]
            tag = e1.get("type") + "-" + interaction.get("type") + "-" + e2.get("type")
            if not counts.has_key(tag):
                counts[tag] = 0
            counts[tag] += 1
            
            if sentenceGraph == None:
                continue
            e2 = sentence.entitiesById[e2Id]
            # Non-overlapping
            tokenPair = (sentenceGraph.entityHeadTokenByEntity[e1].get("id"), sentenceGraph.entityHeadTokenByEntity[e2].get("id")) 
            #if interaction.get("id") in ["GENIA.d127.s6.i4", "GENIA.d127.s6.i5"]:
            #    print "TP", tokenPair
            if not tokenPair in tokenPairsByType.get(tag, []):
                tokenPairsByType.setdefault(tag, set())
                tokenPairsByType[tag].add(tokenPair)
                nonOverlappingCounts.setdefault(tag, 0)
                nonOverlappingCounts[tag] += 1
            #else:
            #    print tokenPair
            
            # Check for self-interactions
            t1 = sentenceGraph.entityHeadTokenByEntity[e1]
            t2 = sentenceGraph.entityHeadTokenByEntity[e2]
            if t1 == t2:
                print "Self-Int", tag
            else:
                if not sentenceGraph.interactionGraph.hasEdges(t1, t2):
                    print "ERROR! Missing-Int", tag
    print "Event Components (Actual, Intersentence, Non-overlapping)"
    for k in sorted(counts.keys()):
        print k, counts[k], interSentenceCounts.get(k, 0), nonOverlappingCounts.get(k, 0)

def countPOS(corpusElements):
    posCounts = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        if sentenceGraph == None:
            continue
        for token in sentenceGraph.tokens:
            pos = token.get("POS")
            if not posCounts.has_key(pos):
                posCounts[pos] = [0,0]
            if len(sentenceGraph.tokenIsEntityHead[token]) > 0:
                posCounts[pos][0] += 1
            else:
                posCounts[pos][1] += 1
    for key in sorted(posCounts.keys()):
        print str(key) + ":", posCounts[key]

def countPOSCombinations(corpusElements):
    posCounts = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        if sentenceGraph == None:
            continue
        for t1 in sentenceGraph.tokens:
            for t2 in sentenceGraph.tokens:
                if t1 == t2:
                    continue
                posTuple = ( t1.get("POS"), t2.get("POS") )
                if not posCounts.has_key(posTuple):
                    posCounts[posTuple] = {}
                if sentenceGraph.interactionGraph.has_edge(t1, t2):
                    intEdges = sentenceGraph.interactionGraph.get_edge_data(t1, t2, default={})
                    for i in range(len(intEdges)):
                        intElement = intEdges[i]["element"]
                        intType = intElement.get("type")
                        if not posCounts[posTuple].has_key(intType):
                            posCounts[posTuple][intType] = 0
                        posCounts[posTuple][intType] += 1
                else:
                    if not posCounts[posTuple].has_key("neg"):
                        posCounts[posTuple]["neg"] = 0
                    posCounts[posTuple]["neg"] += 1
    for key in sorted(posCounts.keys()):
        print str(key) + ":", posCounts[key]

def countDisconnectedHeads(corpusElements):
    edgeCounts = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        if sentenceGraph == None:
            continue
        for entity in sentenceGraph.entities:
            headToken = sentenceGraph.entityHeadTokenByEntity[entity]
            headTokenId = headToken.get("id")
            numEdges = 0
            for dependency in sentenceGraph.dependencies:
                if dependency.get("t1") == headTokenId or dependency.get("t2") == headTokenId:
                    numEdges += 1 
            #numEdges = len(sentenceGraph.dependencyGraph.edges([headToken]))
            if not edgeCounts.has_key(numEdges):
                edgeCounts[numEdges] = 0
            edgeCounts[numEdges] += 1
            if numEdges != 0:
                if not edgeCounts.has_key("non-zero"):
                    edgeCounts["non-zero"] = 0
                edgeCounts["non-zero"] += 1
            else:
                print "Disconnected entity", entity.get("id")
    print edgeCounts

def countOverlappingHeads(corpusElements):
    overlaps = {}
    for sentence in corpusElements.sentences:
        sentenceOverlaps = {}
        for entity in sentence.entities:
            head = entity.get("headOffset")
            if not sentenceOverlaps.has_key(head):
                sentenceOverlaps[head] = set()
            sentenceOverlaps[head].add(entity.get("type"))
        for value in sentenceOverlaps.values():
            if len(value) > 1:
                tag = str(sorted(list(value)))
                if not overlaps.has_key(tag):
                    overlaps[tag] = 0
                overlaps[tag] += 1
    print "Overlaps"
    for key in sorted(overlaps.keys()):
        print " ", key, overlaps[key]

#def isBIEventNode(entity):
##    if entity.get("type") in ["RegulonDependence","BindTo","TranscriptionFrom",
##                              "RegulonMember","SiteOf","TranscriptionBy","PromoterOf",
##                              "PromoterDependence","ActionTarget","Interaction"]:
##        return True
#    eType = entity.get("type")
#    if "(" in eType and ")" in eType and "/" in eType:
#        return True
#    else:
#        return False

def isEventNode(entity):
    return (entity.get("isName") == "False" and entity.get("type") not in ["Entity"]) # or isBIEventNode(entity)

def countEntities(corpusElements, relations=True):
    entitiesById = {}
    for sentence in corpusElements.sentences:
        for entity in sentence.entities:
            entitiesById[entity.get("id")] = entity
            
    counts = {}
    counts["event"] = 0
    counts["non-event"] = 0
    counts["event-equiv"] = 0
    counts["nesting-event"] = 0
    counts["negspec-event"] = 0
    counts["duplicate-event"] = 0
    for sentence in corpusElements.sentences:
        if not relations:
            for entity in sentence.entities:
                eType = entity.get("type")
                if not counts.has_key(eType):
                    counts[eType] = 0
                counts[eType] += 1
                if isEventNode(entity):
                    counts["event"] += 1
                else:
                    counts["non-event"] += 1
                if entity.get("speculation") == "True" or entity.get("negation") == "True":
                    counts["negspec-event"] += 1
    #            # detect equivs
    #            origId = entity.get("origId")
    #            dPart = origId.split(".")[-1]
    #            if dPart[0] == "d":
    #                assert dPart[1:].isdigit(), origId
    #                if dPart[1] != "0":
    #                    counts["event-equiv"] += 1
        else:
            counts["event"] += len(sentence.interactions)
            counts["nesting-event"] = "N/A"
        # Count nesting events
        if not relations:
            detected = set()
            for interaction in sentence.interactions:
                if interaction.get("type") in ["Coref", "Target"]:
                    counts["nesting-event"] = "N/A"
                    continue
                e1 = interaction.get("e1")
                e2 = interaction.get("e2")
                if isEventNode(entitiesById[e2]):
                    if e1 not in detected:
                        counts["nesting-event"] += 1
                        detected.add(e1)
        # Count duplicate events
        detected = set()
        for interaction in sentence.interactions:
            e1 = interaction.get("e1")
            splits = interaction.get("origId").rsplit(".", 1)
            eventId = splits[0]
            if len(splits) == 2 and splits[-1][0] == "d": # for REL
                dupId = splits[-1]
            else:
                dupId = eventId.rsplit(".", 1)[-1]
            #print dupId,
            if dupId[0] == "d":
                assert dupId[1:].isdigit(), (dupId, eventId)
                if dupId[1:] != "0":
                    pass #print True
                    if e1 not in detected:
                        counts["duplicate-event"] += 1
                        if not relations:
                            detected.add(e1)
                else:
                    pass #print False
            else:
                pass #print False
    print "Entity counts"
    for key in sorted(counts.keys()):
        print " ", key, counts[key]
    return counts

def countIntersentenceEvents(corpusElements, totalEvents=None, relations=False):
    counts = {}
    counts["ALL_EVENTS"] = 0
    #entityById = {}
    #for sentence in corpusElements.sentences:
    #    for entity in sentence.entities:
    
    if not relations: # match group of interactions by head node
        interactionsByE1 = {}
        entitiesById = {}
        for sentence in corpusElements.sentences:
            for interaction in sentence.interactions:
                e1 = interaction.get("e1")
                if not interactionsByE1.has_key(e1):
                    interactionsByE1[e1] = []
                interactionsByE1[e1].append(interaction)
            for entity in sentence.entities:
                entitiesById[entity.get("id")] = entity
        intersentenceEvents = set()
        for e1 in sorted(interactionsByE1.keys()):
            isIntersentence = False
            for interaction in interactionsByE1[e1]:
                e1MajorId, e1MinorId = interaction.get("e1").rsplit(".e", 1)
                e2MajorId, e2MinorId = interaction.get("e2").rsplit(".e", 1)
                if e1MajorId != e2MajorId:
                    isIntersentence = True
                    break
            if isIntersentence and interaction.get("e1") not in intersentenceEvents:
                intersentenceEvents.add(interaction.get("e1"))
                eType = entitiesById[e1].get("type")
                if not counts.has_key(eType):
                    counts[eType] = 0 
                counts[eType] += 1
                counts["ALL_EVENTS"] += 1
    else:
        for sentence in corpusElements.sentences:
            for interaction in sentence.interactions:
                e1MajorId, e1MinorId = interaction.get("e1").rsplit(".e", 1)
                e2MajorId, e2MinorId = interaction.get("e2").rsplit(".e", 1)
                if e1MajorId != e2MajorId:
                    counts["ALL_EVENTS"] += 1
    print "Intersentence Event counts"
    for key in sorted(counts.keys()):
        percentage = "N/A"
        if totalEvents != None:
            percentage = float(counts[key]) / float(totalEvents) * 100.0
        print " ", key, counts[key], "percentage:", percentage
    return counts

def analyzeHeadTokens(corpusElements):
    from collections import defaultdict
    posTagsByGroup = defaultdict(lambda : defaultdict(int)) # collections.defaultdict(collections.defaultdict(int)) # {"ALL_TOKENS":{}}
    counts = defaultdict(int) #{"ALL_TOKENS":0}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        if sentenceGraph == None:
            print "Warning, no sentenceGraph for sentence", sentence.sentence.get("id")
            continue
        
        for token in sentenceGraph.tokens:
            posTagsByGroup["ALL_TOKENS"][token.get("POS")] += 1
            counts["ALL_TOKENS"] += 1
            if token not in sentenceGraph.tokenIsEntityHead or len(sentenceGraph.tokenIsEntityHead[token]) == 0:
                continue
            entityGroup = sentenceGraph.tokenIsEntityHead[token]
            entityTypes = set()
            for e in entityGroup:
                entityTypes.add(e.get("type"))
            entityTypes = "---".join(sorted(list(entityTypes)))
            #if not entityTypes in posTagsByGroup:
            #    posTagsByGroup[entityTypes] = {}
            #    counts[entityTypes] = 0
            posTagsByGroup[entityTypes][token.get("POS")] += 1
            counts[entityTypes] += 1
    print "Head token overlap and POS tags"
    for key in sorted(posTagsByGroup.keys()):
        print " ", key + " (" + str(counts[key]) +  "):",
        for k2 in sorted(posTagsByGroup[key].keys()):
            print k2 + "(" + str(posTagsByGroup[key][k2]) + ")",
        print

def analyzeHeadStrings(corpusElements):
    from collections import defaultdict
    dict = defaultdict(lambda : defaultdict(lambda : [0,0]))
    eTypes = set()
    eTypes.add("NON_ENTITY")
    for sentence in corpusElements.sentences:
        #sentenceText = sentence.get("text")
        if sentence.sentenceGraph == None:
            continue
        for token in sentence.tokens:
            tokenString = token.get("text")
            if len(sentence.sentenceGraph.tokenIsEntityHead[token]) == 0:
                dict[tokenString]["NON_ENTITY"][0] += 1
            else:
                for entity in sentence.sentenceGraph.tokenIsEntityHead[token]:
                    eType = entity.get("type")
                    eTypes.add(eType)
                    #headOffset = Range.SingleTupleToOffset(entity.get("headOffset"))
                    #headString = sentenceText[headOffset[0]:headOffset[1]+1]
                    dict[tokenString][eType][0] += 1
    for headString in dict:
        stringSum = 0.0
        for eType in dict[headString]:
            stringSum += dict[headString][eType][0] 
        for eType in dict[headString]:
            dict[headString][eType][1] = dict[headString][eType][0] / stringSum
    eTypes = list(eTypes)
    eTypes.sort()
    typeDistribution = defaultdict(lambda : defaultdict(lambda : [[],0]))
    for eType in eTypes: # for each entity type
        for headString in dict: # for each token string
            if eType in dict[headString]: # if this token string has been part of said entity
                for eType2 in dict[headString]: # add it to the distribution of that entity type's strings
                    typeDistribution[eType][eType2][0] += dict[headString][eType2][0] * [dict[headString][eType2][1]]
    for eType in typeDistribution:
#        instanceSum = 0.0
#        for eType2 in typeDistribution[eType]:
#            instanceSum += typeDistribution[eType][eType2][0]
#        for eType2 in typeDistribution[eType]:
#            typeDistribution[eType][eType2][1] = typeDistribution[eType][eType2][0] / instanceSum
        for eType2 in typeDistribution[eType]:
            typeDistribution[eType][eType2][1] = sum(typeDistribution[eType][eType2][0]) / len(typeDistribution[eType][eType2][0])
    line = "    "
    for eType in eTypes:
        line += eType[0:2] + "    "
    print line
    for eType in eTypes:
        line = eType[0:2]
        for eType2 in eTypes:
            #line += "  (%d,%.1f)" % (typeDistribution[eType][eType2][0], typeDistribution[eType][eType2][1])
            line += "  %.2f" % (typeDistribution[eType][eType2][1])
        print line
     
if __name__=="__main__":
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPIVisible_noCL.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="parse")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output-folder")
    optparser.add_option("-a", "--analyses", default="", dest="analyses", help="selected optional analyses")
    (options, args) = optparser.parse_args()

    if options.output != None:
        if os.path.exists(options.output):
            print >> sys.stderr, "Output directory exists, removing", options.output
            shutil.rmtree(options.output)
        os.makedirs(options.output)
    
    if options.analyses != "bionlp11":
        corpusElements = SentenceGraph.loadCorpus(options.input, options.parse, options.tokenization, removeIntersentenceInteractionsFromCorpusElements=False)
        print >> sys.stderr, "tokenization:", options.tokenization
        print >> sys.stderr, "parse:", options.parse
    
    #calculateMainStatistics(corpusElements)
    #analyzeLengths(corpusElements)
    #countMultipleEdges(corpusElements)
    if options.analyses.find("entities") != -1:
        listEntities(corpusElements)
    if options.analyses.find("structures") != -1:
        listStructures(corpusElements)
    if options.analyses.find("linear_distance") != -1:
        analyzeLinearDistance(corpusElements)
    if options.analyses.find("pos_counts") != -1:
        countPOS(corpusElements)
    if options.analyses.find("pos_pair_counts") != -1:
        countPOSCombinations(corpusElements)
    if options.analyses.find("event_components") != -1:
        countEventComponents(corpusElements)
    if options.analyses.find("disconnected_heads") != -1:
        countDisconnectedHeads(corpusElements)
    if options.analyses.find("overlapping_heads") != -1:
        countOverlappingHeads(corpusElements)
    if options.analyses.find("count_entities") != -1:
        countEntities(corpusElements)
    if options.analyses.find("intersentence") != -1:
        countIntersentenceEvents(corpusElements)
    if options.analyses.find("head_tokens") != -1:
        analyzeHeadTokens(corpusElements)
    if options.analyses.find("head_strings") != -1:
        analyzeHeadStrings(corpusElements)
    
    if options.analyses == "bionlp11":
        corpora = ["OLD", "GE", "EPI", "ID", "BI", "BB", "CO", "REL", "REN"]
        #corpora = ["EPI"]
        #corpora = ["BB"]
        for corpus in corpora:
            # Relations or events
            if corpus in ["BB", "BI", "REL", "REN"]:
                relations = True
            else:
                relations = False
            # Corpus source
            if corpus in ["GE", "EPI", "ID", "BI", "BB"]:
                parse = "split-mccc-preparsed"
                corpusDir = "/home/jari/biotext/BioNLP2011/data/main-tasks"
                corpusPath = corpusDir + "/" + corpus + "/" + corpus + "-devel-and-train.xml"
            elif corpus == "OLD":
                parse = None
                corpusPath = "/home/jari/biotext/BioNLP2011/data/equiv-recalc/OLD/OLD-devel-and-train.xml"
            elif corpus == "REL":
                parse = None
                corpusPath = "/home/jari/biotext/BioNLP2011/data/equiv-recalc/REL/REL-devel-and-train.xml"
            elif corpus == "CO":
                parse = "split-McClosky"
                corpusPath = "/home/jari/biotext/BioNLP2011/data/CO/co-devel-and-train.xml"
            elif corpus == "REN":
                parse = "split-McClosky"
                corpusPath = "/home/jari/biotext/BioNLP2011/data/REN/ren-devel-and-train.xml"
            #corpusPath = corpusDir + "/" + corpus + "/" + corpus + "-devel.xml"
            print "Processing", corpus, "from", corpusPath
            corpusElements = SentenceGraph.loadCorpus(corpusPath, parse, None, removeIntersentenceInteractionsFromCorpusElements=False)
            entityCounts = countEntities(corpusElements, relations = relations)
            intersentenceCounts = countIntersentenceEvents(corpusElements, entityCounts["event"], relations = relations)
            print "Table for", corpus + ":"
            print corpus, "&",
            print len(corpusElements.sentences), "&",
            print entityCounts["event"], "&",
            print "%.1f" % (float(entityCounts["duplicate-event"]) / entityCounts["event"] * 100.0) + "\\%", "&",
            if entityCounts["nesting-event"] != "N/A":
                print "%.1f" % (float(entityCounts["nesting-event"]) / entityCounts["event"] * 100.0) + "\\%", "&",
            else:
                print entityCounts["nesting-event"], "&",
            print "%.1f" % (float(intersentenceCounts["ALL_EVENTS"]) / entityCounts["event"] * 100.0) + "\\%", "&",
            print "%.1f" % (float(entityCounts["negspec-event"]) / entityCounts["event"] * 100.0) + "\\%", "\\\\"
