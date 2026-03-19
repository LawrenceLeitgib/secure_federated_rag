from app.data.dataOwner import DataOwner
from app.domain.models import User
from app.retrieval.retrievalEngine import RetrievalEngine
from app.services.orchestration import SystemOrchestrator


def main() -> None:
    system = SystemOrchestrator()

    owner  = DataOwner.create("Alice")
    reader = User(user_id="reader_1", name="Bob")
    retrieval_engine = RetrievalEngine.create("RAG Engine")

    system.register_dataOwner(owner)
    system.register_retrievalEngine(retrieval_engine)

    sample_text = """
    Retrieval-Augmented Generation improves question answering by retrieving relevant chunks
    from a knowledge base. In this prototype, data owners upload documents, which are chunked,
    hashed into a Merkle tree, encrypted, and stored by an untrusted storage provider.

    A blockchain-like ledger keeps metadata such as user registration, dataset registration,
    Merkle root, and authorizations. Custodians hold key shares and only reconstruct the
    encryption key when the querying user is authorized.

    The retrieval engine embeds chunks and user queries, then performs similarity search.
    The most relevant encrypted chunks are fetched, decrypted, and returned as context.
    """

    dataset = system.upload_document(
        owner_id=owner.user_id,
        document_name="RAG Overview",
        text=sample_text,
    )

    

    print("=== DATASET REGISTERED ===")
    print(f"Dataset ID: {dataset.dataset_id}")
    print(f"Owner ID: {dataset.owner_id}")
    print(f"owner name: {owner.name}")
    print(f"Document Name: {dataset.document_name}")
    for i, chunk in enumerate(dataset.chunks):
        print(f"Chunk {i}: ID={chunk.chunk_id}, Text='{chunk.text[:60]}...'")
    print()

    system.grant_authorization(
        data_owner_id=owner.user_id,
        re_id=retrieval_engine.re_id,
        dataset_id=dataset.dataset_id,
    )
    print(f"Authorization granted to {retrieval_engine.name} for dataset '{dataset.document_name}'")
    print(f"is authorized: {system.ledger.is_authorized(retrieval_engine.re_id, dataset.dataset_id)}")
    print("=== LEDGER ENTRIES ===")
    system.ledger.print_entries()


    print()
    print("=== RETRIEVAL ENGINE STARTED ===")
    print()


    system.giveEmbeddings(
        owner_id=owner.user_id,
        dataset_id=dataset.dataset_id,
        re_id=retrieval_engine.re_id,
    )
    #print(f"Embeddings given to {retrieval_engine.name} for dataset '{dataset.document_name}'")
    #print(f"Retrieval Engine Embeddings: {retrieval_engine.embeddings}")



    query="What is Retrieval-Augmented Generation?"
    results = system.query(
        re_id=retrieval_engine.re_id,
        dataset_id=dataset.dataset_id,
        query_text=query,
        k=2,
    )

    print(f"Query: {query}")
    print("Results:")
    for i, (chunk_id, score, plaintext) in enumerate(results):
        print(f"[{i}] chunk_id={chunk_id} | score={score:.4f} | text='{plaintext[:60]}...'")



if __name__ == "__main__":
    main()