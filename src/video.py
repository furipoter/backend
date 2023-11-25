from flask import Blueprint, request, jsonify
import ffmpeg

from app import s3

router = Blueprint('video', __name__, url_prefix='/video')


@router.route('/convert', methods=['GET'])
async def convert(file_name):
    audio_url = f'tmp/audio-{file_name}'
    video_url = f'tmp/vidio-{file_name}'
    s3.download_file('furiosa-video', f'upload/{file_name}', audio_url)
    s3.download_file('furiosa-video', f'/{file_name}', video_url)
    audio = ffmpeg.input(audio_url)
    video = ffmpeg.input(video_url)
    await ffmpeg.concat(video, audio, v=1, a=1).output(f'tmp/merge-{file_name}').run()
    s3.upload_fileobj(open(f'tmp/merge-{file_name}', 'rb'), 'furiosa-video', f'merge/{file_name}')


@router.route('/upload', methods=['POST'])
def upload_file():
    if 'video' in request.files:
        video = request.files['video']
        file_name = request.form['file_name']
        s3.upload_fileobj(video, 'furiosa-video', f'upload/{file_name}')
        return jsonify({'message': 'Video uploaded successfully'})
    return jsonify({'message': 'No video uploaded'})
