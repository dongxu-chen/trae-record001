from mongo_slow_analyzer.web import create_app

app = create_app()

if __name__ == "__main__":
    from mongo_slow_analyzer.config import load_config
    cfg = load_config()["server"]
    app.run(
        host=cfg.get("host", "0.0.0.0"),
        port=int(cfg.get("port", 5000)),
        debug=bool(cfg.get("debug", True)),
    )
