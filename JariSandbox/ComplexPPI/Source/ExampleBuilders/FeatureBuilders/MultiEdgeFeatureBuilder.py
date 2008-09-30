from FeatureBuilder import FeatureBuilder
#import Stemming.PorterStemmer as PorterStemmer
from EdgeFeatureBuilder import EdgeFeatureBuilder

class MultiEdgeFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
        self.edgeFeatureBuilder = EdgeFeatureBuilder(featureSet)
        
    def setFeatureVector(self, features):
        self.features = features
        self.edgeFeatureBuilder.setFeatureVector(features)

    def getEdges(self, graph, path):
        """
        graph = Directed NetworkX graph
        path = list of token elements
        
        Builds a dictionary where edges are indexed by the indices of their
        start and end tokens in the path. F.e. to get the edges from path[1]
        to path[2] call return_value[1][2].
        """
        pathEdges = {}
        for i in range(0, len(path)):
            pathEdges[i] = {}
        for i in range(1, len(path)):
            pathEdges[i][i-1] = []
            pathEdges[i-1][i] = []
        edges = graph.edges()
        for i in range(1, len(path)):
            found = False
            for edge in edges:
                if edge[0] == path[i-1] and edge[1] == path[i]:
                    pathEdges[i-1][i].append(edge)
                    found = True
                elif edge[1] == path[i-1] and edge[0] == path[i]:
                    pathEdges[i][i-1].append(edge)
                    found = True
            assert(found==True)
        return pathEdges
    
    def getWalks(self, pathTokens, pathEdges, position=1, walk=None):
        """
        A path is defined by a list of tokens. But since there can be more than one edge
        between the same two tokens, there are multiple ways of getting from the first
        token to the last token. This function returns all of these "walks", i.e. the combinations
        of edges that can be travelled to get from the first to the last token of the path.
        """
        allWalks = []
        if walk == None:
            walk = []
        
        edges = pathEdges[position-1][position] + pathEdges[position][position-1]
        for edge in edges:
            if position < len(pathTokens)-1:
                allWalks.extend(self.getWalks(pathTokens, pathEdges, position+1, walk + [edge]))
            else:
                allWalks.append(walk + [edge])
        return allWalks
    
    def buildPathLengthFeatures(self, pathTokens):
        """
        Simple numeric features about the length of the path
        """
        self.features[self.featureSet.getId("len_tokens_"+str(len(pathTokens)))] = 1
        self.features[self.featureSet.getId("len")] = len(pathTokens)

    def buildTerminusTokenFeatures(self, pathTokens, sentenceGraph):
        """
        Token features for the first and last tokens of the path
        """
        self.features[self.featureSet.getId("tokTerm1POS_"+pathTokens[0].attrib["POS"])] = 1
        self.features[self.featureSet.getId("tokTerm1txt_"+sentenceGraph.getTokenText(pathTokens[0]))] = 1
        self.features[self.featureSet.getId("tokTerm2POS_"+pathTokens[-1].attrib["POS"])] = 1
        self.features[self.featureSet.getId("tokTerm2txt_"+sentenceGraph.getTokenText(pathTokens[-1]))] = 1
  
    def buildPathGrams(self, length, pathTokens, pathEdges, sentenceGraph):
        """
        Goes through all the possible walks and builds features for subsections
        of "length" edges.
        """
        walks = self.getWalks(pathTokens, pathEdges)
        dirGrams = []
        for walk in walks:
            dirGrams.append("")
        for i in range(len(pathTokens)-1): # len(pathTokens) == len(walk)
            for j in range(len(walks)):
                if walks[j][i][0] == pathTokens[i]:
                    dirGrams[j] += "F"
                else:
                    dirGrams[j] += "R"
                if i >= length-1:
                    styleGram = dirGrams[j][i-(length-1):i+1]
                    edgeGram = "depGram_" + styleGram
                    # Label tokens by their role in the xgram
                    for token in pathTokens[i-(length-1)+1:i+1]:
                        self.features[self.featureSet.getId("tok_"+styleGram+"_POS_"+token.attrib["POS"])] = 1
                        self.features[self.featureSet.getId("tok_"+styleGram+"_Txt_"+sentenceGraph.getTokenText(token))] = 1
                    # Label edges by their role in the xgram
                    position = 0
                    for edge in walks[j][i-(length-1):i+1]:
                        self.features[self.featureSet.getId("dep_"+styleGram+str(position)+"_"+edge[2].attrib["type"])] = 1
                        position += 1
                        edgeGram += "_" + edge[2].attrib["type"]
                    self.features[self.featureSet.getId(edgeGram)] = 1
    
    def addType(self, token, sentenceGraph, prefix="annType_"):
        if sentenceGraph.tokenIsEntityHead[token] != None:
            self.features[self.featureSet.getId("annType_"+sentenceGraph.tokenIsEntityHead[token].attrib["type"])] = 1
    
    def buildPathEdgeFeatures(self, pathTokens, pathEdges, sentenceGraph):
        edgeList = []
        for i in range(1, len(pathTokens)):
            edgeList.extend(pathEdges[i][i-1])
            edgeList.extend(pathEdges[i-1][i])
        for edge in edgeList:
            depType = edge[2].attrib["type"]
            self.features[self.featureSet.getId("dep_"+depType)] = 1
            # Token 1
            self.features[self.featureSet.getId("txt_"+sentenceGraph.getTokenText(edge[0]))] = 1
            self.features[self.featureSet.getId("POS_"+edge[0].attrib["POS"])] = 1
            self.addType(edge[0], sentenceGraph, prefix="annType_")
            # Token 2
            self.features[self.featureSet.getId("txt_"+sentenceGraph.getTokenText(edge[1]))] = 1
            self.features[self.featureSet.getId("POS_"+edge[1].attrib["POS"])] = 1
            self.addType(edge[1], sentenceGraph, prefix="annType_")
            
            # g-d features
            gText = sentenceGraph.getTokenText(edge[0])
            dText = sentenceGraph.getTokenText(edge[1])
            gPOS = edge[0].attrib["POS"]
            dPOS = edge[1].attrib["POS"]
            gAT = "x"
            dAT = "x"
            if sentenceGraph.tokenIsEntityHead[edge[0]] != None:
                gAT = sentenceGraph.tokenIsEntityHead[edge[0]].attrib["type"]
            if sentenceGraph.tokenIsEntityHead[edge[1]] != None:
                dAT = sentenceGraph.tokenIsEntityHead[edge[1]].attrib["type"]
            self.features[self.featureSet.getId("gov_"+gText+"_"+dText)] = 1
            self.features[self.featureSet.getId("gov_"+gPOS+"_"+dPOS)] = 1
            self.features[self.featureSet.getId("gov_"+gAT+"_"+dAT)] = 1

