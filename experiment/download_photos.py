# Expects the following to be installed:
# pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib pillow

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import tempfile
import subprocess
from pathlib import Path
import shutil
import requests
from datetime import datetime

google_photos = None

def refresh_creds():
    global google_photos
    # If modifying these scopes, delete the file token.json.
    SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
    
    # The ID of a sample document.
    # DOCUMENT_ID = '195j9eDD3ccgjQRttHhJPymLJUCOUjs-jmwTrekvdjFE'
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    try:
        google_photos = build('photoslibrary', 'v1', credentials=creds, static_discovery=False)
    except HttpError as err:
        print(err)
    return google_photos

def get_items(destdir, google_photos, max_items=1000):
    items = []
    nextpagetoken = None
    # The default number of media items to return at a time is 25. The maximum pageSize is 100.
    # while nextpagetoken != '':
    while len(items) < max_items:
        print(f"Retrieving photo metadata: {len(items)}", end='\r')
        results = google_photos.mediaItems().list(pageSize=100, pageToken=nextpagetoken).execute()

        # If we don't get any result, abort since something is wrong
        unfiltered_results = results.get('mediaItems', None)
        if unfiltered_results is None:
            break

        # add anything new to the list of files to get
        items += [i for i in unfiltered_results if not (destdir / item_to_filename(i)).exists()]
        nextpagetoken = results.get('nextPageToken', '')
    print(f"Retrieved photo metadata: {len(items)}")
    return items

# A translation table to remove :-ZT characters
stripchars = str.maketrans('', '', ':-ZT')

def item_to_filename(item):
    return f"{item['mediaMetadata']['creationTime'].translate(stripchars)}-{item['id'][:20]}.jpg"

def process_item(tmpdir, destdir, item):
    """
    Process one item, downloading it and resizing it as needed.
    """
    filename = item_to_filename(item)
    tmppath = tmpdir / filename
    destpath = destdir / filename

    url = item['baseUrl']+'=d'
    if not destpath.exists():
        response = requests.get(url, stream=True)

        # If it is a FORBIDDEN error, refresh creds and try again
        if response.status_code == 403:
            refresh_creds()
            response = requests.get(url, stream=True)

        if response.status_code != 200:
            # Raise an exception if the HTTP status code indicates an error
            raise Exception(f"Failed to download image {item}. Status code: {response.status_code}")

        with open(tmppath, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        subprocess.check_output(f"mogrify -resize '1920x1080>' '{tmppath}'", shell=True)

        # Change the file modification/access time in python - even if the file does not have exif time metadata
        creation = datetime.fromisoformat(item['mediaMetadata']['creationTime']).timestamp()
        os.utime(tmppath, (creation, creation))

        # exif changing the access time
        # subprocess.check_output(f"exiftool '-FileCreateDate<DateTimeOriginal' '-FileModifyDate<DateTimeOriginal' '{tmppath}'", shell=True)


        # with python 3.11, we can just use the Path entries directly.
        shutil.move(str(tmppath), str(destpath))

    return destpath


if __name__ == "__main__":

    with tempfile.TemporaryDirectory() as tmpdirname:
        print('Downloading to', tmpdirname)
        tmpdir = Path(tmpdirname)

        destdir = Path('./pics')
        max_items = 20
        google_photos = refresh_creds()
        items = get_items(destdir, google_photos, max_items)
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # specify the number of worker threads you want to use
        max_workers = 10
        # create a ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_item, tmpdir, destdir, item) for item in items}
            total = len(futures)
            completed = 0
            for future in as_completed(futures):
                completed += 1
                print(f"Completed {completed}/{total}", end='\r')
                future.result()
