import random
import logging
from collections import deque
from typing import List, Tuple, Optional
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers

from config import RLConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tf.get_logger().setLevel(logging.ERROR)


class ReplayBuffer:
    def __init__(self, capacity: int):
        self.buffer = deque(maxlen=capacity)

    def push(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool
    ):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int) -> List[Tuple]:
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))

    def __len__(self) -> int:
        return len(self.buffer)


class DQNetwork(tf.keras.Model):
    def __init__(self, state_dim: int, action_dim: int, hidden_size: int = 256):
        super(DQNetwork, self).__init__()
        
        self.fc1 = layers.Dense(hidden_size, activation='relu')
        self.fc2 = layers.Dense(hidden_size, activation='relu')
        self.fc3 = layers.Dense(hidden_size // 2, activation='relu')
        self.fc4 = layers.Dense(action_dim)
        
        self.state_dim = state_dim
        self.action_dim = action_dim

    def call(self, state: tf.Tensor) -> tf.Tensor:
        x = self.fc1(state)
        x = self.fc2(x)
        x = self.fc3(x)
        return self.fc4(x)

    def build_graph(self):
        x = tf.keras.Input(shape=(self.state_dim,))
        return models.Model(inputs=[x], outputs=self.call(x))


class DQNAgent:
    def __init__(self, state_dim: int, action_dim: int, config: RLConfig):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.config = config
        
        self.device = '/GPU:0' if tf.config.list_physical_devices('GPU') else '/CPU:0'
        logger.info(f"Using device: {self.device}")
        
        with tf.device(self.device):
            self.policy_net = DQNetwork(state_dim, action_dim, config.hidden_size)
            self.target_net = DQNetwork(state_dim, action_dim, config.hidden_size)
            
            dummy_input = tf.random.normal((1, state_dim))
            self.policy_net(dummy_input)
            self.target_net(dummy_input)
            
            self.optimizer = optimizers.Adam(learning_rate=config.learning_rate)
        
        self.replay_buffer = ReplayBuffer(config.memory_capacity)
        
        self.epsilon = config.epsilon_start
        self.epsilon_min = config.epsilon_end
        self.epsilon_decay = config.epsilon_decay
        
        self.gamma = config.gamma
        self.batch_size = config.batch_size
        self.target_update_freq = config.target_update_freq
        
        self.steps_done = 0
        self.episode_rewards = []

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        if training and random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        
        with tf.device(self.device):
            state_tensor = tf.convert_to_tensor(state, dtype=tf.float32)
            state_tensor = tf.expand_dims(state_tensor, 0)
            q_values = self.policy_net(state_tensor)
            return int(tf.argmax(q_values[0]).numpy())

    def update_target_network(self):
        self.target_net.set_weights(self.policy_net.get_weights())

    def train_step(self) -> float:
        if len(self.replay_buffer) < self.batch_size:
            return 0.0
        
        batch = self.replay_buffer.sample(self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        states = tf.convert_to_tensor(np.array(states), dtype=tf.float32)
        actions = tf.convert_to_tensor(actions, dtype=tf.int32)
        rewards = tf.convert_to_tensor(rewards, dtype=tf.float32)
        next_states = tf.convert_to_tensor(np.array(next_states), dtype=tf.float32)
        dones = tf.convert_to_tensor(dones, dtype=tf.float32)
        
        with tf.device(self.device):
            with tf.GradientTape() as tape:
                current_q = self.policy_net(states)
                action_indices = tf.stack([tf.range(self.batch_size), actions], axis=1)
                current_q_values = tf.gather_nd(current_q, action_indices)
                
                next_q = self.target_net(next_states)
                max_next_q = tf.reduce_max(next_q, axis=1)
                target_q_values = rewards + (1.0 - dones) * self.gamma * max_next_q
                
                loss = tf.reduce_mean(tf.square(target_q_values - current_q_values))
            
            gradients = tape.gradient(loss, self.policy_net.trainable_variables)
            self.optimizer.apply_gradients(zip(gradients, self.policy_net.trainable_variables))
        
        self.steps_done += 1
        
        if self.steps_done % self.target_update_freq == 0:
            self.update_target_network()
        
        return float(loss.numpy())

    def decay_epsilon(self):
        self.epsilon = max(
            self.epsilon_min,
            self.epsilon * self.epsilon_decay
        )

    def save(self, path: str):
        self.policy_net.save_weights(path + '_policy')
        self.target_net.save_weights(path + '_target')
        logger.info(f"Model saved to {path}")

    def load(self, path: str):
        self.policy_net.load_weights(path + '_policy')
        self.target_net.load_weights(path + '_target')
        logger.info(f"Model loaded from {path}")

    def get_q_values(self, state: np.ndarray) -> np.ndarray:
        with tf.device(self.device):
            state_tensor = tf.convert_to_tensor(state, dtype=tf.float32)
            state_tensor = tf.expand_dims(state_tensor, 0)
            q_values = self.policy_net(state_tensor)
            return q_values.numpy()[0]


class DQNTrainer:
    def __init__(self, agent: DQNAgent, env, config: RLConfig):
        self.agent = agent
        self.env = env
        self.config = config
        
        self.rewards_history = []
        self.loss_history = []
        self.best_reward = float('-inf')

    def train(self, num_episodes: Optional[int] = None) -> dict:
        num_episodes = num_episodes or self.config.num_episodes
        
        logger.info(f"Starting training for {num_episodes} episodes...")
        
        for episode in range(num_episodes):
            state, _ = self.env.reset()
            episode_reward = 0.0
            episode_loss = 0.0
            steps = 0
            
            while True:
                action = self.agent.select_action(state)
                next_state, reward, terminated, truncated, info = self.env.step(action)
                
                self.agent.replay_buffer.push(
                    state, action, reward, next_state, terminated or truncated
                )
                
                loss = self.agent.train_step()
                
                state = next_state
                episode_reward += reward
                episode_loss += loss
                steps += 1
                
                if terminated or truncated:
                    break
            
            self.agent.decay_epsilon()
            
            self.rewards_history.append(episode_reward)
            self.loss_history.append(episode_loss / max(steps, 1))
            
            if episode_reward > self.best_reward:
                self.best_reward = episode_reward
            
            if (episode + 1) % 10 == 0:
                avg_reward = np.mean(self.rewards_history[-10:])
                avg_loss = np.mean(self.loss_history[-10:])
                logger.info(
                    f"Episode {episode + 1}/{num_episodes} | "
                    f"Reward: {episode_reward:.2f} | "
                    f"Avg Reward: {avg_reward:.2f} | "
                    f"Loss: {avg_loss:.4f} | "
                    f"Epsilon: {self.agent.epsilon:.4f} | "
                    f"Steps: {steps}"
                )
        
        logger.info("Training completed!")
        
        return {
            'rewards': self.rewards_history,
            'losses': self.loss_history,
            'best_reward': self.best_reward
        }

    def evaluate(self, num_episodes: int = 5) -> dict:
        logger.info(f"Evaluating for {num_episodes} episodes...")
        
        total_rewards = []
        final_states = []
        
        for episode in range(num_episodes):
            state, _ = self.env.reset()
            episode_reward = 0.0
            steps = 0
            
            while True:
                action = self.agent.select_action(state, training=False)
                next_state, reward, terminated, truncated, info = self.env.step(action)
                
                state = next_state
                episode_reward += reward
                steps += 1
                
                if terminated or truncated:
                    break
            
            total_rewards.append(episode_reward)
            final_states.append(info)
        
        avg_reward = np.mean(total_rewards)
        logger.info(f"Evaluation complete. Average reward: {avg_reward:.2f}")
        
        return {
            'avg_reward': avg_reward,
            'rewards': total_rewards,
            'final_states': final_states
        }


class IndexRecommender:
    def __init__(self, agent: DQNAgent, candidate_map: dict):
        self.agent = agent
        self.candidate_map = candidate_map
        self.reverse_map = {v: k for k, v in candidate_map.items()}

    def recommend(self, state: np.ndarray, top_k: int = 5) -> List[dict]:
        q_values = self.agent.get_q_values(state)
        
        top_indices = np.argsort(q_values)[::-1][:top_k]
        
        recommendations = []
        for idx in top_indices:
            if idx < len(self.candidate_map):
                table, columns = self.candidate_map[idx]
                recommendations.append({
                    'table': table,
                    'columns': columns,
                    'q_value': float(q_values[idx]),
                    'action_index': idx
                })
        
        return recommendations

    def recommend_from_env(self, env, top_k: int = 5) -> List[dict]:
        state, _ = env.reset()
        return self.recommend(state, top_k)
