import logging
import sys
from es_ilm_tool.api import create_app
from es_ilm_tool.metrics import MetricsExporter
from es_ilm_tool.scheduler import ILMScheduler
from es_ilm_tool.ilm_policy import ILMPolicyManager
from es_ilm_tool import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Elasticsearch ILM Tool...")

    ilm_manager = ILMPolicyManager()
    ilm_manager.ensure_default_policy()
    logger.info("Default ILM policy ensured")

    metrics_exporter = MetricsExporter()
    metrics_exporter.start_metrics_server()
    logger.info("Prometheus metrics server started on port %d", config.PROMETHEUS_PORT)

    app = create_app()

    with app.app_context():
        from es_ilm_tool.scheduler import ILMScheduler
        scheduler = ILMScheduler()
        scheduler.start()
        app.config["ILM_SCHEDULER"] = scheduler

    logger.info("Flask API server starting on %s:%d", config.FLASK_HOST, config.FLASK_PORT)
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )


if __name__ == "__main__":
    main()
