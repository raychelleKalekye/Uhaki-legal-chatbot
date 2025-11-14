from app import embed_query_e5
from sentence_transformers import util
import numpy as np

def test_embedding_generation():

    q1 = "What is data protection?"
    q2 = "Explain data privacy under Kenyan law"
    q3 = "What are the penalties for theft under the Penal Code?"

    emb1 = np.array(embed_query_e5(q1))
    emb2 = np.array(embed_query_e5(q2))
    emb3 = np.array(embed_query_e5(q3))

    assert emb1.shape[0] == 768, "Embedding should be 768-dimensional"

    assert not np.all(emb1 == 0), "Embedding vector should not be all zeros"

    sim12 = util.cos_sim(emb1, emb2)
    sim13 = util.cos_sim(emb1, emb3)

    print("Similarity (Q1 vs Q2):", sim12.item())
    print("Similarity (Q1 vs Q3):", sim13.item())

    assert sim12 > sim13, "Semantically similar questions should have higher similarity"

    print(" Embedding generation passed all tests!")

if __name__ == "__main__":
    test_embedding_generation()
