from fastapi import APIRouter, HTTPException, Body
from google.oauth2 import id_token
from google.auth.transport import requests
from dotenv import load_dotenv
import os

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def create_guest_user():
    pass