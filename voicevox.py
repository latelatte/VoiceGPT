import requests
import json
import io
import wave
import pyaudio

class Voicevox:
    def __init__(self, host="127.0.0.1", port=50021):
        self.host = host
        self.port = port

    def speak(self, text, speaker=14, speed_scale=1.0, pitch_scale=0.0, intonation_scale=1.0, volume_scale=1.0):
        query_params = {
            "text": text,
            "speaker": speaker
        }

        # 音声クエリを生成
        response = requests.post(
            f"http://{self.host}:{self.port}/audio_query",
            params=query_params
        )
        #print("Audio Query Response:", response.text)
        if response.status_code != 200:
            print("Failed to generate audio query:", response.text)
            return
        
        audio_query = response.json()

        # スケールパラメータのみ更新
        audio_query.update({
            'speedScale': speed_scale,
            'pitchScale': pitch_scale,
            'intonationScale': intonation_scale,
            'volumeScale': volume_scale,
        })

        # 音声を合成
        synthesis_params = {
            "speaker": speaker # スピーカーIDをクエリパラメータとして設定
        }
        synthesis_response = requests.post(
            f"http://{self.host}:{self.port}/synthesis",
            headers={"Content-Type": "application/json"},
            params=synthesis_params,  # クエリパラメータの追加
            data=json.dumps(audio_query)
        )
        #print("Synthesis Response:", synthesis_response.text)
        if synthesis_response.status_code != 200:
            print("Synthesis failed:", synthesis_response.text)
            return

        # メモリ上で展開
        audio = io.BytesIO(synthesis_response.content)
        with wave.open(audio, 'rb') as f:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=p.get_format_from_width(f.getsampwidth()),
                channels=f.getnchannels(),
                rate=f.getframerate(),
                output=True
            )
            data = f.readframes(1024)
            while data:
                stream.write(data)
                data = f.readframes(1024)

            stream.stop_stream()
            stream.close()
            p.terminate()

def main():
    vv = Voicevox()
    vv.speak(
        text="こんにちは。いい感じに設定してみました。ピッチとか抑揚を設定したので、確認してください。どうですか？いい感じですか？",
        speaker=14,
        speed_scale=1.2,
        pitch_scale=0.02,
        intonation_scale=1.2,
        volume_scale=1.0
    )

if __name__ == "__main__":
    main()
