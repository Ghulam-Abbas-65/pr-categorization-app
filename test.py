from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')
print(model.encode("test sentence", convert_to_numpy=True))
