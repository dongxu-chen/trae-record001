import json
import base64
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from .detector import K8sConfigDetector, Report, Issue, Severity


class AdmissionResult(Enum):
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"


@dataclass
class AdmissionReview:
    uid: str
    kind: str
    name: str
    namespace: str
    operation: str
    object: Dict[str, Any]
    dry_run: bool = False


@dataclass
class AdmissionResponse:
    uid: str
    allowed: bool
    status: Dict[str, Any]
    warnings: Optional[List[str]] = None
    patch_type: Optional[str] = None
    patch: Optional[str] = None


class AdmissionController:
    def __init__(self, rules_config_path: Optional[str] = None, 
                 deny_on_severity=None):
        self.detector = K8sConfigDetector(rules_config_path)
        if deny_on_severity is None:
            self.deny_on_severity = Severity.ERROR
        elif isinstance(deny_on_severity, str):
            self.deny_on_severity = Severity(deny_on_severity)
        else:
            self.deny_on_severity = deny_on_severity

    def handle_admission_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        request = review_data.get('request', {})
        
        review = AdmissionReview(
            uid=request.get('uid', ''),
            kind=request.get('kind', {}).get('kind', ''),
            name=request.get('name', ''),
            namespace=request.get('namespace', 'default'),
            operation=request.get('operation', ''),
            object=request.get('object', {}),
            dry_run=request.get('dryRun', False)
        )

        response = self.validate(review)
        return self._format_response(response)

    def validate(self, review: AdmissionReview) -> AdmissionResponse:
        if not self._is_workload(review.kind):
            return AdmissionResponse(
                uid=review.uid,
                allowed=True,
                status={'code': 200, 'message': 'Resource type not checked'}
            )

        report = self._scan_resource(review.object)
        
        should_deny = self._should_deny(report)
        warnings = self._get_warnings(report)
        
        if should_deny and not review.dry_run:
            return AdmissionResponse(
                uid=review.uid,
                allowed=False,
                status={
                    'code': 403,
                    'message': f'Resource violates {len(report.get_issues_by_severity(self.deny_on_severity))} security policies'
                },
                warnings=warnings
            )
        else:
            return AdmissionResponse(
                uid=review.uid,
                allowed=True,
                status={'code': 200, 'message': 'OK'},
                warnings=warnings
            )

    def _is_workload(self, kind: str) -> bool:
        return kind in ['Deployment', 'StatefulSet', 'DaemonSet', 'Job', 'CronJob', 'Pod']

    def _scan_resource(self, resource: Dict[str, Any]) -> Report:
        report = Report()
        
        pod_workloads = ['Deployment', 'StatefulSet', 'DaemonSet', 'Job', 'CronJob', 'Pod']
        kind = resource.get('kind', 'Unknown')
        
        if kind in pod_workloads:
            self.detector._scan_resource(resource, 'admission', report)
        
        return report

    def _should_deny(self, report: Report) -> bool:
        severity_order = {
            Severity.CRITICAL: 4,
            Severity.ERROR: 3,
            Severity.WARNING: 2,
            Severity.INFO: 1
        }
        
        threshold = severity_order.get(self.deny_on_severity, 3)
        
        for issue in report.issues:
            if severity_order.get(issue.severity, 0) >= threshold:
                return True
        return False

    def _get_warnings(self, report: Report) -> List[str]:
        warnings = []
        for issue in report.issues:
            warnings.append(
                f"[{issue.severity.value.upper()}] {issue.rule_id}: {issue.message}"
            )
        return warnings

    def _format_response(self, response: AdmissionResponse) -> Dict[str, Any]:
        result = {
            'apiVersion': 'admission.k8s.io/v1',
            'kind': 'AdmissionReview',
            'response': {
                'uid': response.uid,
                'allowed': response.allowed,
                'status': response.status
            }
        }

        if response.warnings:
            result['response']['warnings'] = response.warnings

        if response.patch:
            result['response']['patchType'] = response.patch_type
            result['response']['patch'] = response.patch

        return result


class WebhookServer:
    def __init__(self, controller: AdmissionController, 
                 host: str = '0.0.0.0', port: int = 8443,
                 cert_file: Optional[str] = None, key_file: Optional[str] = None):
        self.controller = controller
        self.host = host
        self.port = port
        self.cert_file = cert_file
        self.key_file = key_file

    def run(self):
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import ssl
        except ImportError:
            raise ImportError("Python standard library is required for webhook server")

        controller = self.controller

        class WebhookHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != '/validate':
                    self.send_error(404)
                    return

                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)

                try:
                    review_data = json.loads(post_data.decode('utf-8'))
                    response = controller.handle_admission_review(review_data)

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                except Exception as e:
                    self.send_error(500, str(e))

            def log_message(self, format, *args):
                pass

        server = HTTPServer((self.host, self.port), WebhookHandler)

        if self.cert_file and self.key_file:
            server.socket = ssl.wrap_socket(
                server.socket,
                server_side=True,
                certfile=self.cert_file,
                keyfile=self.key_file,
                ssl_version=ssl.PROTOCOL_TLS
            )

        print(f"Admission webhook server starting on {self.host}:{self.port}")
        print(f"Validation endpoint: /validate")
        print(f"TLS: {'enabled' if self.cert_file else 'disabled'}")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
            server.server_close()


def generate_webhook_manifest(webhook_name: str, service_name: str, 
                               namespace: str, ca_bundle: str,
                               failure_policy: str = 'Fail') -> Dict[str, Any]:
    return {
        'apiVersion': 'admissionregistration.k8s.io/v1',
        'kind': 'ValidatingWebhookConfiguration',
        'metadata': {
            'name': webhook_name
        },
        'webhooks': [
            {
                'name': f'{webhook_name}.example.com',
                'clientConfig': {
                    'service': {
                        'name': service_name,
                        'namespace': namespace,
                        'path': '/validate'
                    },
                    'caBundle': ca_bundle
                },
                'rules': [
                    {
                        'apiGroups': ['apps', ''],
                        'apiVersions': ['v1'],
                        'resources': ['deployments', 'statefulsets', 'daemonsets', 'pods', 'jobs', 'cronjobs'],
                        'operations': ['CREATE', 'UPDATE']
                    }
                ],
                'failurePolicy': failure_policy,
                'sideEffects': 'None',
                'admissionReviewVersions': ['v1']
            }
        ]
    }


def generate_self_signed_cert(hostname: str) -> tuple:
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        import datetime
    except ImportError:
        raise ImportError("cryptography package is required for certificate generation")

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(hostname)]),
        critical=False,
    ).sign(key, hashes.SHA256(), default_backend())

    cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    ca_bundle = base64.b64encode(cert_pem).decode('ascii')

    return cert_pem, key_pem, ca_bundle
