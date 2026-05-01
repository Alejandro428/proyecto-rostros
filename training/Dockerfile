FROM tensorflow/tensorflow:2.15.0-gpu

WORKDIR /project/training

RUN pip install --no-cache-dir "numpy<2" scikit-learn

COPY train_age.py .

CMD ["python", "train_age.py"]
