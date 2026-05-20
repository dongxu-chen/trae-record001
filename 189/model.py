import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, LSTM, Dense, Dropout, TimeDistributed, RepeatVector, Concatenate
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from config import Config

tf.random.set_seed(Config.RANDOM_SEED)
np.random.seed(Config.RANDOM_SEED)


class AirQualitySeq2Seq:
    def __init__(self, input_shape, output_shape):
        self.config = Config()
        self.input_shape = input_shape
        self.output_shape = output_shape
        self.model = self._build_seq2seq_model()

    def _build_seq2seq_model(self):
        encoder_inputs = Input(shape=self.input_shape, name='encoder_inputs')

        encoder_lstm1 = LSTM(self.config.LSTM_UNITS[0], return_sequences=True, return_state=True, name='encoder_lstm1')
        encoder_outputs1, state_h1, state_c1 = encoder_lstm1(encoder_inputs)
        encoder_outputs1 = Dropout(self.config.DROPOUT_RATE)(encoder_outputs1)

        encoder_lstm2 = LSTM(self.config.LSTM_UNITS[1], return_sequences=True, return_state=True, name='encoder_lstm2')
        encoder_outputs2, state_h2, state_c2 = encoder_lstm2(encoder_outputs1)
        encoder_outputs2 = Dropout(self.config.DROPOUT_RATE)(encoder_outputs2)

        encoder_lstm3 = LSTM(self.config.LSTM_UNITS[2], return_state=True, name='encoder_lstm3')
        encoder_outputs3, state_h3, state_c3 = encoder_lstm3(encoder_outputs2)
        encoder_outputs3 = Dropout(self.config.DROPOUT_RATE)(encoder_outputs3)

        encoder_states = [state_h3, state_c3]

        repeated_context = RepeatVector(self.output_shape[0])(encoder_outputs3)

        decoder_lstm1 = LSTM(self.config.LSTM_UNITS[2], return_sequences=True, name='decoder_lstm1')
        decoder_outputs1 = decoder_lstm1(repeated_context, initial_state=encoder_states)
        decoder_outputs1 = Dropout(self.config.DROPOUT_RATE)(decoder_outputs1)

        decoder_lstm2 = LSTM(self.config.LSTM_UNITS[1], return_sequences=True, name='decoder_lstm2')
        decoder_outputs2 = decoder_lstm2(decoder_outputs1)
        decoder_outputs2 = Dropout(self.config.DROPOUT_RATE)(decoder_outputs2)

        decoder_lstm3 = LSTM(self.config.LSTM_UNITS[0], return_sequences=True, name='decoder_lstm3')
        decoder_outputs3 = decoder_lstm3(decoder_outputs2)
        decoder_outputs3 = Dropout(self.config.DROPOUT_RATE)(decoder_outputs3)

        decoder_dense1 = TimeDistributed(Dense(64, activation='relu'), name='decoder_dense1')
        decoder_outputs = decoder_dense1(decoder_outputs3)
        decoder_outputs = Dropout(self.config.DROPOUT_RATE)(decoder_outputs)

        decoder_dense2 = TimeDistributed(Dense(self.output_shape[1]), name='decoder_dense2')
        decoder_outputs = decoder_dense2(decoder_outputs)

        model = Model(inputs=encoder_inputs, outputs=decoder_outputs)
        model.compile(
            optimizer=Adam(learning_rate=self.config.LEARNING_RATE),
            loss='mse',
            metrics=['mae']
        )
        return model

    def train(self, X_train, y_train, X_val, y_val, model_path='models/aqi_seq2seq.h5'):
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

        callbacks = [
            EarlyStopping(patience=15, restore_best_weights=True, monitor='val_loss'),
            ModelCheckpoint(model_path, save_best_only=True, monitor='val_loss'),
            ReduceLROnPlateau(factor=0.5, patience=8, min_lr=1e-6, monitor='val_loss')
        ]

        history = self.model.fit(
            X_train, y_train,
            batch_size=self.config.BATCH_SIZE,
            epochs=self.config.EPOCHS,
            validation_data=(X_val, y_val),
            callbacks=callbacks,
            verbose=1
        )
        return history

    def predict(self, X):
        return self.model.predict(X, verbose=0)

    def evaluate(self, X_test, y_test):
        return self.model.evaluate(X_test, y_test, verbose=0)

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.model.save(path)

    @classmethod
    def load(cls, path):
        model = load_model(path, compile=False)
        instance = cls.__new__(cls)
        instance.config = Config()
        instance.model = model
        return instance
