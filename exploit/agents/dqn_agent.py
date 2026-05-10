import numpy as np
import random
import tensorflow as tf
import os
import pickle
import json
from collections import deque


class DQNAgent:
    def __init__(self, state_size, config):
        self.state_size = state_size
        self.config = config
        self.action_size = config.total_action_size
        self.memory = deque(maxlen=20000)

        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = (
            0.998  # Slower decay to ensure more exploration across all attack types
        )
        self.learning_rate = 0.0005
        self.tau = 0.005

        self.model = self._build_model()
        self.target_model = self._build_model()
        self.update_target_model_hard()

    def _build_model(self):
        model = tf.keras.Sequential(
            [
                tf.keras.layers.Input(shape=(self.state_size,)),
                tf.keras.layers.Dense(512, activation="relu"),
                tf.keras.layers.LayerNormalization(),
                tf.keras.layers.Dense(256, activation="relu"),
                tf.keras.layers.LayerNormalization(),
                tf.keras.layers.Dense(128, activation="relu"),
                tf.keras.layers.Dense(self.action_size, activation="linear"),
            ]
        )
        optimizer = tf.keras.optimizers.Adam(
            learning_rate=self.learning_rate, clipnorm=1.0
        )
        model.compile(loss=tf.keras.losses.Huber(), optimizer=optimizer)
        return model

    def act(self, state, epsilon=None):
        if epsilon is None:
            epsilon = self.epsilon
        if np.random.rand() <= epsilon:
            return random.randrange(self.action_size)
        q_values = self.model.predict(state.reshape(1, -1), verbose=0)
        return int(np.argmax(q_values[0]))

    def remember(self, state, action_idx, reward, next_state, done):
        self.memory.append((state, action_idx, reward, next_state, done))

    def replay(self, batch_size=64):
        if len(self.memory) < batch_size:
            return
        minibatch = random.sample(self.memory, batch_size)
        states = np.array([m[0] for m in minibatch])
        actions = np.array([m[1] for m in minibatch])
        rewards = np.array([m[2] for m in minibatch])
        next_states = np.array([m[3] for m in minibatch])
        dones = np.array([m[4] for m in minibatch])

        targets = self.model.predict(states, verbose=0)
        target_next_q = self.target_model.predict(next_states, verbose=0)
        model_next_q = self.model.predict(next_states, verbose=0)

        for i in range(len(minibatch)):
            if dones[i]:
                targets[i][actions[i]] = rewards[i]
            else:
                best_next_action = np.argmax(model_next_q[i])
                targets[i][actions[i]] = (
                    rewards[i] + self.gamma * target_next_q[i][best_next_action]
                )

        self.model.fit(states, targets, epochs=1, verbose=0)
        self.update_target_model_soft()
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def update_target_model_soft(self):
        model_weights = self.model.get_weights()
        target_weights = self.target_model.get_weights()
        new_weights = [
            self.tau * m + (1 - self.tau) * t
            for m, t in zip(model_weights, target_weights)
        ]
        self.target_model.set_weights(new_weights)

    def update_target_model_hard(self):
        self.target_model.set_weights(self.model.get_weights())

    def save_checkpoint(self, folder, episode):
        training_results_dir = os.path.join(folder, "training_results")
        os.makedirs(training_results_dir, exist_ok=True)
        model_path = os.path.join(training_results_dir, f"dqn_model_ep{episode}.keras")
        self.model.save(model_path)
        memory_path = os.path.join(training_results_dir, f"dqn_memory_ep{episode}.pkl")
        with open(memory_path, "wb") as f:
            pickle.dump(self.memory, f)
        epsilon_path = os.path.join(
            training_results_dir, f"dqn_epsilon_ep{episode}.json"
        )
        with open(epsilon_path, "w") as f:
            json.dump({"epsilon": self.epsilon}, f)
        print(f"[+] Checkpoint saved for episode {episode}")

    def load_checkpoint(self, model_path, memory_path, epsilon_path):
        if os.path.exists(model_path):
            self.model = tf.keras.models.load_model(model_path)
            self.target_model = tf.keras.models.load_model(model_path)
        if os.path.exists(memory_path):
            with open(memory_path, "rb") as f:
                self.memory = pickle.load(f)
        if os.path.exists(epsilon_path):
            with open(epsilon_path, "r") as f:
                data = json.load(f)
                self.epsilon = data.get("epsilon", self.epsilon)
        print(f"[*] Checkpoint loaded successfully.")

    def load(self, model_path):
        if os.path.exists(model_path):
            self.model = tf.keras.models.load_model(model_path)
            self.target_model = tf.keras.models.load_model(model_path)
            print(f"[*] Model loaded successfully from {model_path}")
            return True
        return False
