from __future__ import annotations

import asyncio
import socket
import subprocess
import sys
from pathlib import Path

from app.data_owner.data_owner_client import WIKI_OWNER_FOLDERS, load_wiki_article
from app.data_owner.service import DataOwnerService


PROJECT_ROOT = Path(__file__).resolve().parent

SERVER_MODULES = [
    ("embedding_server", "app.retrieval.embedding_server", []),
    ("storage_server", "app.storage.storage_server", []),
    ("blockchain_server", "app.blockchain.blockchain_server", []),
    ("custodian_1", "app.custodians.custodian_server", ["--port", "9001"]),
    ("custodian_2", "app.custodians.custodian_server", ["--port", "9002"]),
    ("retrieval_server", "app.retrieval.retrieval_server", []),
]

SERVER_PORTS = [11001, 7001, 8001, 9001, 9002, 10001]
WIKI_DATA_ROOT = PROJECT_ROOT / "wiki_data_owners"


class BenchmarkEnvironment:
    def __init__(self) -> None:
        self.processes: list[subprocess.Popen] = []

    async def __aenter__(self) -> "BenchmarkEnvironment":
        self.start_servers()
        await self.wait_until_ready()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.stop_servers()

    def start_servers(self) -> None:
        for name, module, args in SERVER_MODULES:
            process = subprocess.Popen(
                [sys.executable, "-m", module, *args],
                cwd=PROJECT_ROOT,
            )
            self.processes.append(process)
            print(f"Started {name} with pid={process.pid}")

    async def wait_until_ready(self, timeout_s: float = 120.0) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        for port in SERVER_PORTS:
            while True:
                if await asyncio.to_thread(self._is_port_open, port):
                    break
                if loop.time() >= deadline:
                    raise TimeoutError(f"Timed out waiting for server on port {port}")
                await asyncio.sleep(0.5)

    @staticmethod
    def _is_port_open(port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            return False

    def stop_servers(self) -> None:
        for process in reversed(self.processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(self.processes):
            if process.poll() is None:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


async def bootstrap_wiki_data_owners(
    *,
    benchmark_uploads: bool = False,
) -> tuple[list[DataOwnerService], list[dict]]:
    services: list[DataOwnerService] = []
    upload_results: list[dict] = []

    for owner_name in WIKI_OWNER_FOLDERS:
        service = DataOwnerService()
        await service.create_owner(owner_name)
        services.append(service)

        owner_dir = WIKI_DATA_ROOT / WIKI_OWNER_FOLDERS[owner_name]
        article_paths = sorted(owner_dir.glob("*.txt"))
        if not article_paths:
            print(f"No wiki article files found in: {owner_dir}")
            continue

        print(f"Uploading {len(article_paths)} wiki datasets for {owner_name}")
        for article_path in article_paths:
            document_name, text = load_wiki_article(article_path)
            if benchmark_uploads:
                dataset = await service.upload_text_document_with_benchmark(
                    document_name=document_name,
                    text=text,
                )
            else:
                dataset = await service.upload_text_document(
                    document_name=document_name,
                    text=text,
                )
            dataset["owner_name"] = owner_name
            dataset["source_file"] = str(article_path)
            upload_results.append(dataset)
            print(f"Uploaded {document_name} for {owner_name}")

    if not services:
        return services, upload_results

    result = await services[0].get_retrieval_engine_id()
    if result.get("status") != "ok":
        raise RuntimeError(f"Error while getting retrieval engine id: {result.get('error')}")
    re_id = result.get("result")

    for service in services:
        for dataset in service.list_datasets():
            await service.give_access(dataset_id=dataset["dataset_id"], re_id=re_id)

    return services, upload_results
