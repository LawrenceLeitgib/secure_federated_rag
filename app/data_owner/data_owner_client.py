import asyncio
import argparse
from pathlib import Path
import sys

from app.data_owner.service import DataOwnerService


WIKI_DATA_ROOT = Path("wiki_data_owners")
WIKI_OWNER_FOLDERS = {
    "dataOwner1": "data_owner_1_science",
    "dataOwner2": "data_owner_2_history",
    "dataOwner3": "data_owner_3_technology",
    "dataOwner4": "data_owner_4_geography",
    "dataOwner5": "data_owner_5_art_culture",
}


def prompt(msg: str) -> str:
    try:
        return input(msg)
    except EOFError:
        return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start a data owner client.")
    parser.add_argument(
        "--name",
        help="Owner name to use without prompting, for example dataOwner1.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    service = DataOwnerService()

    # Step 1: create or load an owner
    name = (args.name or prompt("Enter your name (for this data owner): ")).strip()
    if not name:
        print("Name is required. Exiting.")
        sys.exit(1)
   

    owner_info = await service.create_owner(name)

    print(f"Created data owner:")
    print(f"  user_id   : {owner_info['user_id']}")
    print(f"  name      : {owner_info['name']}")
    print(f"  public_key: {owner_info['public_key'][:50]}...")

    if name == "test":
        #upload a test dataset
        await initialize_for_testing(service)
    elif name in WIKI_OWNER_FOLDERS:
        await initialize_wiki_data_owner(service, name)

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


def load_wiki_article(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    document_name = path.stem

    for line in text.splitlines():
        if line.startswith("TITLE: "):
            document_name = line.removeprefix("TITLE: ").strip()
            break

    return document_name, text


async def initialize_wiki_data_owner(service: DataOwnerService, owner_name: str) -> None:
    folder_name = WIKI_OWNER_FOLDERS[owner_name]
    owner_dir = WIKI_DATA_ROOT / folder_name

    if not owner_dir.exists():
        print(f"Wiki data folder not found: {owner_dir}")
        return

    article_paths = sorted(owner_dir.glob("*.txt"))
    if not article_paths:
        print(f"No wiki article files found in: {owner_dir}")
        return

    print(f"Uploading {len(article_paths)} wiki datasets for {owner_name} from {owner_dir}")

    uploaded_datasets = []
    for article_path in article_paths:
        document_name, text = load_wiki_article(article_path)
        dataset = await service.upload_text_document(
            document_name=document_name,
            text=text,
        )
        uploaded_datasets.append(dataset)
        print(f"Uploaded {document_name} with id: {dataset['dataset_id']}")

    result = await service.get_retrieval_engine_id()
    status = result.get("status")
    if status != "ok":
        print(f"Error while getting retrieval engine id: {result.get('error')}")
        return

    re_id = result.get("result")
    for dataset in uploaded_datasets:
        await service.give_access(dataset_id=dataset["dataset_id"], re_id=re_id)
        print(f"Granted access to dataset {dataset['dataset_id']} for retriever {re_id}")


async def initialize_for_testing(service):
    result = await service.get_retrieval_engine_id()
    status = result.get("status")
    if status != "ok":
        print(f"Error while getting retrieval engine id: {result.get('error')}")
        return
    re_id = result.get("result")



    text1="Retrieval-Augmented Generation improves question answering by retrieving relevant chunks     from a knowledge base. In this prototype, data owners upload documents, which are chunked,     hashed into a Merkle tree, encrypted, and stored by an untrusted storage provider.      A blockchain-like ledger keeps metadata such as user registration, dataset registration,     Merkle root, and authorizations. Custodians hold key shares and only reconstruct the     encryption key when the querying user is authorized.      The retrieval engine embeds chunks and user queries, then performs similarity search.     The most relevant encrypted chunks are fetched, decrypted, and returned as context."
    dataset1 = await service.upload_text_document(
                document_name="Rag overview",
                text=text1,
            )
    
    text2 ="A balanced diet is essential for maintaining good health and supporting the body's daily functions. It includes a variety of nutrients such as carbohydrates, proteins, fats, vitamins, and minerals, each playing a specific role.  Carbohydrates are the body's primary source of energy and are found in foods like bread, rice, and fruits. Proteins are crucial for building and repairing tissues, and they are commonly found in meat, fish, eggs, and legumes. Fats, although often misunderstood, are necessary for hormone production and cell structure.  Vitamins and minerals support numerous biological processes. For example, vitamin C helps with immune function, while calcium is important for bone strength. A deficiency in essential nutrients can lead to various health problems.  Hydration is another key component of a healthy diet. Water is involved in digestion, temperature regulation, and the transport of nutrients throughout the body.  Maintaining a balanced diet also involves moderation. Excessive consumption of sugar, salt, or processed foods can increase the risk of chronic diseases such as diabetes and heart disease."
    dataset2 = await service.upload_text_document(
                document_name="Balanced Diet",
                text=text2,
            )
    text3= "The Roman Empire was one of the most influential civilizations in history, lasting from 27 BCE to 476 CE in the West. It expanded across Europe, North Africa, and parts of the Middle East, creating a vast and diverse territory.  Roman society was highly structured, with a clear hierarchy that included emperors, senators, citizens, and slaves. The empire was known for its advanced engineering, including roads, aqueducts, and monumental architecture such as the Colosseum.  The Roman legal system laid the foundation for many modern legal principles. Laws were written and applied across the empire, helping maintain order in such a large territory.  Despite its strength, the empire faced numerous challenges, including political instability, economic difficulties, and external invasions by various tribes. These factors contributed to the eventual fall of the Western Roman Empire.  However, the legacy of Rome continues to influence modern language, law, architecture, and governance systems."

    dataset3 = await service.upload_text_document(
                document_name="Roman Empire",
                text=text3,
            )
    
    text4=" Memory is the cognitive process that allows humans to store, retain, and recall information. It is essential for learning, decision-making, and daily functioning.  There are different types of memory, including short-term memory and long-term memory. Short-term memory temporarily holds information for immediate use, while long-term memory stores information over extended periods.  Long-term memory can be further divided into explicit and implicit memory. Explicit memory involves conscious recall, such as remembering facts or events, whereas implicit memory includes skills and habits that are performed automatically.  Memory is not a perfect recording of events. It can be influenced by emotions, biases, and external suggestions, leading to distortions or false memories.  The process of memory formation involves encoding, storage, and retrieval. Effective learning strategies, such as repetition and meaningful association, can improve memory retention."
    dataset4 = await service.upload_text_document(
                document_name="Memory",
                text=text4,
            )


    print(f"Uploaded test dataset with id: {dataset1['dataset_id']}")
    print(f"Uploaded test dataset with id: {dataset2['dataset_id']}")
    print(f"Uploaded test dataset with id: {dataset3['dataset_id']}")
    print(f"Uploaded test dataset with id: {dataset4['dataset_id']}")


    await service.give_access(dataset_id=dataset1["dataset_id"], re_id=re_id)
    print(f"Granted access to dataset {dataset1['dataset_id']} for retriever {re_id}")
    await service.give_access(dataset_id=dataset2["dataset_id"], re_id=re_id)
    print(f"Granted access to dataset {dataset2['dataset_id']} for retriever {re_id}")
    await service.give_access(dataset_id=dataset3["dataset_id"], re_id=re_id,test=True)
    print(f"Granted access to dataset {dataset3['dataset_id']} for retriever {re_id}")
    await service.give_access(dataset_id=dataset4["dataset_id"], re_id=re_id)
    print(f"Granted access to dataset {dataset4['dataset_id']} for retriever {re_id}")




if __name__ == "__main__":
    asyncio.run(main())
