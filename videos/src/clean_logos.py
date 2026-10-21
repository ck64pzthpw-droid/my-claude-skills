#!/usr/bin/env python3
# Removes Luban branding from the source photos used in the ads (Polina: their logo must never appear).
import cv2, numpy as np, os
IMG = os.environ.get("IMG_DIR", "/mnt/project-files/site/img"); OUT = os.path.dirname(os.path.abspath(__file__)) + "/refs/clean"
# hero-s70: small emblem above the door handle and the brand line under "S70"
im = cv2.imread(IMG + "/hero-s70.jpg"); m = np.zeros(im.shape[:2], np.uint8)
cv2.rectangle(m, (318, 268), (368, 298), 255, -1); cv2.rectangle(m, (318, 345), (358, 362), 255, -1)
cv2.imwrite(OUT + "/hero-s70.jpg", cv2.inpaint(im, m, 5, cv2.INPAINT_TELEA), [cv2.IMWRITE_JPEG_QUALITY, 95])
# s70-kitchen: lit "Lubancabin" lettering on the black wall strip
im = cv2.imread(IMG + "/s70-kitchen.jpg"); x0, y0, x1, y1 = 170, 690, 560, 910
roi = im[y0:y1, x0:x1].astype(int)
mm = ((roi[..., 0] - roi[..., 2] > 25) & (roi[..., 0] > 80)).astype(np.uint8) * 255      # the lettering is lit blue
# keep only the strip itself (dark band), not the lit wall above it
mm = cv2.dilate(mm, np.ones((11, 11), np.uint8)); m = np.zeros(im.shape[:2], np.uint8); m[y0:y1, x0:x1] = mm
band = np.zeros_like(m); pts = np.array([[150, 800], [580, 690], [600, 760], [600, 930], [150, 960]]); cv2.fillPoly(band, [pts], 255)
m &= band
cv2.imwrite(OUT + "/s70-kitchen.jpg", cv2.inpaint(im, m, 7, cv2.INPAINT_TELEA), [cv2.IMWRITE_JPEG_QUALITY, 95])
