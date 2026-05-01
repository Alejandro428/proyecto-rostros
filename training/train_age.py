import os
import shutil
import uuid
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input as resnet_preprocess
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from sklearn.utils.class_weight import compute_class_weight

# =========================
# CONFIGURACIÓN
# =========================

IMG_SIZE   = (256, 320)
BATCH_SIZE = 32
EPOCHS_F1  = 20        # fase 1: base congelada
EPOCHS_FT  = 15        # fase 2: fine-tuning
LR         = 0.001
SEED       = 123
THRESHOLD  = 0.40      # score >= THRESHOLD → MENOR

_DIR        = os.path.dirname(os.path.abspath(__file__))
SRC_PATH    = os.path.join(_DIR, "..", "face_age")
DST_PATH    = os.path.join(_DIR, "dataset_clasificado")
OUTPUT_PATH = os.path.join(_DIR, "modelo_menores.h5")

# =========================
# 1. PREPARAR DATASET
# =========================

def clasificar_dataset(src_path: str, dst_path: str):
    os.makedirs(dst_path + "/menor", exist_ok=True)
    os.makedirs(dst_path + "/mayor", exist_ok=True)
    for folder in os.listdir(src_path):
        folder_path = os.path.join(src_path, folder)
        if not os.path.isdir(folder_path) or not folder.isdigit():
            continue
        edad = int(folder)
        destino = "menor" if edad < 18 else "mayor"
        for img in os.listdir(folder_path):
            src_img = os.path.join(folder_path, img)
            if not os.path.isfile(src_img):
                continue
            ext    = os.path.splitext(img)[1].lower()
            nombre = f"{edad}_{uuid.uuid4().hex[:8]}{ext}"
            shutil.copy(src_img, os.path.join(dst_path, destino, nombre))
    menores = len(os.listdir(dst_path + "/menor"))
    mayores = len(os.listdir(dst_path + "/mayor"))
    print(f"Dataset clasificado — menores: {menores} | mayores: {mayores}")

if not os.path.exists(DST_PATH):
    print("Clasificando dataset...")
    clasificar_dataset(SRC_PATH, DST_PATH)
else:
    print("Dataset ya clasificado, usando el existente")

n_menores = len(os.listdir(os.path.join(DST_PATH, "menor")))
n_mayores = len(os.listdir(os.path.join(DST_PATH, "mayor")))
print(f"Distribución — mayores: {n_mayores} | menores: {n_menores}")

labels  = np.array([0] * n_mayores + [1] * n_menores)
weights = compute_class_weight(class_weight="balanced", classes=np.array([0, 1]), y=labels)
class_weight = dict(enumerate(weights))
print(f"class_weight: {class_weight}")

# =========================
# 2. CARGAR DATOS
# =========================
# Sin normalizar — el preprocesado ResNet va dentro del modelo

train_ds = tf.keras.utils.image_dataset_from_directory(
    DST_PATH,
    validation_split=0.2,
    subset="training",
    seed=SEED,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    label_mode="int",
    shuffle=True
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    DST_PATH,
    validation_split=0.2,
    subset="validation",
    seed=SEED,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    label_mode="int",
    shuffle=False
)

class_names = train_ds.class_names
print(f"\nClases: {class_names}  →  label 0='{class_names[0]}', label 1='{class_names[1]}'")
print(f"score >= {THRESHOLD}  →  MENOR\n")

# =========================
# 3. AUGMENTACIÓN
# =========================

data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.1),
    layers.RandomZoom(0.1),
])

def augmentar(image, label):
    image = data_augmentation(image, training=True)
    return image, label

AUTOTUNE = tf.data.AUTOTUNE

def preprocesar(image, label):
    image = resnet_preprocess(tf.cast(image, tf.float32))
    return image, label

train_ds = train_ds.map(augmentar).map(preprocesar).prefetch(AUTOTUNE)
val_ds   = val_ds.map(preprocesar).prefetch(AUTOTUNE)

# =========================
# 4. MODELO ResNet50
# =========================

def build_model():
    base_model = ResNet50(
        weights="imagenet",
        include_top=False,
        input_shape=(IMG_SIZE[0], IMG_SIZE[1], 3)
    )
    base_model.trainable = False

    inputs  = layers.Input(shape=(IMG_SIZE[0], IMG_SIZE[1], 3))
    x       = base_model(inputs, training=False)
    x       = layers.GlobalAveragePooling2D()(x)
    x       = layers.Dense(64, activation="relu")(x)
    x       = layers.Dropout(0.3)(x)
    x       = layers.Dense(32, activation="relu")(x)
    outputs = layers.Dense(1, activation="sigmoid")(x)

    return Model(inputs, outputs)

model = build_model()
model.summary()

# =========================
# 5. CALLBACKS
# =========================

def get_callbacks(path):
    return [
        EarlyStopping(
            monitor="val_recall_menor",
            mode="max",
            patience=5,
            restore_best_weights=True,
            verbose=1
        ),
        ModelCheckpoint(
            filepath=path,
            monitor="val_recall_menor",
            mode="max",
            save_best_only=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=3,
            min_lr=1e-7,
            verbose=1
        )
    ]

# =========================
# 6. FASE 1 — base congelada
# =========================

recall_menor = tf.keras.metrics.Recall(thresholds=THRESHOLD, name="recall_menor")

model.compile(
    optimizer=tf.keras.optimizers.Adam(LR),
    loss="binary_crossentropy",
    metrics=["accuracy", recall_menor]
)

path_fase1 = OUTPUT_PATH.replace(".h5", "_fase1.h5")
print("===== FASE 1 — ResNet50 base congelada =====\n")
model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS_F1,
    callbacks=get_callbacks(path_fase1),
    class_weight=class_weight,
)

# =========================
# 7. FASE 2 — fine-tuning
# =========================

base = model.get_layer("resnet50")
base.trainable = True

fine_tune_from = len(base.layers) - 30
for layer in base.layers[:fine_tune_from]:
    layer.trainable = False

print(f"\nCapas entrenables en ResNet50: {sum(1 for l in base.layers if l.trainable)} de {len(base.layers)}")

model.compile(
    optimizer=tf.keras.optimizers.Adam(LR / 10),
    loss="binary_crossentropy",
    metrics=["accuracy", tf.keras.metrics.Recall(thresholds=THRESHOLD, name="recall_menor")]
)

print("===== FASE 2 — Fine-tuning últimas 30 capas =====\n")
model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS_FT,
    callbacks=get_callbacks(OUTPUT_PATH),
    class_weight=class_weight,
)

# =========================
# 8. EVALUACIÓN FINAL
# =========================

loss, accuracy, recall = model.evaluate(val_ds)
print(f"\nLoss:         {loss:.4f}")
print(f"Accuracy:     {accuracy:.4f}")
print(f"Recall MENOR: {recall:.4f}")
print(f"\nModelo guardado en: {OUTPUT_PATH}")
print(f"Fase 1 guardada en: {path_fase1}")
print(f"Clases: {class_names}  →  score >= {THRESHOLD} = MENOR (label 1)")
