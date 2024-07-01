import os
import re
from openai import OpenAI
import json
import speech_recognition as sr
import requests
import japanize_kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.uix.label import Label
import threading

# 環境変数からAPIキーを取得
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    )
messages = [{"role": "system", "content": "あなたは私の友達です。タメ口でフレンドリーに接して下さい。会話は5文以内におさめて下さい。"}]


class Voicevox:
    def __init__(self, host="127.0.0.1", port=50021):
        self.host = host
        self.port = port

    def speak(self, text, speaker=14, speed_scale=1.2, pitch_scale=0.03, intonation_scale=1.25, volume_scale=1.0):
        query_params = {"text": text, "speaker": speaker}
        response = requests.post(f"http://{self.host}:{self.port}/audio_query", params=query_params)
        if response.status_code != 200:
            print("Failed to generate audio query:", response.text)
            return
        
        audio_query = response.json()
        audio_query.update({
            'speedScale': speed_scale,
            'pitchScale': pitch_scale,
            'intonationScale': intonation_scale,
            'volumeScale': volume_scale,
        })

        synthesis_params = {"speaker": speaker}
        synthesis_response = requests.post(
            f"http://{self.host}:{self.port}/synthesis",
            headers={"Content-Type": "application/json"},
            params=synthesis_params,
            data=json.dumps(audio_query)
        )
        if synthesis_response.status_code != 200:
            print("Synthesis failed:", synthesis_response.text)
            return

        return synthesis_response.content

class voiceGPT(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical')

        self.start_button = Button(text='会話を始める！', font_name='MPLUSRounded1c-Bold', background_normal='', background_color=(0.98, 0.63, 0.71, 1))
        self.start_button.bind(on_press=self.start_recognition)
        
        self.stop_button = Button(text='会話を終える！', font_name='MPLUSRounded1c-Bold', color=(0.98, 0.63, 0.71, 1), background_normal='', background_color=(0.88, 0.97, 0.94, 1))
        self.stop_button.bind(on_press=self.stop_recognition)
        self.stop_button.disabled = True
        
        self.status_label = Label(text="準備完了！", font_name='MPLUSRounded1c-Bold')

        self.text_output = TextInput(readonly=True, multiline=True, font_name='MPLUSRounded1c-Bold')

        self.layout.add_widget(self.start_button)
        self.layout.add_widget(self.stop_button)
        self.layout.add_widget(self.status_label)
        self.layout.add_widget(self.text_output)
        
        self.recognizing = False  # 音声認識の状態を示すフラグ
        self.recognition_thread = None
        return self.layout
    
    def start_recognition(self, instance):
        if self.recognizing:
            return
        self.recognizing = True
        self.start_button.text = '会話中…'
        self.stop_button.disabled = False
        self.text_output.text = '音声認識を開始しました…'
        self.recognition_thread = threading.Thread(target=self.recognize_and_respond)
        self.recognition_thread.start()
    
    def stop_recognition(self, instance):
        self.recognizing = False
        if self.recognition_thread is not None:
            self.recognition_thread.join()
            Clock.schedule_once(lambda dt: self.update_text("\n音声認識を中止しました。\n"))
            Clock.schedule_once(self.reset_buttons)

    def recognize_and_respond(self):
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()

        while self.recognizing:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source)
                self.update_status("音声認識中…")
                try:
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=6)
                    text = recognizer.recognize_google(audio, language='ja-JP')
                    Clock.schedule_once(lambda dt: self.update_text(f"\nわたし: {text}\n"))
                    self.update_status("応答中…")
                    response = self.get_gpt_response(text)
                    Clock.schedule_once(lambda dt: self.update_text(f"GPT-3: {response}\n"))
                    self.speak_voicevox(response)
                except sr.RequestError:
                    Clock.schedule_once(lambda dt: self.update_text("\n音声認識エラー: APIが利用できません"))
                except sr.UnknownValueError:
                    Clock.schedule_once(lambda dt: self.update_text("\n音声認識エラー: 音声を認識できませんでした"))
                    text = ""
                except UnboundLocalError:
                    text = ""
                

            if re.search(r'またね[。\.]*$', text.strip()):
                self.recognizing = False
        
        Clock.schedule_once(self.reset_buttons)


    def get_gpt_response(self, text):
        messages.append({"role": "user", "content": text})
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150,
        )
        res = response.choices[0].message.content
        messages.append({"role": "assistant", "content": res})
        return res

    def speak_voicevox(self, text):
        vv = Voicevox()
        audio_content = vv.speak(text)
        if audio_content:
            with open("response.wav", "wb") as f:
                f.write(audio_content)
            os.system("afplay response.wav")

    def update_text(self, new_text):
        self.text_output.text += new_text

    def update_status(self, new_status):
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', new_status))

    def reset_buttons(self, dt):
        self.start_button.text = '会話を始める！'
        self.stop_button.disabled = True
        self.update_status("準備完了！")


if __name__ == '__main__':
    voiceGPT().run()
