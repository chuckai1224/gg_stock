import requests
from bs4 import BeautifulSoup
import urllib.parse

def download_file_from_google_drive(file_id, destination):
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    
    # 設置偽裝 user agent，避免被拒絕
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'
    })

    print("Sending initial request...")
    response = session.get(URL, params={'id': file_id}, stream=True)
    
    # 檢查是否為 HTML 警告網頁
    content_type = response.headers.get('Content-Type', '')
    if 'text/html' in content_type:
        print("Received HTML warning page. Parsing form to get confirmation...")
        # 讀取全部網頁內容
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 尋找 download-form 表單
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
            
            print(f"Submitting form to: {action} with params: {params}")
            # 發送確認下載請求
            response = session.get(action, params=params, stream=True)
        else:
            print("Could not find download-form in HTML. Attempting direct download anyway...")
    else:
        print("Direct file download initiated...")

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
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)

if __name__ == '__main__':
    file_id = "1aKMvIJ8Au2RZoS7nTphRZJyCkZX9aFY2"
    destination = "gg_stock_data_20260523.tar.gz"
    download_file_from_google_drive(file_id, destination)
