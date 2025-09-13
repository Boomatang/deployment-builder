"""Execution planning and dependency resolution for service queue system."""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set

from .config import DeploymentConfig, ServiceConfig
from .queue import ServiceItem

logger = logging.getLogger(__name__)


class DependencyGraph:
    """Graph for managing service dependencies and resolving execution order."""

    def __init__(self):
        """Initialize dependency graph."""
        self.graph: Dict[str, Set[str]] = defaultdict(set)  # service -> dependencies
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)  # dependency -> dependents
        self.all_services: Set[str] = set()

    def add_dependency(self, service: str, depends_on: str) -> None:
        """Add dependency relationship.

        Args:
            service: Service that depends on another
            depends_on: Service that is depended upon
        """
        self.all_services.add(service)
        self.all_services.add(depends_on)
        self.graph[service].add(depends_on)
        self.reverse_graph[depends_on].add(service)
        logger.debug(f"Added dependency: {service} depends on {depends_on}")

    def add_service(self, service: str) -> None:
        """Add a service with no dependencies.

        Args:
            service: Service name to add
        """
        self.all_services.add(service)
        logger.debug(f"Added service: {service}")

    def resolve_dependencies(self) -> List[str]:
        """Resolve dependencies using topological sort.

        Returns:
            List of services in execution order

        Raises:
            ValueError: If circular dependencies are detected
        """
        # Check for cycles first
        cycles = self.detect_cycles()
        if cycles:
            raise ValueError(f"Circular dependencies detected: {cycles}")

        # Topological sort using Kahn's algorithm
        in_degree = {service: len(self.graph[service]) for service in self.all_services}
        queue = deque([service for service, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            service = queue.popleft()
            result.append(service)

            # Remove this service from all its dependents' dependencies
            for dependent in self.reverse_graph[service]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Check if all services were processed
        if len(result) != len(self.all_services):
            remaining = self.all_services - set(result)
            raise ValueError(f"Could not resolve dependencies for services: {remaining}")

        logger.info(f"Resolved dependency order: {result}")
        return result

    def detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies using DFS.

        Returns:
            List of cycles found (each cycle is a list of service names)
        """
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(service: str, path: List[str]) -> None:
            if service in rec_stack:
                # Found a cycle
                cycle_start = path.index(service)
                cycle = path[cycle_start:] + [service]
                cycles.append(cycle)
                return

            if service in visited:
                return

            visited.add(service)
            rec_stack.add(service)
            path.append(service)

            for dependent in self.reverse_graph[service]:
                dfs(dependent, path)

            rec_stack.remove(service)
            path.pop()

        for service in self.all_services:
            if service not in visited:
                dfs(service, [])

        return cycles

    def get_ready_services(self, completed: Set[str]) -> List[str]:
        """Get services ready to execute (all dependencies completed).

        Args:
            completed: Set of completed service names

        Returns:
            List of services ready to execute
        """
        ready = []
        for service in self.all_services:
            if service not in completed:
                dependencies = self.graph[service]
                if all(dep in completed for dep in dependencies):
                    ready.append(service)
        return ready

    def get_dependencies(self, service: str) -> Set[str]:
        """Get direct dependencies of a service.

        Args:
            service: Service name

        Returns:
            Set of direct dependencies
        """
        return self.graph[service].copy()

    def get_dependents(self, service: str) -> Set[str]:
        """Get services that depend on this service.

        Args:
            service: Service name

        Returns:
            Set of services that depend on this service
        """
        return self.reverse_graph[service].copy()


@dataclass
class ExecutionTimeline:
    """Represents the execution timeline for services."""

    service_name: str
    cluster_name: str
    cluster_type: str
    estimated_start: datetime
    estimated_duration: float
    estimated_end: datetime
    dependencies: List[str]
    priority: int


class ExecutionPlanner:
    """Creates and manages execution plans for service deployment."""

    def __init__(self, config: DeploymentConfig):
        """Initialize execution planner.

        Args:
            config: Deployment configuration
        """
        self.config = config
        self.service_items: List[ServiceItem] = []
        self.execution_order: List[ServiceItem] = []
        self.dependency_graph = DependencyGraph()
        self.timeline: List[ExecutionTimeline] = []

    def create_execution_plan(self) -> List[ServiceItem]:
        """Create execution plan for all services.

        Returns:
            List of service items in execution order
        """
        logger.info("Creating execution plan for all services")

        # Clear previous plan
        self.service_items.clear()
        self.execution_order.clear()
        self.dependency_graph = DependencyGraph()
        self.timeline.clear()

        # Create service items from configuration
        self._create_service_items()

        # Build dependency graph
        self._build_dependency_graph()

        # Resolve dependencies and create execution order
        self._resolve_execution_order()

        # Optimize execution order for maximum parallelism
        self._optimize_execution_order()

        # Create timeline
        self._create_execution_timeline()

        logger.info(f"Created execution plan with {len(self.execution_order)} service items")
        return self.execution_order

    def _create_service_items(self) -> None:
        """Create service items from configuration."""
        cluster_names = self.config.get_cluster_names()

        for cluster_name in cluster_names:
            # Determine cluster type from name
            cluster_type = self._extract_cluster_type(cluster_name)

            # Get cluster configuration
            cluster_config = self.config.clusters.get(cluster_type)
            if not cluster_config:
                logger.warning(f"No configuration found for cluster type: {cluster_type}")
                continue

            # Create service items for cluster-specific services
            for service_name, service_config in cluster_config.services.items():
                # Create enhanced service config with queue properties
                enhanced_config = self._enhance_service_config(service_config, service_name)

                service_item = ServiceItem(
                    cluster_name=cluster_name,
                    cluster_type=cluster_type,
                    service_name=service_name,
                    service_config=enhanced_config,
                    priority=getattr(enhanced_config, "priority", 0),
                    dependencies=getattr(enhanced_config, "dependencies", []),
                    estimated_duration=getattr(enhanced_config, "estimated_duration", 0.0),
                    max_retries=getattr(enhanced_config, "retry_attempts", 3),
                )

                self.service_items.append(service_item)
                logger.debug(f"Created service item: {service_name} for {cluster_name}")

            # Create service items for global services
            for service_name, service_config in self.config.services.items():
                enhanced_config = self._enhance_service_config(service_config, service_name)

                service_item = ServiceItem(
                    cluster_name=cluster_name,
                    cluster_type=cluster_type,
                    service_name=service_name,
                    service_config=enhanced_config,
                    priority=getattr(enhanced_config, "priority", 0),
                    dependencies=getattr(enhanced_config, "dependencies", []),
                    estimated_duration=getattr(enhanced_config, "estimated_duration", 0.0),
                    max_retries=getattr(enhanced_config, "retry_attempts", 3),
                )

                self.service_items.append(service_item)
                logger.debug(f"Created global service item: {service_name} for {cluster_name}")

    def _extract_cluster_type(self, cluster_name: str) -> str:
        """Extract cluster type from cluster name.

        Args:
            cluster_name: Full cluster name (e.g., "my-project-worker-1")

        Returns:
            Cluster type (e.g., "worker")
        """
        # Remove prefix and number suffix to get cluster type
        parts = cluster_name.split("-")
        if len(parts) >= 2:
            # Remove first part (prefix) and last part (number if present)
            if parts[-1].isdigit():
                cluster_type_parts = parts[1:-1]
            else:
                cluster_type_parts = parts[1:]

            # For complex names like "my-project-database-cluster-2"
            # We want to return "database-cluster", not "project-database-cluster"
            # So we need to find the actual cluster type in the config
            cluster_type = "-".join(cluster_type_parts)

            # Check if this cluster type exists in config
            if cluster_type in self.config.clusters:
                return cluster_type

            # If not found, try to match by removing the first part
            if len(cluster_type_parts) > 1:
                shorter_type = "-".join(cluster_type_parts[1:])
                if shorter_type in self.config.clusters:
                    return shorter_type
                # Try removing one more part if still too long
                if len(cluster_type_parts) > 2:
                    even_shorter_type = "-".join(cluster_type_parts[2:])
                    if even_shorter_type in self.config.clusters:
                        return even_shorter_type

            # If still not found, return the original cluster type
            return cluster_type
        return cluster_name

    def _enhance_service_config(self, service_config: ServiceConfig, service_name: str) -> ServiceConfig:
        """Enhance service config with queue-specific properties.

        Args:
            service_config: Original service configuration
            service_name: Name of the service

        Returns:
            Enhanced service configuration
        """
        # For now, return the original config
        # In the future, this could add queue-specific properties
        return service_config

    def _build_dependency_graph(self) -> None:
        """Build dependency graph from service items."""
        for item in self.service_items:
            # Add service to graph
            service_key = f"{item.cluster_name}:{item.service_name}"
            self.dependency_graph.add_service(service_key)

            # Add dependencies
            for dep in item.dependencies:
                # Dependencies can be either service names or cluster:service format
                if ":" in dep:
                    dep_key = dep
                else:
                    # Assume dependency is for the same cluster
                    dep_key = f"{item.cluster_name}:{dep}"

                self.dependency_graph.add_dependency(service_key, dep_key)

    def _resolve_execution_order(self) -> None:
        """Resolve execution order using dependency graph."""
        try:
            ordered_services = self.dependency_graph.resolve_dependencies()

            # Convert back to service items
            service_map = {f"{item.cluster_name}:{item.service_name}": item for item in self.service_items}

            for service_key in ordered_services:
                if service_key in service_map:
                    self.execution_order.append(service_map[service_key])
                else:
                    logger.warning(f"Service not found in map: {service_key}")

        except ValueError as e:
            logger.error(f"Failed to resolve dependencies: {e}")
            # Fall back to original order
            self.execution_order = self.service_items.copy()

    def _optimize_execution_order(self) -> None:
        """Optimize execution order for maximum parallelism."""
        # Group services by priority and dependencies
        priority_groups = defaultdict(list)

        for item in self.execution_order:
            priority_groups[item.priority].append(item)

        # Sort by priority (lower number = higher priority)
        optimized_order = []
        for priority in sorted(priority_groups.keys()):
            # Within each priority group, maintain dependency order
            optimized_order.extend(priority_groups[priority])

        self.execution_order = optimized_order
        logger.debug(f"Optimized execution order with {len(self.execution_order)} items")

    def _create_execution_timeline(self) -> None:
        """Create execution timeline for visualization."""
        current_time = datetime.now()

        for i, item in enumerate(self.execution_order):
            # Estimate start time (simplified - assumes sequential execution)
            estimated_start = current_time
            if i > 0:
                # Add some overlap for parallel execution
                estimated_start = current_time

            estimated_duration = item.estimated_duration or 60.0  # Default 1 minute
            # Add duration using timedelta
            estimated_end = estimated_start + timedelta(seconds=int(estimated_duration))

            timeline_item = ExecutionTimeline(
                service_name=item.service_name,
                cluster_name=item.cluster_name,
                cluster_type=item.cluster_type,
                estimated_start=estimated_start,
                estimated_duration=estimated_duration,
                estimated_end=estimated_end,
                dependencies=item.dependencies,
                priority=item.priority,
            )

            self.timeline.append(timeline_item)
            current_time = estimated_end

    def calculate_dependencies(self) -> Dict[str, List[str]]:
        """Calculate service dependencies.

        Returns:
            Dictionary mapping service names to their dependencies
        """
        dependencies = {}
        for item in self.service_items:
            service_key = f"{item.cluster_name}:{item.service_name}"
            dependencies[service_key] = item.dependencies.copy()
        return dependencies

    def estimate_total_duration(self) -> float:
        """Estimate total execution duration.

        Returns:
            Estimated total duration in seconds
        """
        if not self.execution_order:
            return 0.0

        # Calculate based on parallel execution with max workers
        max_workers = self.config.general.max_workers
        total_sequential_time = sum(item.estimated_duration or 60.0 for item in self.execution_order)

        # Rough estimate: parallel execution reduces time by factor of max_workers
        estimated_parallel_time = total_sequential_time / max_workers

        return max(estimated_parallel_time, 60.0)  # Minimum 1 minute

    def get_execution_timeline(self) -> List[Dict[str, Any]]:
        """Get detailed execution timeline.

        Returns:
            List of timeline entries with execution details
        """
        timeline_data = []
        for item in self.timeline:
            timeline_data.append(
                {
                    "service_name": item.service_name,
                    "cluster_name": item.cluster_name,
                    "cluster_type": item.cluster_type,
                    "estimated_start": item.estimated_start.isoformat(),
                    "estimated_duration": item.estimated_duration,
                    "estimated_end": item.estimated_end.isoformat(),
                    "dependencies": item.dependencies,
                    "priority": item.priority,
                }
            )
        return timeline_data

    def get_parallel_groups(self) -> List[List[ServiceItem]]:
        """Get services grouped by parallel execution capability.

        Returns:
            List of service groups that can run in parallel
        """
        groups = []
        current_group = []
        completed_services = set()

        for item in self.execution_order:
            # Check if all dependencies are completed
            service_key = f"{item.cluster_name}:{item.service_name}"
            dependencies = self.dependency_graph.get_dependencies(service_key)

            if all(dep in completed_services for dep in dependencies):
                current_group.append(item)
            else:
                # Start new group
                if current_group:
                    groups.append(current_group)
                current_group = [item]

            # Add to completed services
            completed_services.add(service_key)

        # Add final group
        if current_group:
            groups.append(current_group)

        return groups

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution plan summary.

        Returns:
            Dictionary with execution plan summary
        """
        parallel_groups = self.get_parallel_groups()

        return {
            "total_services": len(self.service_items),
            "total_clusters": len(set(item.cluster_name for item in self.service_items)),
            "parallel_groups": len(parallel_groups),
            "estimated_duration": self.estimate_total_duration(),
            "max_workers": self.config.general.max_workers,
            "services_by_priority": {
                priority: len([item for item in self.service_items if item.priority == priority])
                for priority in set(item.priority for item in self.service_items)
            },
            "cluster_types": list(set(item.cluster_type for item in self.service_items)),
        }
