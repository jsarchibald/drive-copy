from sys import argv
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_service():
    """Connects to Google API"""
    creds = None

    if os.path.exists("secure/token.pickle"):
        with open("secure/token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "secure/credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("secure/token.pickle", "wb") as token:
            pickle.dump(creds, token)

    service = build("drive", "v3", credentials=creds)

    return service

def get_children(dir_id, service):
    """Get direct children of this directory."""

    total = []
    page_token = None
    while True:
        #  and mimeType != "application/vnd.google-apps.folder"
        response = service.files().list(q='"{}" in parents'.format(dir_id),
                                            spaces="drive",
                                            fields="nextPageToken, files(id, name, mimeType)",
                                            pageToken=page_token).execute()

        for file in response.get("files", []):
            total.append(file)

        page_token = response.get("nextPageToken", None)
        if page_token is None:
            break

    return total

def create_dir(name, parent, service):
    """Creates a directory given a parent."""
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent]
    }
    file = service.files().create(body=file_metadata,
                                        fields="id").execute()
    return file["id"]

def copy_file(file, parent, service):
    """Copies a file given a new directory parent."""
    new_file = {"name": file["name"], "parents": [parent]}
    service.files().copy(fileId=file["id"], body=new_file).execute()

def copy_dir(dir_id, new_root, service):
    """Recursively copy a full Drive directory.
    
    Args:
        dir_id: the directory to copy.
        new_root: the current destination root directory.
        service: Drive API service object.

    Returns:
        None.
    """

    # List files in the root directory
    children = get_children(dir_id, service)

    # Loop through those files
    for child in children:
        print("Processing", child["name"])
        if child["mimeType"] == "application/vnd.google-apps.folder":
            new_dir = create_dir(child["name"], new_root, service)
            copy_dir(child["id"], new_dir, service)
        else:
            copy_file(child, new_root, service)

def main():
    service = get_service()

    if len(argv) < 3:
        print("Usage: python main.py SOURCE_ID DEST_ID")
        return False
    else:
        dir_id = argv[1]
        new_root = argv[2]

    copy_dir(dir_id, new_root, service)

if __name__ == "__main__":
    main()
