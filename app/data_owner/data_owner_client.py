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

    # Step 2: interactive loop
    while True:
        print("\nWhat do you want to do?")
        print("  1) Upload a text document")
        print("  2) List datasets")
        print("  3) Show owner info")
        print("  4) Quit")

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
            info = service.get_owner_info()
            print("Owner info:")
            print(f"  user_id   : {info['user_id']}")
            print(f"  name      : {info['name']}")
            print(f"  public_key: {info['public_key'][:50]}...")

        elif choice == "4" or choice.lower() in ("q", "quit", "exit"):
            print("Bye!")
            break
        else:
            print("Unknown choice.")

if __name__ == "__main__":
    asyncio.run(main())