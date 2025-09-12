"""Load balancing strategies for service queue system."""

from abc import ABC, abstractmethod
from typing import List
from .queue import ServiceItem, ServiceWorker


class LoadBalancer(ABC):
    """Abstract base class for load balancing strategies."""

    @abstractmethod
    def select_worker(self, item: ServiceItem, workers: List[ServiceWorker]) -> ServiceWorker:
        """Select worker for service item.

        Args:
            item: Service item to assign
            workers: List of available workers

        Returns:
            Selected worker for the service item
        """
        pass


class RoundRobinBalancer(LoadBalancer):
    """Round-robin load balancing strategy."""

    def __init__(self):
        """Initialize round-robin balancer."""
        self._current_index = 0

    def select_worker(self, item: ServiceItem, workers: List[ServiceWorker]) -> ServiceWorker:
        """Select worker using round-robin strategy.

        Args:
            item: Service item to assign
            workers: List of available workers

        Returns:
            Selected worker for the service item
        """
        if not workers:
            raise ValueError("No workers available")

        # Filter to only running workers
        available_workers = [w for w in workers if w.is_running]
        if not available_workers:
            raise ValueError("No running workers available")

        # Select next worker in round-robin fashion
        selected_worker = available_workers[self._current_index % len(available_workers)]
        self._current_index += 1

        return selected_worker


class LeastLoadedBalancer(LoadBalancer):
    """Least loaded worker selection strategy."""

    def select_worker(self, item: ServiceItem, workers: List[ServiceWorker]) -> ServiceWorker:
        """Select least loaded worker.

        Args:
            item: Service item to assign
            workers: List of available workers

        Returns:
            Selected worker for the service item
        """
        if not workers:
            raise ValueError("No workers available")

        # Filter to only running workers
        available_workers = [w for w in workers if w.is_running]
        if not available_workers:
            raise ValueError("No running workers available")

        # Select worker with no current item (least loaded)
        idle_workers = [w for w in available_workers if w.current_item is None]
        if idle_workers:
            return idle_workers[0]

        # If all workers are busy, select the one with the oldest current item
        # (This is a simple heuristic - in practice, you might want more sophisticated logic)
        return available_workers[0]


class PriorityBasedBalancer(LoadBalancer):
    """Priority-based worker selection strategy."""

    def __init__(self, base_balancer: LoadBalancer = None):
        """Initialize priority-based balancer.

        Args:
            base_balancer: Base balancer to use for same-priority items
        """
        self.base_balancer = base_balancer or RoundRobinBalancer()

    def select_worker(self, item: ServiceItem, workers: List[ServiceWorker]) -> ServiceWorker:
        """Select worker based on priority and load.

        Args:
            item: Service item to assign
            workers: List of available workers

        Returns:
            Selected worker for the service item
        """
        if not workers:
            raise ValueError("No workers available")

        # Filter to only running workers
        available_workers = [w for w in workers if w.is_running]
        if not available_workers:
            raise ValueError("No running workers available")

        # For high priority items (priority < 5), prefer idle workers
        if item.priority < 5:
            idle_workers = [w for w in available_workers if w.current_item is None]
            if idle_workers:
                return self.base_balancer.select_worker(item, idle_workers)

        # For normal priority items, use base balancer
        return self.base_balancer.select_worker(item, available_workers)


def create_load_balancer(strategy: str) -> LoadBalancer:
    """Create a load balancer based on strategy name.

    Args:
        strategy: Load balancing strategy name

    Returns:
        Load balancer instance

    Raises:
        ValueError: If strategy is not supported
    """
    strategies = {
        "round_robin": RoundRobinBalancer,
        "least_loaded": LeastLoadedBalancer,
        "priority_based": PriorityBasedBalancer,
    }

    if strategy not in strategies:
        raise ValueError(
            f"Unsupported load balancing strategy: {strategy}. Supported strategies: {list(strategies.keys())}"
        )

    return strategies[strategy]()
