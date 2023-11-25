import uuid

import cv2
from flask import Blueprint, request, jsonify
import ffmpeg
import subprocess

from app import s3

router = Blueprint('video', __name__, url_prefix='/video')


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
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    (width, height) = (int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    fps = video.get(cv2.CAP_PROP_FPS)
    video_no_audio_url = f'tmp/convert-{file_name}'
    out = cv2.VideoWriter(video_no_audio_url, fourcc, fps, (width, height))
    while True:
        ret, frame = video.read()
        if ret:
            # 무언가 frame 전처리 여기서.
            # 일단 임시로 반전 효과 넣음.
            frame = 255 - frame
            out.write(frame)
        else:
            break
    out.release()
    video.release()

    video_url = f'tmp/{uuid.uuid4()}.mp4'
    subprocess.run([
        'ffmpeg',
        '-i', video_no_audio_url,
        '-i', download_url,
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-map', '0:v',
        '-map', '1:a',
        video_url
    ], check=True)

    # s3에 convert 한 비디오 업로드
    s3.upload_fileobj(open(video_url, 'rb'), 'furiosa-video', f'convert/{file_name}')
    convert_url = f'https://furiosa-video.s3.ap-northeast-2.amazonaws.com/convert/{file_name}'

    return jsonify({
        'message': 'Video converted successfully',
        'convert_url': convert_url
    })
