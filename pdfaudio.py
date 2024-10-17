#!/usr/bin/env python3

import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path
from datetime import timedelta

import fitz  # PyMuPDF
from pydub import AudioSegment
from tqdm import tqdm

# Import Tkinter for file dialog
try:
    from tkinter import Tk
    from tkinter.filedialog import askopenfilename
except ImportError:
    # Handle environments without Tkinter
    Tk = None
    askopenfilename = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def parse_arguments():
    parser = argparse.ArgumentParser(description='Convert a PDF book into an audiobook.')
    parser.add_argument('pdf_file', nargs='?', help='Path to the PDF file.')
    parser.add_argument('--start-page', type=int, default=1, help='TOC start page number.')
    parser.add_argument('--end-page', type=int, default=5, help='TOC end page number.')
    parser.add_argument('--content-start-page', type=int, default=6, help='Content start page number.')
    parser.add_argument('--output-folder', type=str, default='output', help='Folder to store output files.')
    parser.add_argument('--voice', type=str, default='en', help='Voice code to use for speech (default is "en").')
    parser.add_argument('--rate', type=int, default=170, help='Speech rate (default is 170 words per minute).')
    parser.add_argument('--volume', type=int, default=100, help='Volume level (0 to 200, default is 100).')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging.')
    return parser.parse_args()


def setup_logging(verbose):
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


def extract_toc_from_pdf(pdf_file, start_page, end_page):
    """
    Extracts the table of contents from specified pages of a PDF file.

    Args:
        pdf_file (str): Path to the PDF file.
        start_page (int): Starting page number (1-indexed).
        end_page (int): Ending page number (1-indexed).

    Returns:
        str: Extracted TOC text.
    """
    try:
        pdf = fitz.open(pdf_file)
    except Exception as e:
        logging.error(f"Error opening PDF file: {e}")
        sys.exit(1)

    toc_text = ""
    for page_num in range(start_page - 1, end_page):
        try:
            page = pdf.load_page(page_num)
            toc_text += page.get_text()
            logging.debug(f"Extracted text from page {page_num + 1}")
        except Exception as e:
            logging.error(f"Error extracting text from page {page_num + 1}: {e}")

    logging.info("TOC extraction complete.")
    return toc_text


def parse_toc(toc_text):
    """
    Parses the TOC text to identify chapters.

    Args:
        toc_text (str): Extracted TOC text.

    Returns:
        list: List of chapter titles.
    """
    logging.info("Analyzing the table of contents for chapters...")
    lines = toc_text.splitlines()
    chapters = []

    for line in lines:
        line = line.strip()
        if len(line) > 0:
            chapters.append(line)

    logging.info(f"Identified {len(chapters)} chapters.")
    return chapters


def extract_chapter_texts(pdf_file, chapters, content_start_page):
    """
    Extracts text for each chapter from the PDF.

    Args:
        pdf_file (str): Path to the PDF file.
        chapters (list): List of chapter titles.
        content_start_page (int): Starting page number for content (1-indexed).

    Returns:
        list: List of tuples containing chapter titles and their corresponding text.
    """
    logging.info("Extracting the content for each chapter from the PDF...")
    pdf = fitz.open(pdf_file)
    total_pages = pdf.page_count
    extracted_chapters = []

    # Map chapters to their starting pages
    chapter_pages = {}

    logging.info("Mapping chapters to their starting pages...")
    for page_num in tqdm(range(content_start_page - 1, total_pages), desc="Scanning pages"):
        page = pdf.load_page(page_num)
        text = page.get_text()
        for chapter in chapters:
            if chapter in text and chapter not in chapter_pages:
                chapter_pages[chapter] = page_num
                logging.debug(f"Found chapter '{chapter}' on page {page_num + 1}")

    # Sort chapters based on their starting pages
    sorted_chapters = sorted(chapter_pages.items(), key=lambda x: x[1])

    # Extract text for each chapter
    for idx, (chapter, start_page) in enumerate(sorted_chapters):
        end_page = total_pages
        if idx + 1 < len(sorted_chapters):
            end_page = sorted_chapters[idx + 1][1]
        chapter_text = ""
        for page_num in range(start_page, end_page):
            page = pdf.load_page(page_num)
            chapter_text += page.get_text()
        extracted_chapters.append((chapter, chapter_text))
        logging.info(f"Extracted text for chapter '{chapter}' from pages {start_page + 1} to {end_page}")

    logging.info("Chapter content extraction completed.")
    return extracted_chapters


