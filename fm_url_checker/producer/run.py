import logging

import connexion

from fm_url_checker.producer import settings

log = logging.getLogger(__name__)


def create_app():
    connexion_app = connexion.App(settings.NAME, specification_dir="fm_url_checker/producer/openapi/")
    connexion_app.add_api(
        "api.yaml",
        # validate_responses=False,
    )

    return connexion_app


app = create_app()

if __name__ == '__main__':
    log.info(f"Server starting on port: {settings.DEV_SERVER_PORT}")
    app.run(port=settings.DEV_SERVER_PORT, debug=settings.DEBUG)
