import firebase_admin
from firebase_admin import credentials

class Firebase:
    __app = None

    @staticmethod
    def get_app():
        if not Firebase.__app:
            if not firebase_admin._apps:
                cred = credentials.Certificate("./agent_iq_firebase_admin_private_key.json")
                Firebase.__app = firebase_admin.initialize_app(credential=cred)
            else:
                Firebase.__app = firebase_admin.get_app()

        return Firebase.__app
