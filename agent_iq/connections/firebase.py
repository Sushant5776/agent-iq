import base64
import json

from firebase_admin import _apps, credentials, get_app, initialize_app

from agent_iq.config import Settings


class Firebase:
    __app = None

    @staticmethod
    def get_app():
        if not Firebase.__app:
            if not _apps:
                settings = Settings.from_environment()
                if settings.firebase_service_account_base64:
                    try:
                        service_account = json.loads(
                            base64.b64decode(
                                settings.firebase_service_account_base64,
                                validate=True,
                            ).decode("utf-8")
                        )
                    except (
                        ValueError,
                        UnicodeDecodeError,
                        json.JSONDecodeError,
                    ) as error:
                        raise ValueError(
                            "FIREBASE_SERVICE_ACCOUNT_BASE64 must contain valid "
                            "Base64-encoded service-account JSON"
                        ) from error

                    cred = credentials.Certificate(service_account)
                    Firebase.__app = initialize_app(credential=cred)
                else:
                    Firebase.__app = initialize_app()
            else:
                Firebase.__app = get_app()

        return Firebase.__app
