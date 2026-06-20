import os
import tarfile
import requests
from bs4 import BeautifulSoup
import shutil

def download_file_from_google_drive(file_id, destination):
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'
    })

    print("Sending initial request to Google Drive...")
    response = session.get(URL, params={'id': file_id}, stream=True)
    
    content_type = response.headers.get('Content-Type', '')
    if 'text/html' in content_type:
        html_content = response.text
        if "signin" in response.url or response.status_code == 401:
            raise Exception("Google Drive returned 401 Unauthorized or login redirect. Please make sure the file sharing permission is set to 'Anyone with the link' (知道連結的任何人均可檢視) and is not restricted.")
            
        soup = BeautifulSoup(html_content, 'html.parser')
        form = soup.find('form', id='download-form')
        if form:
            action = form.get('action')
            inputs = form.find_all('input')
            params = {}
            for inp in inputs:
                name = inp.get('name')
                value = inp.get('value')
                if name:
                    params[name] = value
            
            print("Submitting confirmation form...")
            response = session.get(action, params=params, stream=True)
        else:
            print("Could not find download-form in HTML. Attempting direct download anyway...")
    
    if response.status_code != 200:
        raise Exception(f"Download failed: Google Drive returned status code {response.status_code}")
        
    final_content_type = response.headers.get('Content-Type', '')
    if 'text/html' in final_content_type:
        raise Exception("Download failed: Google Drive returned an HTML page. The download quota may be exceeded or the file is unavailable.")

    save_response_content(response, destination)
    print("Download completed successfully!")

def save_response_content(response, destination):
    CHUNK_SIZE = 32768
    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:
                f.write(chunk)

def extract_tar_gz(filepath, dest_dir="."):
    print(f"Decompressing {filepath} to current directory...")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Cannot find archive to extract: {filepath}")
    
    with tarfile.open(filepath, "r:gz") as tar:
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in member.name:
                raise Exception(f"Security Warning: Blocked suspicious path in archive: {member.name}")
        tar.extractall(path=dest_dir)
    print("Decompression completed successfully!")

def main():
    file_id = "1qol7VOBteb3kfs5Yni882ZuHPiELPUp4"
    destination = "gg_stock_data_20260524.tar.gz"
    
    # 1. 檢查目前目錄是否已存在快照檔
    if os.path.exists(destination):
        print(f"偵測到本地已存在快照壓縮檔 {destination}，將直接進行解壓縮還原...")
        extract_tar_gz(destination)
        return

    # 2. 嘗試從 Google Drive 下載
    try:
        download_file_from_google_drive(file_id, destination)
        extract_tar_gz(destination)
    except Exception as e:
        print(f"\n[錯誤] 無法從 Google Drive 下載檔案：\n{str(e)}")
        print("\n[解決方案/Workaround]")
        print("1. 請手動用瀏覽器開啟此連結下載 (可能需要登入您的 Google 帳號)：")
        print(f"   https://drive.google.com/file/d/{file_id}/view")
        print(f"2. 下載後將檔案 {destination} 放至此專案的根目錄中。")
        print("3. 重新點擊「下載快照」，系統偵測到本地檔案後，即會自動進行解壓縮還原！")
        raise e

if __name__ == '__main__':
    main()
