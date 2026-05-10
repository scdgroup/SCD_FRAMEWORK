import matplotlib.pyplot as plt
import pandas as pd
import os
import numpy as np
import seaborn as sns
from config.env_config import Config


class TrainingMonitor:
    def __init__(self, save_dir=None):
        self.save_dir = save_dir or Config.OUTPUT_DIR_MODEL
        os.makedirs(self.save_dir, exist_ok=True)
        self.log_file = os.path.join(self.save_dir, "training_log.csv")
        self.step_log_file = os.path.join(self.save_dir, "step_log.csv")

        # إنشاء ملفات جديدة بالرؤوس إذا لم تكن موجودة
        if not os.path.exists(self.log_file):
            pd.DataFrame(
                columns=["episode", "reward", "epsilon", "alerts", "success"]
            ).to_csv(self.log_file, index=False)
        if not os.path.exists(self.step_log_file):
            pd.DataFrame(
                columns=[
                    "episode",
                    "step",
                    "reward",
                    "alerts",
                    "success",
                    "attack_name",
                ]
            ).to_csv(self.step_log_file, index=False)

        try:
            plt.style.use("seaborn-v0_8-darkgrid")
        except:
            plt.style.use("ggplot")

    def update(self, episode, reward, epsilon, alerts, success):
        entry = pd.DataFrame(
            [[episode, reward, epsilon, alerts, int(success)]],
            columns=["episode", "reward", "epsilon", "alerts", "success"],
        )
        entry.to_csv(self.log_file, mode="a", header=False, index=False)

    def update_step(self, episode, step, reward, alerts, success, attack_name):
        entry = pd.DataFrame(
            [[episode, step, reward, alerts, int(success), attack_name]],
            columns=["episode", "step", "reward", "alerts", "success", "attack_name"],
        )
        entry.to_csv(self.step_log_file, mode="a", header=False, index=False)

    def plot_custom(
        self,
        start_idx=None,
        end_idx=None,
        output_name="custom_dashboard.png",
        mode="episode",
    ):
        """Generate professional training dashboard based on mode (episode or step)."""
        target_file = self.log_file if mode == "episode" else self.step_log_file
        x_axis = "episode" if mode == "episode" else "step_global"
        label_text = "Episode" if mode == "episode" else "Step"

        if not os.path.exists(target_file):
            print(f"[!] No {mode} log file found to plot.")
            return

        df = pd.read_csv(target_file)
        if df.empty:
            print(f"[!] {mode} log file is empty.")
            return

        if mode == "step":
            df["step_global"] = range(1, len(df) + 1)

        # Filter by range
        if start_idx is not None:
            df = df[df[x_axis] >= start_idx]
        if end_idx is not None:
            df = df[df[x_axis] <= end_idx]

        if df.empty:
            print("[!] No data found in the specified range.")
            return

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            f"Cyber RL Training Analysis - {mode.capitalize()} Mode",
            fontsize=20,
            fontweight="bold",
            y=0.98,
        )

        # 1. Reward Progress
        axes[0, 0].plot(df[x_axis], df["reward"], color="#2ecc71", alpha=0.3)
        window = 5 if mode == "episode" else 20
        if len(df) >= window:
            axes[0, 0].plot(
                df[x_axis],
                df["reward"].rolling(window=window).mean(),
                color="#27ae60",
                linewidth=2,
                label=f"Trend (MA-{window})",
            )
        axes[0, 0].set_title(f"{label_text} Rewards", fontsize=14, fontweight="bold")
        axes[0, 0].set_xlabel(label_text)
        axes[0, 0].set_ylabel("Reward")
        axes[0, 0].legend()

        # 2. Specialized Plot
        if mode == "episode":
            axes[0, 1].fill_between(
                df["episode"], df["epsilon"], color="#3498db", alpha=0.2
            )
            axes[0, 1].plot(df["episode"], df["epsilon"], color="#2980b9", linewidth=2)
            axes[0, 1].set_title(
                "Exploration Rate (Epsilon)", fontsize=14, fontweight="bold"
            )
            axes[0, 1].set_xlabel("Episode")
            axes[0, 1].set_ylabel("Epsilon")
        else:
            if "attack_name" in df.columns and not df["attack_name"].isnull().all():
                sns.boxplot(
                    x="attack_name",
                    y="reward",
                    data=df,
                    ax=axes[0, 1],
                    palette="viridis",
                    hue="attack_name",
                    legend=False,
                )
                axes[0, 1].set_title(
                    "Reward Distribution by Attack Type", fontsize=14, fontweight="bold"
                )
                axes[0, 1].set_xlabel("Attack Name")
                axes[0, 1].set_ylabel("Reward")
                plt.setp(axes[0, 1].get_xticklabels(), rotation=45)
            else:
                axes[0, 1].set_title("Reward Distribution (No Data)", fontsize=14)

        # 3. Alert Analysis
        if mode == "step" and "attack_name" in df.columns:
            pivot_df = df.pivot_table(
                index="attack_name", columns="episode", values="alerts", aggfunc="sum"
            ).fillna(0)
            if not pivot_df.empty:
                sns.heatmap(
                    pivot_df,
                    ax=axes[1, 0],
                    cmap="YlOrRd",
                    cbar_kws={"label": "Total Alerts"},
                )
                axes[1, 0].set_title(
                    "Alert Density Heatmap (Attack vs Episode)",
                    fontsize=14,
                    fontweight="bold",
                )
                axes[1, 0].set_xlabel("Episode")
                axes[1, 0].set_ylabel("Attack Type")
            else:
                axes[1, 0].set_title("Alert Analysis (Insufficient Data)", fontsize=14)
        else:
            axes[1, 0].bar(df[x_axis], df["alerts"], color="#e74c3c", alpha=0.6)
            axes[1, 0].set_title(
                f"IDS Alerts per {label_text}", fontsize=14, fontweight="bold"
            )
            axes[1, 0].set_xlabel(label_text)
            axes[1, 0].set_ylabel("Alert Count")

        # 4. Success Rate
        success_rate = df["success"].expanding().mean() * 100
        axes[1, 1].plot(df[x_axis], success_rate, color="#f1c40f", linewidth=2)
        axes[1, 1].fill_between(df[x_axis], success_rate, color="#f1c40f", alpha=0.1)
        axes[1, 1].set_title(
            f"Success Rate (%) per {label_text}", fontsize=14, fontweight="bold"
        )
        axes[1, 1].set_xlabel(label_text)
        axes[1, 1].set_ylabel("Success %")
        axes[1, 1].set_ylim(0, 105)

        plt.tight_layout(rect=(0, 0.03, 1, 0.95))
        plot_path = os.path.join(self.save_dir, output_name)
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"[+] Dashboard saved: {plot_path}")
