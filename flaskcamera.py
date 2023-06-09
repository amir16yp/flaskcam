#!/usr/bin/python3

from flask import Flask, render_template, Response, request, session, send_file
import cv2
from functools import wraps
from datetime import datetime
import platform
import psutil
import humanize
import distro
import time
import os
import subprocess
from waitress import serve

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--username", type=str, required=True, help="basic auth username")
parser.add_argument("--password", type=str, required=True, help="basic auth password")
parser.add_argument('--host', type=str, required=True)
parser.add_argument('--port', type=int, required=True)
args = parser.parse_args()
      #args.username = os.environ.get('FLASKCAM_USERNAME')
      #args.password = os.environ.get('FLASKCAM_PASSWORD')

app = Flask(__name__)
app.config['BASIC_AUTH_USERNAME'] = args.username #os.environ.get('FLASKCAM_USERNAME')
app.config['BASIC_AUTH_PASSWORD'] = args.password #os.environ.get('FLASKCAM_PASSWORD')
app.config['BASIC_AUTH_FORCE'] = True
app.config['CAMERAS'] = []
app.config['GENERATE_FRAMES'] = True
app.config['RECORD_FRAMES'] = False

def check_auth(username, password):
    return username == app.config['BASIC_AUTH_USERNAME'] and password == app.config['BASIC_AUTH_PASSWORD']

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def require_basic_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/convert/<int:camera_id>')
def convert_to_webm(camera_id):
    directory = f"frames_{camera_id}"
    output_file = f"{directory}.webm"
    
    # Get all files in the directory
    files = os.listdir(directory)

    # Filter for only jpg files and sort them by their frame number
    frames = sorted([file for file in files if file.endswith('.jpg')], key=lambda x: int(x.split('.')[0]))

    # Run ffmpeg to convert frames to webm
    subprocess.run(['ffmpeg', '-y', '-framerate', '30', '-i', f"{directory}/%d.jpg", '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-metadata', f'streamtitle=Camera {camera_id}', output_file], check=True)

    # Return the webm file as a playable file
    return send_file(output_file, mimetype='video/webm')




from datetime import datetime

class VideoCamera(object):
    def __init__(self, camera_id):
        self.video = cv2.VideoCapture(camera_id)
        self.frames_folder = f"frames_{camera_id}"
        os.makedirs(self.frames_folder, exist_ok=True)
        self.frame_count = 0

    def __del__(self):
        self.video.release()

    def get_frame(self):
        success, image = self.video.read()
        if success:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cv2.putText(image, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]
            ret, jpeg = cv2.imencode('.jpg', image, encode_param)
            if app.config['RECORD_FRAMES']:
                filename = os.path.join(self.frames_folder, f"{self.frame_count}.jpg")
                with open(filename, 'wb') as f:
                    f.write(jpeg.tobytes())
                self.frame_count += 1
            return jpeg.tobytes()
        else:
            return None



@app.route('/')
@require_basic_auth
def index():
    # list all available camera devices
    if app.config['CAMERAS'] == []:
        for i in range(10):  # check up to 10 camera devices
            try:
                cap = cv2.VideoCapture(i)

                if cap.isOpened():
                    cap.release()
                    app.config['CAMERAS'].append({'id': i,'name': f'Camera {i}','camera': VideoCamera(i)})
                else:
                    cap.release()
            except:
                pass
    return render_template('index.html', available_cameras=app.config['CAMERAS'])

def gen(camera):
    while app.config['GENERATE_FRAMES']:
        frame = camera.get_frame()
        if frame is None:
            break
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/start_feed', methods=['POST'])
@require_basic_auth
def start_feed():
    app.config['GENERATE_FRAMES'] = True
    return 'Video feed started'

@app.route('/stop_feed', methods=['POST'])
@require_basic_auth
def stop_recrd():
    app.config['GENERATE_FRAMES'] = False
    return 'Video feed stopped'

@app.route('/start_rec', methods=['POST'])
@require_basic_auth
def start_rec():
    app.config['RECORD_FRAMES'] = True
    return 'Video feed started'

@app.route('/stop_rec', methods=['POST'])
@require_basic_auth
def stop_rec():
    app.config['RECORD_FRAMES'] = False
    return 'Video feed stopped'



@app.route('/video_feed')
@require_basic_auth
def video_feed():
    camera_id = request.args.get('camera_id', default=0, type=int)
    for camera in app.config['CAMERAS']:
        if camera['id'] == camera_id:
            the_camera = camera['camera']
            return Response(gen(the_camera), mimetype='multipart/x-mixed-replace; boundary=frame')


@require_basic_auth
@app.route('/distro')
def home():
	# Get system information
	#os_name = os.name
	#os_version = os.version
	#cpu_info = psutil.cpu_info()[0]
	os_name = distro.name()
	os_version = distro.version()
	cpu_info = platform.processor()
	# Get disk usage information
	disk_usage = psutil.disk_usage("/")
	disk_usage_dict = {
	"total": humanize.naturalsize(disk_usage.total),
	"used": humanize.naturalsize(disk_usage.used),
	"percent": disk_usage.percent
}

	# Get memory usage information
	memory_usage = psutil.virtual_memory()
	memory_usage_dict = {
		"total": humanize.naturalsize(memory_usage.total),
		"used": humanize.naturalsize(memory_usage.used),
		"percent": memory_usage.percent
	}

	# Get network IO counters
	network_io_counters = psutil.net_io_counters()
	network_io_counters_dict = {
		"bytes_sent": humanize.naturalsize(network_io_counters.bytes_sent),
		"bytes_recv": humanize.naturalsize(network_io_counters.bytes_recv)
	}

	# Pass the dictionary to the template
	return render_template("distro.html",os_name=os_name,os_version=os_version,cpu_info=cpu_info,disk_usage=disk_usage_dict,memory_usage=memory_usage_dict,network_io_counters=network_io_counters_dict)

if __name__ == '__main__':
    #app.run()
    serve(app, host=args.host, port=args.port)
