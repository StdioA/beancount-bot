import math


def match(query, sentence):
    sentence_seg = {x.strip('"') for x in sentence.split()}
    query_seg = [x.strip('"') for x in query.split()]
    score = sum(1 for x in sentence_seg if x in query_seg)
    return (score + 1) / (len(query_seg) + 1)


def calculate_score(txs, sentence):
    occ_score = math.log(txs["occurance"] + 1, 50)
    return txs["distance"] * occ_score
