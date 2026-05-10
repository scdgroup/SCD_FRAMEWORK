import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.animation import FuncAnimation
import pandas as pd
import os
import argparse
import seaborn as sns
import numpy as np
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
from config.env_config import Config

LOG_FILE_EPISODE = os.path.join(Config.OUTPUT_DIR_MODEL, "training_log.csv")
LOG_FILE_STEP = os.path.join(Config.OUTPUT_DIR_MODEL, "step_log.csv")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        default="episode",
        choices=["episode", "step"],
        help="Visualization mode",
    )
    return parser.parse_args()


args = parse_args()
MODE = args.mode
LOG_FILE = LOG_FILE_EPISODE if MODE == "episode" else LOG_FILE_STEP

if MODE == "episode":
    fig_ep = plt.figure("Episode Performance", figsize=(12, 10))
    anim_fig = fig_ep
else:
    fig_step_main = plt.figure("Step Performance & Logs", figsize=(12, 9))
    fig_step_dist = plt.figure("Attack Distribution", figsize=(10, 7))
    fig_step_heat = plt.figure("Alert Density Analysis", figsize=(10, 7))
    anim_fig = fig_step_main


def animate(i):
    if not os.path.exists(LOG_FILE):
        return []
    try:
        df = pd.read_csv(LOG_FILE)
    except:
        return []
    if df.empty:
        return []
    if MODE == "episode":
        update_episode_mode(df)
    else:
        update_step_mode(df)
    return []


def update_episode_mode(df):
    plt.figure(fig_ep.number)
    plt.clf()
    fig_ep.suptitle("Cyber RL Episode Training Monitor", fontsize=16, fontweight="bold")
    gs = fig_ep.add_gridspec(3, 1, hspace=0.4)
    x = df["episode"]
    ax1 = fig_ep.add_subplot(gs[0, 0])
    ax1.plot(x, df["reward"], color="#2ecc71", marker="o", markersize=4, alpha=0.6)
    if len(df) > 5:
        ax1.plot(
            x,
            df["reward"].rolling(window=5).mean(),
            color="#27ae60",
            linewidth=2,
            label="Trend",
        )
    ax1.set_title("Episode Rewards", fontweight="bold")
    ax1.set_ylabel("Total Reward")
    ax2 = fig_ep.add_subplot(gs[1, 0])
    ax2.fill_between(x, df["epsilon"], color="#3498db", alpha=0.2)
    ax2.plot(x, df["epsilon"], color="#2980b9", linewidth=2)
    ax2.set_title("Exploration Rate (Epsilon)", fontweight="bold")
    ax2.set_ylabel("Epsilon")
    ax3 = fig_ep.add_subplot(gs[2, 0])
    ax3.bar(x, df["alerts"], color="#e74c3c", alpha=0.7)
    ax3.set_title("IDS Alerts Detected", fontweight="bold")
    ax3.set_ylabel("Alert Count")
    ax3.set_xlabel("Episode Number")
    if len(df) > 20:
        for ax in (ax1, ax2, ax3):
            ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=15))


def update_step_mode(df):
    plt.figure(fig_step_main.number)
    plt.clf()
    fig_step_main.suptitle(
        "Step Performance & Live Logs", fontsize=15, fontweight="bold"
    )
    gs_main = fig_step_main.add_gridspec(3, 1, height_ratios=[1, 1, 0.8], hspace=0.5)
    x_steps = range(len(df))
    ax1 = fig_step_main.add_subplot(gs_main[0, 0])
    ax1.plot(x_steps, df["reward"], color="#2ecc71", alpha=0.4)
    if len(df) > 20:
        ax1.plot(
            x_steps,
            df["reward"].rolling(window=20).mean(),
            color="#27ae60",
            linewidth=2,
        )
    ax1.set_title("Live Step Reward", fontweight="bold")
    ax1.set_ylabel("Reward")
    ax2 = fig_step_main.add_subplot(gs_main[1, 0])
    success_rate = df["success"].expanding().mean() * 100
    ax2.plot(x_steps, success_rate, color="#f1c40f", linewidth=2)
    ax2.fill_between(x_steps, success_rate, color="#f1c40f", alpha=0.1)
    ax2.set_title("Overall Success Rate (%)", fontweight="bold")
    ax2.set_ylabel("Success %")
    ax2.set_ylim(-5, 105)
    if len(df) > 3:
        locator = MaxNLocator(nbins=12)
        ax1.xaxis.set_major_locator(locator)
        ax2.xaxis.set_major_locator(locator)
    ax_log = fig_step_main.add_subplot(gs_main[2, 0])
    ax_log.axis("off")
    recent = df.tail(5)
    log_text = "--- LIVE EVENT LOG (Latest Actions) ---\n"
    for _, row in recent.iterrows():
        attack = row.get("attack_name", "dns_recon")
        log_text += f"Ep {int(row['episode'])} Step {int(row['step'])} | {str(attack)[:10]:<10} | R: {row['reward']:>5.2f} | Al: {int(row['alerts'])}\n"
    ax_log.text(
        0.5,
        0.5,
        log_text,
        transform=ax_log.transAxes,
        ha="center",
        va="center",
        fontsize=11,
        family="monospace",
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.5",
            facecolor="#ffffff",
            alpha=1.0,
            edgecolor="#2c3e50",
        ),
    )

    plt.figure(fig_step_dist.number)
    plt.clf()
    if "attack_name" in df.columns and len(df["attack_name"].unique()) > 0:
        sns.boxplot(
            x="attack_name",
            y="reward",
            data=df,
            palette="Set2",
            hue="attack_name",
            legend=False,
        )
        plt.title("Reward Distribution by Attack Type", fontsize=14, fontweight="bold")
        plt.xticks(rotation=20)
        plt.xlabel("")
    else:
        plt.text(0.5, 0.5, "Waiting for data...", ha="center", va="center")

    plt.figure(fig_step_heat.number)
    plt.clf()
    if len(df["episode"].unique()) >= 1:
        pivot_df = df.pivot_table(
            index="attack_name", columns="episode", values="alerts", aggfunc="sum"
        ).fillna(0)
        if pivot_df.shape[1] > 15:
            pivot_df = pivot_df.iloc[:, -15:]
        sns.heatmap(
            pivot_df, cmap="YlOrRd", cbar_kws={"label": "Alerts"}, annot=True, fmt=".0f"
        )
        plt.title(
            "Alert Density Heatmap (Recent Episodes)", fontsize=14, fontweight="bold"
        )
        plt.xlabel("Episode Number")
        plt.ylabel("Attack Type")
    else:
        plt.text(
            0.5, 0.5, "Waiting for episodes to complete...", ha="center", va="center"
        )


def main():
    try:
        sns.set_theme(style="whitegrid")
    except:
        plt.style.use("ggplot")
    print(f"[*] Launching Multi-Window Monitor ({MODE.upper()})...")
    ani = FuncAnimation(anim_fig, animate, interval=2000, cache_frame_data=False)
    plt.show()


if __name__ == "__main__":
    main()
