import os
import shutil
import uuid
import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

# =========================
# CONFIGURACIÓN
# =========================

IMG_SIZE    = (256, 320)        # (alto, ancho) — igual que el notebook
BATCH_SIZE  = 32
EPOCHS      = 30
LR          = 0.001
SEED        = 123

# Rutas relativas al propio script para que funcionen desde cualquier directorio
_DIR        = os.path.dirname(os.path.abspath(__file__))
SRC_PATH    = os.path.join(_DIR, "..", "face_age")   # carpeta face_age en la raíz del proyecto
DST_PATH    = os.path.join(_DIR, "dataset_clasificado")
OUTPUT_PATH = os.path.join(_DIR, "modelo_menores.h5")

# =========================
# 1. PREPARAR DATASET
# =========================
# Organiza las carpetas numéricas de face_age en menor/ y mayor/
# según si la edad < 18 o >= 18.

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

# =========================
# 2. CARGAR DATOS
# =========================
# Clases ordenadas alfabéticamente: mayor=0, menor=1
# → score >= 0.5 significa MENOR

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
print("score >= 0.5  →  MENOR\n")

# =========================
# 3. NORMALIZAR Y AUGMENTAR
# =========================

def normalizar(image, label):
    image = tf.cast(image, tf.float32) / 255.0
    label = tf.cast(label, tf.float32)
    return image, label

data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.1),
    layers.RandomZoom(0.1),
])

def augmentar(image, label):
    image = data_augmentation(image, training=True)
    return image, label

AUTOTUNE = tf.data.AUTOTUNE

train_ds = train_ds.map(normalizar).map(augmentar).prefetch(AUTOTUNE)
val_ds   = val_ds.map(normalizar).prefetch(AUTOTUNE)

# =========================
# 4. ARQUITECTURA
# =========================
# CNN personalizada — arquitectura ganadora del notebook (val_acc ~85.7%)
# Ligera, rápida y sin depender de pesos externos.

def build_model(input_shape=(256, 320, 3)) -> Model:
    inp = layers.Input(shape=input_shape)

    # Bloque 1
    x = layers.Conv2D(32, (3, 3), padding="same", activation="relu")(inp)
    x = layers.Conv2D(32, (3, 3), padding="same", activation="relu")(x)
    x = layers.MaxPooling2D()(x)

    # Bloque 2
    x = layers.Conv2D(64, (5, 5), strides=2, padding="same", activation="relu")(x)
    x = layers.MaxPooling2D()(x)

    # Bloque 3
    x = layers.Conv2D(128, (3, 3), padding="same", activation="relu")(x)

    # Clasificador
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(64, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(32, activation="relu")(x)
    out = layers.Dense(1, activation="sigmoid")(x)

    return Model(inputs=inp, outputs=out)


model = build_model(input_shape=(IMG_SIZE[0], IMG_SIZE[1], 3))
model.summary()

# =========================
# 6. COMPILAR Y ENTRENAR
# =========================

model.compile(
    optimizer=tf.keras.optimizers.Adam(LR),
    loss="binary_crossentropy",
    metrics=["accuracy"]
)

callbacks = [
    EarlyStopping(
        monitor="val_accuracy",
        patience=7,
        restore_best_weights=True,
        verbose=1
    ),
    ModelCheckpoint(
        filepath=OUTPUT_PATH,
        monitor="val_accuracy",
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

print("===== ENTRENANDO =====\n")
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks
)

# =========================
# 7. EVALUACIÓN FINAL
# =========================

loss, accuracy = model.evaluate(val_ds)
print(f"\nLoss:     {loss:.4f}")
print(f"Accuracy: {accuracy:.4f}")
print(f"\nModelo guardado en: {OUTPUT_PATH}")
print(f"Clases: {class_names}  →  score >= 0.5 = MENOR (label 1)")
