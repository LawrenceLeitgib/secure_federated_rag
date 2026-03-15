from app.domain.models import User
from app.services.orchestration import SystemOrchestrator


def main() -> None:
    system = SystemOrchestrator()

    owner = User(user_id="owner_1", name="Leonard")
    reader = User(user_id="reader_1", name="Alice")

    system.register_user(owner)
    system.register_user(reader)

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
        dataset_id="dataset_1",
        document_name="demo_doc.txt",
        text=sample_text,
        chunk_size=180,
        overlap=30,
    )

    print("=== DATASET REGISTERED ===")
    print(f"Dataset ID: {dataset.dataset_id}")
    print(f"Merkle root: {dataset.merkle_root}")
    print()

    system.grant_access(user_id=reader.user_id, dataset_id=dataset.dataset_id)

    print("=== LEDGER ===")
    system.ledger.print_entries()
    print()

    print("=== QUERY RESULTS ===")
    results = system.query(
        user_id=reader.user_id,
        dataset_id=dataset.dataset_id,
        query_text="How does the system control access to encrypted chunks?",
        k=2,
    )

    for r in results:
        print(r)
        print()


if __name__ == "__main__":
    main()