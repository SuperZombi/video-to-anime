import os
import subprocess
import shutil
import base64
import requests
import hashlib
import json
from PIL import Image
from multiprocessing import Pool

def image_to_base64(filename):
	with open(filename, 'rb') as f:
		return base64.b64encode(f.read()).decode('utf-8')

class NoFaceException(Exception): pass

def get_anime_image(base64_image):
	post_url = "https://ai.tu.qq.com/overseas/trpc.shadow_cv.ai_processor_cgi.AIProcessorCgi/Process"
	post_data = {
		"images": [base64_image],
		"busiId": "different_dimension_me_img_entry",
		"extra": "{\"face_rects\":[],\"version\":2,\"platform\":\"web\",\"data_report\":{\"parent_trace_id\":\"4c689320-71ba-1909-ab57-13c0804d4cc6\",\"root_channel\":\"\",\"level\":0}}"
	}
	post_str = json.dumps(post_data)
	url = f'https://h5.tu.qq.com{str(len(post_str))}HQ31X02e'.encode()
	sign_value = hashlib.md5(url).hexdigest()
	headers = {
		'Host': 'ai.tu.qq.com',
		"x-sign-value": sign_value, 
		"x-sign-version": "v1",
		'Origin': 'https://h5.tu.qq.com'
	}
	res = requests.post(post_url, headers=headers, json=post_data)
	json_data = res.json()
	if json_data['code'] == 0:
		return json.loads(json_data['extra'])["img_urls"][0]
	if json_data['code'] == 1001:
		raise NoFaceException("No Face Exception")
	else:
		raise Exception(json_data['msg'])

def crop_anime(url):
	img = Image.open(requests.get(url, stream=True).raw)
	width, height = img.size
	if width > height:
		crop_img = img.crop((508, 24, 978, 728))
	else:
		crop_img = img.crop((20, 542, 778, 1046))
	return crop_img

def make_anime(filename, output_folder, only_errors=False):
	encoded = image_to_base64(filename)
	if not only_errors:
		print(f"Make anime from: {filename}")
	try:
		image_url = get_anime_image(encoded)
	except:
		# Retry one more time
		try:
			image_url = get_anime_image(encoded)
		except Exception as e:
			print(f"Skiped: {filename}: {e}")
			return
	result = crop_anime(image_url)
	result.save(os.path.join(output_folder, os.path.basename(filename)))

def video_to_frames(video, folder):
	p = subprocess.Popen(["ffmpeg", "-hide_banner", "-i", video, "%06d.png"], cwd=folder)
	p.wait()
	return [os.path.join(folder, f) for f in os.listdir(folder)]

def get_video_fps(video):
	out = subprocess.check_output(["ffprobe",video,"-v","0","-select_streams","v","-print_format","flat","-show_entries","stream=r_frame_rate"])
	rate = out.decode().split('=')[1].strip()[1:-1].split('/')
	if len(rate)==1:
		return int(rate[0])
	if len(rate)==2:
		return int(float(rate[0])/float(rate[1]))
	return -1

def verify_files(folder):
	all_files = [f for f in os.listdir(folder)]
	for index, old_filename in enumerate(all_files):
		new_filename = str(index+1).zfill(6) + ".png"
		if old_filename != new_filename:
			os.rename(os.path.join(folder, old_filename),
					  os.path.join(folder, new_filename))

def extract_audio(video):
	audio_file = os.path.splitext(video)[0] + ".mp3"
	if os.path.exists(audio_file): os.remove(audio_file)
	p = subprocess.Popen(["ffmpeg", "-i", video, audio_file], stderr=subprocess.PIPE)
	p.wait()
	return audio_file



def main(video, threads=30, only_errors=False):
	filename = os.path.basename(video)
	temp_folder = os.path.join(
		"temp", os.path.splitext(filename)[0]
	)
	output_folder = os.path.join(
		"output", os.path.splitext(filename)[0]
	)
	if not os.path.exists("temp"): os.mkdir("temp")
	if not os.path.exists("output"): os.mkdir("output")
	if os.path.exists(temp_folder):
		shutil.rmtree(temp_folder)
	if os.path.exists(output_folder):
		shutil.rmtree(output_folder)
	os.mkdir(temp_folder)
	os.mkdir(output_folder)

	arr = video_to_frames(video, temp_folder)
	def add_arg(arg, amount):
		return [arg for a in range(amount)]
	work_arr = list(zip(arr,
						add_arg(output_folder, len(arr)),
						add_arg(only_errors, len(arr))
					))
	if not only_errors:
		print("Making anime...")
	with Pool(threads) as pool:
		pool.starmap(make_anime, work_arr)

	shutil.rmtree(temp_folder)
	verify_files(output_folder)

	audio = extract_audio(video)

	t = os.path.splitext(video)
	output_file = t[0] + "_output" + t[1]
	if os.path.exists(output_file): os.remove(output_file)
	p = subprocess.Popen(["ffmpeg", "-hide_banner", "-framerate", str(get_video_fps(video)), "-i", "%06d.png", "-i", audio, output_file], cwd=output_folder)
	p.wait()

	os.remove(audio)
	shutil.rmtree(output_folder)


if __name__ == "__main__":
	vid = os.path.join(os.getcwd(), "video.mp4") # Full path to video
	main(vid)
