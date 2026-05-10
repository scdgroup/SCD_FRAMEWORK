import matplotlib.pyplot as plt
import pandas as pd
import os
import numpy as np
import seaborn as sns
import threading
from config.env_config import Config


class TrainingMonitor:
    _lock = threading.Lock()  # Ensure thread-safe CSV operations

    def __init__(self, save_dir=None):
        self.save_dir = save_dir or Config.OUTPUT_DIR
        training_results_dir = os.path.join(self.save_dir, "training_results")
        os.makedirs(training_results_dir, exist_ok=True)
        self.log_file = os.path.join(training_results_dir, "training_log.csv")
        self.step_log_file = os.path.join(training_results_dir, "step_log.csv")

        # Initialize CSVs with professional structure
        self._init_csv(
            self.log_file, ["episode", "reward", "epsilon", "alerts", "success"]
        )
        self._init_csv(
            self.step_log_file,
            ["episode", "step", "reward", "alerts", "success", "attack_name"],
        )

        try:
            plt.style.use("seaborn-v0_8-darkgrid")
        except:
            plt.style.use("ggplot")

    def _init_csv(self, path, columns):
        if not os.path.exists(path):
            df = pd.DataFrame(columns=columns)
            df.to_csv(path, index=False)

    def update(self, episode, reward, epsilon, alerts, success):
        """Record stats for an episode. Avoids duplicates by checking episode number."""
        with self._lock:
            try:
                df = pd.read_csv(self.log_file)
                # Prevent duplicate entries for the same episode
                if episode in df["episode"].values:
                    df = df[df["episode"] != episode]

                new_entry = pd.DataFrame(
                    {
                        "episode": [episode],
                        "reward": [reward],
                        "epsilon": [epsilon],
                        "alerts": [alerts],
                        "success": [1 if success else 0],
                    }
                )
                df = pd.concat([df, new_entry], ignore_index=True)
                df.sort_values("episode", inplace=True)
                df.to_csv(self.log_file, index=False)
            except Exception as e:
                print(f"[!] Error updating episode log: {e}")

    def update_step(self, episode, step, reward, alerts, success, attack_name):
        """Record stats for a single step. Handles precise episode/step tracking."""
        with self._lock:
            try:
                # For steps, we usually append, but we can clean up the current episode if it's a retry
                # However, typically we just append as steps are sequential.
                entry = pd.DataFrame(
                    {
                        "episode": [episode],
                        "step": [step],
                        "reward": [reward],
                        "alerts": [alerts],
                        "success": [1 if success else 0],
                        "attack_name": [attack_name],
                    }
                )
                entry.to_csv(self.step_log_file, mode="a", header=False, index=False)
            except Exception as e:
                print(f"[!] Error updating step log: {e}")

    def plot_custom(
        self, start_idx=None, end_idx=None, output_name=None, mode="episode"
    ):
        """
        Generate professional training dashboard.
        Strictly separates data and labels based on the chosen mode.
        """
        target_file = self.log_file if mode == "episode" else self.step_log_file
        if not os.path.exists(target_file):
            print(f"[!] No data file found for {mode} mode.")
            return

        with self._lock:
            df = pd.read_csv(target_file)

        if df.empty:
            print(f"[!] {mode} data is empty.")
            return

        # Ensure we are using the correct X-axis and labels
        if mode == "episode":
            x_col = "episode"
            x_label = "Episode Number"
            title_prefix = "Episode-Level"
        else:
            # Create a global step index for continuous plotting
            df["global_step"] = range(1, len(df) + 1)
            x_col = "global_step"
            x_label = "Global Step Index"
            title_prefix = "Step-Level"

        # Filtering
        if start_idx is not None:
            df = df[df[x_col] >= start_idx]
        if end_idx is not None:
            df = df[df[x_col] <= end_idx]

        if df.empty:
            print("[!] No data in selected range.")
            return

        # Default output name if not provided
        if not output_name:
            output_name = f"dashboard_{mode}.png"

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            f"Cyber RL {title_prefix} Performance Analysis",
            fontsize=22,
            fontweight="bold",
            color="#2c3e50",
        )

        # 1. Reward Trends
        axes[0, 0].plot(
            df[x_col], df["reward"], color="#3498db", alpha=0.3, label="Raw"
        )
        ma_window = 5 if mode == "episode" else 50
        if len(df) >= ma_window:
            axes[0, 0].plot(
                df[x_col],
                df["reward"].rolling(window=ma_window).mean(),
                color="#2980b9",
                linewidth=3,
                label=f"MA-{ma_window}",
            )
        axes[0, 0].set_title("Reward Evolution", fontsize=14, fontweight="bold")
        axes[0, 0].set_xlabel(x_label)
        axes[0, 0].set_ylabel("Reward Value")
        axes[0, 0].legend()

        # 2. Mode-Specific Metric
        if mode == "episode":
            # Show Epsilon for Episode mode
            axes[0, 1].plot(df[x_col], df["epsilon"], color="#e67e22", linewidth=2)
            axes[0, 1].fill_between(
                df[x_col], df["epsilon"], color="#e67e22", alpha=0.1
            )
            axes[0, 1].set_title(
                "Exploration (Epsilon) Decay", fontsize=14, fontweight="bold"
            )
            axes[0, 1].set_xlabel("Episode")
            axes[0, 1].set_ylabel("Epsilon")
        else:
            # Show Attack Distribution for Step mode
            if "attack_name" in df.columns:
                sns.boxplot(
                    x="attack_name",
                    y="reward",
                    data=df,
                    ax=axes[0, 1],
                    palette="Set2",
                    hue="attack_name",
                    legend=False,
                )
                axes[0, 1].set_title(
                    "Reward Distribution per Attack", fontsize=14, fontweight="bold"
                )
                axes[0, 1].set_xlabel("Attack Type")
                plt.setp(axes[0, 1].get_xticklabels(), rotation=30)
            else:
                axes[0, 1].set_title("No Attack Data Available", fontsize=14)

        # 3. Alert / Heatmap Analysis
        if mode == "step" and len(df["episode"].unique()) > 1:
            pivot = df.pivot_table(
                index="attack_name", columns="episode", values="alerts", aggfunc="sum"
            ).fillna(0)
            sns.heatmap(
                pivot, ax=axes[1, 0], cmap="Reds", cbar_kws={"label": "Alert Count"}
            )
            axes[1, 0].set_title("Attack Noise Heatmap", fontsize=14, fontweight="bold")
            axes[1, 0].set_xlabel("Episode")
            axes[1, 0].set_ylabel("Attack Type")
        else:
            axes[1, 0].bar(df[x_col], df["alerts"], color="#e74c3c", alpha=0.7)
            axes[1, 0].set_title("IDS Alert Frequency", fontsize=14, fontweight="bold")
            axes[1, 0].set_xlabel(x_label)
            axes[1, 0].set_ylabel("Alerts")

        # 4. Success Progression
        success_pct = df["success"].expanding().mean() * 100
        axes[1, 1].plot(df[x_col], success_pct, color="#27ae60", linewidth=3)
        axes[1, 1].fill_between(df[x_col], success_pct, color="#27ae60", alpha=0.1)
        axes[1, 1].set_title("Cumulative Success Rate", fontsize=14, fontweight="bold")
        axes[1, 1].set_xlabel(x_label)
        axes[1, 1].set_ylabel("Success %")
        axes[1, 1].set_ylim(-5, 105)

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        save_path = os.path.join(self.save_dir, output_name)
        plt.savefig(save_path, dpi=200)
        plt.close()
        print(f"[+] {mode.capitalize()} Dashboard generated: {save_path}")
