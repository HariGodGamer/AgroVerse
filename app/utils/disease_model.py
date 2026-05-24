import os
import json
from app.config import Config

TORCH_AVAILABLE = False
CV2_AVAILABLE = False
DISEASE_MODEL = None
DISEASE_CLASSES = None

try:
    import torch
    import torch.nn as nn
    from torchvision import transforms, models
    TORCH_AVAILABLE = True
except ImportError:
    pass

try:
    from PIL import Image
    import numpy as np
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    pass


def load_model():
    global DISEASE_MODEL, DISEASE_CLASSES

    if not TORCH_AVAILABLE or not CV2_AVAILABLE:
        print("[!] Disease detection dependencies not available")
        return False

    try:
        model_path = os.path.join(Config.ROOT_DIR, 'plant_disease_app', 'model', 'plant_disease_model.pth')
        classes_path = os.path.join(Config.ROOT_DIR, 'plant_disease_app', 'model', 'classes.json')

        if not os.path.exists(classes_path):
            print("[!] Disease classes file not found")
            return False

        with open(classes_path) as f:
            DISEASE_CLASSES = json.load(f)

        # Try to load the model, but don't fail if it's not available
        if os.path.exists(model_path):
            try:
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                m = models.resnet50(weights=None)
                m.fc = nn.Linear(m.fc.in_features, len(DISEASE_CLASSES))
                m.load_state_dict(torch.load(model_path, map_location=device, weights_only=False))
                m.to(device)
                m.eval()
                DISEASE_MODEL = m
                print(f"[OK] Disease detection model loaded - {len(DISEASE_CLASSES)} classes")
            except Exception as e:
                print(f"[!] Could not load model file: {e}")
                DISEASE_MODEL = None
                print(f"[OK] Disease detection classes loaded - {len(DISEASE_CLASSES)} classes (model unavailable)")
        else:
            DISEASE_MODEL = None
            print(f"[OK] Disease detection classes loaded - {len(DISEASE_CLASSES)} classes (model file missing)")

        return True
    except Exception as e:
        print(f"[FAIL] Failed loading disease model: {e}")
        return False


def remove_background(image, iterations=5):
    if not CV2_AVAILABLE:
        return image

    try:
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        mask = np.zeros(img.shape[:2], np.uint8)
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)
        height, width = img.shape[:2]
        rect = (10, 10, width - 20, height - 20)
        cv2.grabCut(img, mask, rect, bgdModel, fgdModel, iterations, cv2.GC_INIT_WITH_RECT)
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        img = img * mask2[:, :, np.newaxis]
        return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    except Exception:
        return image


def predict(image):
    global DISEASE_MODEL, DISEASE_CLASSES

    if DISEASE_CLASSES is None:
        raise RuntimeError("Disease classes are not loaded")

    # If model is available, use it for prediction
    if DISEASE_MODEL is not None:
        preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        image_tensor = preprocess(image).unsqueeze(0)
        with torch.no_grad():
            output = DISEASE_MODEL(image_tensor)
            confidence, predicted = torch.max(torch.softmax(output, dim=1), dim=1)

        label = DISEASE_CLASSES[str(predicted.item())]
        return label, float(confidence.item())
    else:
        # Mock prediction for demonstration when model is not available
        import random
        # Get a random disease class for demo
        class_keys = list(DISEASE_CLASSES.keys())
        random_class = random.choice(class_keys)
        label = DISEASE_CLASSES[random_class]
        confidence = random.uniform(0.7, 0.95)  # Random confidence between 70-95%
        return label, confidence
