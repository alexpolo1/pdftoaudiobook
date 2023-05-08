import os
import tkinter as tk
from tkinter import filedialog
import pygame
import pyttsx3
import PyPDF2

# Global variable to store the current chapter number
current_chapter = 1
output_dir = "audiobook"

def get_audio(text, output_file_name):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # Adjust the speech rate to a slower value
    engine.setProperty('volume', 1.0)  # Set the volume to maximum
    engine.save_to_file(text, output_file_name)
    engine.runAndWait()

def pdf_to_audiobook(pdf_path, pages_per_chapter=10):
    reader = PyPDF2.PdfReader(pdf_path)
    num_pages = len(reader.pages)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    chapter = 1
    start_page = 0

    while start_page < num_pages:
        end_page = min(start_page + pages_per_chapter, num_pages)
        text = ""

        for page in range(start_page, end_page):
            text += reader.pages[page].extract_text()

        audio_file_name = f"{output_dir}/Chapter_{chapter}.mp3"
        get_audio(text, audio_file_name)
        print(f"Generated: {audio_file_name}")

        chapter += 1
        start_page = end_page

    else:
        print("No bookmarks found in the PDF.")


def play_audio():
    global current_chapter
    pygame.mixer.init()
    audio_file = f"{output_dir}/Chapter_{current_chapter}.mp3"
    if os.path.exists(audio_file):
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
    else:
        print("Audio file not found. Please convert a PDF first.")

def pause_audio():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()

def resume_audio():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.unpause()

def next_chapter():
    global current_chapter
    pygame.mixer.music.stop()
    current_chapter += 1
    play_audio()

def add_bookmark():
    global current_chapter
    bookmark_file = f"{output_dir}/bookmarks.txt"
    with open(bookmark_file, "a") as f:
        f.write(f"Chapter {current_chapter}\n")
    print(f"Bookmark added for Chapter {current_chapter}")

def select_pdf():
    pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
    if pdf_path:
        pdf_to_audiobook(pdf_path)
import tkinter as tk
from tkinter import filedialog
import pygame

def play_audio():
    global current_chapter
    pygame.mixer.init()
    audio_file = f"{output_dir}/Chapter_{current_chapter}.mp3"
    if os.path.exists(audio_file):
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
    else:
        print("Audio file not found. Please convert a PDF first.")

def pause_audio():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()

def resume_audio():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.unpause()

def next_chapter():
    global current_chapter
    pygame.mixer.music.stop()
    current_chapter += 1
    play_audio()

def add_bookmark():
    global current_chapter
    bookmark_file = f"{output_dir}/bookmarks.txt"
    with open(bookmark_file, "a") as f:
        f.write(f"Chapter {current_chapter}\n")
    print(f"Bookmark added for Chapter {current_chapter}")

def select_pdf():
    pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
    if pdf_path:
        pdf_to_audiobook(pdf_path)
        
def create_gui():
    root = tk.Tk()
    root.title("PDF to Audiobook Converter")
    root.geometry("400x200")

    select_button = tk.Button(root, text="Select PDF", command=select_pdf)
    select_button.pack(pady=10)

    play_button = tk.Button(root, text="Play", command=play_audio)
    play_button.pack(side=tk.LEFT, padx=10)

    pause_button = tk.Button(root, text="Pause", command=pause_audio)
    pause_button.pack(side=tk.LEFT, padx=10)

    resume_button = tk.Button(root, text="Resume", command=resume_audio)
    resume_button.pack(side=tk.LEFT, padx=10)

    next_chapter_button = tk.Button(root, text="Next Chapter", command=next_chapter)
    next_chapter_button.pack(side=tk.LEFT, padx=10)

    add_bookmark_button = tk.Button(root, text="Add Bookmark", command=add_bookmark)
    add_bookmark_button.pack(side=tk.LEFT, padx=10)

    root.mainloop()
if __name__ == "__main__":
    create_gui()