#            # Features for edge-type/token combinations that define the governor/dependent roles
#            self.features[self.featureSet.getId("depgov_"+depType+"_"+dText)] = 1
#            self.features[self.featureSet.getId("depgov_"+depType+"_"+dPOS)] = 1
#            self.features[self.featureSet.getId("depgov_"+depType+"_"+dAT)] = 1
#            self.features[self.featureSet.getId("depdep_"+gText+"_"+depType)] = 1
#            self.features[self.featureSet.getId("depdep_"+gPOS+"_"+depType)] = 1
#            self.features[self.featureSet.getId("depdep_"+gAT+"_"+depType)] = 1

    def buildSingleElementFeatures(self, pathTokens, pathEdges, sentenceGraph):
        # Edges directed relative to the path
        for i in range(1,len(pathTokens)):
            for edge in pathEdges[i][i-1]:
                depType = edge[2].attrib["type"]
                self.features[self.featureSet.getId("dep_"+depType+"Forward_")] = 1
            for edge in pathEdges[i-1][i]:
                depType = edge[2].attrib["type"]
                self.features[self.featureSet.getId("dep_Reverse_"+depType)] = 1

        # Internal tokens
        for i in range(1,len(pathTokens)-1):
            self.features[self.featureSet.getId("internalPOS_"+pathTokens[i].attrib["POS"])]=1
            self.features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(pathTokens[i]))]=1
        # Internal dependencies
        for i in range(2,len(pathTokens)-1):
            for edge in pathEdges[i][i-1]:
                self.features[self.featureSet.getId("internalDep_"+edge[2].attrib["type"])] = 1
            for edge in pathEdges[i-1][i]:
                self.features[self.featureSet.getId("internalDep_"+edge[2].attrib["type"])] = 1

    def buildEdgeCombinations(self, pathTokens, pathEdges, sentenceGraph):
            
