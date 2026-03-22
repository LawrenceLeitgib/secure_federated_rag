# app/data_owner/client.py
import asyncio
import sys

from app.data_owner.service import DataOwnerService


def prompt(msg: str) -> str:
    try:
        return input(msg)
    except EOFError:
        return ""


async def main() -> None:
    service = DataOwnerService()

    # Step 1: create or load an owner
    name = prompt("Enter your name (for this data owner): ").strip()
    if not name:
        print("Name is required. Exiting.")
        sys.exit(1)
   

    owner_info = await service.create_owner(name)
    print(f"Created data owner:")
    print(f"  user_id   : {owner_info['user_id']}")
    print(f"  name      : {owner_info['name']}")
    print(f"  public_key: {owner_info['public_key'][:50]}...")

    if(name == "test"):
        #upload a test dataset
        lines=["Retrieval-Augmented Generation improves question answering by retrieving relevant chunks",
                     "from a knowledge base. In this prototype, data owners upload documents, which are chunked,",
                     "hashed into a Merkle tree, encrypted, and stored by an untrusted storage provider.",
                     "",
                     "A blockchain-like ledger keeps metadata such as user registration, dataset registration,",
                     "Merkle root, and authorizations. Custodians hold key shares and only reconstruct the",
                     "encryption key when the querying user is authorized.",
                     "",
                     "The retrieval engine embeds chunks and user queries, then performs similarity search.",
                     "The most relevant encrypted chunks are fetched, decrypted, and returned as context." ]
        text = "\n".join(lines)
        dataset = await service.upload_text_document(
                document_name="Test Document",
                text=text,
            )
        print(f"Uploaded test dataset with id: {dataset['dataset_id']}")

    # Step 2: interactive loop
    while True:
        print("\nWhat do you want to do?")
        print("  1) Upload a text document")
        print("  2) List datasets")
        print("  3) Give access to a retriever")
        print("  4) Show owner info")
        print("  5) Quit")
        

        choice = prompt("> ").strip()

        if choice == "1":
            document_name = prompt("Document name: ").strip()
            print("Paste your text (end with an empty line):")


            lines = []
            while True:
                line = prompt("")
                if line == "":
                    break
                lines.append(line)
            text = "\n".join(lines)

            dataset = await service.upload_text_document(
                document_name=document_name,
                text=text,
            )
            print(f"Uploaded dataset with id: {dataset['dataset_id']}")

        elif choice == "2":
            datasets = service.list_datasets()
            if not datasets:
                print("No datasets yet.")
            else:
                print("Datasets:")
                for ds in datasets:
                    print(f"  - id={ds['dataset_id']} name={ds['document_name']}")
            
        elif choice == "3":
            dataset_id = prompt("Dataset ID to grant access to: ").strip()
            retriever_user_id = prompt("Retriever user ID to grant access to: ").strip()
            await service.give_access(dataset_id=dataset_id, re_id=retriever_user_id)
            print(f"Granted access to dataset {dataset_id} for retriever {retriever_user_id}")

        elif choice == "4":
            info = service.get_owner_info()
            print("Owner info:")
            print(f"  user_id   : {info['user_id']}")
            print(f"  name      : {info['name']}")
            print(f"  public_key: {info['public_key'][:50]}...")

        elif choice == "5" or choice.lower() in ("q", "quit", "exit"):
            print("Bye!")
            break
        else:
            print("Unknown choice.")



if __name__ == "__main__":
    asyncio.run(main())