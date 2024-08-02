import os
import tkinter as tk
import math
import threading
import google.generativeai as genai
from gtts import gTTS
import pygame
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import speech_recognition as sr
import logging
import webbrowser
from bs4 import BeautifulSoup
import requests

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up the Gemini API key
os.environ['GOOGLE_API_KEY'] = 'YOUR_API_KEY_HERE'  # Replace with your actual API key
genai.configure(api_key="AIzaSyB1O-hY0DPcHhV_w4_awdYVgp-m6EQZmQE")
model = genai.GenerativeModel('gemini-1.5-flash')

# Initialize sentence transformer model for encoding
try:
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    logging.error(f"Failed to initialize SentenceTransformer: {e}")
    sentence_model = None

class MemoryStore:
    def __init__(self, max_memory=100, preloaded_memories=None):
        self.max_memory = max_memory
        self.memories = []
        self.embeddings = []

        if preloaded_memories:
            for memory in preloaded_memories:
                self.add_memory(memory)

    def add_memory(self, text):
        if len(self.memories) >= self.max_memory:
            self.memories.pop(0)
            self.embeddings.pop(0)

        self.memories.append(text)
        if sentence_model:
            try:
                embedding = sentence_model.encode([text])[0]
                self.embeddings.append(embedding)
            except Exception as e:
                logging.error(f"Failed to encode memory: {e}")
        else:
            logging.warning("SentenceTransformer not initialized. Skipping embedding.")

    def get_relevant_memories(self, query, top_k=3):
        if not self.memories or not self.embeddings:
            return []

        if not sentence_model:
            logging.warning("SentenceTransformer not initialized. Returning random memories.")
            return np.random.choice(self.memories, min(top_k, len(self.memories)), replace=False).tolist()

        try:
            query_embedding = sentence_model.encode([query])[0]
            similarities = cosine_similarity([query_embedding], self.embeddings)[0]
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            return [self.memories[i] for i in top_indices]
        except Exception as e:
            logging.error(f"Error in get_relevant_memories: {e}")
            return []

class JarvisUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Chitti")
        self.master.geometry("500x500")
        self.master.configure(bg='black')

        self.canvas = tk.Canvas(self.master, width=500, height=500, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.label = tk.Label(self.master, text="CHITTI", font=("Arial", 24, "bold"), fg="#00BFFF", bg="black")
        self.label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.text_output = tk.Text(self.master, height=5, bg='black', fg='#00BFFF', font=("Arial", 10))
        self.text_output.place(relx=0.5, rely=0.85, anchor=tk.CENTER, width=400)

        self.entry_text = tk.Entry(self.master, width=50, bg="#333333", fg="white")
        self.entry_text.place(relx=0.5, rely=0.8, anchor=tk.CENTER)

        self.submit_button = tk.Button(self.master, text="Ask Chitti", command=self.get_user_input, bg="#00BFFF", fg="black")
        self.submit_button.place(relx=0.8, rely=0.8, anchor=tk.CENTER)

        self.voice_button = tk.Button(self.master, text="Speak to Chitti", command=self.get_voice_input, bg="#00BFFF", fg="black")
        self.voice_button.place(relx=0.2, rely=0.8, anchor=tk.CENTER)

        self.angle = 0
        self.inner_rotation = 0
        self.wave_phase = 0
        self.wave_animation_running = False
        self.animate()

        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init()
        except Exception as e:
            logging.error(f"Failed to initialize pygame mixer: {e}")

        # Initialize memory store with pre-trained data
        pretrained_data = [
            "User: What is the weather like today?\nChitti: The weather is sunny and warm with a slight breeze.",
            "User: Who won the football match last night?\nChitti: The home team won with a score of 2-1.",
            "User: Can you play some music?\nChitti: Sure, I can play your favorite songs.",
            # Add more pre-trained conversation pairs here...
        ]

        self.memory_store = MemoryStore(preloaded_memories=pretrained_data)

    def animate(self):
        try:
            self.canvas.delete("all")  # Clear the canvas
            center_x, center_y = 250, 250
            radius = 200

            # Draw outer circle
            self.canvas.create_oval(50, 50, 450, 450, outline="#009ACD", width=2)

            # Draw rotating arc
            start_angle = self.angle - 30
            end_angle = self.angle + 30
            self.canvas.create_arc(50, 50, 450, 450, start=start_angle, extent=60,
                                   outline="#00BFFF", width=5, style=tk.ARC)

            # Draw inner rotating circles
            for i in range(3):
                angle = math.radians(self.inner_rotation + i * 120)
                x = center_x + (radius - 40) * math.cos(angle)
                y = center_y + (radius - 40) * math.sin(angle)
                self.canvas.create_oval(x-20, y-20, x+20, y+20, fill="#00BFFF", outline="")

            # Draw additional details
            for i in range(0, 360, 30):
                angle = math.radians(i)
                start_x = center_x + (radius - 10) * math.cos(angle)
                start_y = center_y + (radius - 10) * math.sin(angle)
                end_x = center_x + radius * math.cos(angle)
                end_y = center_y + radius * math.sin(angle)
                self.canvas.create_line(start_x, start_y, end_x, end_y, fill="#009ACD")

            # Draw wave animation in the center
            if self.wave_animation_running:
                self.draw_wave(center_x, center_y, radius // 2, self.wave_phase)
                self.wave_phase += 5

            self.angle = (self.angle + 10) % 360
            self.inner_rotation = (self.inner_rotation + 5) % 360
            self.master.after(50, self.animate)
        except Exception as e:
            logging.error(f"Error in animate method: {e}")

    def draw_wave(self, center_x, center_y, radius, phase):
        wave_amplitude = 20
        wave_length = 50
        wave_colors = ['#FF4500', '#FFD700', '#ADFF2F', '#00BFFF', '#8A2BE2']

        for i in range(-radius, radius + 1, 2):
            angle = (i + phase) % 360
            y = center_y + wave_amplitude * math.sin(math.radians(angle) * wave_length)
            color = wave_colors[(i // 2) % len(wave_colors)]
            self.canvas.create_line(center_x + i, y, center_x + i + 2, y, fill=color, width=2)

    def start_wave_animation(self):
        self.wave_animation_running = True

    def stop_wave_animation(self):
        self.wave_animation_running = False

    def get_user_input(self):
        user_input = self.entry_text.get()
        if user_input.startswith("browse "):
            url = user_input.split(" ", 1)[1]
            self.browse(url)
        else:
            self.process_input(user_input)
        self.entry_text.delete(0, tk.END)

    def get_voice_input(self):
        threading.Thread(target=self.recognize_speech).start()

    def recognize_speech(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                self.start_wave_animation()
                self.text_output.insert(tk.END, "Listening...\n")
                audio = recognizer.listen(source)
                self.text_output.insert(tk.END, "Processing voice input...\n")
                text = recognizer.recognize_google(audio)
                self.text_output.insert(tk.END, f"You (voice): {text}\n")
                self.process_input(text)
            except sr.UnknownValueError:
                self.text_output.insert(tk.END, "Sorry, I did not understand that.\n")
            except sr.RequestError as e:
                self.text_output.insert(tk.END, f"Could not request results; {e}\n")
            finally:
                self.stop_wave_animation()

    def process_input(self, text):
        try:
            self.text_output.delete(1.0, tk.END)
            self.text_output.insert(tk.END, f"You: {text}\n")
            
            # Retrieve relevant memories
            relevant_memories = self.memory_store.get_relevant_memories(text)
            context = "\n".join(relevant_memories) if relevant_memories else "No previous context available."

            # Include relevant memories in the prompt
            prompt = f"Context from previous conversations:\n{context}\n\nUser: {text}\nChitti:"
            response = model.generate_content(prompt)
            ai_response = response.text

            self.text_output.insert(tk.END, f"Chitti: {ai_response}\n")
            
            # Add the interaction to memory
            self.memory_store.add_memory(f"User: {text}\nChitti: {ai_response}")
            
            # Speak the response
            threading.Thread(target=self.speak_text, args=(ai_response,)).start()
        except Exception as e:
            error_message = f"Error processing input: {e}"
            self.text_output.insert(tk.END, f"{error_message}\n")
            logging.error(error_message)

    def speak_text(self, text):
        try:
            self.start_wave_animation()
            tts = gTTS(text=text, lang='en')
            tts.save("response.mp3")
            pygame.mixer.music.load("response.mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except Exception as e:
            error_message = f"Error in speak_text method: {e}"
            self.text_output.insert(tk.END, f"{error_message}\n")
            logging.error(error_message)
        finally:
            self.stop_wave_animation()

    def browse(self, url):
        logging.debug(f"Opening URL: {url}")
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()
        self.text_output.insert(tk.END, f"Scraped content from {url}:\n{text[:1000]}...")  # Show only first 1000 chars
        self.speak_text(f"Here is some information from the webpage: {text[:200]}")  # Speak first 200 chars

if __name__ == "__main__":
    root = tk.Tk()
    app = JarvisUI(root)
    root.mainloop()