#        if edges[0][1]:
#            features[self.featureSet.getId("internalPOS_"+edges[0][0][0].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[0][0][0]))]=1
#        else:
#            features[self.featureSet.getId("internalPOS_"+edges[0][0][1].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[0][0][1]))]=1
#        if edges[-1][1]:
#            features[self.featureSet.getId("internalPOS_"+edges[-1][0][1].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[-1][0][1]))]=1
#        else:
#            features[self.featureSet.getId("internalPOS_"+edges[-1][0][0].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[-1][0][0]))]=1
#        for i in range(1,len(edges)-1):
#            features[self.featureSet.getId("internalPOS_"+edges[i][0][0].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[i][0][0]))]=1
#            features[self.featureSet.getId("internalPOS_"+edges[i][0][1].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[i][0][1]))]=1
#            features[self.featureSet.getId("internalDep_"+edges[i][0][2].attrib["type"])]=1
        
        return
        # Edge bigrams
        for i in range(1,len(pathTokens)-1):
            edgesForward1 = pathEdges[i][i-1]
            edgesReverse1 = pathEdges[i-1][i]
            edgesForward2 = pathEdges[i][i+1]
            edgesReverse2 = pathEdges[i+1][i]
            for e1 in edgesForward1:
                for e2 in edgesForward2:
                    features[self.featureSet.getId("dep_"+e1[2].attrib["type"]+">"+e2[2].attrib["type"]+">")] = 1
            for e1 in edgesReverse1:
                for e2 in edgesReverse2:
                    features[self.featureSet.getId("dep_"+e1[2].attrib["type"]+"<"+e2[2].attrib["type"]+"<")] = 1
            for e1 in edgesForward1:
                for e2 in edgesReverse2:
                    features[self.featureSet.getId("dep_"+e1[2].attrib["type"]+">"+e2[2].attrib["type"]+"<")] = 1
            for e1 in edgesReverse1:
                for e2 in edgesForward2:
                    features[self.featureSet.getId("dep_"+e1[2].attrib["type"]+"<"+e2[2].attrib["type"]+">")] = 1
                
#        for i in range(1,len(edges)):
#            type1 = edges[i-1][0][2].attrib["type"]
#            type2 = edges[i][0][2].attrib["type"]
#            if edges[i-1][1] and edges[i][1]:
#                features[self.featureSet.getId("dep_"+type1+">"+type2+">")] = 1
#            elif edges[i-1][1] and edges[i][0]:
#                features[self.featureSet.getId("dep_"+type1+">"+type2+"<")] = 1
#            elif edges[i-1][0] and edges[i][0]:
#                features[self.featureSet.getId("dep_"+type1+"<"+type2+"<")] = 1
#            elif edges[i-1][0] and edges[i][1]:
#                features[self.featureSet.getId("dep_"+type1+"<"+type2+">")] = 1

    def buildTerminusFeatures(self, token, prefix, sentenceGraph, features): 
        # Attached edges
        t1InEdges = sentenceGraph.dependencyGraph.in_edges(token)
        for edge in t1InEdges:
            features[self.featureSet.getId(prefix+"HangingIn_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId(prefix+"HangingIn_"+edge[0].attrib["POS"])] = 1
            features[self.featureSet.getId("t1HangingIn_"+sentenceGraph.getTokenText(edge[0]))] = 1
        t1OutEdges = sentenceGraph.dependencyGraph.out_edges(token)
        for edge in t1OutEdges:
            features[self.featureSet.getId(prefix+"HangingOut_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId(prefix+"HangingOut_"+edge[1].attrib["POS"])] = 1
            features[self.featureSet.getId("t1HangingOut_"+sentenceGraph.getTokenText(edge[1]))] = 1    