import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.service_account import Credentials
import io
import os

SCOPES = ['https://www.googleapis.com/auth/drive']
DB_NAME = 'jogos.db'
DRIVE_FILENAME = 'jogos.db'


def _get_service():
    creds_dict = dict(st.secrets["gdrive_credentials"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)


def _get_folder_id():
    return st.secrets["gdrive"]["FOLDER_ID"]


def _find_file_id(service):
    """Acha o ID do jogos.db na pasta do Drive, ou None se não existir"""
    folder_id = _get_folder_id()
    query = f"name='{DRIVE_FILENAME}' and '{folder_id}' in parents and trashed=false"
    result = service.files().list(q=query, fields="files(id)").execute()
    files = result.get('files', [])
    return files[0]['id'] if files else None


def baixar_db():
    """Baixa jogos.db do Drive para o filesystem local. Retorna True se baixou."""
    try:
        service = _get_service()
        file_id = _find_file_id(service)
        if not file_id:
            return False  # ainda não tem no Drive, usa o local

        request = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        with open(DB_NAME, 'wb') as f:
            f.write(buf.getvalue())
        return True
    except Exception as e:
        st.warning(f"⚠️ Não foi possível baixar backup do Drive: {e}")
        return False


def fazer_upload_db():
    """Faz upload do jogos.db local para o Drive (cria ou substitui)."""
    try:
        service = _get_service()
        file_id = _find_file_id(service)
        media = MediaFileUpload(DB_NAME, mimetype='application/octet-stream')

        if file_id:
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            folder_id = _get_folder_id()
            metadata = {'name': DRIVE_FILENAME, 'parents': [folder_id]}
            service.files().create(body=metadata, media_body=media).execute()
    except Exception as e:
        st.warning(f"⚠️ Não foi possível fazer upload para o Drive: {e}")