def save_chapters(extracted_chapters, text_folder):
    """
    Saves each chapter's text into individual text files.

    Args:
        extracted_chapters (list): List of tuples containing chapter titles and text.
        text_folder (Path): Path to the folder where text files will be saved.
    """
    logging.info("Saving chapters into individual text files...")
    for idx, (chapter_title, chapter_text) in enumerate(extracted_chapters):
        safe_title = ''.join(c for c in chapter_title if c.isalnum() or c in (' ', '_')).rstrip()
        file_name = text_folder / f"chapter_{idx + 1}_{safe_title}.txt"
        try:
            with open(file_name, "w", encoding='utf-8') as text_file:
                text_file.write(chapter_text)
            logging.debug(f"Saved chapter '{chapter_title}' to '{file_name}'")
        except Exception as e:
            logging.error(f"Error saving chapter '{chapter_title}': {e}")
    logging.info("All chapters saved successfully.")


def text_to_speech(args):
    """
    Converts text to speech using eSpeak via subprocess.

    Args:
        args (tuple): Contains text_file (Path), audio_file (Path), voice (str), rate (int), volume (int)
    """
    text_file, audio_file, voice, rate, volume = args
    try:
        with open(text_file, "r", encoding='utf-8') as f:
            text = f.read()

        logging.info(f"Converting '{text_file}' to audio using eSpeak...")

        # Prepare the text file for eSpeak
        temp_text_file = text_file.parent / "temp_text.txt"
        with open(temp_text_file, "w", encoding='utf-8') as f:
            f.write(text)

        # Prepare the command for eSpeak
        temp_wav_file = audio_file.with_suffix('.wav')
        command = [
            'espeak',
            '-v', voice,
            '-s', str(rate),
            '-a', str(volume),
            '-f', str(temp_text_file),
            '-w', str(temp_wav_file)
        ]

        # Execute the command
        subprocess.run(command, check=True)

        # Convert WAV to MP3
        audio_segment = AudioSegment.from_wav(temp_wav_file)
        audio_segment.export(audio_file, format="mp3")

        # Remove temporary files
        temp_wav_file.unlink()
        temp_text_file.unlink()

        logging.info(f"Audio saved: {audio_file}")

    except Exception as e:
        logging.error(f"Error converting text to speech for '{text_file}': {e}")
        # Remove the problematic audio file if it exists
        if audio_file.exists():
            audio_file.unlink()
        # Re-raise the exception to stop further processing if needed
        raise


def create_chapters_metadata(audio_files, output_folder):
    """
    Creates a metadata file with chapter timings in ffmetadata format.

    Args:
        audio_files (list): List of audio file paths.
        output_folder (Path): Path to the output folder.

    Returns:
        list: List of valid audio files
    """
    logging.info("Generating metadata for chapters...")
    chapters_txt = output_folder / "chapters.txt"
    try:
        with open(chapters_txt, "w", encoding='utf-8') as chapter_file:
            # Write ffmetadata header
            chapter_file.write(";FFMETADATA1\n\n")
            time_in_ms = 0
            valid_audio_files = []
            for idx, audio_file in enumerate(audio_files):
                if not audio_file.exists():
                    logging.warning(f"Audio file '{audio_file}' does not exist. Skipping.")
                    continue
                try:
                    audio = AudioSegment.from_mp3(audio_file)
                except Exception as e:
                    logging.error(f"Error reading audio file '{audio_file}': {e}")
                    continue
                duration_ms = len(audio)
                chapter_name = audio_file.stem
                chapter_file.write("[CHAPTER]\n")
                chapter_file.write("TIMEBASE=1/1000\n")
                chapter_file.write(f"START={time_in_ms}\n")
                time_in_ms += duration_ms
                chapter_file.write(f"END={time_in_ms}\n")
                chapter_file.write(f"title={chapter_name}\n\n")
                valid_audio_files.append(audio_file)
            if not valid_audio_files:
                logging.error("No valid audio files found for metadata creation.")
                sys.exit(1)
        logging.info("Chapter metadata created.")
        return valid_audio_files  # Return only the valid audio files
    except Exception as e:
        logging.error(f"Error creating chapter metadata: {e}")
        sys.exit(1)


