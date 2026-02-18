import asyncio
import http
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import ParamSpec, TypeVar

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from loguru import logger

from instancer.backends.abc import BackendABC, StartWorkerOptions, StartWorkerResult
from instancer.core.config import settings


class Labels(StrEnum):
    MANAGED_BY = 'app.kubernetes.io/managed-by'
    JOB_ID = 'evmbench.osec.io/job-id'


def ts() -> int:
    return int(datetime.now(tz=UTC).timestamp())


P = ParamSpec('P')
R = TypeVar('R')


class K8sBackend(BackendABC):
    def __init__(self, args: dict[str, str]) -> None:
        super().__init__(args)

        auth_method = args.get('auth_method', 'kubeconfig')
        if auth_method == 'kubeconfig':
            config.load_kube_config()
        elif auth_method == 'incluster':
            config.load_incluster_config()
        else:
            msg = f'Unknown auth_method: {auth_method}'
            raise ValueError(msg)

        self.image_pull_policy = args.get('image_pull_policy', 'Always')
        self.managed_by_value = args.get('managed_by', 'evmbench')

        # this is primarily only needed for local development,
        #   so that kind can connect to internal IP outside the cluster
        _ip_except = args.get(
            'ip_except',
            '10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,100.64.0.0/10,169.254.0.0/16',
        )
        self.ip_except = _ip_except.split(',') if _ip_except != '' else None

    @staticmethod
    async def _k8s(fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def start_worker(self, options: StartWorkerOptions) -> StartWorkerResult:
        v1 = client.CoreV1Api()
        batch_v1 = client.BatchV1Api()
        networking_v1 = client.NetworkingV1Api()

        namespace_name = f'evmbench-job-{options.job_id}'
        while True:
            try:
                ns = await self._k8s(v1.read_namespace, namespace_name)
            except ApiException as e:
                if e.status == http.HTTPStatus.NOT_FOUND:
                    break
                raise

            logger.info(f'Namespace {namespace_name} already exists, deleting it before continuing...')
            if ns.metadata.deletion_timestamp is None:
                await self._k8s(v1.delete_namespace, namespace_name)

            await asyncio.sleep(3)

        namespace = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace_name,
                labels={
                    Labels.MANAGED_BY: self.managed_by_value,
                    Labels.JOB_ID: options.job_id,
                },
            ),
        )
        await self._k8s(v1.create_namespace, namespace)

        network_policies = [
            client.V1NetworkPolicy(
                metadata=client.V1ObjectMeta(name='block-internal-egress'),
                spec=client.V1NetworkPolicySpec(
                    pod_selector=client.V1LabelSelector(match_labels={}),  # all pods
                    policy_types=['Egress'],
                    egress=[
                        # allow egress only to the internet
                        client.V1NetworkPolicyEgressRule(
                            to=[
                                client.V1NetworkPolicyPeer(
                                    ip_block=client.V1IPBlock(
                                        cidr='0.0.0.0/0',
                                        _except=self.ip_except,
                                    ),
                                ),
                            ]
                        ),
                        # allow DNS requests to kube-dns
                        client.V1NetworkPolicyEgressRule(
                            to=[
                                client.V1NetworkPolicyPeer(
                                    pod_selector=client.V1LabelSelector(
                                        match_labels={
                                            'k8s-app': 'kube-dns',
                                        },
                                    ),
                                    namespace_selector=client.V1LabelSelector(
                                        match_labels={'kubernetes.io/metadata.name': 'kube-system'},
                                    ),
                                ),
                            ],
                            ports=[
                                client.V1NetworkPolicyPort(port=53, protocol='UDP'),
                            ],
                        ),
                        # allow egress to evmbench:secretsvc (for prod)
                        client.V1NetworkPolicyEgressRule(
                            to=[
                                client.V1NetworkPolicyPeer(
                                    pod_selector=client.V1LabelSelector(
                                        match_labels={
                                            'app': 'secretsvc',
                                        },
                                    ),
                                    namespace_selector=client.V1LabelSelector(
                                        match_labels={
                                            'kubernetes.io/metadata.name': 'evmbench',
                                        },
                                    ),
                                ),
                            ],
                            ports=[
                                client.V1NetworkPolicyPort(port=8081, protocol='TCP'),  # secretsvc
                            ],
                        ),
                        # allow egress to evmbench:resultsvc (for prod)
                        client.V1NetworkPolicyEgressRule(
                            to=[
                                client.V1NetworkPolicyPeer(
                                    pod_selector=client.V1LabelSelector(
                                        match_labels={
                                            'app': 'resultsvc',
                                        },
                                    ),
                                    namespace_selector=client.V1LabelSelector(
                                        match_labels={
                                            'kubernetes.io/metadata.name': 'evmbench',
                                        },
                                    ),
                                ),
                            ],
                            ports=[
                                client.V1NetworkPolicyPort(port=8083, protocol='TCP'),  # resultsvc
                            ],
                        ),
                        # allow egress to evmbench:oai_proxy
                        client.V1NetworkPolicyEgressRule(
                            to=[
                                client.V1NetworkPolicyPeer(
                                    pod_selector=client.V1LabelSelector(
                                        match_labels={
                                            'app': 'oai_proxy',
                                        },
                                    ),
                                    namespace_selector=client.V1LabelSelector(
                                        match_labels={
                                            'kubernetes.io/metadata.name': 'evmbench',
                                        },
                                    ),
                                ),
                            ],
                            ports=[
                                client.V1NetworkPolicyPort(port=8084, protocol='TCP'),  # oai_proxy
                            ],
                        ),
                    ],
                ),
            ),
        ]

        for network_policy in network_policies:
            await self._k8s(networking_v1.create_namespaced_network_policy, namespace_name, network_policy)

        env: dict[str, str] = {
            'SECRETSVC_HOST': settings.INSTANCER_SECRETSVC_HOST,
            'SECRETSVC_PORT': str(settings.INSTANCER_SECRETSVC_PORT),
            'SECRETSVC_REF': options.secret_ref,
            # technically, we should pass the secretsvc token as a secret ref instead - does this matter?
            'SECRETSVC_TOKEN': settings.INSTANCER_SECRETS_TOKEN_RO.get_secret_value(),
            'RESULTSVC_HOST': settings.INSTANCER_RESULTSVC_HOST,
            'RESULTSVC_PORT': str(settings.INSTANCER_RESULTSVC_PORT),
            'RESULTSVC_JOB_TOKEN': options.result_token,
            'JOB_ID': options.job_id,
            'AGENT_ID': options.model,
        }
        if settings.INSTANCER_OAI_PROXY_BASE_URL:
            env['OAI_PROXY_BASE_URL'] = settings.INSTANCER_OAI_PROXY_BASE_URL

        job = client.V1Job(
            metadata=client.V1ObjectMeta(
                name=f'evmbench-worker-{options.job_id}',
                labels={
                    Labels.MANAGED_BY: self.managed_by_value,
                    Labels.JOB_ID: options.job_id,
                },
            ),
            spec=client.V1JobSpec(
                backoff_limit=0,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={
                            Labels.MANAGED_BY: self.managed_by_value,
                            Labels.JOB_ID: options.job_id,
                        },
                    ),
                    spec=client.V1PodSpec(
                        automount_service_account_token=False,
                        security_context=client.V1SecurityContext(
                            # TODO(trixter-osec): consider in the future hardening and running as non-root?
                            # run_as_user=65534,
                            # run_as_group=65534,
                            # run_as_non_root=True,
                            # fs_group=65534, # not supported by the python client apparently...?
                        ),
                        restart_policy='Never',
                        containers=[
                            client.V1Container(
                                name='evmbench-worker',
                                image=settings.INSTANCER_WORKER_IMAGE,
                                image_pull_policy=self.image_pull_policy,
                                env=[client.V1EnvVar(name=k, value=v) for k, v in env.items()],
                                resources=client.V1ResourceRequirements(
                                    requests={
                                        'memory': '512Mi',
                                        'cpu': '0.25',
                                    },
                                    limits={
                                        'memory': '1Gi',
                                        'cpu': '1',
                                    },
                                ),
                            )
                        ],
                    ),
                ),
            ),
        )
        await self._k8s(batch_v1.create_namespaced_job, namespace_name, job)

        return StartWorkerResult(worker_id=namespace_name)

    async def running_workers(self) -> int:
        batch_v1 = client.BatchV1Api()
        jobs = await self._k8s(
            batch_v1.list_job_for_all_namespaces,
            label_selector=f'{Labels.MANAGED_BY}={self.managed_by_value}',
        )
        return sum((job.status.active or 0) for job in jobs.items)
