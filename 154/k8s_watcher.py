import logging
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException


class K8sWatcher:
    def __init__(self, namespaces=None, kubeconfig_path=None):
        self.namespaces = namespaces or ['default']
        self.logger = logging.getLogger(__name__)
        
        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                config.load_kube_config()
            self.logger.info("Successfully loaded kubeconfig")
        except Exception as e:
            self.logger.warning(f"Failed to load kubeconfig: {e}, trying in-cluster config")
            try:
                config.load_incluster_config()
                self.logger.info("Successfully loaded in-cluster config")
            except Exception as e2:
                self.logger.error(f"Failed to load in-cluster config: {e2}")
                raise
        
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    def watch_events(self, event_callback):
        w = watch.Watch()
        try:
            for namespace in self.namespaces:
                self.logger.info(f"Starting to watch events in namespace: {namespace}")
                for event in w.stream(self.core_v1.list_namespaced_event, namespace=namespace):
                    event_callback(event)
        except ApiException as e:
            self.logger.error(f"Kubernetes API error: {e}")
        except Exception as e:
            self.logger.error(f"Error watching events: {e}")

    def watch_pods(self, event_callback):
        w = watch.Watch()
        try:
            for namespace in self.namespaces:
                self.logger.info(f"Starting to watch pods in namespace: {namespace}")
                for event in w.stream(self.core_v1.list_namespaced_pod, namespace=namespace):
                    event_callback(event)
        except ApiException as e:
            self.logger.error(f"Kubernetes API error: {e}")
        except Exception as e:
            self.logger.error(f"Error watching pods: {e}")

    def restart_pod(self, namespace, pod_name):
        try:
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            restart_policy = pod.spec.restart_policy
            if restart_policy != 'OnFailure':
                self.logger.warning(f"Pod {pod_name} has restartPolicy {restart_policy}, not restarting")
                return False, f"Pod restartPolicy is {restart_policy}, only OnFailure is allowed to restart"
            
            owner_references = pod.metadata.owner_references
            
            if owner_references:
                for owner in owner_references:
                    if owner.kind == 'ReplicaSet':
                        rs_name = owner.name
                        rs = self.apps_v1.read_namespaced_replica_set(name=rs_name, namespace=namespace)
                        if rs.metadata.owner_references:
                            for rs_owner in rs.metadata.owner_references:
                                if rs_owner.kind == 'Deployment':
                                    deploy_name = rs_owner.name
                                    return self._restart_deployment(namespace, deploy_name)
            
            self.core_v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
            self.logger.info(f"Deleted pod {pod_name} in namespace {namespace}")
            return True, f"Pod {pod_name} deleted successfully"
        except ApiException as e:
            self.logger.error(f"Error restarting pod: {e}")
            return False, str(e)

    def _restart_deployment(self, namespace, deploy_name):
        try:
            deploy = self.apps_v1.read_namespaced_deployment(name=deploy_name, namespace=namespace)
            if not deploy.spec.template.metadata.annotations:
                deploy.spec.template.metadata.annotations = {}
            deploy.spec.template.metadata.annotations['kubectl.kubernetes.io/restartedAt'] = str(deploy.metadata.creation_timestamp)
            
            self.apps_v1.patch_namespaced_deployment(
                name=deploy_name,
                namespace=namespace,
                body=deploy
            )
            self.logger.info(f"Restarted deployment {deploy_name} in namespace {namespace}")
            return True, f"Deployment {deploy_name} restarted successfully"
        except ApiException as e:
            self.logger.error(f"Error restarting deployment: {e}")
            return False, str(e)

    def get_pod_logs(self, namespace, pod_name, tail_lines=100):
        try:
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=tail_lines
            )
            return True, logs
        except ApiException as e:
            self.logger.error(f"Error getting logs: {e}")
            return False, str(e)

    def get_pod_status(self, namespace, pod_name):
        try:
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            return True, {
                'phase': pod.status.phase,
                'pod_ip': pod.status.pod_ip,
                'host_ip': pod.status.host_ip,
                'conditions': [c.type for c in pod.status.conditions if c.status == 'True']
            }
        except ApiException as e:
            self.logger.error(f"Error getting pod status: {e}")
            return False, str(e)

    def list_pods(self, namespace):
        try:
            pods = self.core_v1.list_namespaced_pod(namespace=namespace)
            pod_names = [pod.metadata.name for pod in pods.items]
            return True, pod_names
        except ApiException as e:
            self.logger.error(f"Error listing pods: {e}")
            return False, str(e)