def merge_audio_with_chapters(audio_files, output_folder):
    """
    Merges audio files into a single audiobook with chapters.

    Args:
        audio_files (list): List of valid audio file paths.
        output_folder (Path): Path to the output folder.
    """
    if not audio_files:
        logging.error("No valid audio files available for merging.")
        sys.exit(1)

    logging.info("Combining audio files into a single audiobook with chapters...")

    # Create a list file for ffmpeg to concatenate audio
    filelist_path = output_folder / "filelist.txt"
    try:
        with open(filelist_path, "w", encoding='utf-8') as f:
            for audio_file in audio_files:
                # Escape single quotes in file paths
                file_path = str(audio_file.resolve()).replace("'", "'\\''")
                f.write(f"file '{file_path}'\n")
        logging.debug(f"File list for concatenation saved to '{filelist_path}'")
    except Exception as e:
        logging.error(f"Error creating file list for concatenation: {e}")
        sys.exit(1)

    # Merge audio using ffmpeg
    output_audio = output_folder / "audiobook.mp3"
    command_concat = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", str(filelist_path),
        "-c", "copy", str(output_audio)
    ]
    logging.info(f"Merging audio files into '{output_audio}'...")
    run_ffmpeg_command(command_concat)

    # Apply chapter metadata
    chapters_txt = output_folder / "chapters.txt"
    final_output = output_folder / "audiobook_with_chapters.mp3"
    command_metadata = [
        "ffmpeg", "-i", str(output_audio), "-i", str(chapters_txt),
        "-map_metadata", "1", "-id3v2_version", "3", "-codec", "copy", str(final_output)
    ]
    logging.info("Applying chapter metadata...")
    run_ffmpeg_command(command_metadata)

    logging.info(f"Audiobook created with chapters: '{final_output}'")


def run_ffmpeg_command(command):
    """
    Runs an ffmpeg command and checks for errors.

    Args:
        command (list): List of command arguments.
    """
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg command failed: {e}")
        sys.exit(1)


def process_pdf_to_audiobook(args):
    """
    Main function to process the PDF and create the audiobook.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    pdf_file = Path(args.pdf_file)
    if not pdf_file.is_file():
        logging.error(f"PDF file '{pdf_file}' does not exist.")
        sys.exit(1)

    output_folder = Path(args.output_folder)
    text_folder = output_folder / "text_files"
    audio_folder = output_folder / "audio_files"

    # Create necessary directories
    text_folder.mkdir(parents=True, exist_ok=True)
    audio_folder.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract TOC from known pages
    toc_text = extract_toc_from_pdf(pdf_file, args.start_page, args.end_page)

    # Step 2: Parse TOC and identify chapters
    chapters = parse_toc(toc_text)

    if not chapters:
        logging.error("No chapters were identified. Please adjust the TOC parsing logic.")
        sys.exit(1)

    # Step 3: Extract and save chapter texts
    extracted_chapters = extract_chapter_texts(pdf_file, chapters, args.content_start_page)
    save_chapters(extracted_chapters, text_folder)

    # Step 4: Convert each chapter to audio
    text_files = sorted(text_folder.glob("*.txt"))
    audio_files = []
    tasks = []

    for text_file in text_files:
        audio_file = audio_folder / f"{text_file.stem}.mp3"
        audio_files.append(audio_file)
        tasks.append((text_file, audio_file, args.voice, args.rate, args.volume))

    logging.info("Converting chapters to audio using eSpeak...")
    try:
        # Process chapters sequentially
        for task in tqdm(tasks, total=len(tasks), desc="Converting to speech"):
            text_to_speech(task)
    except Exception as e:
        logging.error(f"An error occurred during text-to-speech conversion: {e}")
        logging.info("Terminating the process due to critical error.")
        sys.exit(1)

    if not any(audio_file.exists() for audio_file in audio_files):
        logging.error("No audio files were generated. Something went wrong in the conversion step.")
        sys.exit(1)

    # Step 5: Create chapter metadata
    audio_files = create_chapters_metadata(audio_files, output_folder)

    # Step 6: Merge all audio files into a single audiobook
    merge_audio_with_chapters(audio_files, output_folder)

    logging.info("Process complete! All audio and text files are organized in the corresponding folders.")
    logging.info(f"Audiobook available at: '{output_folder / 'audiobook_with_chapters.mp3'}'")


def main():
    args = parse_arguments()

    setup_logging(args.verbose)

    if not args.pdf_file:
        # Check if Tkinter is available
        if Tk is None or askopenfilename is None:
            logging.error("Tkinter is not available. Please install Tkinter or specify the PDF file as an argument.")
            sys.exit(1)
        logging.info("No PDF file specified, opening file dialog...")
        try:
            Tk().withdraw()  # Hide the root window
            downloads_folder = os.path.expanduser("~/Downloads")
            pdf_file_path = askopenfilename(title="Select PDF file", initialdir=downloads_folder,
                                            filetypes=[("PDF files", "*.pdf")])
            if not pdf_file_path:
                logging.error("No file selected. Exiting.")
                sys.exit(1)
            args.pdf_file = pdf_file_path
        except Exception as e:
            logging.error(f"Error opening file dialog: {e}")
            sys.exit(1)

    process_pdf_to_audiobook(args)


if __name__ == "__main__":
    main()
