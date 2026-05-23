import requests, time

img = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
payload = {"image": f"data:image/jpeg;base64,{img}"}

t0 = time.time()
n = 50
for i in range(n):
    resp = requests.post('http://127.0.0.1:5000/process_frame', json=payload)

duration = time.time() - t0
fps = n / duration

print(f"Backend API processed {n} frames in {duration:.2f} seconds.")
print(f"Backend API FPS: {fps:.2f}")
