import firebase_admin
from firebase_admin import credentials

def get_firebase_app():
    if not firebase_admin._apps:
        cred = credentials.Certificate("./agent_iq_firebase_admin_private_key.json")
        return firebase_admin.initialize_app(credential=cred)
    else:
        return firebase_admin.get_app()

firebase_app = get_firebase_app()