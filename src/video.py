import subprocess
import uuid

import cv2
from flask import Blueprint, request, jsonify

from app import s3
from src.db.room import Room

from furiosa.runtime.sync import create_runner
from utils.preprocess import *
from utils.postprocess import *
import time


router = Blueprint('video', __name__, url_prefix='/video')


@router.route('/count/convert/<filename>')
def count_convert_file_name(filename):
    try:
        room = Room.query.filter_by(id=filename).first()
        if room is None:
            return jsonify({
                'message': 'Room not found'
            }), 404
        else:
            return jsonify({
                'count': len(room.number)
            })
    except Exception as e:
        return jsonify({
            'message': str(e)
        }), 500


# def update_room_number(filename):
#     try:
#         room_id = ".".join(filename.split('.')[:-1])
#         room_id = '-'.join(room_id.split('-')[:-1])
#         print("room_id", room_id)
#         # s3 에서 upload, convert 에서 개수 센 다음 작은걸로 업데이트
#         upload_count = len(s3.list_objects_v2(Bucket='furiosa-video', Prefix=f'upload/{room_id}')['Contents'])
#         convert_count = len(s3.list_objects_v2(Bucket='furiosa-video', Prefix=f'convert/{room_id}')['Contents'])
#         mini_number = min(upload_count, convert_count)
#
#         room = Room.query.filter_by(id=filename).first()
#         if room is None:
#             if mini_number == 1:
#                 return jsonify({
#                     'message': 'No video uploaded'
#                 }), 404
#             else:
#                 room = Room(id=room_id, number=mini_number)
#                 db.session.add(room)
#                 db.session.commit()
#                 return jsonify({
#                     'message': 'Room number updated successfully'
#                 })
#         else:
#             room.number = mini_number
#             db.session.commit()
#             return jsonify({
#                 'message': 'Room number updated successfully'
#             })
#     except Exception as e:
#         return jsonify({
#             'message': str(e)
#         }), 500


@router.route('/upload', methods=['POST'])
def video_upload():
    try:
        if 'video' in request.files:
            video = request.files['video']
            file_name = request.form['file_name']

            s3.upload_fileobj(video, 'furiosa-video', f'upload/{file_name}')
            upload_url = f'https://furiosa-video.s3.ap-northeast-2.amazonaws.com/upload/{file_name}'
            # update_room_number(file_name)
            # return jsonify({
            #     'message': 'Video uploaded successfully',
            #     'upload_url': upload_url
            # })
        else:
            return jsonify({'message': 'No video uploaded'})
        start_time = time.time()
        download_url = f'tmp/{file_name}'
        s3.download_file('furiosa-video', f'upload/{file_name}', download_url)
        video = cv2.VideoCapture(download_url)
        # 비디오 저장
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        (width, height) = (int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        fps = video.get(cv2.CAP_PROP_FPS)
        video_no_audio_url = f'tmp/convert-{file_name}'

        with create_runner("yolov7_i8_2pe.enf", worker_num=8) as runner:
            out = cv2.VideoWriter(video_no_audio_url, fourcc, fps, (width, height))
            cnt = 0
            while True:
                ret, frame = video.read()
                if ret:

                    image_tensor, preproc_params = preproc(frame)
                    output = runner.run(image_tensor)
                    predictions = postproc(output, 0.45, 0.35)
                    predictions = predictions[0]
                    bboxed_img = draw_bbox(frame, predictions, preproc_params)
                    finish_Time = time.time() - start_time
                    cnt += 1
                    # frame = 255 - frame
                    out.write(bboxed_img)
                else:
                    break
            video.release()
            out.release()
            print(time.time() - start_time)
        # s3에 convert 한 비디오 업로드
        s3.upload_fileobj(open(video_no_audio_url, 'rb'), 'furiosa-video', f'convert/{file_name}')
        convert_url = f'https://furiosa-video.s3.ap-northeast-2.amazonaws.com/convert/{file_name}'

        # update_room_number(file_name)
        return jsonify({
            'message': 'Video converted successfully',
            'convert_url': convert_url
        })
    except Exception as e:
        return jsonify({
            'message': str(e)
        }), 500
