import os
import uvicorn


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7860"))
    reload = os.getenv("RELOAD", "false").lower() in ("true", "1", "yes")

    uvicorn.run("src.infrastructure.server.rest:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
