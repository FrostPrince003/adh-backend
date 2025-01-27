import fitz  # PyMuPDF
import cv2  # OpenCV for contour detection in images
import numpy as np
import io
from PIL import Image
# from pptx import Presentation
# from docx import Document
import os

def detect_contours_in_image(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Simply return the count of contours found without cropping
    return len(contours)


def extract_images_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    image_paths = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images = page.get_images(full=True)
        
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            img_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))
            
            image_path = f"E:/adh-backend/app/routers/images/pdf_image_{page_num+1}_{img_index+1}.{img_ext}"
            image.save(image_path)
            image_paths.append(image_path)
    return image_paths


def detect_contours_in_image(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Simply return the count of contours found without cropping
    return len(contours)    


image_paths = extract_images_from_pdf(input(r"Enter the Path to PDF"))