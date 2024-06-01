import os
import json
import requests
import cv2
import time
from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for, flash
from pytube import YouTube
from moviepy.editor import VideoFileClip
from fpdf import FPDF
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flash messages
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

YOUTUBE_API_KEY = "AIzaSyD1J_mq4Vq7lSkSw3m69PK7cBSgQWYCftE"  # Replace with your API key

def get_video_info(video_id):
    url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={YOUTUBE_API_KEY}&part=snippet"
    response = requests.get(url)
    data = json.loads(response.content)
    return data["items"][0]["snippet"]

@app.route("/", methods=["GET", "POST"])
def index():
    video_info = None
    if request.method == "POST":
        video_url = request.form["video_url"]
        yt = YouTube(video_url)
        video_info = get_video_info(yt.video_id)
        video_streams = yt.streams.filter(progressive=True).all()
        streams_info = [{"itag": stream.itag, "resolution": stream.resolution, "mime_type": stream.mime_type} for stream in video_streams]
        return render_template("index.html", video_info=video_info, streams_info=streams_info)
    return render_template("index.html", video_info=None, streams_info=None)

@app.route("/download_video", methods=["POST"])
def download_video():
    video_url = request.form["video_url"]
    itag = request.form["itag"]
    yt = YouTube(video_url)
    video_stream = yt.streams.get_by_itag(itag)
    video_path = video_stream.download(output_path=UPLOAD_FOLDER)
    return send_file(video_path, as_attachment=True)

@app.route("/download_audio", methods=["POST"])
def download_audio():
    video_url = request.form["video_url"]
    yt = YouTube(video_url)
    video_stream = yt.streams.get_highest_resolution()
    video_path = video_stream.download(output_path=UPLOAD_FOLDER)

    # Convert video to MP3
    video_clip = VideoFileClip(video_path)
    mp3_path = os.path.splitext(video_path)[0] + ".mp3"
    video_clip.audio.write_audiofile(mp3_path)

    return send_file(mp3_path, as_attachment=True)

@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    video_url = request.form["video_url"]
    frame_interval_str = request.form["frame_interval"]
    try:
        frame_interval = float(frame_interval_str)
    except ValueError:
        flash('Invalid frame interval. Please enter a valid number.', 'error')
        return redirect(url_for('index'))

    yt = YouTube(video_url)
    video_stream = yt.streams.get_highest_resolution()
    video_path = video_stream.download(output_path=UPLOAD_FOLDER)
    pdf_path = process_video(video_path, frame_interval)
    return send_file(pdf_path, as_attachment=True)

def process_video(video_path, frame_interval):
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    last_capture_time = time.time()
    screenshot_paths = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()
        if current_time - last_capture_time >= frame_interval:
            screenshot_path = os.path.join(UPLOAD_FOLDER, f'frame_{frame_count:04d}.png')
            cv2.imwrite(screenshot_path, frame)
            screenshot_paths.append(screenshot_path)

            frame_count += 1
            last_capture_time = current_time

    cap.release()

    pdf = FPDF()
    for screenshot_path in screenshot_paths:
        pdf.add_page()
        pdf.image(screenshot_path, x=10, y=10, w=190)
        os.remove(screenshot_path)

    pdf_output_path = os.path.join(UPLOAD_FOLDER, "screenshots.pdf")
    pdf.output(pdf_output_path)
    return pdf_output_path

@app.route("/get_video_info", methods=["POST"])
def get_video_info_route():
    video_url = request.form["video_url"]
    yt = YouTube(video_url)
    video_info = get_video_info(yt.video_id)
    video_streams = yt.streams.filter(progressive=True).all()
    streams_info = [{"itag": stream.itag, "resolution": stream.resolution, "mime_type": stream.mime_type} for stream in video_streams]
    return jsonify({"video_info": video_info, "streams_info": streams_info})

if __name__ == "__main__":
    app.run(debug=True)