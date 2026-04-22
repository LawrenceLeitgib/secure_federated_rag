import subprocess
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent

SERVER_MODULES = {
    "embedding_server": ("app.retrieval.embedding_server", ""),
    "storage_server": ("app.storage.storage_server", ""),
    "blockchain_server": ("app.blockchain.blockchain_server", ""),
    "custodian_1": ("app.custodians.custodian_server", "--port 9001"),
    "custodian_2": ("app.custodians.custodian_server", "--port 9002"),
    "retrieval_server": ("app.retrieval.retrieval_server", ""),
}

CLIENT_MODULES = {
    "user_client": ("app.user.user_client", ""),
}

DATA_OWNER_NAMES = [
    "dataOwner1",
    "dataOwner2",
    "dataOwner3",
    "dataOwner4",
    "dataOwner5",
]


def open_in_new_terminal(name: str, module: str, extra_args: str = "") -> subprocess.Popen:
    cmd = [
        "gnome-terminal",
        "--title",
        name,
        "--",
        "bash",
        "-c",
        f"cd '{PROJECT_ROOT}' && python -m {module} {extra_args}; exec bash",
    ]
    return subprocess.Popen(cmd)


def main() -> None:
    processes = []

    for server_name, (module, extra_args) in SERVER_MODULES.items():
        processes.append(open_in_new_terminal(server_name, module, extra_args))
        time.sleep(1.0)

    time.sleep(1.5)

    for owner_name in DATA_OWNER_NAMES:
        module = "app.data_owner.data_owner_client"
        extra_args = f"--name {owner_name}"
        processes.append(open_in_new_terminal(owner_name, module, extra_args))
        time.sleep(0.5)

    for client_name, (module, extra_args) in CLIENT_MODULES.items():
        processes.append(open_in_new_terminal(client_name, module, extra_args))
        time.sleep(0.5)

    try:
        print("Infrastructure, five data owners, and user client started in separate terminals.")
        print("Press Ctrl+C here to exit this launcher (other terminals stay open).")
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Launcher exiting. Child terminals will stay open.")


if __name__ == "__main__":
    main()
