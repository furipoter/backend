import requests

file_path = './tmp/aitest.mp4'
file_name = 'aitest.mp4'
url = 'http://14.35.173.13:38228/api/video/upload'
files = {'video': open(file_path, 'rb')}
r = requests.post(url, files=files, data={'file_name': file_name})
print(r.text)