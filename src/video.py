import cv2
from flask import Blueprint, request, jsonify
import ffmpeg
import subprocess

from app import s3

router = Blueprint('video', __name__, url_prefix='/video')


@router.route('/merge', methods=['GET'])
async def video_merge(file_name):
    audio_url = f'tmp/audio-{file_name}'
    video_url = f'tmp/vidio-{file_name}'
    s3.download_file('furiosa-video', f'upload/{file_name}', audio_url)
    s3.download_file('furiosa-video', f'/{file_name}', video_url)
    audio = ffmpeg.input(audio_url)
    video = ffmpeg.input(video_url)
    await ffmpeg.concat(video, audio, v=1, a=1).output(f'tmp/merge-{file_name}').run()
    s3.upload_fileobj(open(f'tmp/merge-{file_name}', 'rb'), 'furiosa-video', f'merge/{file_name}')


@router.route('/upload', methods=['POST'])
def video_upload():
    if 'video' in request.files:
        video = request.files['video']
        file_name = request.form['file_name']
        s3.upload_fileobj(video, 'furiosa-video', f'upload/{file_name}')
        upload_url = f'https://furiosa-video.s3.ap-northeast-2.amazonaws.com/upload/{file_name}'
        return jsonify({
            'message': 'Video uploaded successfully',
            'upload_url': upload_url
        })
    return jsonify({'message': 'No video uploaded'})


@router.route('/convert/<file_name>', methods=['GET'])
def video_convert(file_name):
    download_url = f'tmp/{file_name}'
    s3.download_file('furiosa-video', f'upload/{file_name}', download_url)
    video = cv2.VideoCapture(f'tmp/{file_name}')
    # 비디오 저장
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    (width, height) = (640, 480)
    fps = cv2.CAP_PROP_FPS
    video_no_audio_url = f'tmp/convert-{file_name}'
    out = cv2.VideoWriter(video_no_audio_url, fourcc, fps, (width, height))
    frames = []
    cnt = 0
    while True:
        ret, frame = video.read()
        if ret:
            cnt += 1
            # 무언가 frame 전처리 여기서.
            frames.append(frame)
        else:
            break

    ## 비디오 저장하고
    for i in range(cnt):
        out.write(frames[i])
    out.release()
    video.release()

    # 비디오에서 오디오 추출
    audio_url = f'tmp/{file_name}-audio.mp3'
    subprocess.run([
        'ffmpeg',
        '-i', f'tmp/{file_name}',
        '-q:a', '0',
        '-map', 'a',
       audio_url
    ], check=True)

    # 오디오를 비디오에 합치기 tttt
    print(video_no_audio_url, audio_url)
    video_url = f'tmp/convert-{file_name}.mp4'
    subprocess.run([
        'ffmpeg',
        '-i', video_no_audio_url,
        '-i', audio_url,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-shortest',
        video_url
    ], check=True)

    # s3에 convert 한 비디오 업로드
    s3.upload_fileobj(open(video_url, 'rb'), 'furiosa-video', f'convert/{file_name}')
    convert_url = f'https://furiosa-video.s3.ap-northeast-2.amazonaws.com/convert/{file_name}'

    return jsonify({
        'message': 'Video converted successfully',
        'convert_url': convert_url
    })
