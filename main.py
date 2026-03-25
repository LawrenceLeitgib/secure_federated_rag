import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

MODULES = {
    "storage_server": ("app.storage.storage_server", ""),
    "blockchain_server": ("app.blockchain.blockchain_server", ""),
    # two custodian instances with different ports
    "custodian_1": ("app.custodians.custodian_server", "--port 9001"),
    "custodian_2": ("app.custodians.custodian_server", "--port 9002"),
    "retrieval_server": ("app.retrieval.retrieval_server", ""),
    "data_owner_client": ("app.data_owner.data_owner_client", ""),
    "user_client": ("app.user.user_client", ""),
}


def open_in_new_terminal(name: str, module: str, extra_args: str = ""):
    cmd = [
        "gnome-terminal",
        "--title", name,
        "--",
        "bash", "-c",
        f"cd '{PROJECT_ROOT}' && python -m {module} {extra_args}; exec bash"
    ]
    return subprocess.Popen(cmd)


def main() -> None:
    processes = []

    servers_order = [
        "storage_server",
        "blockchain_server",
        "custodian_1",
        "custodian_2",
        "retrieval_server",
    ]

    for srv in servers_order:
        module, extra_args = MODULES[srv]
        p = open_in_new_terminal(srv, module, extra_args)
        processes.append(p)
        time.sleep(1.0)

    time.sleep(1.5)
    
    clients_order = [
        "data_owner_client",
        "user_client",
    ]

    for cli in clients_order:
        module, extra_args = MODULES[cli]
        p = open_in_new_terminal(cli, module, extra_args)
        processes.append(p)
        time.sleep(0.5)
    
    try:
        print("All servers and clients started in separate terminals.")
        print("Press Ctrl+C here to exit this launcher (other terminals stay open).")
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Launcher exiting. Child terminals will stay open.")


if __name__ == "__main__":
    main()