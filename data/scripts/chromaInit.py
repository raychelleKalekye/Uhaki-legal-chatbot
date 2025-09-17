import chromadb

def get_chroma_collection():
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_or_create_collection(name="LegalActs")
    return collection
