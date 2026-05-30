import os
import sys
import json
import yaml
from typing import Dict, List, Optional
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir


class SeldonDeploymentManager:
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("SeldonDeployment", self.config)
        self.seldon_config = self.config["deployment"]["seldon"]

    def generate_deployment_yaml(self, model_name: str, model_path: str,
                                  namespace: str = None, replicas: int = None) -> Dict:
        if namespace is None:
            namespace = self.seldon_config.get("namespace", "seldon")
        if replicas is None:
            replicas = self.seldon_config.get("replicas", 2)

        resources = self.seldon_config.get("resources", {
            "requests": {"cpu": "1", "memory": "2Gi"},
            "limits": {"cpu": "2", "memory": "4Gi"}
        })

        deployment = {
            "apiVersion": "machinelearning.seldon.io/v1",
            "kind": "SeldonDeployment",
            "metadata": {
                "name": f"ctr-{model_name.replace('_', '-')}",
                "namespace": namespace,
                "labels": {
                    "app": "ctr-prediction",
                    "model": model_name,
                    "version": datetime.now().strftime("%Y%m%d")
                }
            },
            "spec": {
                "name": model_name,
                "predictors": [
                    {
                        "graph": {
                            "name": "model",
                            "implementation": "TENSORFLOW_SERVER",
                            "modelUri": model_path,
                            "env": [
                                {"name": "MODEL_NAME", "value": model_name}
                            ]
                        },
                        "name": "default",
                        "replicas": replicas,
                        "resources": resources
                    }
                ]
            }
        }

        self.logger.info(f"Generated deployment config for model: {model_name}")
        return deployment

    def generate_ab_test_deployment(self, models: List[Dict], namespace: str = None) -> Dict:
        if namespace is None:
            namespace = self.seldon_config.get("namespace", "seldon")

        predictors = []
        for model_info in models:
            model_name = model_info["name"]
            model_path = model_info["path"]
            traffic = model_info.get("traffic", 50)

            predictor = {
                "graph": {
                    "name": "model",
                    "implementation": "TENSORFLOW_SERVER",
                    "modelUri": model_path,
                    "env": [
                        {"name": "MODEL_NAME", "value": model_name}
                    ]
                },
                "name": model_name.replace("_", "-"),
                "replicas": model_info.get("replicas", 1),
                "traffic": traffic
            }
            predictors.append(predictor)

        deployment = {
            "apiVersion": "machinelearning.seldon.io/v1",
            "kind": "SeldonDeployment",
            "metadata": {
                "name": "ctr-ab-test",
                "namespace": namespace,
                "labels": {
                    "app": "ctr-prediction",
                    "test-type": "ab-test"
                }
            },
            "spec": {
                "name": "ctr-ab-test",
                "predictors": predictors
            }
        }

        self.logger.info(f"Generated A/B test deployment with {len(models)} models")
        return deployment

    def generate_canary_deployment(self, primary_model: Dict, canary_model: Dict,
                                     canary_traffic: int = 10,
                                     namespace: str = None) -> Dict:
        if namespace is None:
            namespace = self.seldon_config.get("namespace", "seldon")

        deployment = {
            "apiVersion": "machinelearning.seldon.io/v1",
            "kind": "SeldonDeployment",
            "metadata": {
                "name": "ctr-canary",
                "namespace": namespace,
                "labels": {
                    "app": "ctr-prediction",
                    "test-type": "canary"
                }
            },
            "spec": {
                "name": "ctr-canary",
                "predictors": [
                    {
                        "graph": {
                            "name": "model",
                            "implementation": "TENSORFLOW_SERVER",
                            "modelUri": primary_model["path"],
                        },
                        "name": "primary",
                        "replicas": 2,
                        "traffic": 100 - canary_traffic
                    },
                    {
                        "graph": {
                            "name": "model",
                            "implementation": "TENSORFLOW_SERVER",
                            "modelUri": canary_model["path"],
                        },
                        "name": "canary",
                        "replicas": 1,
                        "traffic": canary_traffic
                    }
                ]
            }
        }

        self.logger.info(f"Generated canary deployment: {canary_model['name']} ({canary_traffic}% traffic)")
        return deployment

    def save_deployment_yaml(self, deployment: Dict, output_path: str):
        ensure_dir(os.path.dirname(output_path))
        with open(output_path, "w") as f:
            yaml.dump(deployment, f, default_flow_style=False, sort_keys=False)
        self.logger.info(f"Deployment YAML saved to {output_path}")

    def generate_model_wrapper(self, model_name: str, output_path: str):
        ensure_dir(output_path)

        wrapper_code = f"""import tensorflow as tf
import numpy as np
import json
from typing import Dict, List, Any


class CTRModel:
    def __init__(self, model_path: str):
        self.model = tf.keras.models.load_model(model_path)
        self.model_name = "{model_name}"

    def predict(self, X: Dict[str, Any], names: List[str] = None, meta: Dict = None) -> np.ndarray:
        feature_dict = {{}}
        for key, value in X.items():
            if isinstance(value, list):
                feature_dict[key] = tf.convert_to_tensor(value, dtype=tf.float32)
            else:
                feature_dict[key] = tf.convert_to_tensor([value], dtype=tf.float32)
        
        predictions = self.model(feature_dict)
        return predictions.numpy()

    def predict_raw(self, request: Dict[str, Any]) -> Dict[str, Any]:
        data = request.get("data", {{}})
        features = data.get("ndarray", {{}})
        
        if isinstance(features, dict):
            predictions = self.predict(features)
        else:
            predictions = np.array([0.5])
        
        return {{
            "data": {{
                "ndarray": predictions.tolist(),
                "names": ["click_probability"]
            }},
            "meta": {{
                "model_name": self.model_name
            }}
        }}
"""

        wrapper_path = os.path.join(output_path, "model_wrapper.py")
        with open(wrapper_path, "w") as f:
            f.write(wrapper_code)

        self.logger.info(f"Model wrapper saved to {wrapper_path}")

    def generate_kubernetes_resources(self, model_name: str, output_dir: str):
        ensure_dir(output_dir)

        resources = {
            "deployment": self.generate_deployment_yaml(
                model_name,
                f"gs://ctr-models/{model_name}/saved_model"
            ),
            "service": {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": f"ctr-{model_name}-service",
                    "labels": {"app": "ctr-prediction"}
                },
                "spec": {
                    "selector": {"app": "ctr-prediction"},
                    "ports": [
                        {"port": 8000, "targetPort": 8000, "name": "http"},
                        {"port": 9000, "targetPort": 9000, "name": "grpc"}
                    ]
                }
            },
            "hpa": {
                "apiVersion": "autoscaling/v2",
                "kind": "HorizontalPodAutoscaler",
                "metadata": {"name": f"ctr-{model_name}-hpa"},
                "spec": {
                    "scaleTargetRef": {
                        "apiVersion": "machinelearning.seldon.io/v1",
                        "kind": "SeldonDeployment",
                        "name": f"ctr-{model_name}"
                    },
                    "minReplicas": 2,
                    "maxReplicas": 10,
                    "metrics": [
                        {
                            "type": "Resource",
                            "resource": {
                                "name": "cpu",
                                "target": {"type": "Utilization", "averageUtilization": 70}
                            }
                        }
                    ]
                }
            }
        }

        for resource_name, resource_config in resources.items():
            output_path = os.path.join(output_dir, f"{resource_name}.yaml")
            self.save_deployment_yaml(resource_config, output_path)

        self.logger.info(f"Kubernetes resources generated in {output_dir}")
        return resources

    def get_deployment_status(self, deployment_name: str, namespace: str = None) -> Dict:
        if namespace is None:
            namespace = self.seldon_config.get("namespace", "seldon")

        status = {
            "deployment_name": deployment_name,
            "namespace": namespace,
            "status": "NotAvailable",
            "message": "Kubernetes connection required for real status",
            "available_replicas": 0,
            "ready_replicas": 0
        }

        return status

    def generate_deployment_report(self, model_name: str, deployment_config: Dict,
                                    output_path: str = "reports/deployment_report.md"):
        ensure_dir(os.path.dirname(output_path))

        report = f"""# Deployment Report: {model_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Deployment Configuration

- **Model Name**: {model_name}
- **Namespace**: {deployment_config.get('metadata', {}).get('namespace', 'default')}
- **Replicas**: {deployment_config.get('spec', {}).get('predictors', [{}])[0].get('replicas', 1)}

## Resources

"""

        resources = deployment_config.get("spec", {}).get("predictors", [{}])[0].get("resources", {})
        if resources:
            report += "| Resource | Request | Limit |\n"
            report += "|----------|---------|-------|\n"
            report += f"| CPU | {resources.get('requests', {}).get('cpu', 'N/A')} | {resources.get('limits', {}).get('cpu', 'N/A')} |\n"
            report += f"| Memory | {resources.get('requests', {}).get('memory', 'N/A')} | {resources.get('limits', {}).get('memory', 'N/A')} |\n"

        report += """
## Deployment Instructions

1. Apply the deployment:
```bash
kubectl apply -f deployment.yaml
```

2. Check status:
```bash
kubectl get seldondeployments
```

3. Monitor logs:
```bash
kubectl logs -l app=ctr-prediction
```

## Scaling Configuration

- Horizontal Pod Autoscaler enabled
- Target CPU utilization: 70%
- Min replicas: 2
- Max replicas: 10
"""

        with open(output_path, "w") as f:
            f.write(report)

        self.logger.info(f"Deployment report saved to {output_path}")


def main():
    print("Seldon Deployment Module")
    print("Use this module to generate Seldon deployment configurations")


if __name__ == "__main__":
    main()
