FROM python:3.11

# वर्किंग डायरेक्टरी सेट करें
WORKDIR /Auto-Filter-Bot

# FFmpeg इंस्टॉल करें (मीडिया/वीडियो बॉट्स के लिए जरूरी)
RUN apt-get update && apt-get install -y ffmpeg

# पहले सिर्फ requirements.txt कॉपी करें (Docker Caching का फायदा उठाने के लिए)
COPY requirements.txt .

# डिपेंडेंसी इंस्टॉल करें
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# बाकी का सारा कोड कॉपी करें
COPY . .

# बॉट को रन करें
CMD ["python", "bot.py"]
