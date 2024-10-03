import requests
import logging
import time
import os
from difflib import SequenceMatcher

def get_token(username, password, client_id, client_secret):
    try:
        url = 'https://api.mangadex.org/auth/login'
        payload = {
            'username': username,
            'password': password
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data['token']['session'], data['token']['refresh']
    except requests.RequestException as e:
        logging.error(f"Error obtaining token: {e}")
        return None, None
    
    
def sequence_matcher(a, b):
    return SequenceMatcher(None, a, b).ratio()

def search_manga(name, access_token):
    try:
        # long_strip_tag_id = get_tag_id(LONG_STRIP_TAG_NAME, access_token)
        # if not long_strip_tag_id:
        #     logging.error(f"Tag ID not found. Cannot proceed with search for {name}.")
        #     return None
        
        url = 'https://api.mangadex.org/manga'
        params = {
            'title': name,
            # 'includedTags[]': [long_strip_tag_id]
        }
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        best_match = None
        highest_ratio = 0.0
        results = data.get('data', [])
        if results:
            for result in results:
                attributes = result.get('attributes', {})
                result_title = attributes.get('title', {}).get('en', '')
                match_ratio = sequence_matcher(name, result_title)

                alt_titles = attributes.get('altTitles', [])
                for alt_title in alt_titles:
                    for lang, alt_name in alt_title.items():
                        alt_match_ratio = sequence_matcher(name, alt_name)
                        if alt_match_ratio > match_ratio:
                            match_ratio = alt_match_ratio

                if match_ratio > highest_ratio:
                    highest_ratio = match_ratio
                    best_match = result.get('id')

            logging.info(f"Best match for {name} is with ratio {highest_ratio} and ID {best_match}")
            if best_match:
                return best_match
        else:
            logging.warning(f"No results found for manga {name}")
    except requests.RequestException as e:
        logging.error(f"Error searching for manga {name}: {e}")
    return None

def add_manga_to_follows(manga_id, access_token):

    try:
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        response = requests.post( f'https://api.mangadex.org/manga/{manga_id}/status', headers=headers,json={"status": 'plan_to_read'},)
        response = requests.post( f'https://api.mangadex.org/manga/{manga_id}/follow', headers=headers,)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logging.error(f"Error adding manga ID {manga_id} to follows list: {e} - {e.response.text}")
        return False

def read_manga_names(file_path):
    try:
        with open(file_path, 'r') as file:
            manga_names = file.read().splitlines()
        return manga_names
    except FileNotFoundError as e:
        logging.error(f"File not found: {file_path}")
        return []

def write_not_found_manga_to_file(not_found_manga, file_path='not_found_manga.txt'):
    try:
        print(f"Attempting to write to {file_path}")  # Debug print the file path
        print(f"Current working directory: {os.getcwd()}")  # Check current directory
        print(f"Not found manga list: {not_found_manga}")  # Debug print the list content
        with open(file_path, 'w') as file:
            for manga in not_found_manga:
                file.write(manga + "\n")
        logging.info(f"Written not found mangas to {file_path}")
    except FileNotFoundError as fnf_error:
        logging.error(f"FileNotFoundError: {fnf_error}")
        print(f"FileNotFoundError: {fnf_error}")
    except PermissionError as p_error:
        logging.error(f"PermissionError: {p_error}")
        print(f"PermissionError: {p_error}")
    except Exception as e:  # Catch all exceptions
        logging.error(f"General Exception: {e}")
        print(f"Exception occurred: {e}")

def main(file_path, username, password, client_id, client_secret):
    manga_names = read_manga_names(file_path)
    if not manga_names:
        logging.error("No manga names to process. Exiting.")
        return

    access_token, refresh_token = get_token(username, password, client_id, client_secret)
    if not access_token:
        logging.error("Failed to obtain authentication token. Exiting.")
        return

    not_found_manga = []

    for name in manga_names:
        manga_id = search_manga(name, access_token)
        if manga_id:
            success = add_manga_to_follows(manga_id, access_token)
            if success:
                logging.info(f"Successfully added manga '{name}' with ID {manga_id} to follows list.")
            else:
                logging.error(f"Failed to add manga '{name}' with ID {manga_id} to follows list.")
            time.sleep(0.2)  # Adjust by the API limit to prevent rate limiting
        else:
            logging.warning(f"Manga '{name}' not found.")
            not_found_manga.append(name)
            write_not_found_manga_to_file(not_found_manga)
            
logging.basicConfig(level=logging.DEBUG,  # Adjust level as needed
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[#logging.StreamHandler(),  # Log to console
                              logging.FileHandler("debug_log.txt")  # Log to file
                             ])
    


if __name__ == "__main__":
    file_name = 'manga_names.txt'
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    username = ''
    password = ''
    # list_id = ''
    client_id = ''
    client_secret = ''
    main(file_path, username, password, client_id, client_secret)
