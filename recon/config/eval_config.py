import os
from config.env_config import Config


class EvalConfig:
    def __init__(self):
        # Network Settings for Evaluation
        self.TARGET_IP = Config.TARGET_DOMAIN
        self.INTERFACE = Config.INTERFACE

        # Evaluation Run Settings
        self.DEFAULT_EPISODES = 2
        self.DEFAULT_MAX_STEPS = 5

        # Output Directory
        self.OUTPUT_DIR = Config.OUTPUT_DIR
        self.OUTPUT_DIR_MODEL = Config.OUTPUT_DIR_MODEL
        # Files for Universal Evaluator
        self.DETAILED_LOG_FILE = "detailed_eval_logs.csv"
        self.SUMMARY_LOG_FILE = "summary_eval_logs.json"

        # Files for Buffer Analyzer
        self.BUFFER_ANALYSIS_FILE = "buffer_analysis.csv"
        self.BUFFER_SUMMARY_FILE = "buffer_summary.json"

        # Files for Model Inspector
        self.MODEL_KNOWLEDGE_FILE = "model_knowledge.json"

        # Default Model and Buffer Paths (تم التصحيح)
        self.DEFAULT_MODEL_PATH = os.path.join(
            Config.OUTPUT_DIR_MODEL, "dqn_model_ep20.keras"
        )
        self.DEFAULT_BUFFER_PATH = os.path.join(
            Config.OUTPUT_DIR_MODEL, "dqn_memory_ep20.pkl"
        )  # كان خطأ سابقاً
        # Ensure output directories exist
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR_MODEL, exist_ok=True)

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
