from firebase_admin import _apps, credentials, get_app, initialize_app


class Firebase:
    __app = None

    @staticmethod
    def get_app():
        if not Firebase.__app:
            if not _apps:
                cred = credentials.Certificate("./agent_iq_firebase_admin_private_key.json")
                Firebase.__app = initialize_app(credential=cred)
            else:
                Firebase.__app = get_app()

        return Firebase.__app
