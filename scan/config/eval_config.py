import os
from config.env_config import Config


class EvalConfig:
    def __init__(self):
        # Network Settings for Evaluation
        self.TARGET_IP = Config.TARGET_IP
        self.INTERFACE = Config.INTERFACE

        # Evaluation Run Settings
        self.DEFAULT_EPISODES = Config.DEFAULT_EPISODES
        self.DEFAULT_MAX_STEPS = Config.DEFAULT_MAX_STEPS

        # Output Directory (English Name)
        # self.OUTPUT_DIR = "/var/log/scdlogs/test_results"
        self.OUTPUT_DIR = "/var/log/scdlogs/scan"
        self.OUTPUT_DIR_MODEL = os.path.join(self.OUTPUT_DIR, "training_results")
        # Files for Universal Evaluator
        self.DETAILED_LOG_FILE = "detailed_eval_logs.csv"
        self.SUMMARY_LOG_FILE = "summary_eval_logs.json"

        # Files for Buffer Analyzer
        self.BUFFER_ANALYSIS_FILE = "buffer_analysis.csv"
        self.BUFFER_SUMMARY_FILE = "buffer_summary.json"

        # Files for Model Inspector
        self.MODEL_KNOWLEDGE_FILE = "model_knowledge.json"

        # Default Model and Buffer Paths
        self.DEFAULT_MODEL_PATH = os.path.join(
            self.OUTPUT_DIR_MODEL, "dqn_model_ep60.keras"
        )
        self.DEFAULT_BUFFER_PATH = os.path.join(
            self.OUTPUT_DIR_MODEL, "dqn_memory_ep60.pkl"
        )

        # Ensure output directory exists
        if not os.path.exists(self.OUTPUT_DIR):
            os.makedirs(self.OUTPUT_DIR)
        if not os.path.exists(self.OUTPUT_DIR_MODEL):
            os.makedirs(self.OUTPUT_DIR_MODEL)

    @property
    def csv_path(self):
        return os.path.join(self.OUTPUT_DIR, self.DETAILED_LOG_FILE)

    @property
    def json_path(self):
        return os.path.join(self.OUTPUT_DIR, self.SUMMARY_LOG_FILE)

    @property
    def buffer_csv_path(self):
        return os.path.join(self.OUTPUT_DIR, self.BUFFER_ANALYSIS_FILE)

    @property
    def buffer_json_path(self):
        return os.path.join(self.OUTPUT_DIR, self.BUFFER_SUMMARY_FILE)

    @property
    def model_knowledge_path(self):
        return os.path.join(self.OUTPUT_DIR, self.MODEL_KNOWLEDGE_FILE)
