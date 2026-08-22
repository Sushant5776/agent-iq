from firebase_admin import _apps, credentials, get_app, initialize_app

from agent_iq.config import Settings


class Firebase:
    __app = None

    @staticmethod
    def get_app():
        if not Firebase.__app:
            if not _apps:
                settings = Settings.from_environment()
                if settings.firebase_credentials_path:
                    cred = credentials.Certificate(settings.firebase_credentials_path)
                    Firebase.__app = initialize_app(credential=cred)
                else:
                    Firebase.__app = initialize_app()
            else:
                Firebase.__app = get_app()

        return Firebase.__app
