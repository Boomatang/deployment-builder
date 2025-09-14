import multiprocessing as mp
import queue
import subprocess
from itertools import zip_longest
from time import perf_counter

from rich.table import Table

from deployment_builder.config import Config
from deployment_builder.kind import Kind
from deployment_builder.logging_config import get_logger


class Plan:
    def __init__(self, config, engine: Kind):
        self.config = config
        self.log = get_logger()
        self.engine = engine
        self.workers = self._get_workers()

        self.log.info("Plan created")

    def cluster_queue(self) -> mp.Queue:
        q = mp.Queue()
        for cluster in self.get_plan():
            q.put(cluster)
        return q

    def services_queue(self) -> mp.Queue:
        plan_details = self.get_plan()
        services = mp.Queue()
        stopped = False
        while not stopped:
            stopped = True
            for cluster in plan_details:
                service = cluster.next_service()
                if service is not None:
                    stopped = False
                    services.put(service)
        return services

    def get_plan(self):
        clusters_names = get_cluster_names_with_config(self.config)

        plan = []
        for cluster in clusters_names:
            plan.append(Cluster(cluster[0], cluster[1], self.engine))

        for service in self.config["services"]:
            for p in plan:
                p.add(Service(service, self.config["services"][service], context=p.context))

        return plan

    def cluster_count(self):
        plan_details = self.get_plan()
        return len(plan_details)

    def cluster_names(self):
        plan_details = self.get_plan()
        return [c.name for c in plan_details]

    def as_text(self):
        self.log.info("Building text view of plan.")
        data = []

        # build general table
        cluster_kinds = Table(title="Cluster types to create")
        cluster_kinds.add_column("Cluster Kinds", justify="centre")
        cluster_kinds.add_column("Count", justify="right")
        cluster_kinds.add_column("Services", justify="right")
        for row in self._type_count(len(self.config["services"])):
            cluster_kinds.add_row(row[0], str(row[1]), str(row[2]))
        data.append(cluster_kinds)

        # build detail table
        detail_table = Table(title="Service to add to cluster kind, ordered")
        standard_services = list(self.config["services"].keys())
        clusters = self._service_overview(standard_services)
        services = []
        for kind in clusters:
            detail_table.add_column(kind)
            services.append(clusters[kind])

        transposed = list(zip_longest(*services, fillvalue=""))
        for row in transposed:
            detail_table.add_row(*row)

        data.append(detail_table)
        return data

    def _service_overview(self, services=None):
        s = services
        data = {}
        for cluster in self.config["clusters"]:
            c = self.config["clusters"][cluster]
            data[cluster] = []
            if s is not None:
                data[cluster].extend(s)

            if c.get("services"):
                custom_services = list(c["services"].keys())
                data[cluster].extend(custom_services)
        return data

    def _get_workers(self):
        count = self.config["general"]["max_workers"]

        if count <= 0:
            self.log.warn(f"Number of worker set below usable; max_workers: {count}")
            self.log.warn("Setting the number of workers to 1")
            count = 1
        return count

    def _type_count(self, services=0):
        data = []
        for cluster in self.config["clusters"]:
            s = services
            c = self.config["clusters"][cluster]
            count = c.get("count", 0)
            if c.get("enable") and c["enable"]:
                count = 1
            s += len(c.get("services", []))
            data.append((cluster, count, s))
        return data


class Service:
    def __init__(self, name, config, context=None):
        self.name = name
        self.config = config
        self.context = context
        self.log = get_logger()

    def command(self):
        cmd = self.config["cmd"].split()
        if self.context:
            cmd.extend(["--context", self.context])
        return cmd

    def run(self):
        start = perf_counter()
        self.log.info(f"creating cluster {self.name}")

        result = subprocess.run(
            self.command(), capture_output=True, text=True, check=False  # Don't raise exception on non-zero exit
        )
        success = result.returncode == 0

        # Log output if requested (debug level) or if there was an error
        if result.stdout:
            self.log.debug(f"Service stdout: {result.stdout}")
        if result.stderr:
            self.log.debug(f"Service stderr: {result.stderr}")

        end = perf_counter()
        if success:
            self.log.info(f"Service: {self.name} completed successfully, time taken: {end - start}")
        else:
            self.log.error(
                f"Service: {self.name} failed with return code {result.returncode}, time taken: {end - start}"
            )

    def __repr__(self):
        return f"SERVICE: {self.name}, {self.config=}"


class Cluster:
    def __init__(self, name, config, engine: Kind):
        self.name = name
        self.context = f"kind-{name}"
        self.config = config
        self.services = []
        self.engine = engine
        self.engine.name = self.name
        self._idx = 0
        for service in config.get("services", []):
            self.services.append(Service(service, config["services"][service], context=self.context))

    def create(self):
        self.engine.create(self.name)

    def delete(self):
        self.engine.delete(self.name)

    def add(self, service: Service) -> None:
        self.services.insert(0, service)

    def next_service(self) -> Service:

        if self._idx >= len(self.services):
            return None

        service = self.services[self._idx]
        self._idx += 1
        return service

    def __repr__(self):
        return f"Cluster: {self.name}, {self.config=}, {self.services=}"


def get_cluster_names_with_config(config: dict) -> list[str]:
    prefix = config[Config.GENERAL.value][Config.PREFIX.value]
    clusters = []
    for cluster in config[Config.CLUSTERS.value]:
        c = config[Config.CLUSTERS.value][cluster]
        if Config.ENABLE.value in c and c[Config.ENABLE.value]:
            clusters.append(("-".join([prefix, cluster]), c))
            continue
        for num in range(c.get(Config.COUNT.value, 0)):
            clusters.append(("-".join([prefix, cluster, str(num + 1)]), c))

    return clusters


def service_worker(task_queue: mp.Queue, result_queue, worker_id: int):
    while not task_queue.empty():
        try:
            service = task_queue.get(timeout=0.1)

            if service is None:
                return

            service.run()
            result_queue.put(("SUCCESS", "Service ran"))

        except queue.Empty:
            continue
        except Exception as e:
            result_queue.put(("ERROR", f"Worker {worker_id} error: {str(e)}"))


def cluster_create_worker(task_queue: mp.Queue, result_queue, worker_id: int):
    while not task_queue.empty():
        try:
            cluster = task_queue.get(timeout=0.1)

            if cluster is None:
                return

            cluster.create()
            result_queue.put(("SUCCESS", "Cluster created"))

        except queue.Empty:
            continue
        except Exception as e:
            result_queue.put(("ERROR", f"Worker {worker_id} error: {str(e)}"))


def cluster_delete_worker(task_queue: mp.Queue, result_queue, worker_id: int):
    while not task_queue.empty():
        try:
            cluster = task_queue.get(timeout=0.1)

            if cluster is None:
                return

            cluster.delete()
            result_queue.put(("SUCCESS", "Cluster deleted"))

        except queue.Empty:
            continue
        except Exception as e:
            result_queue.put(("ERROR", f"Worker {worker_id} error: {str(e)}"))
