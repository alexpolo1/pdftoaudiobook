import fitz  # PyMuPDF
import pyttsx3
import subprocess
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# Function to extract TOC and split PDF into text by chapter
def extract_toc_and_text(pdf_file):
    # Open the PDF
    pdf = fitz.open(pdf_file)

    # Extract Table of Contents
    toc = pdf.get_toc()
    
    chapters = []
    for i, entry in enumerate(toc):
        chapter_title = entry[1]
        start_page = entry[2] - 1  # Page numbers in PyMuPDF are 0-based
        end_page = toc[i+1][2] - 2 if i+1 < len(toc) else pdf.page_count - 1

        chapter_text = ""
        for page_num in range(start_page, end_page + 1):
            page = pdf.load_page(page_num)
            chapter_text += page.get_text()

        chapters.append((chapter_title, chapter_text))
    
    return chapters

# Function to convert text to speech using pyttsx3
def text_to_speech(text, output_file):
    engine = pyttsx3.init()
    engine.save_to_file(text, output_file)
    engine.runAndWait()

# Function to create chapter metadata
def create_chapters_metadata(chapters):
    with open("chapters.txt", "w") as chapter_file:
        time_in_seconds = 0
        for i, chapter in enumerate(chapters):
            chapter_file.write(f"CHAPTER{i+1:02}={time_in_seconds // 3600:02}:{(time_in_seconds % 3600) // 60:02}:{time_in_seconds % 60:02}.000\n")
            chapter_file.write(f"CHAPTER{i+1:02}NAME={chapter[0]}\n")
            # Adjust this duration based on average length of each chapter (for example, 10 minutes)
            time_in_seconds += 600  # Adjust per chapter length

# Function to merge audio files and apply chapter metadata
def merge_audio_with_chapters(chapter_files):
    # First, concatenate all chapter audio files
    with open("filelist.txt", "w") as f:
        for chapter_file in chapter_files:
            f.write(f"file '{chapter_file}'\n")
    
    # Merge files using ffmpeg
    subprocess.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", "filelist.txt", "-c", "copy", "audiobook.mp3"])

    # Apply chapters metadata
    subprocess.run(["ffmpeg", "-i", "audiobook.mp3", "-i", "chapters.txt", "-map_metadata", "1", "-codec", "copy", "audiobook_with_chapters.mp3"])

# Main function to run the whole process
def process_pdf_to_audiobook():
    # Set the Downloads directory as default
    downloads_folder = os.path.expanduser("~/Downloads")
    
    # Use tkinter to open a file dialog in the Downloads folder
    Tk().withdraw()  # We don't want a full GUI, so keep the root window from appearing
    pdf_file = askopenfilename(title="Select PDF file", initialdir=downloads_folder, filetypes=[("PDF files", "*.pdf")])
    
    if not pdf_file:
        print("No file selected, exiting.")
        return
    
    # Step 1: Extract TOC and Text
    chapters = extract_toc_and_text(pdf_file)

    # Step 2: Convert text to speech for each chapter
    chapter_audio_files = []
    for i, (chapter_title, chapter_text) in enumerate(chapters):
        chapter_audio_file = f"chapter_{i+1}.mp3"
        text_to_speech(chapter_text, chapter_audio_file)
        chapter_audio_files.append(chapter_audio_file)

    # Step 3: Create chapters metadata
    create_chapters_metadata(chapters)

    # Step 4: Merge audio files and add chapters
    merge_audio_with_chapters(chapter_audio_files)

# Example usage
process_pdf_to_audiobook()

# Clean up temporary files (optional)
for file in os.listdir():
    if file.startswith("chapter_") or file == "filelist.txt" or file == "chapters.txt":
        os.remove(file)
