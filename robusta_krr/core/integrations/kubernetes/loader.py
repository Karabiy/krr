from typing import List, Optional, Sequence, Tuple, Union

import kubernetes_asyncio as k8s

from robusta_krr.core.models.config import settings
from robusta_krr.core.models.objects import K8sObjectData, ListableK8sObject
from robusta_krr.utils.progress_bar import ProgressBar

class KubernetesLoader:
    async def list_scannable_objects(
        self, clusters: Optional[Sequence[str]] = None
    ) -> list[K8sObjectData]:
        """List all scannable objects.

        :param clusters: List of clusters to list objects from.
        :returns: A list of scannable objects.
        """

        if clusters is None:
            clusters = await self.list_clusters()

        logger.info(f"Listing scannable objects for clusters: {clusters} and namespaces: {self._namespaces}")
        logger.debug(f"Namespaces: {self._namespaces}")

        if clusters is None:
            workloads_and_pods = await self._list_scannable_objects(None)
        else:
            with ProgressBar(total=len(clusters), title="Discovering workloads") as progress:
                workloads_and_pods = []
                for cluster in clusters:
                    cluster_workloads = await self._list_scannable_objects(cluster)
                    workloads_and_pods.extend(cluster_workloads)
                    progress.progress(description=f"Cluster: {cluster}")

        workloads = _build_scannable_objects(workloads_and_pods, self._namespaces)
        logger.info(f"Found {len(workloads)} workloads to scan")

        return workloads 