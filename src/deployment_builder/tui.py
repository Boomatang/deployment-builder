import queue

from rich.progress import Progress


def cluster_create(total: int, result_queue):
    with Progress() as progress:
        task_id = progress.add_task("[green]Creating cluster...", total=total)
        completed = 0
        while completed < total:
            try:
                _ = result_queue.get(timeout=0.1)
                completed += 1
                progress.advance(task_id, 1)

            except queue.Empty:
                continue


def cluster_delete(total: int, result_queue):
    with Progress() as progress:
        task_id = progress.add_task("[red]Creating cluster...", total=total)
        completed = 0
        while completed < total:
            try:
                _ = result_queue.get(timeout=0.1)
                completed += 1
                progress.advance(task_id, 1)

            except queue.Empty:
                continue


def service_run(total: int, result_queue):
    with Progress() as progress:
        task_id = progress.add_task("[green]Running service commands...", total=total)
        completed = 0
        while completed < total:
            try:
                _ = result_queue.get(timeout=0.1)

                completed += 1
                progress.advance(task_id, 1)

            except queue.Empty:
                continue
